"""
Survivor Network — Full Flow Simulation

Tests the complete loop:
1. Seed participants (helpers with various skills/verification)
2. Simulate survivors reporting incidents
3. Cases get created via incident-service
4. Admin-service recommends and assigns participants
5. Cases move through status workflow

Usage:
    python full_flow_sim.py --survivors 50 --helpers 10
    python full_flow_sim.py --survivors 10 --helpers 5 --ramp-up 10
"""

import argparse
import asyncio
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INCIDENT_SERVICE = "http://incident-service.127.0.0.1.nip.io"
PARTICIPANT_SERVICE = "http://participant-service.127.0.0.1.nip.io"
ADMIN_SERVICE = "http://admin-service.127.0.0.1.nip.io"

# ---------------------------------------------------------------------------
# Helper personas
# ---------------------------------------------------------------------------

HELPER_PERSONAS = [
    {"display_name": "Thandi Mokoena", "phone": "+27821000001", "roles": ["volunteer", "responder"],
     "skills": ["transport", "first_aid"], "verification_status": "admin_verified", "trust_level": "high",
     "can_transport_people": True, "can_offer_shelter": False, "can_offer_counselling": False,
     "can_handle_medical": False, "home_location_text": "Randburg", "latitude": -26.094, "longitude": 28.006},
    {"display_name": "James Nkosi", "phone": "+27821000002", "roles": ["volunteer", "counsellor"],
     "skills": ["counselling", "gbv_support"], "verification_status": "admin_verified", "trust_level": "high",
     "can_transport_people": False, "can_offer_shelter": False, "can_offer_counselling": True,
     "can_handle_medical": False, "home_location_text": "Soweto", "latitude": -26.228, "longitude": 27.905},
    {"display_name": "Naledi Dlamini", "phone": "+27821000003", "roles": ["ngo_worker", "responder"],
     "skills": ["shelter", "crisis_support"], "verification_status": "organization_verified", "trust_level": "high",
     "can_transport_people": False, "can_offer_shelter": True, "can_offer_counselling": True,
     "can_handle_medical": False, "home_location_text": "Hillbrow", "latitude": -26.192, "longitude": 28.048},
    {"display_name": "Sipho Mabaso", "phone": "+27821000004", "roles": ["volunteer", "driver"],
     "skills": ["transport", "logistics"], "verification_status": "admin_verified", "trust_level": "high",
     "can_transport_people": True, "can_offer_shelter": False, "can_offer_counselling": False,
     "can_handle_medical": False, "home_location_text": "Germiston", "latitude": -26.220, "longitude": 28.170},
    {"display_name": "Lerato Khumalo", "phone": "+27821000005", "roles": ["clinic_worker", "medical"],
     "skills": ["medical", "first_aid", "triage"], "verification_status": "background_checked", "trust_level": "high",
     "can_transport_people": False, "can_offer_shelter": False, "can_offer_counselling": False,
     "can_handle_medical": True, "home_location_text": "Katlehong", "latitude": -26.345, "longitude": 28.151},
    {"display_name": "Mpho Tshabalala", "phone": "+27821000006", "roles": ["legal_advisor"],
     "skills": ["legal", "protection_orders"], "verification_status": "admin_verified", "trust_level": "high",
     "can_transport_people": False, "can_offer_shelter": False, "can_offer_counselling": False,
     "can_offer_legal_help": True, "can_handle_medical": False, "home_location_text": "Pretoria", "latitude": -25.746, "longitude": 28.188},
    {"display_name": "Bongani Zulu", "phone": "+27821000007", "roles": ["volunteer"],
     "skills": ["general"], "verification_status": "phone_verified", "trust_level": "medium",
     "can_transport_people": True, "can_offer_shelter": False, "can_offer_counselling": False,
     "can_handle_medical": False, "home_location_text": "Benoni", "latitude": -26.188, "longitude": 28.321},
    {"display_name": "Zanele Mthembu", "phone": "+27821000008", "roles": ["volunteer", "shelter_host"],
     "skills": ["shelter", "childcare"], "verification_status": "admin_verified", "trust_level": "high",
     "can_transport_people": False, "can_offer_shelter": True, "can_offer_counselling": False,
     "can_handle_medical": False, "home_location_text": "Tembisa", "latitude": -26.001, "longitude": 28.227},
    {"display_name": "David Pillay", "phone": "+27821000009", "roles": ["volunteer"],
     "skills": ["transport"], "verification_status": "unverified", "trust_level": "low",
     "can_transport_people": True, "can_offer_shelter": False, "can_offer_counselling": False,
     "can_handle_medical": False, "home_location_text": "Boksburg", "latitude": -26.212, "longitude": 28.256},
    {"display_name": "Fatima Adams", "phone": "+27821000010", "roles": ["counsellor", "ngo_worker"],
     "skills": ["counselling", "trauma", "gbv"], "verification_status": "background_checked", "trust_level": "high",
     "can_transport_people": False, "can_offer_shelter": False, "can_offer_counselling": True,
     "can_handle_medical": False, "home_location_text": "Mamelodi", "latitude": -25.720, "longitude": 28.396},
]

