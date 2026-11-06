"""
Unit tests for the agent configuration store (tool toggles, MCP servers).
"""
import json
import os

import pytest

from web_ui.backend.services.agent.config_store import AgentConfigStore


@pytest.fixture
def store(tmp_path):
    return AgentConfigStore(path=str(tmp_path / "agent" / "config.json"))


def test_defaults(store):
    cfg = store.load()
    assert cfg["provider"] == ""
    assert cfg["model"] == ""
    assert cfg["enabled_tools"] == {}
    assert cfg["mcp_servers"] == {}
    assert cfg["extra_system_prompt"] == ""


def test_save_and_reload(store):
    saved = store.save({
        "provider": "openai",
        "model": "gpt-4o",
        "max_iterations": 5,
        "enabled_tools": {"delete_project": True, "list_projects": False},
    })
    assert saved["provider"] == "openai"
    assert saved["enabled_tools"]["list_projects"] is False

    fresh = AgentConfigStore(path=store.path)
    assert fresh.load()["model"] == "gpt-4o"
    assert fresh.load()["enabled_tools"] == {"delete_project": True, "list_projects": False}


def test_partial_update_keeps_other_keys(store):
    store.save({"provider": "zhipu"})
    store.save({"model": "glm-5.3"})
    cfg = store.load()
    assert cfg["provider"] == "zhipu"
    assert cfg["model"] == "glm-5.3"


def test_invalid_values_sanitized(store):
    saved = store.save({
        "enabled_tools": {"ok": "yes", "bad": 123},  # type-coerced
        "mcp_servers": {
            "good": {"transport": "stdio", "command": "npx", "args": ["-y", "x"]},
            "": {"command": "no-name"},
            "notadict": None,
        },
    })
    assert saved["enabled_tools"] == {"ok": True, "bad": True}
    assert set(saved["mcp_servers"]) == {"good"}
    assert saved["mcp_servers"]["good"]["enabled"] is True


def test_resolved_falls_back_to_env(store, monkeypatch):
    monkeypatch.setattr("config.AGENT_LLM_PROVIDER", None, raising=False)
    monkeypatch.setattr("config.LLM_PROVIDER", "gemini", raising=False)
    monkeypatch.setattr("config.AGENT_MAX_ITERATIONS", 9, raising=False)
    monkeypatch.setattr("config.AGENT_ALLOW_DANGEROUS_TOOLS", False, raising=False)
    resolved = store.resolved()
    assert resolved["provider"] == "gemini"
    assert resolved["max_iterations"] == 9
    assert resolved["dangerous_tools_allowed"] is False


def test_json_file_is_valid(store):
    store.save({"provider": "qwen"})
    with open(store.path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["provider"] == "qwen"
    assert os.path.isfile(store.path)


def test_external_edits_reload_live(store):
    """Config edited outside this process (or vice versa) is picked up without restart."""
    store.save({"provider": "deepseek"})
    assert store.load()["provider"] == "deepseek"
    # Simulate another process rewriting the file.
    import time
    with open(store.path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["provider"] = "kimi"
    with open(store.path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    # mtime granularity on some filesystems is 1s — bump if needed.
    if os.path.getmtime(store.path) == store._cache_mtime:
        os.utime(store.path, (time.time() + 1,) * 2)
    assert store.load()["provider"] == "kimi"
