"""
AI Agent Assistant API — REST endpoints + streaming chat WebSocket.
"""
import asyncio
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from web_ui.backend.models.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentChatStep,
    AgentConfigResponse,
    AgentConfigUpdate,
    AgentConversationDetail,
    AgentConversationSummary,
    AgentStatus,
    AgentTestResponse,
    AgentToolInfo,
    ConversationCreateRequest,
    ConversationUpdateRequest,
    SkillCreateRequest,
)
from web_ui.backend.services.agent.config_store import get_agent_config_store
from web_ui.backend.services.agent.conversations import get_conversation_store
from web_ui.backend.services.agent.engine import get_agent_engine
from web_ui.backend.services.agent.mcp_client import get_mcp_manager
from web_ui.backend.services.agent.registry import catalog
from web_ui.backend.services.agent.skills import get_skill_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])

_LLM_PROVIDERS = ["gemini", "openai", "zhipu", "deepseek", "qwen", "kimi", "ollama", "lmstudio"]

# Model suggestions per provider for the settings dropdown (plus "Custom…").
# Mirrors the Configuration page's model dropdowns/placeholders
# (web_ui/frontend/src/app/config/page.tsx); the provider's currently
# configured model is always merged in at the top.
_PROVIDER_MODELS = {
    "gemini": ["gemini-3.5-flash-lite", "gemini-3-pro-preview"],
    "zhipu": ["glm-5.3", "glm-5.3-flash"],
    "openai": ["gpt-4o"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "qwen": ["qwen-max"],
    "kimi": ["kimi-labs"],
    "ollama": ["llama2"],
    "lmstudio": ["lmstudio-community/qwen2"],
}

# provider -> (config model attr) used to merge the configured default in
_PROVIDER_MODEL_ATTR = {
    "gemini": "GEMINI_TEXT_MODEL", "openai": "OPENAI_MODEL", "zhipu": "ZHIPU_MODEL",
    "deepseek": "DEEPSEEK_MODEL", "qwen": "QWEN_MODEL", "kimi": "KIMI_MODEL",
    "ollama": "OLLAMA_MODEL", "lmstudio": "LMSTUDIO_MODEL",
}


def _effort_options(provider: str, model: str) -> list:
    """Effort levels the provider/model genuinely supports ([] = not supported).

    Empty selection always means "auto" — nothing is sent and the model picks
    its own default.
    """
    provider = (provider or "").lower()
    model = (model or "").lower()
    if provider == "zhipu":
        return ["default", "low", "high", "max"]
    if provider == "openai":
        # reasoning_effort is only accepted by reasoning models; sending it to
        # gpt-4o & co returns "Unsupported parameter".
        if re.match(r"^(o\d|gpt-5)", model):
            return ["minimal", "low", "medium", "high"]
    return []


def _provider_models() -> dict:
    import config
    result = {}
    for provider, models in _PROVIDER_MODELS.items():
        attr = _PROVIDER_MODEL_ATTR.get(provider)
        configured = getattr(config, attr, "") if attr else ""
        merged = list(models)
        if configured and configured not in merged:
            merged.insert(0, configured)
        result[provider] = merged
    return result


def _status_from_config(cfg: dict, raw: dict) -> AgentStatus:
    import config
    effective_provider = cfg.get("provider") or ""
    # What the engine would really run: agent override, else the provider's
    # configured default model (e.g. DEEPSEEK_MODEL).
    default_attr = _PROVIDER_MODEL_ATTR.get(effective_provider)
    effective_model = (cfg.get("model") or
                       (getattr(config, default_attr, "") if default_attr else ""))
    options = _effort_options(effective_provider, effective_model)
    return AgentStatus(
        provider=raw.get("provider") or "",           # saved value ('' = follow app LLM)
        model=raw.get("model") or "",                 # saved value ('' = provider default)
        effort=(raw.get("effort") or "").lower(),     # '' = auto (model default)
        effort_options=options,
        effort_supported=bool(options),
        effective_provider=effective_provider,
        effective_model=effective_model,
        max_iterations=int(cfg.get("max_iterations") or 12),
        dangerous_tools_allowed=bool(cfg.get("dangerous_tools_allowed")),
        extra_system_prompt=cfg.get("extra_system_prompt") or "",
        auto_include_project_context=bool(cfg.get("auto_include_project_context", True)),
        enabled_tools=cfg.get("enabled_tools") or {},
        mcp_servers=cfg.get("mcp_servers") or {},
        provider_models=_provider_models(),
    )


# ------------------------------------------------------------------ config

@router.get("/config", response_model=AgentConfigResponse)
async def get_agent_config():
    """Agent settings + tool catalog + skills + conversations in one call."""
    store = get_agent_config_store()
    return AgentConfigResponse(
        config=_status_from_config(store.resolved(), store.load()),
        tools=[AgentToolInfo(**t) for t in catalog(store.load())],
        skills=get_skill_store().list_skills(),
        conversations=get_conversation_store().list_conversations(),
        llm_providers=_LLM_PROVIDERS,
    )


@router.put("/config", response_model=AgentStatus)
async def update_agent_config(update: AgentConfigUpdate):
    """Update agent settings (provider, tools toggles, MCP servers, ...)."""
    store = get_agent_config_store()
    payload = update.model_dump(exclude_unset=True)
    if "mcp_servers" in payload and payload["mcp_servers"] is not None:
        payload["mcp_servers"] = {
            name: (server.model_dump() if hasattr(server, "model_dump") else server)
            for name, server in payload["mcp_servers"].items()
        }
    try:
        saved = store.save(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    return _status_from_config(store.resolved(), saved)


@router.get("/tools", response_model=List[AgentToolInfo])
async def get_agent_tools():
    return [AgentToolInfo(**t) for t in catalog()]


@router.post("/test", response_model=AgentTestResponse)
async def test_agent_llm():
    """Verify the configured agent LLM responds."""
    result = await get_agent_engine().test_connection()
    return AgentTestResponse(**result)


# -------------------------------------------------------------------- MCP

@router.get("/mcp/{server_name}/tools")
async def list_mcp_server_tools(server_name: str):
    """Start (if needed) an MCP server and list its tools."""
    store = get_agent_config_store()
    servers = store.enabled_mcp_servers()
    if server_name not in servers:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' is not configured/enabled")
    try:
        manager = get_mcp_manager()
        client = await manager.get_client(server_name, servers[server_name])
        tools = await client.list_tools()
        return {"server": server_name, "tools": tools}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"MCP server error: {exc}")


# ----------------------------------------------------------------- skills

@router.get("/skills")
async def list_skills():
    return get_skill_store().list_skills()


@router.post("/skills")
async def create_skill(request: SkillCreateRequest):
    try:
        return get_skill_store().create_skill(request.name, request.description, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/skills/{skill_name}")
async def read_skill(skill_name: str):
    try:
        return get_skill_store().read_skill(skill_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/skills/{skill_name}")
async def delete_skill(skill_name: str):
    deleted = get_skill_store().delete_skill(skill_name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return {"deleted": True, "name": skill_name}


# ----------------------------------------------------------- conversations

@router.get("/conversations", response_model=List[AgentConversationSummary])
async def list_conversations():
    return get_conversation_store().list_conversations()


@router.post("/conversations", response_model=AgentConversationDetail)
async def create_conversation(request: ConversationCreateRequest):
    return get_conversation_store().create(project_id=request.project_id, title=request.title)


@router.get("/conversations/{conversation_id}", response_model=AgentConversationDetail)
async def get_conversation(conversation_id: str):
    conversation = get_conversation_store().get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=AgentConversationDetail)
async def update_conversation(conversation_id: str, request: ConversationUpdateRequest):
    try:
        return get_conversation_store().update(
            conversation_id, title=request.title, project_id=request.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if not get_conversation_store().delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


# -------------------------------------------------------------- chat (REST)

@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """Non-streaming fallback for the WebSocket chat."""
    engine = get_agent_engine()
    conversation_id = request.conversation_id
    if conversation_id:
        if get_conversation_store().get(conversation_id) is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation_id = get_conversation_store().create(project_id=request.project_id)["id"]
    result = await engine.run(conversation_id, request.message, project_id=request.project_id)
    return AgentChatResponse(
        conversation_id=result["conversation_id"],
        answer=result.get("answer", ""),
        steps=[AgentChatStep(**s) for s in result.get("steps", [])],
        error=result.get("error"),
    )


# ---------------------------------------------------------- chat (WebSocket)

@router.websocket("/ws")
async def agent_chat_ws(websocket: WebSocket):
    """Streaming agent chat.

    Client sends: {"type": "chat", "message": "...", "project_id": "...", "conversation_id": "..."}
                  {"type": "stop"}
    Server sends: llm_start | tool_start | tool_result | final | error | event
    """
    await websocket.accept()
    engine = get_agent_engine()
    conversations = get_conversation_store()
    loop = asyncio.get_running_loop()
    current_task: Optional[asyncio.Task] = None

    async def send(payload: dict) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:  # noqa: BLE001 — socket may be closing
            pass

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type")

            if msg_type == "ping":
                await send({"type": "pong"})
                continue

            if msg_type == "stop":
                if current_task and not current_task.done():
                    current_task.cancel()
                continue

            if msg_type != "chat":
                await send({"type": "error", "message": f"Unknown message type '{msg_type}'"})
                continue

            if current_task and not current_task.done():
                await send({"type": "error", "message": "A message is still being processed — send stop first."})
                continue

            message = (raw.get("message") or "").strip()
            if not message:
                await send({"type": "error", "message": "Empty message"})
                continue

            project_id = raw.get("project_id") or None
            conversation_id = raw.get("conversation_id")
            if conversation_id:
                if conversations.get(conversation_id) is None:
                    await send({"type": "error", "message": "Conversation not found"})
                    continue
            else:
                conversation_id = conversations.create(project_id=project_id)["id"]

            await send({"type": "conversation", "conversation_id": conversation_id})

            async def run_agent() -> None:
                # Ordered outbound queue: guarantees tool events arrive before 'done'.
                outbound: asyncio.Queue = asyncio.Queue()

                def on_event(event: dict) -> None:
                    # FIFO ordering matters (events before 'done'): when already on
                    # the loop thread (the normal case) put directly; only true
                    # cross-thread callers go through call_soon_threadsafe.
                    try:
                        if asyncio.get_running_loop() is loop:
                            outbound.put_nowait(event)
                            return
                    except RuntimeError:
                        pass
                    loop.call_soon_threadsafe(outbound.put_nowait, event)

                async def writer() -> None:
                    while True:
                        item = await outbound.get()
                        try:
                            await websocket.send_json(item)
                        except Exception:  # noqa: BLE001 — socket may be closing
                            pass
                        finally:
                            outbound.task_done()

                writer_task = asyncio.create_task(writer())
                try:
                    await engine.run(conversation_id, message, project_id=project_id,
                                     on_event=on_event)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Agent WS run failed")
                    outbound.put_nowait({"type": "error", "message": str(exc)})
                finally:
                    outbound.put_nowait({"type": "done"})
                    try:
                        await asyncio.wait_for(outbound.join(), timeout=10)
                    except asyncio.TimeoutError:
                        pass
                    writer_task.cancel()

            current_task = asyncio.create_task(run_agent())
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Agent WS error: {exc}")
    finally:
        if current_task and not current_task.done():
            current_task.cancel()
