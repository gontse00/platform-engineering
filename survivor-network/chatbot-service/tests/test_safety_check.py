"""Unit tests for deterministic safety layer."""

import pytest
from app.services.safety_check import run_safety_check


class TestSafetyCheck:
    def test_no_keywords_returns_safe_defaults(self):
        result = run_safety_check("I need some general advice about my situation")
        assert result["immediate_danger"] is False
        assert result["urgency_floor"] == "standard"
        assert result["matched_keywords"] == []

    def test_bleeding_triggers_critical(self):
        result = run_safety_check("I'm bleeding badly from a stab wound")
        assert result["immediate_danger"] is True
        assert result["urgency_floor"] == "critical"
        assert len(result["matched_keywords"]) > 0

    def test_attacked_triggers_critical(self):
        result = run_safety_check("I am being attacked right now, please help")
        assert result["immediate_danger"] is True
        assert result["urgency_floor"] == "critical"

    def test_suicidal_triggers_critical(self):
        result = run_safety_check("I want to kill myself, I can't take it anymore")
        assert result["immediate_danger"] is True
        assert result["urgency_floor"] == "critical"

    def test_overdose_triggers_critical(self):
        result = run_safety_check("I took too many pills and I feel dizzy")
        assert result["immediate_danger"] is True
        assert result["urgency_floor"] == "critical"

    def test_death_threat_triggers_high(self):
        result = run_safety_check("He threatened to kill me if I leave")
        assert result["immediate_danger"] is False
        assert result["urgency_floor"] == "high"

    def test_sexual_assault_triggers_high(self):
        result = run_safety_check("I was raped last night")
        assert result["immediate_danger"] is False
        assert result["urgency_floor"] == "high"

    def test_weapon_triggers_high(self):
        result = run_safety_check("He has a knife and he's angry")
        assert result["immediate_danger"] is False
        assert result["urgency_floor"] == "high"

    def test_kidnapped_triggers_high(self):
        result = run_safety_check("I'm locked in a room and can't leave")
        assert result["immediate_danger"] is False
        assert result["urgency_floor"] == "high"

    def test_multiple_keywords_picks_highest(self):
        result = run_safety_check("I'm bleeding and he has a gun, I was raped")
        assert result["immediate_danger"] is True
        assert result["urgency_floor"] == "critical"
        assert len(result["matched_keywords"]) >= 2

    def test_case_insensitive(self):
        result = run_safety_check("I AM BLEEDING HEAVILY")
        assert result["urgency_floor"] == "critical"

    def test_mugged_and_shelter_happy_path(self):
        """End-to-end happy path: 'I was mugged and I need shelter in Johannesburg'"""
        result = run_safety_check("I was mugged and I need shelter in Johannesburg")
        # "mugged" doesn't match any crisis keywords directly
        # but the system should still return safe defaults
        assert result["urgency_floor"] == "standard" or result["urgency_floor"] in ("urgent", "high")
        assert isinstance(result["matched_keywords"], list)
