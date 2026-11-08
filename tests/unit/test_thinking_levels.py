"""
Per-provider thinking levels (Settings-driven) + the Strata local provider.

Payloads are captured by monkeypatching llm_engine.http_session.post.
"""
import json
import sys
from types import SimpleNamespace

import pytest

import core.llm_engine as lle
from core.llm_engine import (
    LLMProvider,
    OpenAIProvider,
    OllamaProvider,
    QwenProvider,
    StrataProvider,
    ZAIProvider,
    LMStudioProvider,
    get_provider,
)


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload

    @property
    def text(self):
        return json.dumps(self._payload)


def _capture(monkeypatch, content="ok"):
    """Capture the JSON body posted through llm_engine.http_session."""
    captured = {}

    def _post(url, json=None, headers=None, timeout=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({
            "choices": [{"message": {"content": content}}],
            "output": {"text": content},
            "response": content,
        })

    monkeypatch.setattr(lle, "http_session", SimpleNamespace(post=_post))
    return captured


def test_set_thinking_level_base_semantics():
    class _P(LLMProvider):
        def ask(self, prompt, response_format=None):
            return ""

        @property
        def name(self):
            return "P"

        @property
        def requires_api_key(self):
            return False

    p = _P()
    assert p.set_thinking_level("Turbo ") is True
    assert p.thinking_level == "turbo"  # raw passthrough, lowercased
    assert p.set_thinking_level("default") is False
    assert p.thinking_level is None
    assert p.set_thinking_level("") is False
    assert p.set_thinking_level(None) is False


def test_zai_payload_levels(monkeypatch):
    cap = _capture(monkeypatch)

    p = ZAIProvider(api_key="k", model="glm-5.3")
    p.set_thinking_level("low")
    p.ask("hi")
    assert cap["json"]["thinking"] == {"type": "enabled", "effort": "low"}

    p.set_thinking_level("off")
    p.ask("hi")
    assert cap["json"]["thinking"] == {"type": "disabled"}

    p.set_thinking_level("turbo")  # custom passes through
    p.ask("hi")
    assert cap["json"]["thinking"] == {"type": "enabled", "effort": "turbo"}

    p.set_thinking_level(None)
    p.ask("hi")
    assert "thinking" not in cap["json"]


def test_zai_disable_thinking_precedence(monkeypatch):
    cap = _capture(monkeypatch)
    p = ZAIProvider(api_key="k", model="glm-5.3")
    p.set_thinking_level("max")
    p.disable_thinking()  # story generation must win over the configured level
    p.ask("hi")
    assert cap["json"]["thinking"] == {"type": "disabled"}


def test_openai_custom_and_disabled(monkeypatch):
    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)

            class _Msg:
                content = "ok"

            class _Choice:
                message = _Msg()

            class _Resp:
                choices = [_Choice()]

            return _Resp()

    class _Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=_Completions())

    # The openai package isn't installed in every environment; inject a stub
    # so `import openai` inside ask() resolves to our capturing client.
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_Client))

    p = OpenAIProvider(api_key="k", model="gpt-5.1")
    p.set_thinking_level("none")  # custom value passes through verbatim
    p.ask("hi")
    assert captured["reasoning_effort"] == "none"

    p2 = OpenAIProvider(api_key="k", model="gpt-5.1")
    p2.set_thinking_level("high")
    p2.disable_thinking()
    p2.ask("hi")
    assert captured["reasoning_effort"] == "none"  # disable wins over level


def test_ollama_openai_compat_payload(monkeypatch):
    """Ollama now posts to the OpenAI-compatible /v1 endpoint; the thinking
    format comes from the model declaration (default: openai ->
    reasoning_effort)."""
    cap = _capture(monkeypatch)

    p = OllamaProvider(api_key="", model="qwen3")
    p.provider_key = "ollama"
    p.set_thinking_level("low")
    p.ask("hi")
    assert cap["url"].endswith("/v1/chat/completions")
    assert cap["json"]["messages"][0]["content"] == "hi"
    assert cap["json"]["reasoning_effort"] == "low"

    # no level configured -> no thinking field at all
    p.set_thinking_level(None)
    p.ask("hi")
    assert "reasoning_effort" not in cap["json"] and "think" not in cap["json"]


def test_qwen_enable_thinking(monkeypatch):
    """Qwen now posts to DashScope compatible-mode; the qwen format sends
    top-level enable_thinking (class default for unregistered models)."""
    cap = _capture(monkeypatch)

    p = QwenProvider(api_key="k", model="qwen3-max")
    p.provider_key = "qwen"
    p.set_thinking_level("off")
    p.ask("hi")
    assert cap["url"].endswith("/compatible-mode/v1/chat/completions")
    assert cap["json"]["enable_thinking"] is False
    assert cap["json"]["messages"][0]["content"] == "hi"

    p.set_thinking_level("on")
    p.ask("hi")
    assert cap["json"]["enable_thinking"] is True

    p.set_thinking_level(None)
    p.ask("hi")
    assert "enable_thinking" not in cap["json"]


def test_lmstudio_reasoning_effort_passthrough(monkeypatch):
    cap = _capture(monkeypatch)

    p = LMStudioProvider(api_key="", model="gpt-oss")
    p.set_thinking_level("low")
    p.ask("hi")
    assert cap["json"]["reasoning_effort"] == "low"
    assert cap["url"].endswith("/v1/chat/completions")

    p.set_thinking_level("off")  # openai format: "none" disables reasoning
    p.ask("hi")
    assert cap["json"]["reasoning_effort"] == "none"

    p.set_thinking_level(None)
    p.ask("hi")
    assert "reasoning_effort" not in cap["json"]


