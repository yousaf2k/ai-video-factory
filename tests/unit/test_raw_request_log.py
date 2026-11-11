"""
Full raw LLM API request/response wire logging: headers redacted, JSON body
(incl. thinking fields) recorded into llm_calls.jsonl and llm_io.log.
"""
import json
import sys
from types import SimpleNamespace

import core.llm_engine as lle
from core import llm_call_log
from core.llm_engine import ZAIProvider


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
    """Capture posted payloads + the JSONL record written by complete_call."""

    def __init__(self, monkeypatch):
        self.bodies = []
        self.record = {}

        def _post(url, json=None, headers=None, timeout=None, **kwargs):
            self.bodies.append(json)
            return SimpleNamespace(status_code=200, text='{"choices": []}',
                                   json=lambda: {"choices": [{"message": {"content": "ok"}}],
                                                 "output": {"text": "ok"},
                                                 "response": "ok"})

        monkeypatch.setattr(lle, "http_session", SimpleNamespace(post=_post))
        monkeypatch.setattr(llm_call_log, "_append",
                            lambda record: self.record.update(record))


def test_redact_headers():
    red = llm_call_log.redact_headers({
        "Authorization": "Bearer sk-verysecret-value",
        "Content-Type": "application/json",
        "x-goog-api-key": "AIzaSecretKey123",
    })
    assert red["Content-Type"] == "application/json"
    assert "sk-verysecret-value" not in red["Authorization"]
    assert red["Authorization"].endswith("***")
    assert "AIzaSecretKey123" not in red["x-goog-api-key"]
    # the secret never appears anywhere in the redacted structure
    assert all("secret" not in str(v).lower() for k, v in red.items() if "content" not in k.lower())


def test_zai_raw_request_response_logged(monkeypatch):
    cap = _Capture(monkeypatch)
    p = lle.get_provider("zhipu", config_module=_shim(
        ZHIPU_BASE_URL="", ZHIPU_MODEL="glm-5.3", ZHIPU_REASONING_EFFORT="low",
        ZHIPU_API_KEY="sk-secret-key"))
    p.ask("hello")

    raw_req = cap.record.get("raw_request")
    assert raw_req, "raw_request missing from call log record"
    assert raw_req["url"].endswith("/chat/completions")
    assert raw_req["method"] == "POST"
    # auth redacted
    auth = raw_req["headers"]["Authorization"]
    assert "sk-secret-key" not in auth and auth.endswith("***")
    # exact JSON body incl. the dispatched thinking fields
    body = raw_req["body"]
    assert body["model"] == "glm-5.3"
    assert body["messages"][0]["content"] == "hello"
    assert body["thinking"] == {"type": "enabled", "effort": "low"}

    raw_res = cap.record.get("raw_response")
    assert raw_res and raw_res["status"] == 200
    assert "choices" in raw_res["body"]


def test_openai_sdk_raw_request_logged(monkeypatch):
    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)

            class _Resp:
                choices = [SimpleNamespace(message=SimpleNamespace(content="ok"))]

                def model_dump(self):
                    return {"id": "resp-1", "choices": [{"message": {"content": "ok"}}]}

            return _Resp()

    class _Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_Client))

    cap = _Capture(monkeypatch)
    p = lle.get_provider("openai", config_module=_shim(
        OPENAI_BASE_URL="", OPENAI_MODEL="gpt-5.1", OPENAI_REASONING_EFFORT="off",
        OPENAI_API_KEY="sk-openai-secret"))
    p.ask("hello")

    raw_req = cap.record.get("raw_request")
    assert raw_req and raw_req["url"].endswith("/chat/completions")
    assert raw_req["body"]["reasoning_effort"] == "none"  # gpt-5.1 map off->none
    assert "sk-openai-secret" not in json.dumps(raw_req["headers"])
    assert cap.record["raw_response"]["body"]["id"] == "resp-1"


def test_raw_logging_toggle_off(monkeypatch):
    monkeypatch.setattr(llm_call_log, "raw_enabled", lambda: False)
    cap = _Capture(monkeypatch)
    p = lle.get_provider("zhipu", config_module=_shim(
        ZHIPU_BASE_URL="", ZHIPU_MODEL="glm-5.3", ZHIPU_REASONING_EFFORT="low"))
    p.ask("hello")
    assert "raw_request" not in cap.record
    assert "raw_response" not in cap.record


def test_raw_logging_survives_sdk_objects_without_dump():
    # _jsonify falls back to str() for objects without model_dump/to_dict/dict
    class _Odd:
        def __str__(self):
            return "odd-object"

    assert llm_call_log._jsonify(_Odd()) == "odd-object"
    assert llm_call_log._jsonify({"a": 1}) == {"a": 1}
    assert llm_call_log._jsonify(None) is None
