/**
 * Transcript view model for the agent chat.
 *
 * The saved conversation messages and the live WebSocket stream are two
 * projections of the same agent loop, so both are normalized here into one
 * `TranscriptItem[]`. A turn therefore renders the same while it runs and
 * after a refresh rebuilds it from disk — collapsible blocks included.
 */
import type {
  AgentLiveTurn,
  AgentMessage,
  AgentSegment,
  AgentTurnItem,
  AgentTurnStatus,
  ThinkingSegment,
  ToolSegment,
  TranscriptItem,
} from '@/types/agent';

/** Prefix of the assistant message the engine saves when its loop fails. */
const AGENT_ERROR_PREFIX = 'Agent error: ';
/** Error event the engine emits when the user stops a run. */
const CANCELLED_MESSAGE = 'Cancelled.';

export function formatDuration(ms?: number): string {
  if (ms == null) return '';
  if (ms < 1000) return `${Math.max(1, Math.round(ms))} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  return `${minutes}m ${Math.round((ms % 60000) / 1000)}s`;
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/** Short one-line rendering of a tool call's arguments, e.g. `shot: 4 +2`. */
export function summarizeArguments(args: Record<string, unknown>): string {
  const entries = Object.entries(args ?? {}).filter(
    ([key, value]) => key !== 'project_id' && value != null && value !== '',
  );
  if (entries.length === 0) return '';
  const [key, value] = entries[0];
  const first = typeof value === 'object' ? `${key}: {…}` : `${key}: ${truncate(String(value), 32)}`;
  return entries.length > 1 ? `${first} +${entries.length - 1}` : first;
}

/** Pretty-print a tool output (saved results arrive as JSON text). */
export function formatResult(value: unknown): string {
  if (value == null) return '';
  if (typeof value !== 'string') return JSON.stringify(value, null, 2);
  const trimmed = value.trim();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return JSON.stringify(JSON.parse(trimmed), null, 2);
    } catch {
      // not JSON after all — show it as-is
    }
  }
  return value;
}

function savedToolSegment(
  call: { tool: string; arguments?: Record<string, unknown> },
  result?: AgentMessage,
): ToolSegment {
  return {
    kind: 'tool',
    tool: call.tool,
    arguments: call.arguments ?? {},
    status: result?.ok ? 'ok' : 'error',
    // Saved failures carry a redundant "ERROR: " prefix.
    result: result ? String(result.content ?? '').replace(/^ERROR: /, '') : 'No result was recorded.',
    durationMs: result?.duration_ms,
  };
}

/** Number the thinking passes within each turn (1-based). */
function numberPasses(items: TranscriptItem[]): TranscriptItem[] {
  for (const item of items) {
    if (item.kind !== 'turn') continue;
    let pass = 0;
    for (const segment of item.segments) {
      if (segment.kind === 'thinking') segment.iteration = ++pass;
    }
  }
  return items;
}

/** Rebuild the transcript from a saved conversation. */
export function buildTranscript(messages: AgentMessage[] = []): TranscriptItem[] {
  const items: TranscriptItem[] = [];
  // Everything the agent does between two user messages is one turn.
  let turn: AgentTurnItem | null = null;
  const openTurn = (): AgentTurnItem => {
    if (!turn) {
      turn = { kind: 'turn', status: 'done', segments: [] };
      items.push(turn);
    }
    return turn;
  };

  messages.forEach((message, index) => {
    if (message.role === 'user') {
      turn = null;
      items.push({ kind: 'user', content: message.content });
      return;
    }
    if (message.role === 'tool_result') return; // rendered as part of its call

    const current = openTurn();
    const call = message.tool_call;
    if (message.role === 'assistant' && call) {
      current.segments.push(
        { kind: 'thinking', status: 'done', durationMs: message.thinking_ms },
        ...(message.narration ? [{ kind: 'narration' as const, text: message.narration }] : []),
        savedToolSegment(call, messages[index + 1]),
      );
      return;
    }
    if (message.role === 'system') {
      // The engine only saves a system message when it stops a run.
      current.status = 'cancelled';
      return;
    }

    current.segments.push({ kind: 'thinking', status: 'done', durationMs: message.thinking_ms });
    if (message.content.startsWith(AGENT_ERROR_PREFIX)) {
      current.status = 'error';
      current.segments.push({
        kind: 'error', message: message.content.slice(AGENT_ERROR_PREFIX.length),
      });
    } else {
      current.segments.push({ kind: 'answer', text: message.content });
    }
  });
  return numberPasses(items);
}

/** Rebuild the turn that is streaming right now from its events so far. */
export function buildLiveTurn(live: AgentLiveTurn, running: boolean, now: number): AgentTurnItem {
  const segments: AgentSegment[] = [];
  let status: AgentTurnStatus = running ? 'running' : 'done';
  // Where the pass currently in flight begins. A pass the engine abandons
  // (stopped, or it failed mid-call) is never saved, so it is dropped here too.
  let passStart = 0;
  let thinkingStarted = 0;
  let tool: ToolSegment | null = null;
  let toolStarted = 0;

  const endThinking = (at: number) => {
    const thinking = segments[passStart] as ThinkingSegment | undefined;
    if (thinking?.kind === 'thinking' && thinking.status === 'running') {
      thinking.status = 'done';
      thinking.durationMs = Math.max(0, at - thinkingStarted);
    }
  };

  for (const event of live.events) {
    const at = event.ts ?? now;
    switch (event.type) {
      case 'llm_start':
        passStart = segments.length;
        thinkingStarted = at;
        tool = null;
        segments.push({ kind: 'thinking', status: 'running', model: event.model });
        break;
      case 'tool_start':
        endThinking(at);
        if (event.narration) segments.push({ kind: 'narration', text: event.narration });
        toolStarted = at;
        tool = { kind: 'tool', tool: event.tool, arguments: event.arguments ?? {}, status: 'running' };
        segments.push(tool);
        break;
      case 'tool_result':
        if (tool) {
          tool.status = event.ok ? 'ok' : 'error';
          tool.result = event.result;
          tool.durationMs = event.duration_ms ?? Math.max(0, at - toolStarted);
        }
        break;
      case 'final':
        endThinking(at);
        status = 'done';
        if (event.content) segments.push({ kind: 'answer', text: event.content });
        break;
      case 'error':
        if (tool?.status === 'running') segments.length = passStart + 1;
        if (event.message === CANCELLED_MESSAGE) {
          segments.length = passStart;
          status = 'cancelled';
        } else {
          endThinking(at);
          status = 'error';
          segments.push({ kind: 'error', message: event.message });
        }
        break;
      default:
        break;
    }
  }

  if (running) {
    // Keep the in-flight timers ticking between events.
    const last = segments[segments.length - 1];
    if (last?.kind === 'thinking' && last.status === 'running') {
      last.durationMs = Math.max(0, now - thinkingStarted);
    } else if (last?.kind === 'tool' && last.status === 'running') {
      last.durationMs = Math.max(0, now - toolStarted);
    }
  } else if (status === 'running') {
    status = 'error';
    segments.push({ kind: 'error', message: 'The agent stopped without replying.' });
  }
  const turn: AgentTurnItem = { kind: 'turn', status, segments };
  numberPasses([turn]);
  return turn;
}
