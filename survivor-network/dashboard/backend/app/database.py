"""
PostgreSQL Database Operations - Local Survivor Network
Handles all database interactions for events and participants using SQLAlchemy Async.
"""

import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json

from sqlalchemy import Column, String, Integer, Boolean, DateTime, select, update, delete
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# =============================================================================
# Configuration & Setup
# =============================================================================

# Connection details pointing to your Kind cluster's Data Tier
DB_USER = os.environ.get("DB_USER", "survivor")
DB_PASS = os.environ.get("DB_PASS", "survivor-pw")
DB_HOST = os.environ.get("DB_HOST", "survivor-db-postgresql.data.svc.cluster.local")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "survivor")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the Async Engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory for handling requests
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

Base = declarative_base()

# =============================================================================
# SQLAlchemy Models (The "Everything Store")
# =============================================================================

class Event(Base):
    __tablename__ = "events"
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    participant_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # JSONB stores the flexible attributes (description, max_participants, etc.)
    data = Column(JSONB, default={})

class Participant(Base):
    __tablename__ = "participants"
    participant_id = Column(String, primary_key=True)
    event_code = Column(String, index=True)
    username = Column(String, nullable=False)
    username_lower = Column(String, index=True) # Optimized for check_username_exists
    x = Column(Integer, default=0)
    y = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    # JSONB stores NoSQL-style metadata (levels, inventory, evidence_urls)
    data = Column(JSONB, default={})

class Admin(Base):
    __tablename__ = "admins"
    email = Column(String, primary_key=True)

# =============================================================================
# Event Operations
# =============================================================================

def json_serializable(obj):
    """Helper to convert non-serializable objects to strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

async def get_event(code: str) -> Optional[Dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).where(Event.code == code))
        event = result.scalar_one_or_none()
        if event:
            res = dict(event.data or {})
            res.update({
                "code": event.code, 
                "name": event.name,
                "active": event.active, 
                "participant_count": event.participant_count
            })
            return res
        return None

async def list_events() -> List[Dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event))
        return [
            {**e.data, "code": e.code, "name": e.name, "active": e.active, "participant_count": e.participant_count}
            for e in result.scalars()
        ]

async def create_event(event_data: Dict) -> str:
    async with AsyncSessionLocal() as session:
        code = event_data.get("code")
        name = event_data.get("name")
        
        # Sanitize the dictionary for JSONB
        # This converts any datetime objects to strings
        clean_data = json.loads(
            json.dumps(event_data, default=json_serializable)
        )
        
        new_event = Event(
            code=code,
            name=name,
            data=clean_data
        )
        session.add(new_event)
        await session.commit()
        return code

async def delete_event(code: str) -> None:
    """Soft delete: mark as inactive."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Event).where(Event.code == code).values(active=False)
        )
        await session.commit()

async def increment_participant_count(event_code: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Event)
            .where(Event.code == event_code)
            .values(participant_count=Event.participant_count + 1)
        )
        await session.commit()

# =============================================================================
# Participant Operations
# =============================================================================

async def get_participant(participant_id: str) -> Optional[Dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Participant).where(Participant.participant_id == participant_id)
        )
        p = result.scalar_one_or_none()
        if p:
            res = dict(p.data or {})
            res.update({
                "participant_id": p.participant_id,
                "event_code": p.event_code,
                "username": p.username,
                "x": p.x,
                "y": p.y,
                "active": p.active
            })
            return res
        return None

async def list_participants_by_event(event_code: str) -> List[Dict]:
    async with AsyncSessionLocal() as session:
        # 1. Use .all() to ensure we get the full list of objects
        result = await session.execute(
            select(Participant).where(Participant.event_code == event_code)
        )
        participants = result.scalars().all() # Explicitly fetch all
        
        # 2. Add a debug print to see what's happening in the logs
        print(f"DEBUG: Found {len(participants)} participants for {event_code}")
        
        return [
            {
                **(p.data or {}), 
                "participant_id": p.participant_id, 
                "username": p.username, 
                "x": p.x, 
                "y": p.y,
                "event_code": p.event_code
            }
            for p in participants
        ]
    
async def check_username_exists(event_code: str, username: str) -> bool:
    async with AsyncSessionLocal() as session:
        query = select(Participant).where(
            Participant.event_code == event_code,
            Participant.username_lower == username.lower()
        ).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None

async def create_participant(p_data: dict) -> str:
    async with AsyncSessionLocal() as session:
        # 1. Clean the dictionary so it's JSON serializable
        # This converts the 'created_at' datetime into a string
        p_data["registered_at"] = datetime.now(timezone.utc).isoformat()
        clean_data = json.loads(
            json.dumps(p_data, default=str)
        )

        new_p = Participant(
            participant_id=p_data["participant_id"],
            event_code=p_data["event_code"],
            username=p_data["username"],
            username_lower=p_data["username"].lower(),
            x=p_data.get("x", 0),
            y=p_data.get("y", 0),
            data=clean_data # Use the cleaned version here
        )
        session.add(new_p)
        
        # Ensure you also update the count on the event
        await session.execute(
            update(Event)
            .where(Event.code == p_data["event_code"])
            .values(participant_count=Event.participant_count + 1)
        )
        
        await session.commit()
        return new_p.participant_id

async def update_participant(participant_id: str, updates: Dict) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Participant).where(Participant.participant_id == participant_id)
        )
        p = result.scalar_one_or_none()
        if p:
            # Sync top-level columns if they are in the update
            if "x" in updates: p.x = updates["x"]
            if "y" in updates: p.y = updates["y"]
            if "active" in updates: p.active = updates["active"]
            
            # Merge remaining updates into JSONB blob
            current_data = dict(p.data or {})
            current_data.update(updates)
            p.data = current_data
            
            await session.commit()

# =============================================================================
# Auth Operations
# =============================================================================

async def is_admin(email: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.email == email))
        return result.scalar_one_or_none() is not None
    

async def create_tables():
    async with engine.begin() as conn:
        # This will only create tables that don't exist yet
        await conn.run_sync(Base.metadata.create_all)
    print("🚀 Database tables verified/created.")