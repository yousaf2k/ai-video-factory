"""
models.json (PI format) model registry: loading, env-ref apiKey resolution,
thinkingLevelMap application, and the registry-driven get_provider rewire.
"""
import json
import os
from types import SimpleNamespace

import pytest

import core.llm_engine as lle
from core import model_registry


@pytest.fixture
def real_registry():
    """Ensure the real project models.json is loaded (and restore after)."""
    model_registry.load_models_config(force=True)
    yield
    model_registry.load_models_config(force=True)


def _shim(**overrides):
    import config
    s = SimpleNamespace()
    for attr in dir(config):
        if attr.isupper():
            setattr(s, attr, getattr(config, attr))
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


class _Capture:
    """Capture JSON bodies posted through llm_engine.http_session."""

    def __init__(self, monkeypatch):
        self.bodies = []
        self.urls = []

        def _post(url, json=None, headers=None, timeout=None, **kwargs):
            self.bodies.append(json)
            self.urls.append(url)
            return SimpleNamespace(
                status_code=200, text="{}",
                json=lambda: {
                    "choices": [{"message": {"content": "ok"}}],
                    "output": {"text": "ok"},
                    "response": "ok",
                })

        monkeypatch.setattr(lle, "http_session", SimpleNamespace(post=_post))

    @property
    def last(self):
        return self.bodies[-1]

    @property
    def last_url(self):
        return self.urls[-1]


# ---------------------------------------------------------------- file loading

def test_models_json_loads_all_providers(real_registry):
    providers = model_registry.load_models_config()["providers"]
    for p in ("gemini", "openai", "zhipu", "deepseek", "qwen",
              "kimi", "ollama", "lmstudio", "strata"):
        assert p in providers, p
        assert providers[p].get("baseUrl")
        assert providers[p].get("api")


def test_model_ids_from_file(real_registry):
    assert model_registry.get_model_ids("zhipu") == ["glm-5.3", "glm-5.3-flash"]
    assert model_registry.get_model_ids("openai") == ["gpt-4o", "gpt-5.1"]
    assert model_registry.get_model_ids("nope") == []


def test_thinking_format_metadata(real_registry):
    glm = model_registry.get_model_entry("zhipu", "glm-5.3")
    assert glm["compat"]["thinkingFormat"] == "zai"
    assert glm["reasoning"] is True
    gpt5 = model_registry.get_model_entry("openai", "gpt-5.1")
    assert gpt5["compat"]["thinkingFormat"] == "openai"
    gpt4 = model_registry.get_model_entry("openai", "gpt-4o")
    assert gpt4["reasoning"] is False


def test_resolve_api_key_ref_shapes():
    assert model_registry.resolve_api_key_ref("${GEMINI_API_KEY}") == ("GEMINI_API_KEY", True)
    assert model_registry.resolve_api_key_ref("$OPENAI_API_KEY") == ("OPENAI_API_KEY", True)
    assert model_registry.resolve_api_key_ref("none") == (None, True)
    assert model_registry.resolve_api_key_ref("") == (None, True)
    assert model_registry.resolve_api_key_ref(None) == (None, True)


