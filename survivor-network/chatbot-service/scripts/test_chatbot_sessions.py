import requests

BASE_URL = "http://chatbot-service.127.0.0.1.nip.io"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def start_session(initial_message=None):
    payload = {}
    if initial_message:
        payload["initial_message"] = initial_message
    r = requests.post(f"{BASE_URL}/sessions/start", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def send_message(session_id: str, message: str, client_message_id: str | None = None):
    payload = {"message": message}
    if client_message_id:
        payload["client_message_id"] = client_message_id
    r = requests.post(f"{BASE_URL}/sessions/{session_id}/message", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def submit_session(session_id: str):
    r = requests.post(f"{BASE_URL}/sessions/{session_id}/submit", timeout=30)
    r.raise_for_status()
    return r.json()


def get_session(session_id: str):
    r = requests.get(f"{BASE_URL}/sessions/{session_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def test_urgent_flow():
    print("Running urgent flow...")
    start = start_session("I was assaulted and I am bleeding in Johannesburg")
    sid = start["session_id"]

    assert_true(start["stage"] == "collecting_followup_after_escalation", "Expected escalation stage")
    assert_true(start["provisional_case"] is not None, "Expected provisional case")
    assert_true(start["latest_assessment"]["triage"]["urgency"] == "critical", "Expected critical urgency")

    followup = send_message(
        sid,
        "Yes, I am in immediate danger and text is safer",
        client_message_id="msg-urgent-1",
    )
    assert_true("safe_contact_method" not in followup.get("missing_fields", []), "Expected safe contact method to be captured")

    submitted = submit_session(sid)
    assert_true(submitted["submitted"] is True, "Expected submitted true")
    assert_true(submitted["state"]["safe_contact_method"] == "text", "Expected safe_contact_method=text")
    assert_true(submitted["state"]["submission_mode"] in {"complete", "provisional_partial"}, "Expected submission mode")


def test_duplicate_message_idempotency():
    print("Running duplicate message idempotency...")
    start = start_session()
    sid = start["session_id"]

    first = send_message(sid, "I need shelter in Johannesburg", client_message_id="msg-dup-1")
    second = send_message(sid, "I need shelter in Johannesburg", client_message_id="msg-dup-1")

    assert_true(second["bot_message"].startswith("This message was already received"), "Expected duplicate detection")

    state = get_session(sid)
    user_messages = [m for m in state["state"].get("history", []) if m.get("role") == "user"]
    assert_true(len(user_messages) == 1, "Expected single user history entry for duplicate client message id")


def test_nonurgent_requires_info_before_submit():
    print("Running non-urgent submit validation...")
    start = start_session()
    sid = start["session_id"]

    send_message(sid, "I need help", client_message_id="msg-basic-1")
    submitted = submit_session(sid)

    assert_true(submitted["submitted"] is False, "Expected submit to fail without enough info")
    assert_true(len(submitted["missing_fields"]) > 0, "Expected missing fields")


if __name__ == "__main__":
    test_urgent_flow()
    test_duplicate_message_idempotency()
    test_nonurgent_requires_info_before_submit()
    print("All chatbot session tests passed.")