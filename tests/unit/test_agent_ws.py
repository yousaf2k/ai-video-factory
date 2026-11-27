"""
WebSocket tests for the agent chat endpoint (streaming events, ordering).
"""
import asyncio

import pytest
from fastapi.testclient import TestClient


class FakeEngine:
    """Emits a representative event sequence without calling any LLM."""

    def __init__(self):
        self.calls = []

    async def run(self, conversation_id, message, project_id=None, on_event=None):
        self.calls.append((conversation_id, message, project_id))
        on_event({"type": "llm_start", "iteration": 1, "provider": "fake", "model": "m"})
        on_event({"type": "tool_start", "tool": "list_projects", "arguments": {}})
        on_event({"type": "tool_result", "tool": "list_projects", "ok": True, "result": {}})
        await asyncio.sleep(0.02)
        on_event({"type": "final", "content": "answer text"})
        return {"conversation_id": conversation_id, "answer": "answer text", "steps": []}


@pytest.fixture
def client_and_engine(monkeypatch):
    import web_ui.backend.api.agent as agent_api
    engine = FakeEngine()
    monkeypatch.setattr(agent_api, "get_agent_engine", lambda: engine)
    from web_ui.backend.main import app
    return app, engine


def test_ws_chat_event_order(client_and_engine):
    app, engine = client_and_engine
    with TestClient(app) as client:
        with client.websocket_connect("/api/agent/ws") as ws:
            ws.send_json({"type": "chat", "message": "hello", "project_id": "proj_x"})
            got = []
            while True:
                msg = ws.receive_json()
                got.append(msg)
                if msg.get("type") == "done":
                    break
    types = [m["type"] for m in got]
    # Events must arrive in order and before 'done'.
    assert types == ["conversation", "llm_start", "tool_start", "tool_result", "final", "done"]
    conversation_id = got[0]["conversation_id"]
    assert engine.calls == [(conversation_id, "hello", "proj_x")]

    # Conversation persisted by the fake flow's store (cleanup)
    from web_ui.backend.services.agent.conversations import get_conversation_store
    get_conversation_store().delete(conversation_id)


def test_ws_ping_pong(client_and_engine):
    app, _ = client_and_engine
    with TestClient(app) as client:
        with client.websocket_connect("/api/agent/ws") as ws:
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}


def test_ws_rejects_unknown_type(client_and_engine):
    app, _ = client_and_engine
    with TestClient(app) as client:
        with client.websocket_connect("/api/agent/ws") as ws:
            ws.send_json({"type": "bogus"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Unknown message type" in msg["message"]


def test_conversation_detail_backfills_narration_for_older_saves(client_and_engine):
    """Tool-call replies saved before `narration` existed get it computed on read."""
    from web_ui.backend.services.agent.conversations import get_conversation_store
    store = get_conversation_store()
    conversation = store.create()
    store.append_messages(conversation["id"], [
        {"role": "user", "content": "add it"},
        {"role": "assistant",
         "content": 'Checking first.\n```tool_call\n{"tool": "get_story", "arguments": {}}\n```',
         "tool_call": {"tool": "get_story", "arguments": {}}},
        {"role": "assistant", "content": "saved later",
         "tool_call": {"tool": "get_story", "arguments": {}}, "narration": "kept as saved"},
    ])
    app, _ = client_and_engine
    try:
        with TestClient(app) as client:
            detail = client.get(f"/api/agent/conversations/{conversation['id']}").json()
    finally:
        store.delete(conversation["id"])

    assert detail["messages"][1]["narration"] == "Checking first."
    assert detail["messages"][2]["narration"] == "kept as saved"
