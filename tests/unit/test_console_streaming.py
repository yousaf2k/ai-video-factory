"""
Console streaming of LLM output: OpenAI-compatible SSE streaming via
_post_chat, and the LLM_STREAM_TO_CONSOLE toggle.
"""
import json
import sys
from types import SimpleNamespace

import pytest

import config
import core.llm_engine as lle
from core import llm_call_log
from core.llm_engine import ZAIProvider


@pytest.fixture
def streaming_on(monkeypatch):
    """Re-enable console streaming (the autouse conftest fixture disables it
    for the offline suite's non-streaming mocks)."""
    monkeypatch.setattr(config, "LLM_STREAM_TO_CONSOLE", True)


def _shim(**overrides):
    s = SimpleNamespace()
    for attr in dir(config):
        if attr.isupper():
            setattr(s, attr, getattr(config, attr))
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _sse_response(chunks, status=200):
    """Fake streaming http response yielding OpenAI-style SSE lines."""
    lines = []
    for c in chunks:
        lines.append("data: " + json.dumps(
            {"choices": [{"delta": {"content": c}}]}))
    lines.append("data: [DONE]")
    return SimpleNamespace(
        status_code=status,
        text="{}" if status == 200 else "error",
        iter_lines=lambda decode_unicode=True: iter(lines),
    )


class _Capture:
    def __init__(self, monkeypatch, response):
        self.bodies = []
        self.record = {}

        def _post(url, json=None, headers=None, timeout=None, stream=False, **kwargs):
            self.bodies.append(json)
            self.stream_flag = stream
            return response

        monkeypatch.setattr(lle, "http_session", SimpleNamespace(post=_post))
        monkeypatch.setattr(llm_call_log, "_append",
                            lambda record: self.record.update(record))


def test_streaming_prints_tokens_and_returns_full_text(monkeypatch, capsys, streaming_on):
    resp = _sse_response(["Hello", " world", "!"])
    cap = _Capture(monkeypatch, resp)

    p = ZAIProvider(api_key="k", model="glm-5.3")
    p.provider_key = "zhipu"
    p.set_thinking_level("low")
    out = p.ask("hi")

    assert out == "Hello world!"
    # request was sent with stream enabled
    assert cap.bodies[0]["stream"] is True
    # tokens were printed to the console as they arrived
    printed = capsys.readouterr().out
    assert "Hello" in printed and "world" in printed and "!" in printed
    # structured call log still records the full output
    assert cap.record["output"] == "Hello world!"


def test_streaming_disabled_uses_non_streaming_path(monkeypatch, capsys):
    resp = SimpleNamespace(
        status_code=200, text="{}",
        json=lambda: {"choices": [{"message": {"content": "full reply"}}]},
        iter_lines=lambda decode_unicode=True: iter([]),
    )
    cap = _Capture(monkeypatch, resp)

    p = ZAIProvider(api_key="k", model="glm-5.3")
    p.set_thinking_level("low")
    out = p.ask("hi")

    assert out == "full reply"
    assert cap.bodies[0].get("stream") in (False, None)  # not forced on
    assert "full reply" not in capsys.readouterr().out  # nothing echoed


def test_streaming_non_200_raises(monkeypatch):
    resp = _sse_response(["x"], status=500)
    _Capture(monkeypatch, resp)

    p = ZAIProvider(api_key="k", model="glm-5.3")
    with pytest.raises(Exception, match="HTTP 500"):
        p.ask("hi")


def test_streaming_skips_reasoning_and_empty_deltas(monkeypatch, capsys, streaming_on):
    # reasoning-only chunks (delta without content) produce no console output
    lines = [
        "data: " + json.dumps({"choices": [{"delta": {"reasoning_content": "thinking..."}}]}),
        "data: " + json.dumps({"choices": [{"delta": {"content": "answer"}}]}),
        "data: [DONE]",
    ]
    resp = SimpleNamespace(status_code=200, text="{}",
                           iter_lines=lambda decode_unicode=True: iter(lines))
    _Capture(monkeypatch, resp)

    p = ZAIProvider(api_key="k", model="glm-5.3")
    out = p.ask("hi")

    assert out == "answer"
    printed = capsys.readouterr().out
    assert "thinking..." not in printed
    assert "answer" in printed


def test_openai_sdk_streaming(monkeypatch, capsys, streaming_on):
    class _Delta:
        content = "token "

    class _Choice:
        delta = _Delta()

    class _Chunk:
        choices = [_Choice()]

    class _Stream:
        def __iter__(self):
            return iter([_Chunk(), _Chunk()])

    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Stream()

    class _Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_Client))

    p = lle.OpenAIProvider(api_key="k", model="gpt-5.1")
    p.set_thinking_level("low")
    out = p.ask("hi")

    assert out == "token token "
    assert captured["stream"] is True
    printed = capsys.readouterr().out
    assert "token" in printed


def test_toggle_matches_config(monkeypatch):
    monkeypatch.setattr(config, "LLM_STREAM_TO_CONSOLE", True)
    p = ZAIProvider(api_key="k", model="glm-5.3")
    assert p._console_stream_enabled() is True

    monkeypatch.setattr(config, "LLM_STREAM_TO_CONSOLE", False)
    assert p._console_stream_enabled() is False
