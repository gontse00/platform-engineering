"""Tests for agent-service /reason endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestReason:
    def test_basic_reason_request(self):
        resp = client.post("/reason", json={
            "session_id": "test-123",
            "message": "I need help, I was attacked and I don't know where to go",
            "safety_flags": {
                "immediate_danger": False,
                "urgency_floor": "standard",
                "matched_keywords": [],
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "extracted" in data
        assert "triage" in data
        assert "actions" in data
        assert "reply" in data
        assert isinstance(data["reply"]["message"], str)
        assert len(data["reply"]["message"]) > 0

    def test_critical_safety_flags_raise_urgency(self):
        resp = client.post("/reason", json={
            "session_id": "test-456",
            "message": "I'm bleeding badly, someone stabbed me",
            "safety_flags": {
                "immediate_danger": True,
                "urgency_floor": "critical",
                "matched_keywords": ["Active bleeding reported"],
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["triage"]["suggested_urgency"] == "critical"
        assert data["extracted"]["immediate_danger"] is True

    def test_shelter_need_extraction(self):
        resp = client.post("/reason", json={
            "session_id": "test-789",
            "message": "I need shelter in Johannesburg, my partner kicked me out",
            "safety_flags": {
                "immediate_danger": False,
                "urgency_floor": "standard",
                "matched_keywords": [],
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["extracted"]["primary_need"] == "Emergency Shelter"

    def test_mugged_shelter_johannesburg_e2e(self):
        """End-to-end happy path: mugged + shelter + Johannesburg."""
        resp = client.post("/reason", json={
            "session_id": "e2e-001",
            "message": "I was mugged and I need shelter in Johannesburg",
            "safety_flags": {
                "immediate_danger": False,
                "urgency_floor": "standard",
                "matched_keywords": [],
            },
        })
        assert resp.status_code == 200
        data = resp.json()

        # Structured need extracted
        assert data["extracted"]["primary_need"] is not None

        # Location may or may not be extracted in keyword-only mode
        # (LLM mode would extract it reliably)

        # Triage assessed
        assert data["triage"]["suggested_urgency"] in ("standard", "urgent", "high", "critical")

        # Safe empathetic response returned
        assert len(data["reply"]["message"]) > 10

        # Actions suggested
        assert len(data["actions"]) >= 1

    def test_urgency_floor_enforced(self):
        """Agent cannot return urgency below the safety floor."""
        resp = client.post("/reason", json={
            "session_id": "floor-test",
            "message": "I need some advice",
            "safety_flags": {
                "immediate_danger": False,
                "urgency_floor": "urgent",
                "matched_keywords": ["test"],
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        urgency_order = ["standard", "urgent", "high", "critical"]
        assert urgency_order.index(data["triage"]["suggested_urgency"]) >= urgency_order.index("urgent")

    def test_conversation_context_passed(self):
        resp = client.post("/reason", json={
            "session_id": "ctx-test",
            "message": "I also need medical help",
            "conversation_context": {
                "known_location": "Soweto",
                "known_primary_need": "Emergency Shelter",
            },
            "safety_flags": {
                "immediate_danger": False,
                "urgency_floor": "standard",
                "matched_keywords": [],
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "extracted" in data

    def test_empty_message(self):
        resp = client.post("/reason", json={
            "session_id": "empty-test",
            "message": "",
            "safety_flags": {
                "immediate_danger": False,
                "urgency_floor": "standard",
                "matched_keywords": [],
            },
        })
        assert resp.status_code == 200
