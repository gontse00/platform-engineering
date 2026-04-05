"""
Database Initializer - Local Survivor Network
Run this once to create tables in the Postgres Data Tier.
"""
import asyncio
import os
from app.database import engine, Base, Admin, AsyncSessionLocal
from sqlalchemy import select

async def init_db():
    print("Connecting to PostgreSQL in the Data Tier...")
    try:
        async with engine.begin() as conn:
            # Create all tables defined in database.py
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created successfully.")

        # Seed an initial admin for your MacBook access
        async with AsyncSessionLocal() as session:
            admin_email = os.environ.get("ADMIN_EMAIL", "admin@survivor.net")
            result = await session.execute(select(Admin).where(Admin.email == admin_email))
            if not result.scalar_one_or_none():
                session.add(Admin(email=admin_email))
                await session.commit()
                print(f"👤 Seeded admin: {admin_email}")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())