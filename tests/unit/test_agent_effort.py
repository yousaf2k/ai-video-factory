"""
Effort / reasoning-effort wiring: provider payloads, agent engine shim, API options.
"""
import asyncio

import pytest


# ------------------------------------------------------------ provider layer

class _FakeResponse:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "ok"}}]}


def test_zai_provider_sends_thinking_effort(monkeypatch):
    from core import llm_engine
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None, verify=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(llm_engine.http_session, "post", fake_post)
    provider = llm_engine.ZAIProvider(api_key="k", model="glm-5.3-flash",
                                      base_url="https://example.invalid",
                                      reasoning_effort="max")
    provider.ask("hi")
    assert captured["json"]["thinking"] == {"type": "enabled", "effort": "max"}


def test_zai_provider_omits_thinking_when_unset(monkeypatch):
    from core import llm_engine
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None, verify=None):
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(llm_engine.http_session, "post", fake_post)
    provider = llm_engine.ZAIProvider(api_key="k", model="glm-5.3-flash",
                                      base_url="https://example.invalid")
    provider.ask("hi")
    assert "thinking" not in captured["json"]


def test_zai_effort_normalized_and_rejected(monkeypatch):
    from core import llm_engine
    assert llm_engine.ZAIProvider(api_key="k", model="m", reasoning_effort="HIGH").reasoning_effort == "high"
    assert llm_engine.ZAIProvider(api_key="k", model="m", reasoning_effort="bogus").reasoning_effort is None
    assert llm_engine.ZAIProvider(api_key="k", model="m").reasoning_effort is None


def test_get_provider_reads_effort_config(monkeypatch):
    from types import SimpleNamespace
    from core.llm_engine import get_provider
    shim = SimpleNamespace(ZHIPU_API_KEY="k", ZHIPU_MODEL="glm-5.3", ZHIPU_BASE_URL="",
                           ZHIPU_REASONING_EFFORT="high")
    provider = get_provider("zhipu", config_module=shim)
    assert provider.reasoning_effort == "high"


# -------------------------------------------------------------- agent engine

def test_engine_shim_applies_effort(tmp_path, monkeypatch):
    from web_ui.backend.services.agent.config_store import AgentConfigStore
    from web_ui.backend.services.agent.engine import _build_provider
    store = AgentConfigStore(path=str(tmp_path / "c.json"))
    store.save({"provider": "zhipu", "model": "glm-5.3-flash", "effort": "max"})
    provider, name, model = _build_provider(store.resolved())
    assert name == "zhipu" and model == "glm-5.3-flash"
    assert provider.reasoning_effort == "max"


def test_engine_shim_auto_sends_nothing(tmp_path):
    from web_ui.backend.services.agent.config_store import AgentConfigStore
    from web_ui.backend.services.agent.engine import _build_provider
    store = AgentConfigStore(path=str(tmp_path / "c.json"))
    store.save({"provider": "zhipu", "effort": ""})  # auto
    provider, _, _ = _build_provider(store.resolved())
    assert provider.reasoning_effort is None


def test_engine_shim_ignores_effort_for_unsupported_provider(tmp_path):
    from web_ui.backend.services.agent.config_store import AgentConfigStore
    from web_ui.backend.services.agent.engine import _build_provider
    store = AgentConfigStore(path=str(tmp_path / "c.json"))
    store.save({"provider": "zhipu", "effort": "max"})
    # deepseek: effort irrelevant — provider builds fine, no error
    store.save({"provider": "deepseek", "effort": "max"})
    provider, name, _ = _build_provider(store.resolved())
    assert name == "deepseek"
    assert not hasattr(provider, "reasoning_effort") or provider.reasoning_effort is None


# ------------------------------------------------------------------ API layer

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Backend app with agent config pointed at a temp file."""
    from web_ui.backend.services.agent import config_store as cs
    monkeypatch.setattr(cs, "_store", cs.AgentConfigStore(path=str(tmp_path / "c.json")))
    from web_ui.backend.services.agent import engine as engine_mod
    engine_mod._engine = None
    from fastapi.testclient import TestClient
    from web_ui.backend.main import app
    with TestClient(app) as c:
        yield c


def test_effort_options_per_provider(client):
    cfg = client.get("/api/agent/config").json()["config"]

    # zhipu (current app provider) -> the four GLM effort levels
    if cfg["effective_provider"] == "zhipu":
        assert cfg["effort_options"] == ["default", "low", "high", "max"]
        assert cfg["effort_supported"] is True
    assert cfg["effort"] == ""  # auto by default

    def options_for(provider, model):
        client.put("/api/agent/config", json={"provider": provider, "model": model, "effort": ""})
        c = client.get("/api/agent/config").json()["config"]
        return c["effort_options"], c["effort_supported"]

    assert options_for("deepseek", "deepseek-chat") == ([], False)
    assert options_for("openai", "gpt-4o") == ([], False)          # non-reasoning model
    opts, ok = options_for("openai", "o4-mini")                     # reasoning model
    assert ok and "high" in opts and "minimal" in opts
    client.put("/api/agent/config", json={"provider": "", "model": ""})


def test_effort_roundtrip_via_api(client):
    r = client.put("/api/agent/config", json={"effort": "max"}).json()
    assert r["effort"] == "max"
    r = client.get("/api/agent/config").json()["config"]
    assert r["effort"] == "max"
    client.put("/api/agent/config", json={"effort": ""})  # back to auto
    assert client.get("/api/agent/config").json()["config"]["effort"] == ""
