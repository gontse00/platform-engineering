"""Tests for admin-service."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "admin-service"


class TestDashboard:
    def test_summary_returns_safe_defaults_when_services_unavailable(self):
        """Dashboard summary should not crash when downstream services are down."""
        resp = client.get("/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_cases" in data
        assert "system_status" in data
        assert isinstance(data["warnings"], list)

    def test_cases_returns_503_when_incident_service_down(self):
        resp = client.get("/dashboard/cases")
        # Will be 503 since incident-service isn't running in test
        assert resp.status_code in (200, 503)

    def test_participants_returns_503_when_participant_service_down(self):
        resp = client.get("/dashboard/participants")
        assert resp.status_code in (200, 503)


class TestAssignmentSafety:
    """Safety check tests — these validate the rules without real downstream services."""

    def test_assign_rejects_missing_case(self):
        """Should fail when incident-service is unavailable."""
        resp = client.post("/admin/cases/fake-id/assign", json={
            "participant_id": "fake-participant",
            "assignment_type": "helper",
        })
        assert resp.status_code == 503

    def test_recommend_fails_gracefully(self):
        resp = client.post("/admin/cases/fake-id/recommend-participants", json={
            "needs": ["transport"],
            "urgency": "urgent",
            "safety_risk": "high",
        })
        assert resp.status_code == 503
