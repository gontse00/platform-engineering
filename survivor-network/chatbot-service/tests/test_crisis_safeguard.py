"""Tests for deterministic crisis safeguards, enum normalization, and schema validation."""

import pytest

from app.domain.constants import (
    Urgency,
    SafetyRisk,
    check_crisis_keywords,
    normalize_urgency,
    normalize_safety_risk,
    normalize_primary_need,
    normalize_injury_status,
    normalize_contact_method,
)
from app.clients.llm_client import ExtractedFields, LLMResponse


# ── Crisis keyword detection ──────────────────────────────────────────────


class TestCrisisKeywords:
    def test_active_bleeding_triggers_critical(self):
        result = check_crisis_keywords("Please help, I am bleeding heavily")
        assert result is not None
        assert result["min_urgency"] == Urgency.CRITICAL
        assert result["min_safety"] == SafetyRisk.IMMEDIATE
        assert result["immediate_danger"] is True

    def test_active_attack_triggers_critical(self):
        result = check_crisis_keywords("Someone is hurting me right now")
        assert result is not None
        assert result["min_urgency"] == Urgency.CRITICAL

    def test_suicidal_ideation_triggers_critical(self):
        result = check_crisis_keywords("I want to kill myself")
        assert result is not None
        assert result["min_urgency"] == Urgency.CRITICAL
        assert result["immediate_danger"] is True

    def test_death_threat_triggers_high(self):
        result = check_crisis_keywords("He threatened to kill me last night")
        assert result is not None
        assert result["min_urgency"] == Urgency.HIGH
        assert result["min_safety"] == SafetyRisk.HIGH

    def test_sexual_violence_triggers_high(self):
        result = check_crisis_keywords("I was raped")
        assert result is not None
        assert result["min_urgency"] == Urgency.HIGH

    def test_child_endangerment_triggers_high(self):
        result = check_crisis_keywords("My child is hurt badly")
        assert result is not None
        assert result["min_urgency"] == Urgency.HIGH

    def test_weapon_triggers_high(self):
        result = check_crisis_keywords("He has a knife and he's angry")
        assert result is not None
        assert result["min_urgency"] == Urgency.HIGH

    def test_no_crisis_keywords_returns_none(self):
        result = check_crisis_keywords("I need help finding a shelter nearby")
        assert result is None

    def test_case_insensitive(self):
        result = check_crisis_keywords("I AM BLEEDING HEAVILY")
        assert result is not None
        assert result["min_urgency"] == Urgency.CRITICAL

    def test_multiple_rules_take_highest(self):
        # Contains both a HIGH rule (death threat) and CRITICAL rule (bleeding)
        result = check_crisis_keywords("He threatened to kill me and I am bleeding")
        assert result is not None
        assert result["min_urgency"] == Urgency.CRITICAL
        assert len(result["reasons"]) == 2

    def test_overdose_triggers_critical(self):
        result = check_crisis_keywords("I took too many pills and I feel dizzy")
        assert result is not None
        assert result["min_urgency"] == Urgency.CRITICAL

    def test_trapped_triggers_high(self):
        result = check_crisis_keywords("He won't let me leave the house")
        assert result is not None
        assert result["min_urgency"] == Urgency.HIGH


# ── Enum normalization ────────────────────────────────────────────────────


class TestNormalization:
    def test_normalize_urgency_valid(self):
        assert normalize_urgency("critical") == "critical"
        assert normalize_urgency("HIGH") == "high"
        assert normalize_urgency("  Urgent  ") == "urgent"
        assert normalize_urgency("standard") == "standard"

    def test_normalize_urgency_invalid(self):
        assert normalize_urgency("extreme") == "standard"
        assert normalize_urgency(None) == "standard"
        assert normalize_urgency("") == "standard"

    def test_normalize_safety_risk_valid(self):
        assert normalize_safety_risk("immediate") == "immediate"
        assert normalize_safety_risk("LOW") == "low"

    def test_normalize_safety_risk_invalid(self):
        assert normalize_safety_risk("very_high") == "low"
        assert normalize_safety_risk(None) == "low"

    def test_normalize_primary_need_exact(self):
        assert normalize_primary_need("Emergency Medical") == "Emergency Medical"
        assert normalize_primary_need("emergency shelter") == "Emergency Shelter"

    def test_normalize_primary_need_partial(self):
        assert normalize_primary_need("medical") == "Emergency Medical"
        assert normalize_primary_need("shelter") == "Emergency Shelter"

    def test_normalize_primary_need_none(self):
        assert normalize_primary_need(None) is None
        assert normalize_primary_need("") is None

    def test_normalize_injury_status(self):
        assert normalize_injury_status("injured") == "injured"
        assert normalize_injury_status("not_injured") == "not_injured"
        assert normalize_injury_status("NOT injured") == "not_injured"
        assert normalize_injury_status("yes, I'm hurt") == "injured"
        assert normalize_injury_status(None) is None

    def test_normalize_contact_method(self):
        assert normalize_contact_method("whatsapp") == "whatsapp"
        assert normalize_contact_method("WhatsApp") == "whatsapp"
        assert normalize_contact_method("sms") == "text"
        assert normalize_contact_method("phone call") == "call"
        assert normalize_contact_method(None) is None


# ── Pydantic schema validation ────────────────────────────────────────────


class TestSchemaValidation:
    def test_extracted_fields_normalizes_values(self):
        fields = ExtractedFields(
            injury_status="NOT injured",
            primary_need="medical",
            safe_contact_method="WhatsApp",
            immediate_danger="true",
        )
        assert fields.injury_status == "not_injured"
        assert fields.primary_need == "Emergency Medical"
        assert fields.safe_contact_method == "whatsapp"
        assert fields.immediate_danger is True

    def test_extracted_fields_handles_nulls(self):
        fields = ExtractedFields()
        assert fields.incident_summary is None
        assert fields.location is None
        assert fields.immediate_danger is None

    def test_llm_response_defaults(self):
        resp = LLMResponse()
        assert resp.bot_message == ""
        assert resp.extracted_fields.incident_summary is None

    def test_llm_response_from_valid_json(self):
        data = {
            "bot_message": "I hear you.",
            "extracted_fields": {
                "location": "Soweto",
                "immediate_danger": True,
                "primary_need": "Emergency Medical",
            },
        }
        resp = LLMResponse.model_validate(data)
        assert resp.bot_message == "I hear you."
        assert resp.extracted_fields.location == "Soweto"
        assert resp.extracted_fields.immediate_danger is True
        assert resp.extracted_fields.primary_need == "Emergency Medical"

    def test_llm_response_normalizes_bad_values(self):
        data = {
            "bot_message": "Tell me more.",
            "extracted_fields": {
                "injury_status": "yes hurt",
                "safe_contact_method": "SMS",
                "immediate_danger": "false",
            },
        }
        resp = LLMResponse.model_validate(data)
        assert resp.extracted_fields.injury_status == "injured"
        assert resp.extracted_fields.safe_contact_method == "text"
        assert resp.extracted_fields.immediate_danger is False