def test_strata_provider_defaults_and_payload(monkeypatch):
    cap = _capture(monkeypatch)

    p = StrataProvider(api_key="", model="strata")
    assert p.base_url == "http://127.0.0.1:8080"
    assert p.name == "Strata"
    assert p.requires_api_key is False

    p.set_thinking_level("medium")
    p.ask("hi")
    assert cap["json"]["reasoning_effort"] == "medium"


def _shim(**overrides):
    import config
    shim = SimpleNamespace()
    for attr in dir(config):
        if attr.isupper():
            setattr(shim, attr, getattr(config, attr))
    for k, v in overrides.items():
        setattr(shim, k, v)
    return shim


def test_get_provider_strata_branch():
    p = get_provider("strata", config_module=_shim(
        STRATA_BASE_URL="http://127.0.0.1:8080", STRATA_MODEL="strata",
        STRATA_THINKING_LEVEL=None))
    assert isinstance(p, StrataProvider)
    assert p.thinking_level is None

    p2 = get_provider("strata", config_module=_shim(STRATA_THINKING_LEVEL="high"))
    assert p2.thinking_level == "high"


def test_get_provider_wires_thinking_levels():
    o = get_provider("ollama", config_module=_shim(OLLAMA_THINKING_LEVEL="off"))
    assert o.thinking_level == "off"
    q = get_provider("qwen", config_module=_shim(QWEN_THINKING_LEVEL="on"))
    assert q.thinking_level == "on"
    g = get_provider("gemini", config_module=_shim(GEMINI_THINKING_LEVEL="high"))
    assert g.thinking_level == "high"
    z = get_provider("zhipu", config_module=_shim(ZHIPU_REASONING_EFFORT="off"))
    assert z.thinking_level == "off"


def test_config_thinking_registry():
    import config
    assert set(config.THINKING_CONFIG_FIELDS) == {
        "gemini", "openai", "zhipu", "deepseek", "qwen", "kimi",
        "ollama", "lmstudio", "strata"}
    assert config.THINKING_LEVELS == ["off", "minimal", "low", "medium", "high", "xhigh"]
    # standard levels offered uniformly for every provider
    for prov in ("gemini", "openai", "zhipu", "deepseek", "qwen", "kimi",
                 "ollama", "lmstudio", "strata"):
        assert config.THINKING_OPTIONS[prov] == config.THINKING_LEVELS, prov
    assert config.THINKING_CONFIG_FIELDS["deepseek"] == "deepseek_thinking_level"
    assert config.THINKING_CONFIG_FIELDS["kimi"] == "kimi_thinking_level"
    # every field in THINKING_CONFIG_FIELDS must be an editable _CONFIG_FIELDS entry
    from web_ui.backend.api.config_api import _CONFIG_FIELDS
    for field in config.THINKING_CONFIG_FIELDS.values():
        assert field in _CONFIG_FIELDS, field


def test_shot_planner_counts_strata_as_local(monkeypatch):
    import core.shot_planner as sp
    monkeypatch.setattr(sp, "LLM_PROVIDER", "strata")
    assert sp.is_local_provider() is True
    monkeypatch.setattr(sp, "LLM_PROVIDER", "gemini")
    assert sp.is_local_provider() is False


import pytest


@pytest.fixture
def real_registry():
    """Ensure the real project models.json is loaded (and restore after)."""
    from core import model_registry
    model_registry.load_models_config(force=True)
    yield
    model_registry.load_models_config(force=True)


def test_standard_levels_map_end_to_end(real_registry, monkeypatch):
    """Dropdown levels map through thinkingLevelMap for every provider kind.

    Expectations are derived from the live models.json (user-owned data):
    a level mapped to a value returns it; mapped to null returns None
    (unsupported -> nothing sent); absent from the map passes through.
    """
    import config
    from core import model_registry
    model_registry.load_models_config(force=True)

    STD = config.THINKING_LEVELS
    for provider, entry in model_registry.load_models_config()["providers"].items():
        for m in entry.get("models", []):
            tm = m.get("thinkingLevelMap") or {}
            reasoning = bool(m.get("reasoning", False))
            for lvl in STD:
                if not reasoning:
                    expected = None  # reasoning: false -> nothing ever sent
                else:
                    expected = tm.get(lvl) if lvl in tm else lvl
                assert model_registry.map_thinking_level(provider, m["id"], lvl) == expected,                     (provider, m["id"], lvl)

    # null-mapped models (non-reasoning) support nothing
    for lvl in STD:
        assert model_registry.map_thinking_level("openai", "gpt-4o", lvl) is None
        assert model_registry.map_thinking_level("kimi", "kimi-labs", lvl) is None


def test_nonreasoning_model_level_sends_nothing(real_registry, monkeypatch):
    """Selecting a level for a non-reasoning model sends no thinking field."""
    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content="ok"))])

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kw: SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))))
    p = lle.get_provider("openai", config_module=_shim(
        OPENAI_BASE_URL="", OPENAI_MODEL="gpt-4o", OPENAI_REASONING_EFFORT="high"))
    p.ask("hi")
    assert "reasoning_effort" not in captured


def test_deepseek_kimi_thinking_fields_wired(real_registry):
    p = lle.get_provider("deepseek", config_module=_shim(
        DEEPSEEK_BASE_URL="", DEEPSEEK_THINKING_LEVEL="low"))
    assert p.thinking_level == "low" and p.provider_key == "deepseek"
    p2 = lle.get_provider("kimi", config_module=_shim(
        KIMI_THINKING_LEVEL="xhigh"))
    assert p2.thinking_level == "xhigh" and p2.provider_key == "kimi"
