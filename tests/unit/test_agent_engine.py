"""
Unit tests for the agent engine: tool-call parsing and the agentic loop with a
scripted fake LLM provider.
"""
import asyncio
import json

import pytest

from web_ui.backend.services.agent import engine as engine_mod
from web_ui.backend.services.agent.config_store import AgentConfigStore
from web_ui.backend.services.agent.conversations import ConversationStore
from web_ui.backend.services.agent.engine import AgentEngine, parse_tool_call, _clean_final_answer
from web_ui.backend.services.agent.mcp_client import MCPManager
from web_ui.backend.services.agent.skills import SkillStore


# ----------------------------------------------------------------- parsing

def test_parse_fenced_tool_call():
    text = 'Sure, checking.\n```tool_call\n{"tool": "get_shot", "arguments": {"project_id": "p", "shot": 1}}\n```'
    call = parse_tool_call(text)
    assert call == {"tool": "get_shot", "arguments": {"project_id": "p", "shot": 1}}


def test_parse_prefix_tool_call():
    text = 'TOOL_CALL: {"tool": "list_projects", "arguments": {}}'
    assert parse_tool_call(text)["tool"] == "list_projects"


def test_parse_bare_json_reply():
    text = '{"tool": "read_file", "arguments": {"path": "a.txt"}}'
    assert parse_tool_call(text)["tool"] == "read_file"


def test_parse_trailing_commas_repaired():
    text = '```tool_call\n{"tool": "x", "arguments": {"a": 1,},}\n```'
    assert parse_tool_call(text) == {"tool": "x", "arguments": {"a": 1}}


def test_parse_final_answer_returns_none():
    assert parse_tool_call("The shot now shows the character running.") is None
    assert parse_tool_call("") is None
    assert parse_tool_call("```json\n{\"scene_count\": 4}\n```") is None


# ------------------------------------------------- final answer cleanup

def test_clean_unescapes_literal_newlines():
    """The exact 'not readable' case: model escaped every newline."""
    raw = "**1. Status:**\\n- agent OK\\n- key invalid\\n\\nDone."
    assert _clean_final_answer(raw) == "**1. Status:**\n- agent OK\n- key invalid\n\nDone."


def test_clean_extracts_json_string_wrapper():
    raw = '"line one\\nline two with \\"quotes\\""'
    assert _clean_final_answer(raw) == 'line one\nline two with "quotes"'


def test_clean_extracts_json_object_wrapper():
    raw = '{"answer": "**Summary**\\n- fixed shot 4\\n- queued regen"}'
    assert _clean_final_answer(raw) == "**Summary**\n- fixed shot 4\n- queued regen"


def test_clean_leaves_real_newlines_and_code_verbatim():
    text = "explanation\n\n```python\ns = \"a\\nb\"\n```\nmore"
    assert _clean_final_answer(text) == text


def test_clean_leaves_plain_text_untouched():
    assert _clean_final_answer("plain answer") == "plain answer"
    assert _clean_final_answer("") == ""


def test_engine_final_answer_is_cleaned(agent_env, monkeypatch):
    eng, conversations = agent_env
    conversation = conversations.create()
    _patch_provider(monkeypatch, eng, [
        '```tool_call\n{"tool": "list_skills", "arguments": {}}\n```',
        "**Result:**\\n- fix-shot-prompt\\n- new-project-wizard",
    ])
    result = asyncio.run(eng.run(conversation["id"], "list skills"))
    assert result["answer"] == "**Result:**\n- fix-shot-prompt\n- new-project-wizard"
    stored = conversations.get(conversation["id"])
    assert stored["messages"][-1]["content"] == result["answer"]


# ------------------------------------------------------------------- loop