def test_get_api_key_from_env(real_registry, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    assert model_registry.get_api_key("gemini") == "test-key-123"
    # local providers use the "none" literal -> empty key
    assert model_registry.get_api_key("ollama") == ""
    assert model_registry.get_api_key("strata") == ""


# ------------------------------------------------------- thinking level maps

def test_map_thinking_level_mapped(real_registry):
    import config
    # Expectations are derived from the live models.json (user-owned data)
    glm_map = model_registry.get_model_entry("zhipu", "glm-5.3")["thinkingLevelMap"]
    for lvl in config.THINKING_LEVELS:
        expected = glm_map.get(lvl)
        expected = expected if lvl in glm_map else lvl  # missing key passes through
        assert model_registry.map_thinking_level("zhipu", "glm-5.3", lvl) == expected
    # gpt-5.1 declares openai format with off -> "none"
    gpt_map = model_registry.get_model_entry("openai", "gpt-5.1")["thinkingLevelMap"]
    assert model_registry.map_thinking_level("openai", "gpt-5.1", "off") == gpt_map["off"]


def test_map_thinking_level_null_unsupported(real_registry):
    # deepseek-reasoner maps every level to null -> unsupported
    assert model_registry.map_thinking_level("deepseek", "deepseek-reasoner", "high") is None


def test_map_thinking_level_custom_passthrough(real_registry):
    # values absent from the map (custom levels) pass through unchanged
    assert model_registry.map_thinking_level("zhipu", "glm-5.3", "turbo") == "turbo"
    # models/providers without a registry entry pass through
    assert model_registry.map_thinking_level("zhipu", "unknown-model", "high") == "high"
    assert model_registry.map_thinking_level("nope", "x", "low") == "low"


# ------------------------------------------------- get_provider registry-driven

def test_get_provider_base_url_from_models_json(real_registry):
    p = lle.get_provider("strata", config_module=_shim(STRATA_BASE_URL=""))
    assert p.base_url == "http://127.0.0.1:8080"  # from models.json
    assert p.provider_key == "strata"


def test_get_provider_base_url_setting_overrides_file(real_registry):
    p = lle.get_provider("strata", config_module=_shim(STRATA_BASE_URL="http://1.2.3.4:9"))
    assert p.base_url == "http://1.2.3.4:9"


def test_get_provider_default_model_from_file(real_registry):
    p = lle.get_provider("zhipu", config_module=_shim(ZHIPU_BASE_URL="", ZHIPU_MODEL=""))
    assert p.model == "glm-5.3"  # first model in models.json
    assert p.provider_key == "zhipu"


def test_get_provider_configured_model_and_custom_ids(real_registry):
    p = lle.get_provider("zhipu", config_module=_shim(ZHIPU_BASE_URL="", ZHIPU_MODEL="glm-5.3-flash"))
    assert p.model == "glm-5.3-flash"
    # custom id not listed in the file still works
    p2 = lle.get_provider("zhipu", config_module=_shim(ZHIPU_BASE_URL="", ZHIPU_MODEL="my-fine-tune"))
    assert p2.model == "my-fine-tune"


def test_get_provider_ollama_keyless(real_registry):
    p = lle.get_provider("ollama", config_module=_shim(OLLAMA_BASE_URL="", OLLAMA_MODEL=""))
    assert p.model == "llama2"  # first model in the file
    assert p.api_key == ""


# ------------------------------------------------- thinkingLevelMap in payloads

def test_zai_payload_uses_level_map(real_registry, monkeypatch):
    import config
    cap = _Capture(monkeypatch)
    glm_map = model_registry.get_model_entry("zhipu", "glm-5.3")["thinkingLevelMap"]
    # pick a standard level the model supports (non-null map value)
    lvl = next(l for l in config.THINKING_LEVELS if glm_map.get(l) not in (None, "off"))
    p = lle.get_provider("zhipu", config_module=_shim(
        ZHIPU_BASE_URL="", ZHIPU_MODEL="glm-5.3", ZHIPU_REASONING_EFFORT=lvl))
    p.ask("hi")
    # zai format: enabled + the mapped effort value
    assert cap.last["thinking"] == {"type": "enabled", "effort": glm_map[lvl]}


def test_openai_payload_maps_off_to_none(real_registry, monkeypatch):
    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content="ok"))])

    monkeypatch.setitem(__import__("sys").modules, "openai",
                        SimpleNamespace(OpenAI=lambda **kw: SimpleNamespace(
                            chat=SimpleNamespace(completions=_Completions()))))

    p = lle.get_provider("openai", config_module=_shim(
        OPENAI_BASE_URL="", OPENAI_MODEL="gpt-5.1", OPENAI_REASONING_EFFORT="off"))
    p.ask("hi")
    # gpt-5.1 maps off -> none via thinkingLevelMap
    assert captured["reasoning_effort"] == "none"


