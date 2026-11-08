"""
Per-model thinking format dispatch: compat.thinkingFormat from models.json
drives the wire format; thinking_formats.build implements each PI format.
"""
import sys
from types import SimpleNamespace

import pytest

import core.llm_engine as lle
from core import model_registry, thinking_formats


@pytest.fixture
def real_registry():
    model_registry.load_models_config(force=True)
    yield
    model_registry.load_models_config(force=True)


class _Capture:
    def __init__(self, monkeypatch):
        self.bodies = []

        def _post(url, json=None, headers=None, timeout=None, **kwargs):
            self.bodies.append(json)
            return SimpleNamespace(status_code=200, text="{}",
                                   json=lambda: {"choices": [{"message": {"content": "ok"}}],
                                                 "output": {"text": "ok"},
                                                 "response": "ok"})

        monkeypatch.setattr(lle, "http_session", SimpleNamespace(post=_post))

    @property
    def last(self):
        return self.bodies[-1]


def _shim(**overrides):
    import config
    s = SimpleNamespace()
    for attr in dir(config):
        if attr.isupper():
            setattr(s, attr, getattr(config, attr))
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


# ------------------------------------------------------------ format builders

def test_build_openai():
    assert thinking_formats.build("openai", "medium") == {"reasoning_effort": "medium"}
    # mapped "none" passes verbatim (only the literal "off" is hard-off)
    assert thinking_formats.build("openai", "none") == {"reasoning_effort": "none"}
    assert thinking_formats.build("openai", "off") == {"reasoning_effort": "none"}


def test_build_zai():
    assert thinking_formats.build("zai", "low") == {"thinking": {"type": "enabled", "effort": "low"}}
    assert thinking_formats.build("zai", "off") == {"thinking": {"type": "disabled"}}


def test_build_deepseek():
    assert thinking_formats.build("deepseek", "high") == {"thinking": {"type": "enabled"}}
    assert thinking_formats.build("deepseek", "off") == {"thinking": {"type": "disabled"}}


def test_build_qwen_effort_support():
    """qwen format: boolean switch + reasoning_effort for real level values.
    Boolean map values (DashScope style) keep the request pure."""
    # off / boolean values -> pure enable_thinking (no effort field)
    assert thinking_formats.build("qwen", "off") == {"enable_thinking": False}
    assert thinking_formats.build("qwen", "false") == {"enable_thinking": False}
    assert thinking_formats.build("qwen", "none") == {"enable_thinking": False}
    assert thinking_formats.build("qwen", "true") == {"enable_thinking": True}
    # real effort levels -> switch on + effort passed through
    assert thinking_formats.build("qwen", "low") ==         {"enable_thinking": True, "reasoning_effort": "low"}
    assert thinking_formats.build("qwen", "high") ==         {"enable_thinking": True, "reasoning_effort": "high"}
    assert thinking_formats.build("qwen", "turbo") ==         {"enable_thinking": True, "reasoning_effort": "turbo"}


def test_build_bool_style_formats():
    # qwen / chat-template / qwen-chat-template / together / baseten
    assert thinking_formats.build("qwen", "true") == {"enable_thinking": True}
    assert thinking_formats.build("qwen", "false") == {"enable_thinking": False}
    assert thinking_formats.build("qwen", "off") == {"enable_thinking": False}
    assert thinking_formats.build("qwen", "high") ==         {"enable_thinking": True, "reasoning_effort": "high"}
    assert thinking_formats.build("qwen-chat-template", "off") == \
        {"chat_template_kwargs": {"enable_thinking": False}}
    assert thinking_formats.build("chat-template", "low") == \
        {"chat_template_kwargs": {"thinking": True}}
    assert thinking_formats.build("baseten", "low") == \
        {"chat_template_kwargs": {"thinking": True}}
    assert thinking_formats.build("together", "off") == {"reasoning": {"enabled": False}}
    assert thinking_formats.build("together", "low") == {"reasoning": {"enabled": True}}


