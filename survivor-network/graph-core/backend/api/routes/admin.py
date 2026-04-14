"""Admin API routes for the dashboard.

Provides endpoints for case visibility, resource lookup, real-time
streaming, case status management, and case assignment for the admin dashboard.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from models.graph import GraphEdgeDB, GraphNodeDB
from services.distance_util import haversine_km

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# JWT-style authentication (simple HMAC token)
# ---------------------------------------------------------------------------
# In production, use a proper JWT library.  For this first version we use a
# shared secret: the admin generates a token = HMAC-SHA256(secret, expiry_ts).
# The dashboard sends it as "Authorization: Bearer <token>:<expiry_ts>".
#
# Set via env ADMIN_JWT_SECRET.  If empty/unset, auth is DISABLED (dev mode).
# ---------------------------------------------------------------------------
import os

_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", "")


def _verify_admin_token(authorization: str | None = Header(None)):
    """Dependency that gates admin routes behind a token when configured."""
    if not _JWT_SECRET:
        return  # dev mode — no auth required

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        scheme, token_payload = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError()
        token, expiry_str = token_payload.rsplit(":", 1)
        expiry = int(expiry_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Malformed Authorization header")

    if time.time() > expiry:
        raise HTTPException(status_code=401, detail="Token expired")

    expected = hmac.new(
        _JWT_SECRET.encode(), expiry_str.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid token")


# Apply auth to all admin routes
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(_verify_admin_token)],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class StatusUpdateRequest(BaseModel):
    status: str  # new, in_progress, escalated, resolved


class AddNoteRequest(BaseModel):
    text: str
    author: str = "Admin"


class AssignRequest(BaseModel):
    assigned_to: str  # caseworker node ID


# ---------------------------------------------------------------------------
# Seed caseworkers — created once at startup as CaseWorker graph nodes
# ---------------------------------------------------------------------------
_SEED_CASEWORKERS = [
    "Thandi Mokoena",
    "James Nkosi",
    "Naledi Dlamini",
    "Sipho Mabaso",
    "Lerato Khumalo",
]


def _ensure_seed_caseworkers(db: Session) -> list[GraphNodeDB]:
    """Return all CaseWorker nodes, creating seed data if none exist."""
    existing = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.node_type == "CaseWorker")
        .order_by(GraphNodeDB.label)
        .all()
    )
    if existing:
        return existing

    nodes = []
    for name in _SEED_CASEWORKERS:
        node = GraphNodeDB(
            node_type="CaseWorker",
            label=name,
            metadata_json={"role": "caseworker", "active": True},
        )
        db.add(node)
        nodes.append(node)
    db.commit()
    for n in nodes:
        db.refresh(n)
    return nodes


def _node_dict(node: GraphNodeDB) -> dict:
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "label": node.label,
        "metadata": node.metadata_json or {},
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }


def _build_case_record(db: Session, case_node: GraphNodeDB) -> dict:
    """Build a denormalized case record for the dashboard.

    Joins the Case node with its linked Survivor (INVOLVED_IN),
    Assessment (ASSESSED_AS), and Location (LOCATED_IN) nodes.
    """
    meta = case_node.metadata_json or {}

    # --- linked survivor (Survivor --INVOLVED_IN--> Case) ---
    survivor_edge = (
        db.query(GraphEdgeDB)
        .filter(
            GraphEdgeDB.to_node_id == case_node.id,
            GraphEdgeDB.edge_type == "INVOLVED_IN",
        )
        .first()
    )
    survivor_node = None
    if survivor_edge:
        survivor_node = db.query(GraphNodeDB).get(survivor_edge.from_node_id)

    # --- linked assessment (Case --ASSESSED_AS--> Assessment) ---
    assessment_edge = (
        db.query(GraphEdgeDB)
        .filter(
            GraphEdgeDB.from_node_id == case_node.id,
            GraphEdgeDB.edge_type == "ASSESSED_AS",
        )
        .first()
    )
    assessment_node = None
    assessment_meta: dict = {}
    if assessment_edge:
        assessment_node = db.query(GraphNodeDB).get(assessment_edge.to_node_id)
        if assessment_node:
            assessment_meta = assessment_node.metadata_json or {}

    # --- linked location (Case --LOCATED_IN--> Location) ---
    location_edge = (
        db.query(GraphEdgeDB)
        .filter(
            GraphEdgeDB.from_node_id == case_node.id,
            GraphEdgeDB.edge_type == "LOCATED_IN",
        )
        .first()
    )
    location_node = None
    if location_edge:
        location_node = db.query(GraphNodeDB).get(location_edge.to_node_id)

    # --- build incident summary ---
    incident_summary = assessment_meta.get("message", "")
    if not incident_summary and survivor_node:
        incident_summary = (survivor_node.metadata_json or {}).get("message", "")
    # Truncate for list view, full text available in detail
    incident_summary_short = (
        incident_summary[:120] + "..." if len(incident_summary) > 120 else incident_summary
    )

    # --- build location object ---
    location = None
    lat = meta.get("latitude")
    lon = meta.get("longitude")
    if lat is not None and lon is not None:
        location = {
            "latitude": lat,
            "longitude": lon,
            "location_source": meta.get("location_source", "browser"),
            "accuracy_meters": meta.get("location_accuracy"),
            "is_approximate": meta.get("location_accuracy") is not None
            and meta.get("location_accuracy", 0) > 500,
            "consent_to_share": meta.get("location_consent", True),
            "captured_at": case_node.created_at.isoformat() if case_node.created_at else None,
        }
    elif location_node:
        # Fall back to linked Location node coordinates (suburb-level)
        loc_meta = location_node.metadata_json or {}
        if loc_meta.get("lat") and loc_meta.get("lon"):
            location = {
                "latitude": loc_meta["lat"],
                "longitude": loc_meta["lon"],
                "location_source": "graph_location_node",
                "accuracy_meters": None,
                "is_approximate": True,
                "consent_to_share": True,
                "captured_at": case_node.created_at.isoformat() if case_node.created_at else None,
            }

    # Final fallback: look up normalized_location as a Location node label
    if location is None and meta.get("normalized_location"):
        fallback_loc = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.node_type == "Location",
                GraphNodeDB.label == meta["normalized_location"],
            )
            .first()
        )
        if fallback_loc:
            fb_meta = fallback_loc.metadata_json or {}
            if fb_meta.get("lat") and fb_meta.get("lon"):
                location = {
                    "latitude": fb_meta["lat"],
                    "longitude": fb_meta["lon"],
                    "location_source": "normalized_location_fallback",
                    "accuracy_meters": None,
                    "is_approximate": True,
                    "consent_to_share": True,
                    "captured_at": case_node.created_at.isoformat() if case_node.created_at else None,
                }

    # --- map urgency to dashboard levels ---
    raw_urgency = meta.get("urgency", "standard")
    urgency_map = {
        "critical": "critical",
        "high": "urgent",
        "urgent": "urgent",
        "standard": "normal",
        "low": "low",
    }
    urgency = urgency_map.get(raw_urgency, "normal")

    # --- map status ---
    raw_status = meta.get("status", "open")
    status_map = {
        "open": "new",
        "in_progress": "in_progress",
        "escalated": "escalated",
        "resolved": "resolved",
        "closed": "resolved",
    }
    status = status_map.get(raw_status, "new")

    # --- note count ---
    note_count = (
        db.query(GraphEdgeDB)
        .filter(
            GraphEdgeDB.from_node_id == case_node.id,
            GraphEdgeDB.edge_type == "HAS_NOTE",
        )
        .count()
    )

    # --- assigned caseworker ---
    assigned_to = meta.get("assigned_to")
    assigned_to_name: str | None = None
    if assigned_to:
        cw_node = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.id == assigned_to,
                GraphNodeDB.node_type == "CaseWorker",
            )
            .first()
        )
        if cw_node:
            assigned_to_name = cw_node.label

    return {
        "case_id": str(case_node.id),
        "label": case_node.label,
        "note_count": note_count,
        "incident_summary": incident_summary,
        "incident_summary_short": incident_summary_short,
        "urgency": urgency,
        "raw_urgency": raw_urgency,
        "status": status,
        "raw_status": raw_status,
        "safety_risk": meta.get("safety_risk", "unknown"),
        "queue": meta.get("queue"),
        "created_at": case_node.created_at.isoformat() if case_node.created_at else None,
        "updated_at": case_node.created_at.isoformat() if case_node.created_at else None,
        "location": location,
        "normalized_location": meta.get("normalized_location"),
        "primary_needs": assessment_meta.get("primary_needs", []),
        "incident_types": assessment_meta.get("incident_types", []),
        "requires_human_review": assessment_meta.get("requires_human_review", False),
        "escalation_recommended": assessment_meta.get("escalation_recommended", False),
        "survivor": _node_dict(survivor_node) if survivor_node else None,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name,
    }


@router.get("/cases")
def list_cases(
    status: str | None = Query(None, description="Filter by status: new, in_progress, escalated, resolved"),
    urgency: str | None = Query(None, description="Filter by urgency: low, normal, urgent, critical"),
    has_location: bool | None = Query(None, description="Filter to cases with GPS location"),
    assigned_to: str | None = Query(None, description="Filter by caseworker ID, or 'unassigned' for unassigned cases"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all cases for the admin dashboard.

    Returns denormalized case records with survivor, assessment,
    and location data joined from the graph.
    """
    # Query all Case nodes
    query = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Case")
    query = query.order_by(GraphNodeDB.created_at.desc())

    all_cases = query.all()

    # Build denormalized records
    records = [_build_case_record(db, c) for c in all_cases]

    # Apply filters in Python (small dataset, avoids JSONB query complexity)
    if status:
        records = [r for r in records if r["status"] == status]
    if urgency:
        records = [r for r in records if r["urgency"] == urgency]
    if has_location is True:
        records = [r for r in records if r["location"] is not None]
    elif has_location is False:
        records = [r for r in records if r["location"] is None]
    if assigned_to:
        if assigned_to == "unassigned":
            records = [r for r in records if r["assigned_to"] is None]
        else:
            records = [r for r in records if r["assigned_to"] == assigned_to]

    total = len(records)
    records = records[offset : offset + limit]

    return {
        "cases": records,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/cases/stream")
async def case_stream(request: Request, db: Session = Depends(get_db)):
    """Server-Sent Events stream.

    Pushes updated case list every 5 seconds.  The client compares
    the payload hash to skip re-renders when nothing changed.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        last_hash = ""
        while True:
            if await request.is_disconnected():
                break

            # Re-query cases
            all_cases = (
                db.query(GraphNodeDB)
                .filter(GraphNodeDB.node_type == "Case")
                .order_by(GraphNodeDB.created_at.desc())
                .all()
            )
            records = [_build_case_record(db, c) for c in all_cases]
            payload = json.dumps({"cases": records, "total": len(records)}, default=str)

            current_hash = hashlib.md5(payload.encode()).hexdigest()
            if current_hash != last_hash:
                last_hash = current_hash
                yield f"data: {payload}\n\n"

            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get a single case with full detail."""
    case_node = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.id == case_id, GraphNodeDB.node_type == "Case")
        .first()
    )
    if not case_node:
        raise HTTPException(status_code=404, detail="Case not found")

    return _build_case_record(db, case_node)


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Dashboard summary statistics."""
    all_cases = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Case").all()

    total = len(all_cases)
    by_status: dict[str, int] = {}
    by_urgency: dict[str, int] = {}
    with_location = 0

    for c in all_cases:
        meta = c.metadata_json or {}
        st = meta.get("status", "open")
        by_status[st] = by_status.get(st, 0) + 1

        urg = meta.get("urgency", "standard")
        by_urgency[urg] = by_urgency.get(urg, 0) + 1

        if meta.get("latitude") is not None:
            with_location += 1

    return {
        "total_cases": total,
        "by_status": by_status,
        "by_urgency": by_urgency,
        "with_location": with_location,
    }


# ---------------------------------------------------------------------------
# Feature 1: Nearby resources
# ---------------------------------------------------------------------------

RESOURCE_TYPE_MAP = {
    "public_hospital": "hospital",
    "private_hospital": "hospital",
    "public_clinic": "clinic",
    "clinic": "clinic",
    "pharmacy": "clinic",
    "police_station": "police",
    "shelter": "shelter",
    "crisis_hotline": "hotline",
    "thuthuzela_care_centre": "hospital",
    "counseling_centre": "counseling",
    "ngo": "ngo",
    "legal_aid": "legal",
    "social_facility": "ngo",
    "community_centre": "ngo",
    "fire_station": "hospital",
}


@router.get("/resources/nearby")
def list_nearby_resources(
    lat: float = Query(..., description="Latitude of the center point"),
    lon: float = Query(..., description="Longitude of the center point"),
    radius_km: float = Query(15.0, ge=1, le=100, description="Search radius in km"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    db: Session = Depends(get_db),
):
    """Return resources within radius_km of (lat, lon), sorted by distance."""
    all_resources = (
        db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Resource").all()
    )

    results = []
    for r in all_resources:
        meta = r.metadata_json or {}
        r_lat = meta.get("lat")
        r_lon = meta.get("lon")
        if r_lat is None or r_lon is None:
            continue

        distance = haversine_km(lat, lon, float(r_lat), float(r_lon))
        if distance > radius_km:
            continue

        raw_type = meta.get("type", "")
        mapped_type = RESOURCE_TYPE_MAP.get(raw_type, "other")

        if resource_type and mapped_type != resource_type:
            continue

        results.append({
            "id": str(r.id),
            "name": r.label,
            "type": mapped_type,
            "raw_type": raw_type,
            "latitude": float(r_lat),
            "longitude": float(r_lon),
            "distance_km": round(distance, 2),
            "phone": meta.get("phone", ""),
            "address": meta.get("address", ""),
            "hours": meta.get("hours", ""),
            "services": meta.get("services", []),
        })

    results.sort(key=lambda x: x["distance_km"])
    return {"resources": results, "center": {"lat": lat, "lon": lon}, "radius_km": radius_km}


# ---------------------------------------------------------------------------
# Feature 3: Case status management
# ---------------------------------------------------------------------------

VALID_STATUSES = {"open", "in_progress", "escalated", "resolved"}
DASHBOARD_TO_RAW = {
    "new": "open",
    "in_progress": "in_progress",
    "escalated": "escalated",
    "resolved": "resolved",
}


@router.patch("/cases/{case_id}/status")
def update_case_status(
    case_id: str,
    body: StatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update the workflow status of a case."""
    raw_status = DASHBOARD_TO_RAW.get(body.status, body.status)
    if raw_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    case_node = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.id == case_id, GraphNodeDB.node_type == "Case")
        .first()
    )
    if not case_node:
        raise HTTPException(status_code=404, detail="Case not found")

    meta = dict(case_node.metadata_json or {})
    old_status = meta.get("status", "open")
    meta["status"] = raw_status
    meta["status_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    case_node.metadata_json = meta
    db.commit()

    return {
        "case_id": case_id,
        "old_status": old_status,
        "new_status": raw_status,
        "updated": True,
    }


# ---------------------------------------------------------------------------
# Case assignment
# ---------------------------------------------------------------------------

@router.get("/caseworkers")
def list_caseworkers(db: Session = Depends(get_db)):
    """Return all caseworkers, seeding sample data on first call."""
    workers = _ensure_seed_caseworkers(db)
    return {
        "caseworkers": [
            {"id": str(w.id), "name": w.label}
            for w in workers
        ],
    }


@router.patch("/cases/{case_id}/assign")
def assign_case(
    case_id: str,
    body: AssignRequest,
    db: Session = Depends(get_db),
):
    """Assign a case to a caseworker (or unassign by passing empty string)."""
    case_node = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.id == case_id, GraphNodeDB.node_type == "Case")
        .first()
    )
    if not case_node:
        raise HTTPException(status_code=404, detail="Case not found")

    # Validate caseworker exists (unless unassigning)
    caseworker_name: str | None = None
    if body.assigned_to:
        cw_node = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.id == body.assigned_to,
                GraphNodeDB.node_type == "CaseWorker",
            )
            .first()
        )
        if not cw_node:
            raise HTTPException(status_code=404, detail="Caseworker not found")
        caseworker_name = cw_node.label

    meta = dict(case_node.metadata_json or {})
    if body.assigned_to:
        meta["assigned_to"] = body.assigned_to
        meta["assigned_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    else:
        meta.pop("assigned_to", None)
        meta.pop("assigned_at", None)

    case_node.metadata_json = meta
    db.commit()

    return {
        "case_id": case_id,
        "assigned_to": body.assigned_to or None,
        "assigned_to_name": caseworker_name,
        "assigned_at": meta.get("assigned_at"),
    }


# ---------------------------------------------------------------------------
# Case notes / activity log
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/notes")
def add_case_note(case_id: str, body: AddNoteRequest, db: Session = Depends(get_db)):
    """Add a timestamped note to a case."""
    case_node = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.id == case_id, GraphNodeDB.node_type == "Case")
        .first()
    )
    if not case_node:
        raise HTTPException(status_code=404, detail="Case not found")

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    note_node = GraphNodeDB(
        node_type="CaseNote",
        label=body.text[:50],
        metadata_json={
            "text": body.text,
            "author": body.author,
            "created_at": now_iso,
        },
    )
    db.add(note_node)
    db.flush()  # populate note_node.id

    edge = GraphEdgeDB(
        from_node_id=case_node.id,
        to_node_id=note_node.id,
        edge_type="HAS_NOTE",
    )
    db.add(edge)
    db.commit()

    return {
        "id": str(note_node.id),
        "text": body.text,
        "author": body.author,
        "created_at": now_iso,
    }


@router.get("/cases/{case_id}/notes")
def list_case_notes(case_id: str, db: Session = Depends(get_db)):
    """List all notes for a case, newest first."""
    case_node = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.id == case_id, GraphNodeDB.node_type == "Case")
        .first()
    )
    if not case_node:
        raise HTTPException(status_code=404, detail="Case not found")

    note_edges = (
        db.query(GraphEdgeDB)
        .filter(
            GraphEdgeDB.from_node_id == case_node.id,
            GraphEdgeDB.edge_type == "HAS_NOTE",
        )
        .all()
    )

    note_ids = [e.to_node_id for e in note_edges]
    if not note_ids:
        return {"notes": []}

    note_nodes = (
        db.query(GraphNodeDB)
        .filter(GraphNodeDB.id.in_(note_ids))
        .all()
    )

    notes = []
    for n in note_nodes:
        meta = n.metadata_json or {}
        notes.append({
            "id": str(n.id),
            "text": meta.get("text", ""),
            "author": meta.get("author", "Unknown"),
            "created_at": meta.get("created_at", n.created_at.isoformat() if n.created_at else None),
        })

    # Sort by created_at descending
    notes.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return {"notes": notes}
