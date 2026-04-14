"""Tests for AssessmentContext — the canonical DTO for graph-core calls."""
import pytest
from app.services.assessment_context import AssessmentContext


class TestAssessmentContextBuilder:
    def _base_state(self, **overrides):
        state = {
            "incident_summary": "I was attacked",
            "location": "Soweto",
            "immediate_danger": True,
            "injury_status": "injured",
            "primary_need": "Emergency Medical",
            "safe_contact_method": "whatsapp",
            "latitude": -26.2041,
            "longitude": 28.0473,
            "location_accuracy": 15.0,
            "location_source": "browser",
            "attachments": [],
            "history": [],
            "latest_graph_assessment": None,
            "submission_mode": None,
        }
        state.update(overrides)
        return state

    def test_builds_pre_parsed_with_all_fields(self):
        state = self._base_state()
        ctx = AssessmentContext.from_session_state(state, "help me")
        assert ctx.pre_parsed is not None
        assert ctx.pre_parsed["location"] == "Soweto"
        assert ctx.pre_parsed["primary_needs"] == ["Emergency Medical"]
        assert ctx.pre_parsed["immediate_danger"] is True
        assert ctx.pre_parsed["injury_status"] == "injured"
        assert ctx.pre_parsed["incident_summary"] == "I was attacked"
        assert ctx.pre_parsed["latitude"] == -26.2041
        assert ctx.pre_parsed["longitude"] == 28.0473
        assert ctx.pre_parsed["location_source"] == "browser"

    def test_coordinates_on_context(self):
        state = self._base_state()
        ctx = AssessmentContext.from_session_state(state, "help")
        assert ctx.latitude == -26.2041
        assert ctx.longitude == 28.0473
        assert ctx.location_accuracy == 15.0
        assert ctx.location_source == "browser"

    def test_no_coordinates_when_absent(self):
        state = self._base_state(latitude=None, longitude=None)
        ctx = AssessmentContext.from_session_state(state, "help")
        assert ctx.latitude is None
        assert ctx.longitude is None
        assert "latitude" not in ctx.pre_parsed

    def test_crisis_override_passthrough(self):
        state = self._base_state()
        crisis = {"min_urgency": "critical", "min_safety": "immediate", "reasons": ["bleeding"], "immediate_danger": True}
        ctx = AssessmentContext.from_session_state(state, "help", crisis_override=crisis)
        assert ctx.crisis_override == crisis

    def test_message_includes_context(self):
        state = self._base_state()
        ctx = AssessmentContext.from_session_state(state, "I need an ambulance")
        assert "Soweto" in ctx.message
        assert "injured" in ctx.message.lower() or "User is injured" in ctx.message
        assert "I need an ambulance" in ctx.message

    def test_immutable(self):
        state = self._base_state()
        ctx = AssessmentContext.from_session_state(state, "help")
        with pytest.raises(AttributeError):
            ctx.latitude = 0.0


class TestSubmitFlowContext:
    """Verify that submit and message flows produce identical context shape."""

    def test_same_context_shape(self):
        state = {
            "incident_summary": "attacked",
            "location": "Soweto",
            "immediate_danger": True,
            "injury_status": "injured",
            "primary_need": "Emergency Medical",
            "safe_contact_method": "whatsapp",
            "latitude": -26.2041,
            "longitude": 28.0473,
            "location_accuracy": 15.0,
            "location_source": "browser",
            "latest_crisis_override": {
                "min_urgency": "critical",
                "min_safety": "immediate",
                "reasons": ["bleeding"],
                "immediate_danger": True,
            },
            "attachments": [],
            "history": [],
            "latest_graph_assessment": None,
            "submission_mode": None,
        }

        # Message-time context
        msg_ctx = AssessmentContext.from_session_state(
            state, "help me", crisis_override=state["latest_crisis_override"]
        )

        # Submit-time context (same builder, using stored crisis_override)
        submit_ctx = AssessmentContext.from_session_state(
            state, state["incident_summary"], crisis_override=state.get("latest_crisis_override")
        )

        # Both should have same pre_parsed keys
        assert set(msg_ctx.pre_parsed.keys()) == set(submit_ctx.pre_parsed.keys())
        assert msg_ctx.latitude == submit_ctx.latitude
        assert msg_ctx.longitude == submit_ctx.longitude
        assert msg_ctx.crisis_override == submit_ctx.crisis_override