def test_build_string_thinking():
    assert thinking_formats.build("string-thinking", "off") == {"thinking": False}
    assert thinking_formats.build("string-thinking", "true") == {"thinking": True}
    assert thinking_formats.build("string-thinking", "false") == {"thinking": False}
    # gpt-oss-style level strings pass through
    assert thinking_formats.build("string-thinking", "high") == {"thinking": "high"}


def test_build_openrouter_and_ant_ling():
    assert thinking_formats.build("openrouter", "high") == {"reasoning": {"effort": "high"}}
    assert thinking_formats.build("openrouter", "off") == {}  # no off representation
    assert thinking_formats.build("ant-ling", "high") == {"reasoning": {"effort": "high"}}
    assert thinking_formats.build("ant-ling", "off") == {}


def test_build_unknown_format():
    assert thinking_formats.build("moonshot-custom", "low") == {}
    assert thinking_formats.build(None, "low") == {}


# --------------------------------------------------- per-model format dispatch

def test_format_resolution_model_beats_class_default(real_registry):
    # class defaults
    assert lle.OpenAIProvider.default_thinking_format == "openai"
    assert lle.ZAIProvider.default_thinking_format == "zai"
    assert lle.DeepSeekProvider.default_thinking_format == "deepseek"
    assert lle.LMStudioProvider.default_thinking_format == "openai"
    # model declaration from models.json wins over the class default
    assert model_registry.get_thinking_format("zhipu", "glm-5.3") == "zai"
    # every model with a declared compat.thinkingFormat resolves to it
    declared = [(pid, m["id"], m["compat"]["thinkingFormat"])
                for pid, e in model_registry.load_models_config()["providers"].items()
                for m in e.get("models", [])
                if isinstance(m.get("compat"), dict) and m.get("compat").get("thinkingFormat")]
    assert declared  # the file declares at least one format
    for pid, mid, fmt in declared:
        assert model_registry.get_thinking_format(pid, mid) == fmt, (pid, mid)
    # models without compat -> None -> class default applies
    assert model_registry.get_thinking_format("openai", "gpt-4o") is None


def test_strata_running_qwen_model_uses_qwen_format(real_registry, monkeypatch):
    """The headline case: a qwen model served by Strata declares "qwen" and
    gets enable_thinking — NOT reasoning_effort."""
    cap = _Capture(monkeypatch)
    p = lle.get_provider("strata", config_module=_shim(
        STRATA_BASE_URL="", STRATA_MODEL="qwen3", STRATA_THINKING_LEVEL="high"))
    p.ask("hi")
    assert cap.last.get("enable_thinking") is True
    assert "reasoning_effort" not in cap.last


def test_deepseek_format_dispatch(real_registry, monkeypatch):
    cap = _Capture(monkeypatch)
    p = lle.get_provider("deepseek", config_module=_shim(
        DEEPSEEK_BASE_URL="", DEEPSEEK_MODEL="deepseek-reasoner"))
    p.disable_thinking()  # story generation hard-off -> thinking.type disabled
    p.ask("hi")
    assert cap.last["thinking"] == {"type": "disabled"}


def test_null_mapped_level_sends_nothing(real_registry, monkeypatch):
    """glm-5.3's map marks medium/minimal/xhigh null -> nothing is sent."""
    cap = _Capture(monkeypatch)
    p = lle.get_provider("zhipu", config_module=_shim(
        ZHIPU_BASE_URL="", ZHIPU_MODEL="glm-5.3", ZHIPU_REASONING_EFFORT="medium"))
    p.ask("hi")
    assert "thinking" not in cap.last


def test_model_without_format_sends_nothing(real_registry, monkeypatch):
    """Kimi models declare no thinkingFormat -> no thinking field ever."""
    cap = _Capture(monkeypatch)
    p = lle.get_provider("kimi", config_module=_shim(
        KIMI_API_KEY="k", KIMI_MODEL="kimi-labs", KIMI_THINKING_LEVEL="low"))
    p.ask("hi")
    assert "thinking" not in cap.last
    assert "reasoning_effort" not in cap.last


