"""
Pydantic models for the AI Agent Assistant
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentToolInfo(BaseModel):
    name: str
    category: str
    description: str
    dangerous: bool = False
    enabled: bool = True
    blocked_by_dangerous_gate: bool = False
    source: str = "builtin"          # "builtin" | "mcp"
    server: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class McpServerConfig(BaseModel):
    transport: str = Field(default="stdio", description="'stdio' or 'http'")
    command: Optional[str] = Field(default=None, description="stdio: executable, e.g. 'npx' or 'python'")
    args: List[str] = Field(default_factory=list, description="stdio: command arguments")
    env: Dict[str, str] = Field(default_factory=dict)
    cwd: Optional[str] = None
    url: Optional[str] = Field(default=None, description="http: MCP endpoint URL")
    headers: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class AgentConfigUpdate(BaseModel):
    provider: Optional[str] = Field(default=None, description="LLM provider; '' follows env/LLM_PROVIDER")
    model: Optional[str] = Field(default=None, description="Model override; '' uses provider default")
    effort: Optional[str] = Field(default=None, description="Reasoning effort; '' = auto (model default)")
    max_iterations: Optional[int] = Field(default=None, ge=1, le=50)
    dangerous_tools_allowed: Optional[bool] = None
    enabled_tools: Optional[Dict[str, bool]] = None
    mcp_servers: Optional[Dict[str, McpServerConfig]] = None
    extra_system_prompt: Optional[str] = None
    auto_include_project_context: Optional[bool] = None


class AgentStatus(BaseModel):
    provider: str                        # saved value; '' = follow the app LLM
    model: str                           # saved value; '' = provider default
    effort: str = ""                     # saved value; '' = auto (model default)
    effort_options: List[str] = Field(default_factory=list)
    effort_supported: bool = False
    effective_provider: str = ""         # what actually runs after env fallbacks
    effective_model: str = ""
    max_iterations: int
    dangerous_tools_allowed: bool
    extra_system_prompt: str = ""
    auto_include_project_context: bool = True
    enabled_tools: Dict[str, bool] = Field(default_factory=dict)
    mcp_servers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    provider_models: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Model suggestions per provider for the settings dropdown",
    )


class AgentConfigResponse(BaseModel):
    config: AgentStatus
    tools: List[AgentToolInfo]
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    conversations: List[Dict[str, Any]] = Field(default_factory=list)
    llm_providers: List[str] = Field(default_factory=list)


class AgentMessage(BaseModel):
    role: str
    content: str = ""
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    ok: Optional[bool] = None
    timestamp: Optional[str] = None


class AgentConversationSummary(BaseModel):
    id: str
    title: str
    project_id: Optional[str] = None
    updated_at: str = ""
    message_count: int = 0


class AgentConversationDetail(AgentConversationSummary):
    created_at: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    project_id: Optional[str] = Field(default=None, description="Project currently open in the UI")


class AgentChatStep(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    ok: bool = False
    result: Any = None


class AgentChatResponse(BaseModel):
    conversation_id: str
    answer: str = ""
    steps: List[AgentChatStep] = Field(default_factory=list)
    error: Optional[str] = None


class AgentTestResponse(BaseModel):
    ok: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    reply: Optional[str] = None
    error: Optional[str] = None


class SkillCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64,
                      description="Skill folder name, e.g. 'fix-shot-prompt'")
    description: str = Field(default="", max_length=500)
    content: str = Field(default="", description="Markdown instructions (without frontmatter)")


class ConversationCreateRequest(BaseModel):
    project_id: Optional[str] = None
    title: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    project_id: Optional[str] = None
