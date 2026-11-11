"""
Story generation disables LLM thinking/reasoning: provider-level
disable_thinking() behaviour.
"""
from core.llm_engine import LLMProvider, GeminiProvider, OpenAIProvider, ZAIProvider


def test_base_provider_disable_thinking_sets_flag():
    class _MinimalProvider(LLMProvider):
        def ask(self, prompt, response_format=None):
            return ""

        @property
        def name(self):
            return "Minimal"

        @property
        def requires_api_key(self):
            return False

    p = _MinimalProvider()
    assert getattr(p, "_thinking_disabled", False) is False
    assert p.disable_thinking() is True  # universal hard-off flag
    assert p._thinking_disabled is True
    # A provider with no declared thinking format still sends nothing either way
    assert p._thinking_request_fields() == {}


def test_openai_disable_thinking_sets_none_effort():
    p = OpenAIProvider(api_key="k", model="gpt-5")
    assert p.reasoning_effort is None
    assert p.disable_thinking() is True
    assert p.reasoning_effort == "none"


def test_zai_disable_thinking_sends_disabled_type():
    p = ZAIProvider(api_key="k", model="glm-5.3")
    assert p._thinking_disabled is False
    assert p.disable_thinking() is True
    assert p._thinking_disabled is True


def test_gemini_disable_thinking_sets_flag():
    p = GeminiProvider(api_key="k", model="gemini-3.5-flash-lite")
    assert p._thinking_disabled is False
    assert p.disable_thinking() is True
    assert p._thinking_disabled is True


def test_story_engine_story_builders_disable_thinking(monkeypatch):
    """build_story / build_story_then_vs_now / build_story_asmr_glass_cutting
    must call disable_thinking() on their freshly created provider."""
    import core.story_engine as se

    calls = []

    class _RecordingProvider:
        def disable_thinking(self):
            calls.append("off")
            return True

        def ask(self, prompt, response_format=None):
            return "{}"

    monkeypatch.setattr(se, "get_provider", lambda: _RecordingProvider())
    monkeypatch.setattr(se, "parse_story_json_with_retry", lambda provider, text: {"scenes": []})

    # disable_thinking() runs right after provider creation; the builders may
    # still raise downstream on the minimal "{}" story - that's irrelevant here.
    for builder, arg in (
        (se.build_story, "a calm ocean sunset"),
        (se.build_story_then_vs_now, "The Notebook"),
        (se.build_story_asmr_glass_cutting, "strawberry, apple"),
    ):
        try:
            builder(arg)
        except Exception:
            pass

    assert calls == ["off", "off", "off"]
