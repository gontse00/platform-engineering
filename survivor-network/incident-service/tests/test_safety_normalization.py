"""Unit tests for deterministic safety normalization in incident-service."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.safety_rules import normalize_case_safety


class TestSexualAssault:
    def test_raped(self):
        u, s, needs, itype = normalize_case_safety(
            "i was raped last night", "medium", "low", [], None, False)
        assert u == "urgent"
        assert s == "high"
        assert itype == "Sexual Assault"
        assert "Emergency Medical" in needs
        assert "Mental Health Support" in needs

    def test_sexual_assault(self):
        u, s, needs, itype = normalize_case_safety(
            "i was sexually assaulted", "standard", "low", [], None, False)
        assert u == "urgent"
        assert s == "high"
        assert itype == "Sexual Assault"


class TestActiveDomesticViolence:
    def test_husband_beating_now(self):
        u, s, needs, itype = normalize_case_safety(
            "my husband is beating me right now, i locked myself in the bathroom",
            "medium", "low", [], None, True)
        assert u == "critical"
        assert s == "immediate"
        assert itype == "Domestic Violence"
        assert "Emergency Shelter" in needs
        assert "Protection Order Support" in needs

    def test_partner_hitting(self):
        u, s, needs, itype = normalize_case_safety(
            "my partner is hitting me", "medium", "low", [], None, False)
        assert u == "critical"
        assert s == "immediate"
        assert itype == "Domestic Violence"

    def test_past_domestic_violence(self):
        u, s, needs, itype = normalize_case_safety(
            "i experienced domestic violence last week", "medium", "low", [], None, False)
        assert u == "urgent"
        assert s == "high"
        assert itype == "Domestic Violence"


class TestStabbingBleeding:
    def test_stabbed(self):
        u, s, needs, itype = normalize_case_safety(
            "someone stabbed me outside", "medium", "low", [], None, True)
        assert u == "critical"
        assert s == "immediate"
        assert "Emergency Medical" in needs
        assert itype == "Assault"

    def test_bleeding_heavily(self):
        u, s, needs, itype = normalize_case_safety(
            "i am bleeding heavily from a wound", "standard", "low", [], None, False)
        assert u == "critical"
        assert s == "immediate"
        assert "Emergency Medical" in needs


class TestOverdoseSelfHarm:
    def test_overdose(self):
        u, s, needs, itype = normalize_case_safety(
            "i took too many pills and feel dizzy", "medium", "low", [], None, False)
        assert u == "critical"
        assert s == "immediate"
        assert itype == "Mental Health Crisis"
        assert "Emergency Medical" in needs
        assert "Mental Health Support" in needs

    def test_suicidal(self):
        u, s, needs, itype = normalize_case_safety(
            "i want to kill myself", "standard", "low", [], None, False)
        assert u == "critical"
        assert s == "immediate"
        assert itype == "Mental Health Crisis"

    def test_self_harm(self):
        u, s, needs, itype = normalize_case_safety(
            "i have been self-harm ing", "medium", "low", [], None, False)
        assert u == "critical"
        assert s == "immediate"


class TestBuildingCollapseTrapped:
    def test_building_collapse(self):
        u, s, needs, itype = normalize_case_safety(
            "there was a building collapse, people are trapped",
            "medium", "low", [], None, True)
        assert u == "critical"
        assert s == "immediate"
        assert itype == "Disaster / Emergency"
        assert "Emergency Medical" in needs

    def test_trapped_under(self):
        u, s, needs, itype = normalize_case_safety(
            "someone is trapped under rubble", "standard", "low", [], None, False)
        assert u == "critical"
        assert s == "immediate"


class TestHIVMedication:
    def test_arv(self):
        u, s, needs, itype = normalize_case_safety(
            "i ran out of my arv medication three days ago",
            "medium", "low", [], None, False)
        assert u == "urgent"
        assert s == "medium"
        assert itype == "Medication Access"
        assert "Medication Access" in needs

    def test_hiv_medication(self):
        u, s, needs, itype = normalize_case_safety(
            "my hiv medication was stolen", "standard", "low", [], None, False)
        assert u == "urgent"
        assert s == "medium"
        assert "Medication Access" in needs


class TestVagueHelp:
    def test_general_help_not_over_escalated(self):
        u, s, needs, itype = normalize_case_safety(
            "i need some help with my situation", "medium", "low", [], None, False)
        assert u == "medium"
        assert s == "low"
        # Should not have critical/urgent escalation for vague messages

    def test_advice_not_over_escalated(self):
        u, s, needs, itype = normalize_case_safety(
            "can someone give me advice about reporting a crime",
            "standard", "low", [], None, False)
        assert u in ("standard", "medium")
        assert s == "low"


class TestNeedsCombination:
    def test_primary_and_secondary_combined(self):
        u, s, needs, itype = normalize_case_safety(
            "i need help", "medium", "low",
            ["Emergency Shelter", "Transport Support"], None, False)
        assert "Emergency Shelter" in needs
        assert "Transport Support" in needs

    def test_incoming_needs_preserved_with_inferred(self):
        u, s, needs, itype = normalize_case_safety(
            "i was stabbed and need transport",
            "medium", "low", ["Transport Support"], None, False)
        assert "Transport Support" in needs
        assert "Emergency Medical" in needs  # inferred from stabbed


class TestIdempotency:
    # TODO: DB-level idempotency test requires database setup.
    # The /cases/from-intake endpoint checks source_session_id uniqueness.
    # For now, normalization logic is tested above.
    pass
