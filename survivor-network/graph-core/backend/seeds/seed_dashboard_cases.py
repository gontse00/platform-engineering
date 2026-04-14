"""Seed realistic test cases with GPS coordinates for dashboard testing.

Run inside the graph-core pod:
  python seeds/seed_dashboard_cases.py
"""
import sys
import os
import time
import uuid

sys.path.insert(0, "/app")
os.chdir("/app")

from app.db import SessionLocal
from models.graph import GraphNodeDB, GraphEdgeDB

CASES = [
    {
        "label": "Shelter request - Soweto",
        "urgency": "urgent",
        "status": "open",
        "safety_risk": "medium",
        "queue": "shelter",
        "normalized_location": "Soweto",
        "latitude": -26.2227,
        "longitude": 27.8540,
        "location_consent": True,
        "location_source": "browser",
        "needs": ["Emergency Shelter", "Food"],
        "incident_types": ["Domestic Violence"],
        "summary": "Location: Soweto. Primary need: Emergency Shelter. Latest user message: I need shelter in Soweto",
    },
    {
        "label": "Medical emergency - Soweto",
        "urgency": "critical",
        "status": "open",
        "safety_risk": "high",
        "queue": "medical",
        "normalized_location": "Soweto",
        "latitude": -26.2280,
        "longitude": 27.8610,
        "location_consent": True,
        "location_source": "browser",
        "needs": ["Emergency Medical"],
        "incident_types": ["Assault"],
        "summary": "Location: Soweto. User is injured. Primary need: Emergency Medical. Latest user message: I am injured and need medical help urgently",
    },
    {
        "label": "Legal assistance - Johannesburg CBD",
        "urgency": "critical",
        "status": "open",
        "safety_risk": "medium",
        "queue": "legal",
        "normalized_location": "Johannesburg",
        "latitude": -26.2041,
        "longitude": 28.0473,
        "location_consent": True,
        "location_source": "browser",
        "needs": ["Legal Aid", "Protection Order"],
        "incident_types": ["Sexual Assault"],
        "summary": "CBD area. Survivor needs legal assistance and protection order. Referred by clinic.",
    },
    {
        "label": "Crisis counseling - Meadowlands",
        "urgency": "critical",
        "status": "open",
        "safety_risk": "critical",
        "queue": "crisis",
        "normalized_location": "Soweto",
        "latitude": -26.2195,
        "longitude": 27.8960,
        "location_consent": True,
        "location_source": "browser",
        "needs": ["Crisis Counseling", "Safety Planning"],
        "incident_types": ["Domestic Violence", "Threats"],
        "summary": "Meadowlands area. Survivor in immediate danger, perpetrator nearby. Needs crisis intervention and safety planning.",
    },
    {
        "label": "Support services - Diepsloot",
        "urgency": "urgent",
        "status": "open",
        "safety_risk": "medium",
        "queue": "support",
        "normalized_location": "Diepsloot",
        "latitude": -25.9320,
        "longitude": 28.0180,
        "location_consent": True,
        "location_source": "browser",
        "needs": ["Counseling", "Food", "Transport"],
        "incident_types": ["Community Violence"],
        "summary": "Diepsloot area. Survivor displaced, needs counseling and basic support services.",
    },
    {
        "label": "Shelter request - Pretoria",
        "urgency": "critical",
        "status": "open",
        "safety_risk": "high",
        "queue": "shelter",
        "normalized_location": "Pretoria",
        "latitude": -25.7479,
        "longitude": 28.2293,
        "location_consent": True,
        "location_source": "gps",
        "needs": ["Emergency Shelter", "Medical"],
        "incident_types": ["Human Trafficking"],
        "summary": "Pretoria central. Trafficking survivor. Needs secure shelter and medical attention. SAPS referral pending.",
    },
    {
        "label": "Follow-up case - Orlando West",
        "urgency": "low",
        "status": "open",
        "safety_risk": "low",
        "queue": "follow_up",
        "normalized_location": "Soweto",
        "latitude": -26.2350,
        "longitude": 27.9080,
        "location_consent": True,
        "location_source": "browser",
        "needs": ["Follow-up Counseling"],
        "incident_types": ["Domestic Violence"],
        "summary": "Orlando West. Existing survivor returning for follow-up. Previous shelter placement successful.",
    },
]


def seed():
    db = SessionLocal()
    try:
        existing_labels = {
            n.label
            for n in db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Case").all()
        }
        cases_to_add = [c for c in CASES if c["label"] not in existing_labels]
        if not cases_to_add:
            print(f"Dashboard cases already seeded ({len(existing_labels)} found), skipping.")
            return
        CASES_FILTERED = cases_to_add

        for c in CASES_FILTERED:
            # Create survivor node
            survivor = GraphNodeDB(
                node_type="Survivor",
                label=f"Survivor-{uuid.uuid4().hex[:6]}",
                metadata_json={"message": c["summary"], "channel": "chatbot"},
            )
            db.add(survivor)
            db.flush()

            # Create case node
            case = GraphNodeDB(
                node_type="Case",
                label=c["label"],
                metadata_json={
                    "urgency": c["urgency"],
                    "status": c["status"],
                    "safety_risk": c["safety_risk"],
                    "queue": c["queue"],
                    "normalized_location": c["normalized_location"],
                    "latitude": c["latitude"],
                    "longitude": c["longitude"],
                    "location_consent": c["location_consent"],
                    "location_source": c["location_source"],
                },
            )
            db.add(case)
            db.flush()

            # Create assessment node
            assessment = GraphNodeDB(
                node_type="Assessment",
                label=f"Assessment for {c['label']}",
                metadata_json={
                    "message": c["summary"],
                    "primary_needs": c["needs"],
                    "incident_types": c["incident_types"],
                    "requires_human_review": c["urgency"] in ("critical", "urgent"),
                    "escalation_recommended": c["safety_risk"] in ("high", "critical"),
                },
            )
            db.add(assessment)
            db.flush()

            # Create edges
            db.add(GraphEdgeDB(from_node_id=survivor.id, to_node_id=case.id, edge_type="INVOLVED_IN"))
            db.add(GraphEdgeDB(from_node_id=case.id, to_node_id=assessment.id, edge_type="ASSESSED_AS"))

            # Link to location node if exists
            loc_node = (
                db.query(GraphNodeDB)
                .filter(
                    GraphNodeDB.node_type == "Location",
                    GraphNodeDB.label == c["normalized_location"],
                )
                .first()
            )
            if loc_node:
                db.add(GraphEdgeDB(from_node_id=case.id, to_node_id=loc_node.id, edge_type="LOCATED_IN"))

        db.commit()
        print(f"Seeded {len(CASES_FILTERED)} dashboard test cases with GPS coordinates.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