# ---------------------------------------------------------------------------
# Incident scenarios
# ---------------------------------------------------------------------------

INCIDENT_SCENARIOS = [
    {"message": "I was mugged near the taxi rank, they took my phone and bag", "location_text": "Diepkloof",
     "urgency": "urgent", "safety_risk": "medium", "primary_need": "Transport", "incident_type": "Robbery", "immediate_danger": False},
    {"message": "My partner hit me and I need somewhere safe to stay tonight", "location_text": "Tembisa",
     "urgency": "urgent", "safety_risk": "high", "primary_need": "Emergency Shelter", "incident_type": "Domestic Violence", "immediate_danger": False},
    {"message": "I was assaulted and I'm bleeding from my head", "location_text": "Alexandra",
     "urgency": "critical", "safety_risk": "critical", "primary_need": "Emergency Medical", "incident_type": "Assault", "immediate_danger": True},
    {"message": "Someone broke into my house while I was sleeping", "location_text": "Randburg",
     "urgency": "medium", "safety_risk": "medium", "primary_need": "Protection Order Support", "incident_type": "Break-in", "immediate_danger": False},
    {"message": "I need counselling, I was attacked last week and I can't sleep", "location_text": "Soweto",
     "urgency": "medium", "safety_risk": "low", "primary_need": "Mental Health Support", "incident_type": "Assault", "immediate_danger": False},
    {"message": "My child was grabbed outside school, I got them back but I'm terrified", "location_text": "Katlehong",
     "urgency": "urgent", "safety_risk": "high", "primary_need": "Protection Order Support", "incident_type": "Child Endangerment", "immediate_danger": False},
    {"message": "I witnessed a hijacking on the N1, the victim needs help", "location_text": "Midrand",
     "urgency": "critical", "safety_risk": "high", "primary_need": "Emergency Medical", "incident_type": "Hijacking", "immediate_danger": True},
    {"message": "I'm stranded at the hospital with no way to get home after treatment", "location_text": "Benoni",
     "urgency": "medium", "safety_risk": "low", "primary_need": "Transport", "incident_type": "Displacement", "immediate_danger": False},
    {"message": "There's a group of men threatening people in our street", "location_text": "Hillbrow",
     "urgency": "urgent", "safety_risk": "high", "primary_need": "Emergency Shelter", "incident_type": "Threats", "immediate_danger": True},
    {"message": "I need legal help to get a protection order against my ex", "location_text": "Pretoria",
     "urgency": "medium", "safety_risk": "medium", "primary_need": "Protection Order Support", "incident_type": "Domestic Violence", "immediate_danger": False},
    {"message": "I was sexually assaulted and I don't know what to do", "location_text": "Germiston",
     "urgency": "critical", "safety_risk": "critical", "primary_need": "Emergency Medical", "incident_type": "Sexual Violence", "immediate_danger": False},
    {"message": "My medication was stolen and I need my ARVs urgently", "location_text": "Vosloorus",
     "urgency": "urgent", "safety_risk": "medium", "primary_need": "Medication Access", "incident_type": "Robbery", "immediate_danger": False},
]

