"""
AI Agent Assistant engine.

A provider-agnostic ReAct-style agent loop: the LLM answers either with plain
text (final answer) or with a JSON tool call, which is executed and fed back
until a final answer or the iteration budget is exhausted. Works with every
LLM provider supported by core.llm_engine (native function-calling is not
required — tool calls travel as structured JSON in the prompt).

Events (for the WebSocket UI):
    llm_start        – an LLM call started (iteration n)
    tool_start       – {tool, arguments}
    tool_result      – {tool, ok, result|error}
    final            – {content} the agent's answer
    error            – {message}
"""
import asyncio
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# provider -> (model attr, api key attr, base url attr)
_PROVIDER_ATTRS = {
    "gemini": ("GEMINI_TEXT_MODEL", "GEMINI_API_KEY", "GEMINI_BASE_URL"),
    "openai": ("OPENAI_MODEL", "OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "zhipu": ("ZHIPU_MODEL", "ZHIPU_API_KEY", "ZHIPU_BASE_URL"),
    "deepseek": ("DEEPSEEK_MODEL", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
    "qwen": ("QWEN_MODEL", "QWEN_API_KEY", "QWEN_BASE_URL"),
    "kimi": ("KIMI_MODEL", "KIMI_API_KEY", "KIMI_BASE_URL"),
    "ollama": ("OLLAMA_MODEL", None, "OLLAMA_BASE_URL"),
    "lmstudio": ("LMSTUDIO_MODEL", None, "LMSTUDIO_BASE_URL"),
}

# Rough context-window sizes (tokens) for the usage meter. Estimates — set
# AGENT_CONTEXT_LIMIT_TOKENS to override with the exact window of your model.
_PROVIDER_CONTEXT_LIMITS = {
    "gemini": 1_000_000,
    "openai": 128_000,
    "zhipu": 128_000,
    "deepseek": 128_000,
    "qwen": 128_000,
    "kimi": 128_000,
    "ollama": 32_000,
    "lmstudio": 32_000,
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def _context_limit_tokens(provider: str) -> int:
    override = int(getattr(config, "AGENT_CONTEXT_LIMIT_TOKENS", 0) or 0)
    if override > 0:
        return override
    return _PROVIDER_CONTEXT_LIMITS.get(provider, 128_000)


def _estimate_tokens(text: str) -> int:
    """CJK-aware token estimate: ~1 token per CJK char, ~3.8 chars/token otherwise."""
    cjk = len(_CJK_RE.findall(text))
    return int(cjk + (len(text) - cjk) / 3.8)


# ------------------------------------------------------------ tool call parse

_FENCE_RE = re.compile(r"```(?:tool_call|tool|json)?\s*\n(\{.*?\})\s*\n```", re.DOTALL)
_TOOL_PREFIX_RE = re.compile(r"TOOL_CALL\s*[:：]?\s*(\{.*)", re.DOTALL | re.IGNORECASE)


def parse_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """Extract {"tool": name, "arguments": {...}} from an LLM reply, if any.

    Accepted shapes (most providers get this right with just the system prompt):
      - a fenced block:        ```tool_call {"tool": ..., "arguments": ...}```
      - a TOOL_CALL: {...} line
      - the entire reply being a single JSON object with a "tool" key
    """
    if not text:
        return None
    candidates: List[str] = []
    for match in _FENCE_RE.finditer(text):
        candidates.append(match.group(1))
    prefix = _TOOL_PREFIX_RE.search(text)
    if prefix:
        candidates.append(prefix.group(1))
    stripped = text.strip()
    if stripped.startswith("{"):
        candidates.append(_balanced_json(stripped) or stripped)
    for candidate in candidates:
        parsed = _try_load_json(candidate)
        if isinstance(parsed, dict) and "tool" in parsed:
            tool = str(parsed["tool"]).strip()
            if tool:
                return {"tool": tool, "arguments": parsed.get("arguments") or {}}
    return None


def _balanced_json(text: str) -> Optional[str]:
    """Return the first balanced {...} block in text (string-aware)."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _try_load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    repaired = re.sub(r",\s*([}\]])", r"\1", text)  # trailing commas
    repaired = re.sub(r"(?<=\{|,)\s*'([^']+?)'\s*:", r'"\1":', repaired)  # single-quoted keys
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


# Keys an LLM may use when it wraps its final answer in a JSON object.
_ANSWER_KEYS = ("answer", "content", "text", "response", "reply", "message", "output")


def _clean_final_answer(text: str) -> str:
    """Recover readable prose from malformed final answers.

    Models in tool-call mode sometimes (a) escape newlines as literal \\n
    backslash sequences, or (b) wrap the answer in a JSON string/object like
    {"answer": "..."}. Both render as one unreadable line in the chat UI.
    """
    if not text:
        return text
    stripped = text.strip()
    # Bare JSON string literal: "line1\nline2"
    if len(stripped) > 1 and stripped.startswith('"') and stripped.endswith('"'):
        try:
            value = json.loads(stripped)
            if isinstance(value, str):
                return value.strip()
        except json.JSONDecodeError:
            pass
    # JSON object wrapper like {"answer": "..."} (objects with a "tool" key
    # are tool calls and never reach here).
    if stripped.startswith("{") and stripped.endswith("}"):
        parsed = _try_load_json(stripped)
        if isinstance(parsed, dict) and "tool" not in parsed:
            for key in _ANSWER_KEYS:
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    # Prose where every newline was escaped (no real newlines at all). Text
    # with real newlines is left alone — literal \\n there is usually inside
    # code the user wants verbatim.
    if "\\n" in text and "\n" not in text:
        cleaned = text.replace("\\r\\n", "\n").replace("\\n", "\n")
        cleaned = cleaned.replace("\\t", "\t").replace('\\"', '"')
        return cleaned
    return text


# ------------------------------------------------------------------- provider

def _build_provider(cfg: Dict[str, Any]):
    """Resolve (provider_instance, provider_name, model_label) for the agent."""
    from types import SimpleNamespace
    from core.llm_engine import get_provider

    provider_name = (cfg.get("provider") or config.AGENT_LLM_PROVIDER or config.LLM_PROVIDER or "").lower()
    model_override = cfg.get("model") or config.AGENT_LLM_MODEL or ""

    shim = SimpleNamespace()
    for attr in dir(config):
        if attr.isupper():
            setattr(shim, attr, getattr(config, attr))
    model_attr = _PROVIDER_ATTRS.get(provider_name, (None, None, None))[0]
    if model_attr and model_override:
        setattr(shim, model_attr, model_override)
    # Agent effort override: only for providers whose wire format supports it.
    effort = (cfg.get("effort") or "").strip().lower()
    if provider_name == "zhipu" and effort in ("default", "low", "high", "max"):
        shim.ZHIPU_REASONING_EFFORT = effort
    elif provider_name == "zhipu":
        shim.ZHIPU_REASONING_EFFORT = None
    if provider_name == "openai" and effort in ("minimal", "low", "medium", "high"):
        shim.OPENAI_REASONING_EFFORT = effort
    elif provider_name == "openai":
        shim.OPENAI_REASONING_EFFORT = None
    provider = get_provider(provider_name, config_module=shim)
    model_label = model_override or (getattr(shim, model_attr, "") if model_attr else "")
    return provider, provider_name, model_label


# -------------------------------------------------------------- system prompt

_SYSTEM_PROMPT_TEMPLATE = """You are the AI Agent Assistant inside AI Video Factory — an end-to-end pipeline that turns ideas into cinematic videos (story -> scenes -> shots -> images -> videos -> narration, rendered via ComfyUI / Gemini).

You can operate the ENTIRE application through tools: create and configure projects, generate and edit stories/scenes/characters/shots, fix prompts, queue image/video/SFX/narration generation, manage the render queue, read/write project files, list/edit workflows and directors, and search project data.

## Current context
{context}

## How to respond
You think, then either call ONE tool or give the final answer.

To call a tool, reply with EXACTLY a fenced block (nothing else):
```tool_call
{{"tool": "<tool name>", "arguments": {{<arguments object>}}}}
```

Rules:
- Call tools to fetch facts before acting (e.g. get_shot before update_shot). Never invent shot ids, scene ids or file paths — look them up.
- NEVER analyze, compare, quote or edit shot/story/scene content you have not read with a tool in this conversation. The project context summary is an INDEX ONLY (no prompt text) — full text comes only from get_shot / get_story. If you haven't fetched it, you don't know it: fetch, never guess.
- One tool call per reply. After each call you receive its result and may call another tool.
- When you have the answer or finished the requested change, reply with plain text for the user (no tool_call block). Keep it concise; use markdown.
- If the user reports something is wrong (e.g. "shot 4's character is doing the wrong action"), inspect the actual data first, explain what you found, fix it with the appropriate tool, then optionally queue regeneration — and say exactly what you changed.
- Generation tools (images/videos/SFX) are queued, not instant: tell the user generation started and where to watch progress (Queue page).
- Dangerous tools (delete_*) require the user's explicit intent — confirm before destructive actions.
- If a skill matches the task, call read_skill first and follow it.

## Available tools
{tools}

## Skills (instruction playbooks — read_skill "<name>" before using)
{skills}
{mcp_section}{extra}"""


def _render_tools(tools: List[Dict[str, Any]]) -> str:
    lines = []
    for t in tools:
        params = t.get("parameters") or {}
        props = params.get("properties") or {}
        required = params.get("required") or []
        args = ", ".join(
            f"{name}{'*' if name in required else ''}" for name in props
        )
        lines.append(f"- {t['name']}({args}): {t['description'].splitlines()[0]}")
    return "\n".join(lines) if lines else "(no tools available)"


_MODE_BRIEFINGS = {
    "r2v": (
        "- WORKFLOW MODE: REFERENCE-TO-VIDEO (r2v{mode_note}). Shots have NO first-frame "
        "images — NEVER call generate_shot_image or batch-regenerate images.\n"
        "  * Visual identity comes from REFERENCE IMAGES: character 8-view sheets "
        "(generate_character_reference), scene backgrounds (generate_scene_background) "
        "and prop sheets (generate_prop_reference). They auto-attach to shots "
        "(characters -> scene background -> props, max 9 slots).\n"
        "  * Wrong look of a character/scene/prop -> regenerate that reference, not the shot.\n"
        "  * Wrong action/motion/sound in a shot -> update_shot its video_prompt "
        "(six-section full-reference format; keep the section structure), then "
        "generate_shot_video (references are picked up automatically).\n"
        "  * The skill 'r2v-workflow' has the full format rules — read_skill it before "
        "rewriting video prompts."
    ),
    "t2v": (
        "- WORKFLOW MODE: TEXT-TO-VIDEO (t2v). No images at all — NEVER call "
        "generate_shot_image or generate_character_reference. Everything (look, action, "
        "sound) is authored in the shot's video_prompt; edit it with update_shot, then "
        "generate_shot_video."
    ),
    "i2v": (
        "- WORKFLOW MODE: IMAGE-TO-VIDEO (i2v, standard). First frame per shot comes from "
        "generate_shot_image; wrong pose/action in the FIRST FRAME means fixing "
        "image_prompt and regenerating the image; wrong MOTION means fixing "
        "motion_prompt/video_prompt and regenerating the video."
    ),
}


def _project_context_block(project_id: Optional[str]) -> str:
    if not project_id:
        return ("- No project is currently open in the UI. Use list_projects / "
                "create_project when the user asks about projects.")
    try:
        from web_ui.backend.services.agent.registry import TOOLS
        handler = TOOLS["get_project_overview"].handler
        overview = handler({"project_id": project_id})
        overview["shots"] = overview.get("shots", [])[:40]
        mode = (overview.get("video_generation_type") or "i2v").lower()
        briefing = _MODE_BRIEFINGS.get(mode, _MODE_BRIEFINGS["i2v"])
        if mode == "r2v" and overview.get("r2v_mode"):
            briefing = briefing.format(mode_note=f", {overview['r2v_mode']} mode")
        else:
            briefing = briefing.format(mode_note="")
        return (f"- Active project ({project_id}):\n```json\n"
                f"{json.dumps(overview, ensure_ascii=False, default=str)[:6000]}\n```\n"
                "- WARNING: the shot entries in the JSON above are an INDEX ONLY — "
                "they contain no prompt text. Before quoting, comparing or editing "
                "any shot you MUST call get_shot for its full prompts.\n"
                + briefing)
    except Exception as exc:  # noqa: BLE001 — context is best-effort
        return f"- Active project: {project_id} (details unavailable: {exc})"


# -------------------------------------------------------------------- engine

class AgentEngine:
    def __init__(self):
        from web_ui.backend.services.agent.config_store import get_agent_config_store
        from web_ui.backend.services.agent.conversations import get_conversation_store
        from web_ui.backend.services.agent.mcp_client import get_mcp_manager
        from web_ui.backend.services.agent.skills import get_skill_store
        self.config_store = get_agent_config_store()
        self.conversations = get_conversation_store()
        self.skills = get_skill_store()
        self.mcp = get_mcp_manager()

    # -------------------------------------------------------------- provider
    def build_provider(self):
        return _build_provider(self.config_store.resolved())

    # ---------------------------------------------------------------- prompt
    async def _collect_mcp_tools(self, cfg: dict) -> tuple[List[Dict[str, Any]], Dict[str, dict]]:
        servers = {
            name: sc for name, sc in (cfg.get("mcp_servers") or {}).items()
            if sc.get("enabled", True) and (sc.get("command") or sc.get("url"))
        }
        if not servers:
            return [], servers
        try:
            listing = await asyncio.wait_for(self.mcp.list_tools(servers), timeout=45)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Agent MCP list_tools failed: {exc}")
            return [], servers
        errors = listing.pop("_errors", {})
        tools: List[Dict[str, Any]] = []
        for server_name, server_tools in listing.items():
            for t in server_tools:
                tools.append({
                    "name": f"mcp__{server_name}__{t['name']}",
                    "description": f"[MCP {server_name}] {t.get('description', '')}".splitlines()[0],
                    "category": "mcp",
                    "parameters": t.get("inputSchema") or {"type": "object", "properties": {}},
                    "_mcp_server": server_name,
                    "_mcp_tool": t["name"],
                })
        if errors:
            logger.info(f"Agent MCP servers failed to list: {errors}")
        return tools, servers

    def _system_prompt(self, tools: List[Dict[str, Any]], mcp_tools: List[Dict[str, Any]],
                       skills: List[Dict[str, Any]], project_id: Optional[str], cfg: dict) -> str:
        all_tools = tools + mcp_tools
        skill_lines = "\n".join(
            f"- {s['name']}: {s.get('description', '')}" for s in skills
        ) or "(none installed)"
        mcp_section = ""
        if mcp_tools:
            mcp_section = ("\n## MCP tools (external servers)\n"
                           "Same tool_call protocol; names start with mcp__<server>__.\n")
        extra = ""
        if cfg.get("extra_system_prompt"):
            extra = f"\n## Additional instructions from the user\n{cfg['extra_system_prompt']}\n"
        return _SYSTEM_PROMPT_TEMPLATE.format(
            context=_project_context_block(project_id if cfg.get("auto_include_project_context", True) else None),
            tools=_render_tools(all_tools),
            skills=skill_lines,
            mcp_section=mcp_section,
            extra=extra,
        )

    # ------------------------------------------------------------- main loop
    async def run(self, conversation_id: str, user_message: str,
                  project_id: Optional[str] = None,
                  on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        cfg = self.config_store.resolved()
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            conversation = self.conversations.create(project_id=project_id)
            conversation_id = conversation["id"]

        def emit(event: Dict[str, Any]) -> None:
            if on_event:
                try:
                    on_event(event)
                except Exception:  # noqa: BLE001 — UI errors must not kill the loop
                    logger.exception("Agent event callback failed")

        base_history = list(conversation.get("messages", []))[-config.AGENT_HISTORY_MAX_MESSAGES:]
        base_len = len(base_history)
        # Running transcript for THIS turn: user message + every assistant
        # reply + every tool result. The model sees the full chain each
        # iteration — dropping earlier turns made it lose the task mid-run.
        transcript: List[Dict[str, Any]] = base_history + [
            {"role": "user", "content": user_message}]

        try:
            provider, provider_name, model_label = self.build_provider()
        except Exception as exc:  # noqa: BLE001
            emit({"type": "error", "message": f"Agent LLM not available: {exc}"})
            return {"conversation_id": conversation_id, "error": str(exc), "steps": []}

        from web_ui.backend.services.agent.registry import get_effective_tools
        builtin = get_effective_tools(cfg)
        mcp_tools, mcp_servers = await self._collect_mcp_tools(cfg)
        mcp_by_name = {t["name"]: t for t in mcp_tools}
        skills = self.skills.list_skills()
        system_prompt = self._system_prompt(
            [t.to_schema() for t in builtin.values()], mcp_tools, skills, project_id, cfg)

        steps: List[Dict[str, Any]] = []
        final_answer: Optional[str] = None
        max_iterations = int(cfg.get("max_iterations") or config.AGENT_MAX_ITERATIONS)
        limit_tokens = _context_limit_tokens(provider_name)
        last_usage: Optional[Dict[str, Any]] = None

        try:
            for iteration in range(1, max_iterations + 1):
                prompt = self._render_prompt(system_prompt, transcript)
                est_tokens = _estimate_tokens(prompt)
                last_usage = {
                    "prompt_chars": len(prompt),
                    "est_tokens": est_tokens,
                    "limit_tokens": limit_tokens,
                    "percent": round(min(100.0, 100.0 * est_tokens / limit_tokens), 1),
                }
                emit({"type": "context_usage", **last_usage})
                emit({"type": "llm_start", "iteration": iteration,
                      "provider": provider_name, "model": model_label})
                response = await asyncio.to_thread(provider.ask, prompt)
                response = (response or "").strip()
                if not response:
                    response = "(empty response from model)"

                call = parse_tool_call(response)
                if call is None:
                    final_answer = _clean_final_answer(response)
                    if not final_answer:
                        final_answer = "(empty response from model)"
                    transcript.append({"role": "assistant", "content": final_answer})
                    break

                tool_name = call["tool"]
                arguments = call.get("arguments") or {}
                emit({"type": "tool_start", "tool": tool_name, "arguments": arguments})
                result = await self._dispatch(tool_name, arguments, cfg, mcp_by_name, mcp_servers)
                emit({"type": "tool_result", "tool": tool_name, "ok": result.get("ok"),
                      "result": result.get("result") if result.get("ok") else result.get("error")})
                steps.append({"tool": tool_name, "arguments": arguments,
                              "ok": result.get("ok", False),
                              "result": result.get("result") if result.get("ok") else result.get("error")})
                transcript.append({
                    "role": "assistant", "content": response,
                    "tool_call": {"tool": tool_name, "arguments": arguments},
                })
                transcript.append({
                    "role": "tool_result", "tool": tool_name,
                    "ok": result.get("ok", False),
                    "content": self._stringify_result(result),
                })
            else:
                final_answer = (
                    "I reached my tool-call budget for this message. Here is the last "
                    "tool activity — ask me to continue if anything is still missing.\n\n"
                    + "\n".join(f"- `{s['tool']}` → {'ok' if s['ok'] else 'failed'}" for s in steps[-5:]))
                transcript.append({"role": "assistant", "content": final_answer})
        except asyncio.CancelledError:
            transcript.append({"role": "system", "content": "Generation cancelled by user."})
            self.conversations.append_messages(conversation_id, transcript[base_len:])
            emit({"type": "error", "message": "Cancelled."})
            return {"conversation_id": conversation_id, "cancelled": True, "steps": steps}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent loop failed")
            transcript.append({"role": "assistant", "content": f"Agent error: {exc}"})
            emit({"type": "error", "message": str(exc)})
            self.conversations.append_messages(conversation_id, transcript[base_len:])
            return {"conversation_id": conversation_id, "error": str(exc), "steps": steps}

        if project_id and conversation.get("project_id") != project_id:
            self.conversations.update(conversation_id, project_id=project_id)
        self.conversations.append_messages(conversation_id, transcript[base_len:])
        if last_usage:
            self.conversations.update(conversation_id, context_usage=last_usage)
        emit({"type": "final", "content": final_answer or ""})
        return {
            "conversation_id": conversation_id,
            "answer": final_answer or "",
            "steps": steps,
            "iterations": len(steps) + (1 if final_answer else 0),
            "context": last_usage,
        }

    # ------------------------------------------------------------- dispatch
    async def _dispatch(self, tool_name: str, arguments: Dict[str, Any], cfg: dict,
                        mcp_by_name: Dict[str, Dict[str, Any]], mcp_servers: Dict[str, dict]) -> Dict[str, Any]:
        if tool_name in mcp_by_name:
            meta = mcp_by_name[tool_name]
            try:
                result = await asyncio.wait_for(
                    self.mcp.call(meta["_mcp_server"], meta["_mcp_tool"], arguments, mcp_servers),
                    timeout=120)
                ok = not result.get("isError", False)
                return {"ok": ok, "tool": tool_name,
                        "result" if ok else "error": result.get("content", "")}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "tool": tool_name, "error": f"MCP call failed: {exc}"}
        from web_ui.backend.services.agent.registry import execute_tool
        return await execute_tool(tool_name, arguments, cfg)

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _stringify_result(result: Dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"ERROR: {result.get('error', 'unknown error')}"
        payload = result.get("result")
        try:
            text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(payload)
        limit = config.AGENT_MAX_TOOL_RESULT_CHARS
        if len(text) > limit:
            omitted = len(text) - limit
            text = (text[:limit]
                    + f"\n…[RESULT TRUNCATED — {omitted} chars omitted. Re-query more "
                      "narrowly (e.g. get_shot one shot at a time, or read_file with "
                      "offset) if you need the missing part.]")
        return text

    @staticmethod
    def _render_prompt(system_prompt: str, messages: List[Dict[str, Any]]) -> str:
        parts: List[str] = [system_prompt, "", "## Conversation so far"]
        for msg in messages:
            role = msg.get("role", "user")
            if role == "user":
                parts.append(f"User: {msg.get('content', '')}")
            elif role == "assistant":
                # content holds the model's raw reply — including its own fenced
                # tool_call block when it made one (kept verbatim so the model
                # keeps seeing the exact format it should emit).
                parts.append(f"Assistant: {msg.get('content', '')}")
            elif role == "tool_result":
                status = "ok" if msg.get("ok") else "FAILED"
                parts.append(f"TOOL RESULT ({msg.get('tool')}, {status}):\n{msg.get('content', '')}")
            elif role == "system":
                parts.append(f"System: {msg.get('content', '')}")
        parts.append("Assistant:")
        return "\n\n".join(parts)

    # ----------------------------------------------------------------- test
    async def test_connection(self) -> Dict[str, Any]:
        cfg = self.config_store.resolved()
        try:
            provider, provider_name, model_label = self.build_provider()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "provider": cfg.get("provider"), "error": str(exc)}
        try:
            reply = await asyncio.to_thread(provider.ask, "Reply with exactly one word: PONG")
            return {"ok": True, "provider": provider_name, "model": model_label,
                    "reply": (reply or "").strip()[:100]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "provider": provider_name, "model": model_label,
                    "error": str(exc)}


_engine: Optional[AgentEngine] = None


def get_agent_engine() -> AgentEngine:
    global _engine
    if _engine is None:
        _engine = AgentEngine()
    return _engine
