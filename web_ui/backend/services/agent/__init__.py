"""
AI Agent Assistant service package.

Exposes the Web UI backend as LLM tools so an in-app agent can operate the
whole video pipeline (projects, stories, scenes, characters, shots, workflows,
directors, queue, files) plus user-authored Skills and external MCP servers.
"""
from web_ui.backend.services.agent.config_store import AgentConfigStore, get_agent_config_store
from web_ui.backend.services.agent.conversations import ConversationStore, get_conversation_store
from web_ui.backend.services.agent.engine import AgentEngine, get_agent_engine
from web_ui.backend.services.agent.mcp_client import MCPManager, get_mcp_manager
from web_ui.backend.services.agent.registry import TOOLS, Tool, execute_tool, get_effective_tools
from web_ui.backend.services.agent.skills import SkillStore, get_skill_store

__all__ = [
    "AgentConfigStore", "get_agent_config_store",
    "ConversationStore", "get_conversation_store",
    "AgentEngine", "get_agent_engine",
    "MCPManager", "get_mcp_manager",
    "TOOLS", "Tool", "execute_tool", "get_effective_tools",
    "SkillStore", "get_skill_store",
]
