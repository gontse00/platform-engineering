import requests

BASE = "http://127.0.0.1:8080"

start = requests.post(f"{BASE}/sessions/start", json={})
start.raise_for_status()
session = start.json()
print("START:", session)

session_id = session["session_id"]

turn1 = requests.post(
    f"{BASE}/sessions/{session_id}/message",
    json={"message": "I was assaulted and I am bleeding in Johannesburg"},
)
turn1.raise_for_status()
print("TURN1:", turn1.json())

state = requests.get(f"{BASE}/sessions/{session_id}")
state.raise_for_status()
print("STATE:", state.json())