def test_strata_qwen_format_off_sends_enable_thinking_false(real_registry, monkeypatch):
    """Regression: Off on a qwen-format model served by Strata must send
    enable_thinking: false (previously the local-server off-skip swallowed it)."""
    cap = _Capture(monkeypatch)
    # simulated strata model: qwen format, map passes "off" through unmapped
    monkeypatch.setattr(model_registry, "get_thinking_format", lambda p, m: "qwen")
    monkeypatch.setattr(model_registry, "map_thinking_level", lambda p, m, l: l)
    p = lle.get_provider("strata", config_module=_shim(
        STRATA_BASE_URL="", STRATA_MODEL="any-qwen-model", STRATA_THINKING_LEVEL="off"))
    p.ask("hi")
    assert cap.last.get("enable_thinking") is False

    # On-level still maps through
    p2 = lle.get_provider("strata", config_module=_shim(
        STRATA_BASE_URL="", STRATA_MODEL="any-qwen-model", STRATA_THINKING_LEVEL="low"))
    p2.ask("hi")
    assert cap.last.get("enable_thinking") is True


def test_strata_story_disable_sends_enable_thinking_false(real_registry, monkeypatch):
    """Story-generation hard-off on a qwen-format local model also sends
    enable_thinking: false now (previously nothing)."""
    cap = _Capture(monkeypatch)
    monkeypatch.setattr(model_registry, "get_thinking_format", lambda p, m: "qwen")
    monkeypatch.setattr(model_registry, "map_thinking_level", lambda p, m, l: l)
    p = lle.get_provider("strata", config_module=_shim(
        STRATA_BASE_URL="", STRATA_MODEL="any-qwen-model"))
    p.disable_thinking()
    p.ask("hi")
    assert cap.last.get("enable_thinking") is False


def test_lmstudio_openai_format_off_sends_none(real_registry, monkeypatch):
    """openai format: Off -> reasoning_effort "none" (completely disables
    hidden reasoning tokens); maps adapt per model if needed."""
    cap = _Capture(monkeypatch)
    monkeypatch.setattr(model_registry, "get_thinking_format", lambda p, m: "openai")
    monkeypatch.setattr(model_registry, "map_thinking_level", lambda p, m, l: l)
    p = lle.get_provider("lmstudio", config_module=_shim(
        LMSTUDIO_BASE_URL="", LMSTUDIO_MODEL="any", LMSTUDIO_THINKING_LEVEL="off"))
    p.ask("hi")
    assert cap.last.get("reasoning_effort") == "none"


def test_strata_openai_format_levels_real_file(real_registry, monkeypatch):
    """The user's live strata model (qwen3.8-flash-next on Strata, openai
    format): every dropdown level lands as reasoning_effort in the request."""
    cap = _Capture(monkeypatch)
    # off -> reasoning_effort "none" (openai format has no enable_thinking)
    p = lle.get_provider("strata", config_module=_shim(
        STRATA_BASE_URL="", STRATA_MODEL="qwen3.8-flash-next-coder-iq1_m",
        STRATA_THINKING_LEVEL="off"))
    p.ask("hi")
    assert cap.last.get("reasoning_effort") == "none"
    assert "enable_thinking" not in cap.last

    # levels -> reasoning_effort passed through verbatim (identity map)
    for level, expected in (("low", "low"), ("medium", "medium"), ("high", "high")):
        p = lle.get_provider("strata", config_module=_shim(
            STRATA_BASE_URL="", STRATA_MODEL="qwen3.8-flash-next-coder-iq1_m",
            STRATA_THINKING_LEVEL=level))
        p.ask("hi")
        assert cap.last.get("reasoning_effort") == expected, level
        assert "enable_thinking" not in cap.last
