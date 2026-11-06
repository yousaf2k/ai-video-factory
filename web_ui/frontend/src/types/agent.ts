/**
 * Types for the AI Agent Assistant
 */

export interface AgentToolInfo {
  name: string;
  category: string;
  description: string;
  dangerous: boolean;
  enabled: boolean;
  blocked_by_dangerous_gate: boolean;
  source: 'builtin' | 'mcp';
  server?: string | null;
  parameters: Record<string, unknown>;
}

export interface McpServerConfig {
  transport: 'stdio' | 'http';
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string | null;
  url?: string | null;
  headers?: Record<string, string>;
  enabled: boolean;
}

export interface AgentStatusConfig {
  /** Saved value; '' = follow the app LLM (LLM_PROVIDER) */
  provider: string;
  /** Saved value; '' = provider default model */
  model: string;
  /** Saved value; '' = auto (model picks its default) */
  effort: string;
  effort_options: string[];
  effort_supported: boolean;
  /** What actually runs after env fallbacks */
  effective_provider: string;
  effective_model: string;
  max_iterations: number;
  dangerous_tools_allowed: boolean;
  extra_system_prompt: string;
  auto_include_project_context: boolean;
  enabled_tools: Record<string, boolean>;
  mcp_servers: Record<string, McpServerConfig>;
  /** Model suggestions per provider for the dropdown */
  provider_models: Record<string, string[]>;
}

export interface AgentSkill {
  name: string;
  description: string;
  dir: string;
}

export interface AgentConversationSummary {
  id: string;
  title: string;
  project_id?: string | null;
  updated_at: string;
  message_count: number;
}

export interface AgentConfigResponse {
  config: AgentStatusConfig;
  tools: AgentToolInfo[];
  skills: AgentSkill[];
  conversations: AgentConversationSummary[];
  llm_providers: string[];
}

export interface AgentChatStep {
  tool: string;
  arguments: Record<string, unknown>;
  ok: boolean;
  result?: unknown;
}

export interface AgentChatResponse {
  conversation_id: string;
  answer: string;
  steps: AgentChatStep[];
  error?: string | null;
}

/** Stored conversation message (backend shape) */
export interface AgentMessage {
  role: 'user' | 'assistant' | 'tool_result' | 'system';
  content: string;
  tool?: string;
  arguments?: Record<string, unknown>;
  ok?: boolean;
}

export interface AgentConversationDetail extends AgentConversationSummary {
  created_at: string;
  messages: AgentMessage[];
  context_usage?: ContextUsage;
}

/** Context-window usage reported by the engine (estimate) */
export interface ContextUsage {
  prompt_chars: number;
  est_tokens: number;
  limit_tokens: number;
  percent: number;
}

/** WebSocket events streamed by /api/agent/ws */
export type AgentStreamEvent =
  | { type: 'conversation'; conversation_id: string }
  | { type: 'llm_start'; iteration: number; provider: string; model: string }
  | { type: 'tool_start'; tool: string; arguments: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; ok: boolean; result?: unknown }
  | { type: 'context_usage'; prompt_chars: number; est_tokens: number; limit_tokens: number; percent: number }
  | { type: 'final'; content: string }
  | { type: 'error'; message: string }
  | { type: 'done' }
  | { type: 'pong' };

/** Stream event with the client-side receive timestamp (for elapsed-time UI). */
export type TimedAgentEvent = AgentStreamEvent & { ts?: number };

export interface AgentTestResult {
  ok: boolean;
  provider?: string | null;
  model?: string | null;
  reply?: string | null;
  error?: string | null;
}

export interface McpToolDescriptor {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}