def test_ollama_payload_uses_level_map(real_registry, monkeypatch):
    """ollama/qwen3 declares the openai format: levels dispatch as
    reasoning_effort; null-mapped levels (off/minimal) send nothing."""
    cap = _Capture(monkeypatch)
    p = lle.get_provider("ollama", config_module=_shim(
        OLLAMA_BASE_URL="", OLLAMA_MODEL="qwen3", OLLAMA_THINKING_LEVEL="low"))
    p.ask("hi")
    assert cap.last["reasoning_effort"] == "low"
    assert cap.last["messages"][0]["content"] == "hi"
    assert cap.last_url.endswith("/v1/chat/completions")

    p2 = lle.get_provider("ollama", config_module=_shim(
        OLLAMA_BASE_URL="", OLLAMA_MODEL="qwen3", OLLAMA_THINKING_LEVEL="off"))
    p2.ask("hi")
    assert "reasoning_effort" not in cap.last  # off is null-mapped for qwen3


# ------------------------------------------------------- missing-file fallback

def test_missing_models_json_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(model_registry, "_models_config_path",
                        lambda: os.path.join(os.getcwd(), "definitely-missing.json"))
    try:
        reg = model_registry.load_models_config(force=True)
        assert reg == {"providers": {}}
        assert model_registry.get_model_ids("zhipu") == []
        # get_provider falls back to class defaults
        p = lle.get_provider("strata", config_module=_shim(STRATA_BASE_URL="", STRATA_MODEL=""))
        assert p.base_url == "http://127.0.0.1:8080"  # StrataProvider ctor default
        assert p.model == "strata"                    # get_provider fallback_model
    finally:
        model_registry.load_models_config(force=True)


def test_invalid_models_json_degrades_gracefully(monkeypatch, tmp_path):
    bad = tmp_path / "models.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(model_registry, "_models_config_path", lambda: str(bad))
    try:
        reg = model_registry.load_models_config(force=True)
        assert reg == {"providers": {}}
    finally:
        model_registry.load_models_config(force=True)


# ------------------------------------------------- supported level filtering

def test_supported_thinking_levels_filter_nulls(real_registry):
    import config
    STD = config.THINKING_LEVELS

    def expected(provider, model_id):
        m = model_registry.get_model_entry(provider, model_id)
        if not m:
            return STD
        if not m.get("reasoning", False):
            return []  # reasoning: false -> model cannot think
        tm = m.get("thinkingLevelMap")
        if not isinstance(tm, dict):
            return STD
        return [l for l in STD if tm.get(l) is not None]

    # expectations derived from the live file for every registered model
    for provider, entry in model_registry.load_models_config()["providers"].items():
        for m in entry.get("models", []):
            assert model_registry.supported_thinking_levels(provider, m["id"]) ==                 expected(provider, m["id"]), (provider, m["id"])
    # unknown model / provider -> no map -> all levels pass through
    assert model_registry.supported_thinking_levels("openai", "o4-mini") == STD
    assert model_registry.supported_thinking_levels("nope", "x") == STD


def test_thinking_level_maps_payload(real_registry):
    maps = model_registry.get_thinking_level_maps()
    providers = model_registry.load_models_config()["providers"]
    # every model with a map is exposed verbatim from the live file
    for provider, entry in providers.items():
        for m in entry.get("models", []):
            if isinstance(m.get("thinkingLevelMap"), dict):
                assert maps[provider][m["id"]] == m["thinkingLevelMap"], (provider, m["id"])
    # null entries survive the round-trip (used by the UI to hide levels)
    assert any(v is None
               for model_maps in maps.values()
               for tm in model_maps.values()
               for v in tm.values())


def test_config_api_thinking_options_filtered(real_registry):
    import asyncio
    import config
    from web_ui.backend.api import config_api
    # asyncio.run: the main thread's loop may have been closed by earlier tests
    cfg = asyncio.run(config_api.get_config())
    # options per provider == levels its configured model supports (live file)
    for provider in cfg["thinking_options"]:
        model_attr = "GEMINI_TEXT_MODEL" if provider == "gemini" else f"{provider.upper()}_MODEL"
        model = getattr(config, model_attr, "") or ""
        assert cfg["thinking_options"][provider] ==             model_registry.supported_thinking_levels(provider, model), provider
    # full maps served for live UI filtering
    gpt_map = model_registry.get_model_entry("openai", "gpt-5.1")["thinkingLevelMap"]
    assert cfg["thinking_level_maps"]["openai"]["gpt-5.1"] == gpt_map
