import json
import os
import sys
from pathlib import Path

import requests

BASE_URL = os.getenv("BASE_URL", "http://graph-core.127.0.0.1.nip.io")
CASES_PATH = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).resolve().parents[1] / "tests" / "intake_triage_cases.json"
)


def extract_top_destination(payload: dict) -> str | None:
    destinations = payload.get("escalation_destinations") or []
    if not destinations:
        return None

    first = destinations[0]
    node = first.get("node") or {}
    return node.get("label") or first.get("kind")


def check_expectations(case: dict, payload: dict) -> list[str]:
    errors: list[str] = []
    expect = case.get("expect", {})

    intake = payload.get("intake", {})
    triage = payload.get("triage", {})
    escalation = payload.get("escalation", {})
    top_destination = extract_top_destination(payload)

    primary_needs = intake.get("primary_needs", [])
    derived_support_needs = intake.get("derived_support_needs", [])
    normalized_barriers = intake.get("normalized_barriers", [])
    incident_types = triage.get("incident_types", [])

    if "urgency" in expect and triage.get("urgency") != expect["urgency"]:
        errors.append(
            f"expected urgency={expect['urgency']}, got {triage.get('urgency')}"
        )

    if "queue" in expect and escalation.get("queue") != expect["queue"]:
        errors.append(
            f"expected queue={expect['queue']}, got {escalation.get('queue')}"
        )

    if "primary_needs_contains" in expect:
        for need in expect["primary_needs_contains"]:
            if need not in primary_needs:
                errors.append(
                    f"expected primary_needs to contain '{need}', got {primary_needs}"
                )

    if "derived_support_needs_contains" in expect:
        for need in expect["derived_support_needs_contains"]:
            if need not in derived_support_needs:
                errors.append(
                    f"expected derived_support_needs to contain '{need}', got {derived_support_needs}"
                )

    if "barriers_contains" in expect:
        for barrier in expect["barriers_contains"]:
            if barrier not in normalized_barriers:
                errors.append(
                    f"expected normalized_barriers to contain '{barrier}', got {normalized_barriers}"
                )

    if "incident_types_contains" in expect:
        for incident in expect["incident_types_contains"]:
            if incident not in incident_types:
                errors.append(
                    f"expected incident_types to contain '{incident}', got {incident_types}"
                )

    if "top_destination_in" in expect:
        allowed = expect["top_destination_in"]
        if top_destination not in allowed:
            errors.append(
                f"expected top_destination in {allowed}, got {top_destination}"
            )

    return errors


def main() -> int:
    if not CASES_PATH.exists():
        print(f"Cases file not found: {CASES_PATH}")
        return 1

    with CASES_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Loaded {len(cases)} cases from {CASES_PATH}")
    print(f"Calling {BASE_URL}/triage/assess\n")

    failures = 0

    for case in cases:
        name = case["name"]
        message = case["message"]

        try:
            response = requests.post(
                f"{BASE_URL}/triage/assess",
                json={"message": message, "top_k": 5},
                timeout=30,
            )
        except Exception as exc:
            failures += 1
            print("=" * 80)
            print(f"[FAIL] {name}")
            print(f"message: {message}")
            print(f"error: {exc}")
            continue

        if response.status_code != 200:
            failures += 1
            print("=" * 80)
            print(f"[FAIL] {name}")
            print(f"message: {message}")
            print(f"status: {response.status_code}")
            print(response.text)
            continue

        payload = response.json()
        intake = payload.get("intake", {})
        triage = payload.get("triage", {})
        escalation = payload.get("escalation", {})

        primary_needs = intake.get("primary_needs", [])
        derived_support_needs = intake.get("derived_support_needs", [])
        barriers = intake.get("normalized_barriers", [])
        urgency = triage.get("urgency")
        queue = escalation.get("queue")
        destination = extract_top_destination(payload)

        expectation_errors = check_expectations(case, payload)

        print("=" * 80)
        status = "OK" if not expectation_errors else "FAIL"
        print(f"[{status}] {name}")
        print(f"message: {message}")
        print(f"primary_needs: {primary_needs}")
        print(f"derived_support_needs: {derived_support_needs}")
        print(f"barriers: {barriers}")
        print(f"urgency: {urgency}")
        print(f"queue: {queue}")
        print(f"top_destination: {destination}")

        if expectation_errors:
            failures += 1
            print("expectation_errors:")
            for err in expectation_errors:
                print(f"  - {err}")

    print("\n" + "=" * 80)
    if failures:
        print(f"Completed with {failures} failure(s).")
        return 1

    print("Completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())