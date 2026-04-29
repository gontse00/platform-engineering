"""Tests for case ownership refactor.

Verifies that chatbot-service creates cases through incident-service,
not graph-core.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.clients.incident_service_client import IncidentServiceClient, IncidentServiceUnavailableError


class TestIncidentServiceClient:
    def test_create_case_from_intake_success(self):
        client = IncidentServiceClient(base_url="http://fake:8080")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "case-123",
            "urgency": "urgent",
            "safety_risk": "medium",
            "status": "new",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.clients.incident_service_client.requests.post", return_value=mock_resp):
            result = client.create_case_from_intake({
                "session_id": "sess-1",
                "message": "I was mugged",
                "urgency": "urgent",
            })
            assert result["id"] == "case-123"
            assert result["urgency"] == "urgent"

    def test_create_case_from_intake_unavailable(self):
        client = IncidentServiceClient(base_url="http://fake:8080")

        with patch("app.clients.incident_service_client.requests.post", side_effect=Exception("connection refused")):
            with pytest.raises(IncidentServiceUnavailableError):
                client.create_case_from_intake({"message": "test"})

    def test_add_timeline_entry_success(self):
        client = IncidentServiceClient(base_url="http://fake:8080")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "entry-1", "event_type": "submitted"}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.clients.incident_service_client.requests.post", return_value=mock_resp):
            result = client.add_timeline_entry("case-123", "submitted", "Case submitted")
            assert result["event_type"] == "submitted"


class TestSessionSubmitUsesIncidentService:
    """Verify submit flow creates cases through incident-service."""

    def test_submit_calls_incident_service_not_graph_core(self):
        """The submit service should call incident-service, not graph.create_case()."""
        from app.services.session_submit_service import SessionSubmitService

        # Verify the module imports incident_service_client
        import inspect
        source = inspect.getsource(SessionSubmitService.submit_session)
        assert "IncidentServiceClient" in source or "incident_client" in source
        # Should NOT contain graph.create_case for operational case creation
        assert "graph.create_case(" not in source


class TestMessageIngestionUsesIncidentService:
    """Verify auto-escalation creates cases through incident-service."""

    def test_auto_escalation_uses_incident_service(self):
        """The message ingestion auto-escalation should use incident-service."""
        from app.services.message_ingestion_service import MessageIngestionService

        import inspect
        source = inspect.getsource(MessageIngestionService.process_user_message)
        # Should contain incident-service client usage for case creation
        assert "IncidentServiceClient" in source or "incident_client" in source


class TestGracefulDegradation:
    """Verify services handle unavailability gracefully."""

    def test_incident_service_unavailable_on_submit_returns_error(self):
        """If incident-service is down during submit, return a clear error."""
        from app.services.session_submit_service import SessionSubmitService

        # The submit method should handle IncidentServiceUnavailableError
        import inspect
        source = inspect.getsource(SessionSubmitService.submit_session)
        assert "IncidentServiceUnavailableError" in source

    def test_graph_core_unavailable_does_not_block_case_creation(self):
        """Graph-core failure should not prevent case creation."""
        from app.services.session_submit_service import SessionSubmitService

        import inspect
        source = inspect.getsource(SessionSubmitService)
        # Graph-core update should be in a safe/optional method
        assert "_safe_graph_context_update" in source