class FakeProvider:
    """Scripted provider: returns queued replies in order."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def ask(self, prompt, response_format=None):
        self.prompts.append(prompt)
        return self.replies.pop(0)


@pytest.fixture
def agent_env(tmp_path, monkeypatch):
    """Engine wired to temp stores, no MCP servers, no live LLM."""
    store = AgentConfigStore(path=str(tmp_path / "config.json"))
    conversations = ConversationStore(directory=str(tmp_path / "conversations"))
    skills = SkillStore(root=str(tmp_path / "skills"))

    eng = AgentEngine()
    eng.config_store = store
    eng.conversations = conversations
    eng.skills = skills
    eng.mcp = MCPManager()
    return eng, conversations


def _patch_provider(monkeypatch, eng, replies):
    fake = FakeProvider(replies)
    monkeypatch.setattr(eng, "build_provider", lambda: (fake, "fake", "fake-model"))
    return fake


def test_engine_runs_tool_then_answers(agent_env, monkeypatch):
    eng, conversations = agent_env
    conversation = conversations.create()
    # Turn 1: read a skill (real tool); Turn 2: final answer.
    _patch_provider(monkeypatch, eng, [
        '```tool_call\n{"tool": "list_skills", "arguments": {}}\n```',
        "I found the skills. **Done!**",
    ])

    events = []
    result = asyncio.run(eng.run(conversation["id"], "what skills exist?",
                                 on_event=events.append))

    assert result["answer"] == "I found the skills. **Done!**"
    assert result["steps"][0]["tool"] == "list_skills"
    assert result["steps"][0]["ok"] is True
    types = [e["type"] for e in events]
    assert "tool_start" in types and "tool_result" in types and "final" in types

    # Conversation persisted with user, tool-call, tool result and final answer.
    stored = conversations.get(conversation["id"])
    roles = [m["role"] for m in stored["messages"]]
    assert roles == ["user", "assistant", "tool_result", "assistant"]
    assert stored["messages"][1]["tool_call"]["tool"] == "list_skills"
    assert stored["title"].startswith("what skills exist")


def test_engine_feeds_tool_result_back(agent_env, monkeypatch):
    eng, conversations = agent_env
    conversation = conversations.create()
    fake = _patch_provider(monkeypatch, eng, [
        'TOOL_CALL: {"tool": "list_skills", "arguments": {}}',
        "final",
    ])
    asyncio.run(eng.run(conversation["id"], "the user task wording"))
    second_prompt = fake.prompts[1]
    assert "TOOL RESULT (list_skills, ok)" in second_prompt
    assert "Available tools" in fake.prompts[0]  # system prompt embedded
    assert "How to respond" in fake.prompts[0]


def test_engine_keeps_full_context_across_iterations(agent_env, monkeypatch):
    """Regression: after tool calls the model must still see the user's request,
    its own earlier tool calls AND every tool result (the 'agent forgot the task
    and echoed the overview' bug)."""
    eng, conversations = agent_env
    conversation = conversations.create()
    fake = _patch_provider(monkeypatch, eng, [
        '```tool_call\n{"tool": "list_skills", "arguments": {}}\n```',
        '```tool_call\n{"tool": "list_directors", "arguments": {}}\n```',
        "done analyzing",
    ])
    asyncio.run(eng.run(conversation["id"], "analyze shot 9 and shot 10 continuity"))

    prompt2, prompt3 = fake.prompts[1], fake.prompts[2]
    # 2nd iteration: user request still visible + own tool call + its result
    assert "analyze shot 9 and shot 10 continuity" in prompt2
    assert '"tool": "list_skills"' in prompt2          # raw fenced tool call kept
    assert "TOOL RESULT (list_skills, ok)" in prompt2
    # 3rd iteration: BOTH tool results and the request still present
    assert "analyze shot 9 and shot 10 continuity" in prompt3
    assert "TOOL RESULT (list_skills, ok)" in prompt3
    assert "TOOL RESULT (list_directors, ok)" in prompt3
    assert '"tool": "list_directors"' in prompt3


def test_engine_tool_error_is_reported_not_raised(agent_env, monkeypatch):
    eng, conversations = agent_env
    conversation = conversations.create()
    _patch_provider(monkeypatch, eng, [
        '```tool_call\n{"tool": "get_shot", "arguments": {"project_id": "nope", "shot": 1}}\n```',
        "Sorry — that project does not exist.",
    ])
    result = asyncio.run(eng.run(conversation["id"], "show shot 1"))
    assert result["steps"][0]["ok"] is False
    assert result["answer"].startswith("Sorry")


def test_engine_iteration_budget(agent_env, monkeypatch):
    eng, conversations = agent_env
    conversation = conversations.create()
    eng.config_store.save({"max_iterations": 2})
    loop_reply = '```tool_call\n{"tool": "list_skills", "arguments": {}}\n```'
    _patch_provider(monkeypatch, eng, [loop_reply, loop_reply, loop_reply])
    result = asyncio.run(eng.run(conversation["id"], "loop forever"))
    assert "tool-call budget" in result["answer"]
    assert len(result["steps"]) == 2


def test_engine_missing_conversation_creates_one(agent_env, monkeypatch):
    eng, conversations = agent_env
    _patch_provider(monkeypatch, eng, ["direct answer"])
    result = asyncio.run(eng.run("conv_does_not_exist", "hi"))
    assert result["conversation_id"] != "conv_does_not_exist"
    assert conversations.get(result["conversation_id"]) is not None


def test_engine_final_json_payload_is_not_tool_call(agent_env, monkeypatch):
    """A plain JSON reply without a 'tool' key must be treated as an answer."""
    eng, conversations = agent_env
    conversation = conversations.create()
    _patch_provider(monkeypatch, eng, ['{"summary": "3 scenes, 12 shots"}'])
    result = asyncio.run(eng.run(conversation["id"], "summarize"))
    assert json.loads(result["answer"])["summary"] == "3 scenes, 12 shots"


def test_tool_result_truncation_marker_is_instructive():
    import config as cfg_mod
    from web_ui.backend.services.agent.engine import AgentEngine
    limit = cfg_mod.AGENT_MAX_TOOL_RESULT_CHARS
    long_result = AgentEngine._stringify_result({"ok": True, "result": "x" * (limit + 5_000)})
    assert "RESULT TRUNCATED" in long_result
    assert "get_shot" in long_result  # tells the model how to narrow the query
    short = AgentEngine._stringify_result({"ok": True, "result": "x" * max(limit - 100, 10)})
    assert "TRUNCATED" not in short
    assert AgentEngine._stringify_result({"ok": False, "error": "boom"}) == "ERROR: boom"


# ------------------------------------------------------- context usage meter

def test_estimate_tokens_cjk_aware():
    from web_ui.backend.services.agent.engine import _estimate_tokens
    cjk = _estimate_tokens("你好世界")            # 4 CJK chars -> ~4 tokens
    latin = _estimate_tokens("hello world!")     # 12 chars -> ~3 tokens
    assert 3 <= cjk <= 5
    assert 2 <= latin <= 4
    assert _estimate_tokens("") == 0


def test_context_limit_override(monkeypatch):
    import web_ui.backend.services.agent.engine as engine_mod
    monkeypatch.setattr(engine_mod.config, "AGENT_CONTEXT_LIMIT_TOKENS", 8192)
    assert engine_mod._context_limit_tokens("zhipu") == 8192
    monkeypatch.setattr(engine_mod.config, "AGENT_CONTEXT_LIMIT_TOKENS", 0)
    assert engine_mod._context_limit_tokens("gemini") == 1_000_000
    assert engine_mod._context_limit_tokens("zhipu") == 128_000


def test_engine_emits_and_persists_context_usage(agent_env, monkeypatch):
    eng, conversations = agent_env
    conversation = conversations.create()
    _patch_provider(monkeypatch, eng, ["direct answer"])
    events = []
    result = asyncio.run(eng.run(conversation["id"], "hi", on_event=events.append))

    usage_events = [e for e in events if e["type"] == "context_usage"]
    assert usage_events, "context_usage event missing"
    usage = usage_events[0]
    assert usage["est_tokens"] > 0
    assert usage["limit_tokens"] > 0
    assert 0 < usage["percent"] < 100
    assert result["context"]["est_tokens"] == usage["est_tokens"]
    # Persisted on the conversation for reload
    stored = conversations.get(conversation["id"])
    assert stored["context_usage"]["est_tokens"] == usage["est_tokens"]
