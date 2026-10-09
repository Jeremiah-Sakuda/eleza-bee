"""
Server integration tests for Eleza review surface (ELZ-400, ELZ-700)
"""

from fastapi.testclient import TestClient
from eleza.server import app

client = TestClient(app)

def test_index_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Eleza" in response.text
    assert "Say it without the notes" in response.text

def test_bee_status_endpoint():
    response = client.get("/api/bee/status")
    assert response.status_code == 200
    data = response.json()
    assert "installed" in data

def test_session_evaluation_and_ledger():
    response = client.post("/api/session/evaluate-sample")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "report" in data
    assert data["report"]["covered_count"] > 0
    assert data["report"]["contradicted_count"] >= 1

    # Check latest session
    latest_res = client.get("/api/session/latest")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["session_id"] == data["session_id"]

    # Check ledger endpoint
    ledger_res = client.get("/api/ledger")
    assert ledger_res.status_code == 200
    ledger_data = ledger_res.json()
    assert "insights" in ledger_data
    assert "gap_prompt" in ledger_data

def test_record_student_action():
    # Record 'got_it' action
    response = client.post("/api/action", json={
        "session_id": "test-sess",
        "target_idea": "The first phase produces ATP and energy for the cell.",
        "action": "got_it"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"

def test_process_live_speech():
    response = client.post("/api/session/process-speech", json={
        "transcript": "Hexokinase phosphorylates glucose into glucose-6-phosphate using up one molecule of ATP.",
        "speaker": "wearer"
    })
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["report"]["covered_count"] >= 1
