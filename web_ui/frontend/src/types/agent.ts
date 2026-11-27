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
  /** Assistant replies that called a tool: the call that was executed. */
  tool_call?: { tool: string; arguments: Record<string, unknown> };
  /** Text the model wrote ahead of its tool call — agent output in its own right. */
  narration?: string | null;
  /** How long the model deliberated before this reply (ms). */
  thinking_ms?: number;
  /** Tool results: how long the call took (ms). */
  duration_ms?: number;
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
  | { type: 'tool_start'; tool: string; arguments: Record<string, unknown>; narration?: string }
  | { type: 'tool_result'; tool: string; ok: boolean; result?: unknown; duration_ms?: number }
  | { type: 'context_usage'; prompt_chars: number; est_tokens: number; limit_tokens: number; percent: number }
  | { type: 'final'; content: string }
  | { type: 'error'; message: string }
  | { type: 'done' }
  | { type: 'pong' };

/** Stream event with the client-side receive timestamp (for elapsed-time UI). */
export type TimedAgentEvent = AgentStreamEvent & { ts?: number };

/**
 * The turn currently streaming over the socket: the user's message plus every
 * event of the run. It stands in for its saved copy in the transcript.
 */
export interface AgentLiveTurn {
  message: string;
  conversationId: string | null;
  /** Messages the conversation held when this turn was sent. */
  baseCount: number;
  events: TimedAgentEvent[];
}

/* Transcript view model — one shape for what the agent did in a turn, built
   alike from saved messages and from the live stream (lib/agentTranscript.ts). */

export type AgentTurnStatus = 'running' | 'done' | 'error' | 'cancelled';

/** One LLM call ("pass"), from llm_start until its reply is in. */
export interface ThinkingSegment {
  kind: 'thinking';
  status: 'running' | 'done';
  /** 1-based pass number within the turn. */
  iteration?: number;
  model?: string;
  durationMs?: number;
}

/** Text the model wrote ahead of its tool call. */
export interface NarrationSegment {
  kind: 'narration';
  text: string;
}

export interface ToolSegment {
  kind: 'tool';
  tool: string;
  arguments: Record<string, unknown>;
  status: 'running' | 'ok' | 'error';
  /** The tool's output, or the error text when status is 'error'. */
  result?: unknown;
  durationMs?: number;
}

export interface AnswerSegment {
  kind: 'answer';
  text: string;
}

export interface ErrorSegment {
  kind: 'error';
  message: string;
}

export type AgentSegment =
  | ThinkingSegment | NarrationSegment | ToolSegment | AnswerSegment | ErrorSegment;

/** Everything the agent did in response to one user message, in order. */
export interface AgentTurnItem {
  kind: 'turn';
  status: AgentTurnStatus;
  segments: AgentSegment[];
}

export interface UserItem {
  kind: 'user';
  content: string;
}

export type TranscriptItem = UserItem | AgentTurnItem;

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
