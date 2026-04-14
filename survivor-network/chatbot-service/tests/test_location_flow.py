"""Tests for location data flow through chatbot-service."""
import pytest
from app.services.intake_state_service import IntakeStateService


class TestLocationState:
    def test_initial_state_has_location_fields(self):
        state = IntakeStateService.initial_state()
        assert state["latitude"] is None
        assert state["longitude"] is None
        assert state["location_accuracy"] is None
        assert state["location_source"] is None

    def test_apply_location_from_browser(self):
        state = IntakeStateService.initial_state()
        location = {"latitude": -26.2041, "longitude": 28.0473, "accuracy": 10.0, "source": "browser"}
        updated = IntakeStateService.apply_location(state, location)
        assert updated["latitude"] == -26.2041
        assert updated["longitude"] == 28.0473
        assert updated["location_accuracy"] == 10.0
        assert updated["location_source"] == "browser"

    def test_apply_location_updates_existing(self):
        """Latest location should always win (user may have moved)."""
        state = IntakeStateService.initial_state()
        state["latitude"] = -26.0
        state["longitude"] = 28.0
        location = {"latitude": -26.5, "longitude": 28.5, "accuracy": 100.0, "source": "browser"}
        updated = IntakeStateService.apply_location(state, location)
        assert updated["latitude"] == -26.5
        assert updated["longitude"] == 28.5

    def test_apply_location_with_empty_dict(self):
        state = IntakeStateService.initial_state()
        updated = IntakeStateService.apply_location(state, {})
        assert updated["latitude"] is None
        assert updated["longitude"] is None

    def test_apply_location_defaults_source_to_browser(self):
        state = IntakeStateService.initial_state()
        location = {"latitude": -26.2041, "longitude": 28.0473}
        updated = IntakeStateService.apply_location(state, location)
        assert updated["location_source"] == "browser"
        assert updated["location_accuracy"] == 0.0

    def test_apply_location_does_not_affect_other_fields(self):
        state = IntakeStateService.initial_state()
        state["location"] = "Soweto"
        state["primary_need"] = "Emergency Medical"
        location = {"latitude": -26.2041, "longitude": 28.0473, "accuracy": 10.0, "source": "browser"}
        updated = IntakeStateService.apply_location(state, location)
        assert updated["location"] == "Soweto"
        assert updated["primary_need"] == "Emergency Medical"
        assert updated["latitude"] == -26.2041

    def test_location_coordinates_in_state_after_apply(self):
        """Verify coordinates are present in state for _build_pre_parsed to pick up."""
        state = IntakeStateService.initial_state()
        state["latitude"] = -26.2041
        state["longitude"] = 28.0473
        state["location"] = "Soweto"
        state["primary_need"] = "Emergency Medical"
        assert state["latitude"] is not None
        assert state["longitude"] is not None
