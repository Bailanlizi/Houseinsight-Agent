from fastapi.testclient import TestClient

from server.main import app


def test_websocket_emits_schema_then_ready():
    c = TestClient(app)
    with c.websocket_connect("/sessions/ws-test-session/ws") as ws:
        first = ws.receive_json()
        assert first.get("event") == "schema"
        assert first.get("session_id") == "ws-test-session"
        assert "events" in first
        second = ws.receive_json()
        assert second.get("event") == "ready"
        assert second.get("session_id") == "ws-test-session"