# Assignment type mapping based on primary need
NEED_TO_ASSIGNMENT = {
    "Transport": "driver",
    "Emergency Shelter": "helper",
    "Emergency Medical": "medical_support",
    "Mental Health Support": "counsellor",
    "Protection Order Support": "legal_advisor",
    "Medication Access": "helper",
}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class FlowMetrics:
    helpers_created: int = 0
    cases_created: int = 0
    assignments_made: int = 0
    assignments_rejected: int = 0
    recommendations_found: int = 0
    status_updates: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration_s(self) -> float:
        return self.end_time - self.start_time

    def summary(self) -> dict:
        return {
            "duration_seconds": round(self.duration_s, 1),
            "helpers_created": self.helpers_created,
            "cases_created": self.cases_created,
            "assignments_made": self.assignments_made,
            "assignments_rejected": self.assignments_rejected,
            "recommendations_found": self.recommendations_found,
            "status_updates": self.status_updates,
            "errors": len(self.errors),
            "error_samples": self.errors[:5],
        }


# ---------------------------------------------------------------------------
# Simulation steps
# ---------------------------------------------------------------------------

async def seed_helpers(session: aiohttp.ClientSession, count: int, metrics: FlowMetrics) -> list[str]:
    """Create helper participants and mark them available."""
    helper_ids = []

    for i in range(count):
        persona = HELPER_PERSONAS[i % len(HELPER_PERSONAS)]
        payload = {
            "display_name": f"{persona['display_name']} #{i+1}" if i >= len(HELPER_PERSONAS) else persona["display_name"],
            "phone": persona.get("phone", ""),
            "roles": persona.get("roles", []),
            "skills": persona.get("skills", []),
            "availability_status": "available",
            "verification_status": persona.get("verification_status", "unverified"),
            "trust_level": persona.get("trust_level", "low"),
            "can_transport_people": persona.get("can_transport_people", False),
            "can_offer_shelter": persona.get("can_offer_shelter", False),
            "can_offer_counselling": persona.get("can_offer_counselling", False),
            "can_offer_legal_help": persona.get("can_offer_legal_help", False),
            "can_handle_medical": persona.get("can_handle_medical", False),
            "can_handle_crime_report": persona.get("can_handle_crime_report", False),
            "home_location_text": persona.get("home_location_text"),
            "latitude": persona.get("latitude"),
            "longitude": persona.get("longitude"),
        }

        try:
            async with session.post(f"{PARTICIPANT_SERVICE}/participants", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    helper_ids.append(data["id"])
                    metrics.helpers_created += 1
                else:
                    text = await resp.text()
                    metrics.errors.append(f"Create helper failed ({resp.status}): {text[:100]}")
        except Exception as exc:
            metrics.errors.append(f"Create helper error: {exc}")

    return helper_ids


async def create_incident_case(
    session: aiohttp.ClientSession,
    scenario: dict,
    metrics: FlowMetrics,
) -> str | None:
    """Create a case via incident-service from-intake endpoint."""
    payload = {
        "session_id": f"sim-{random.randint(1000, 9999)}",
        "message": scenario["message"],
        "location_text": scenario["location_text"],
        "urgency": scenario["urgency"],
        "safety_risk": scenario["safety_risk"],
        "primary_need": scenario["primary_need"],
        "incident_type": scenario["incident_type"],
        "immediate_danger": scenario.get("immediate_danger", False),
    }

    try:
        async with session.post(f"{INCIDENT_SERVICE}/cases/from-intake", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                metrics.cases_created += 1
                return data["id"]
            else:
                text = await resp.text()
                metrics.errors.append(f"Create case failed ({resp.status}): {text[:100]}")
    except Exception as exc:
        metrics.errors.append(f"Create case error: {exc}")

    return None


async def recommend_and_assign(
    session: aiohttp.ClientSession,
    case_id: str,
    scenario: dict,
    metrics: FlowMetrics,
) -> None:
    """Use admin-service to recommend participants and assign one."""

    # Recommend
    recommend_payload = {
        "needs": [scenario["primary_need"]],
        "location_text": scenario["location_text"],
        "urgency": scenario["urgency"],
        "safety_risk": scenario["safety_risk"],
        "limit": 5,
    }

    try:
        async with session.post(
            f"{ADMIN_SERVICE}/admin/cases/{case_id}/recommend-participants",
            json=recommend_payload,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                available = data.get("available", [])
                metrics.recommendations_found += len(available)

                if not available:
                    return

                # Pick the first available participant and assign
                participant = available[0]
                assignment_type = NEED_TO_ASSIGNMENT.get(scenario["primary_need"], "helper")

                assign_payload = {
                    "participant_id": participant["id"],
                    "assignment_type": assignment_type,
                    "note": f"Auto-assigned for {scenario['primary_need']} in {scenario['location_text']}",
                    "notify_participant": False,  # notification-service not deployed
                }

                async with session.post(
                    f"{ADMIN_SERVICE}/admin/cases/{case_id}/assign",
                    json=assign_payload,
                ) as assign_resp:
                    if assign_resp.status == 200:
                        metrics.assignments_made += 1
                    elif assign_resp.status == 400:
                        metrics.assignments_rejected += 1
                        text = await assign_resp.text()
                        metrics.errors.append(f"Assignment rejected: {text[:100]}")
                    else:
                        text = await assign_resp.text()
                        metrics.errors.append(f"Assignment failed ({assign_resp.status}): {text[:100]}")
            elif resp.status == 503:
                metrics.errors.append("participant-service unavailable for recommendations")
            else:
                text = await resp.text()
                metrics.errors.append(f"Recommend failed ({resp.status}): {text[:100]}")
    except Exception as exc:
        metrics.errors.append(f"Recommend/assign error: {exc}")


async def update_case_status(
    session: aiohttp.ClientSession,
    case_id: str,
    new_status: str,
    metrics: FlowMetrics,
) -> None:
    """Update case status via admin-service."""
    try:
        async with session.patch(
            f"{ADMIN_SERVICE}/admin/cases/{case_id}/status",
            json={"status": new_status, "note": f"Simulation: moving to {new_status}"},
        ) as resp:
            if resp.status == 200:
                metrics.status_updates += 1
            else:
                text = await resp.text()
                metrics.errors.append(f"Status update failed ({resp.status}): {text[:100]}")
    except Exception as exc:
        metrics.errors.append(f"Status update error: {exc}")


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

async def run_simulation(num_survivors: int, num_helpers: int, ramp_up: float) -> FlowMetrics:
    metrics = FlowMetrics()
    metrics.start_time = time.monotonic()

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(
        timeout=timeout,
        headers={"Content-Type": "application/json"},
    ) as session:

        # Health checks
        print("  Checking services...", flush=True)
        for name, url in [("incident-service", INCIDENT_SERVICE), ("participant-service", PARTICIPANT_SERVICE), ("admin-service", ADMIN_SERVICE)]:
            try:
                async with session.get(f"{url}/health") as resp:
                    if resp.status == 200:
                        print(f"    ✅ {name}", flush=True)
                    else:
                        print(f"    ❌ {name} ({resp.status})", flush=True)
                        metrics.errors.append(f"{name} unhealthy")
            except Exception as exc:
                print(f"    ❌ {name}: {exc}", flush=True)
                metrics.errors.append(f"{name} unreachable: {exc}")
                metrics.end_time = time.monotonic()
                return metrics

        # Phase 1: Seed helpers
        print(f"\n  Phase 1: Seeding {num_helpers} helpers...", flush=True)
        helper_ids = await seed_helpers(session, num_helpers, metrics)
        print(f"    Created {len(helper_ids)} helpers", flush=True)

        # Phase 2: Create cases
        print(f"\n  Phase 2: Creating {num_survivors} incident cases...", flush=True)
        case_ids: list[tuple[str, dict]] = []
        delay = ramp_up / num_survivors if num_survivors > 1 and ramp_up > 0 else 0

        for i in range(num_survivors):
            scenario = INCIDENT_SCENARIOS[i % len(INCIDENT_SCENARIOS)]
            case_id = await create_incident_case(session, scenario, metrics)
            if case_id:
                case_ids.append((case_id, scenario))
            if delay > 0:
                await asyncio.sleep(delay)
            if (i + 1) % 10 == 0:
                print(f"    Created {i + 1}/{num_survivors} cases...", flush=True)

        print(f"    Total cases created: {metrics.cases_created}", flush=True)

        # Phase 3: Recommend and assign
        print(f"\n  Phase 3: Recommending and assigning participants...", flush=True)
        for case_id, scenario in case_ids:
            await recommend_and_assign(session, case_id, scenario, metrics)

        print(f"    Assignments made: {metrics.assignments_made}", flush=True)
        print(f"    Assignments rejected (safety): {metrics.assignments_rejected}", flush=True)

        # Phase 4: Move some cases through workflow
        print(f"\n  Phase 4: Updating case statuses...", flush=True)
        assigned_cases = [(cid, s) for cid, s in case_ids if metrics.assignments_made > 0]
        for case_id, _ in assigned_cases[:min(10, len(assigned_cases))]:
            await update_case_status(session, case_id, "in_progress", metrics)
            await asyncio.sleep(0.1)
            await update_case_status(session, case_id, "resolved", metrics)

        print(f"    Status updates: {metrics.status_updates}", flush=True)

        # Final dashboard check
        print(f"\n  Phase 5: Dashboard summary...", flush=True)
        try:
            async with session.get(f"{ADMIN_SERVICE}/dashboard/summary") as resp:
                if resp.status == 200:
                    summary = await resp.json()
                    print(f"    Active cases: {summary['active_cases']}", flush=True)
                    print(f"    Urgent cases: {summary['urgent_cases']}", flush=True)
                    print(f"    Available participants: {summary['available_participants']}", flush=True)
        except Exception:
            pass

    metrics.end_time = time.monotonic()
    return metrics


def print_results(metrics: FlowMetrics) -> None:
    summary = metrics.summary()
    print("\n" + "=" * 64)
    print("  FULL FLOW SIMULATION RESULTS")
    print("=" * 64)
    print(f"  Duration:              {summary['duration_seconds']}s")
    print(f"  Helpers created:       {summary['helpers_created']}")
    print(f"  Cases created:         {summary['cases_created']}")
    print(f"  Recommendations found: {summary['recommendations_found']}")
    print(f"  Assignments made:      {summary['assignments_made']}")
    print(f"  Assignments rejected:  {summary['assignments_rejected']}")
    print(f"  Status updates:        {summary['status_updates']}")
    print(f"  Errors:                {summary['errors']}")
    if summary["error_samples"]:
        print("\n  Error samples:")
        for err in summary["error_samples"]:
            print(f"    - {err}")
    print("=" * 64)

    output_file = f"full_flow_results_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results written to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Survivor Network Full Flow Simulation")
    parser.add_argument("--survivors", type=int, default=50, help="Number of incident cases to create")
    parser.add_argument("--helpers", type=int, default=10, help="Number of helper participants to seed")
    parser.add_argument("--ramp-up", type=float, default=10, help="Ramp-up seconds for case creation")
    args = parser.parse_args()

    print("\n" + "=" * 64)
    print("  SURVIVOR NETWORK — FULL FLOW SIMULATION")
    print("=" * 64)
    print(f"  Survivors:  {args.survivors}")
    print(f"  Helpers:    {args.helpers}")
    print(f"  Ramp-up:    {args.ramp_up}s")
    print(f"  Scenarios:  {len(INCIDENT_SCENARIOS)} incident types")
    print("=" * 64)

    metrics = asyncio.run(run_simulation(args.survivors, args.helpers, args.ramp_up))
    print_results(metrics)


if __name__ == "__main__":
    main()
