/**
 * Collapsible activity blocks of an agent pass: the "thinking" row and the
 * tool call it led to. Both are folded to one line until the user opens them,
 * live and after a refresh alike; a running step shows its progress in the row.
 */
'use client';

import { useState, type ReactNode } from 'react';
import {
  Ban, Brain, Check, ChevronRight, Copy, Loader2, Pencil, Plug, Plus, Search, Sparkles,
  Trash2, Wrench, X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { CopyButton } from '@/components/agent/AgentMarkdown';
import { formatDuration, formatResult, summarizeArguments } from '@/lib/agentTranscript';
import { cn } from '@/lib/utils';
import type { ThinkingSegment, ToolSegment } from '@/types/agent';

/** Icon per tool, by what its name says it does. */
const TOOL_ICONS: Array<[RegExp, LucideIcon]> = [
  [/^mcp__/, Plug],
  [/^(get|list|read|search|find|select)_/, Search],
  [/^(add|create)_/, Plus],
  [/^(delete|remove|clear)_/, Trash2],
  [/^cancel_/, Ban],
  [/^duplicate_/, Copy],
  [/^(generate|regenerate|batch|queue|run)_/, Sparkles],
  [/^(update|write|edit|set|fix|upload|replan)_/, Pencil],
];

function ToolIcon({ tool }: { tool: string }) {
  const Icon = TOOL_ICONS.find(([pattern]) => pattern.test(tool))?.[1] ?? Wrench;
  return <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground/80" aria-hidden />;
}

const Spinner = () => <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />;

function StepBlock({ open, onToggle, icon, trailing, body, children }: {
  open: boolean;
  onToggle: () => void;
  icon: ReactNode;
  trailing?: ReactNode;
  body: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={cn(
      'rounded-lg border transition-colors',
      open ? 'border-border/70 bg-muted/20' : 'border-transparent',
    )}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center gap-1.5 rounded-lg px-1.5 py-1 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
      >
        {icon}
        {children}
        <span className="ml-auto flex shrink-0 items-center gap-1.5">
          {trailing}
          <ChevronRight className={cn(
            'h-3.5 w-3.5 transition-transform duration-200',
            open && 'rotate-90',
          )} />
        </span>
      </button>
      <div className={cn(
        'grid transition-[grid-template-rows] duration-200 ease-out',
        open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
      )}>
        <div className="min-h-0 overflow-hidden">{body}</div>
      </div>
    </div>
  );
}

export function ThinkingBlock({ segment, outcome }: {
  segment: ThinkingSegment;
  outcome: string;
}) {
  const [open, setOpen] = useState(false);
  const running = segment.status === 'running';
  const elapsed = formatDuration(segment.durationMs);

  return (
    <StepBlock
      open={open}
      onToggle={() => setOpen((value) => !value)}
      icon={running ? <Spinner /> : <Brain className="h-3.5 w-3.5 shrink-0" />}
      trailing={running && segment.durationMs != null && (
        <span className="tabular-nums">{Math.floor(segment.durationMs / 1000)}s</span>
      )}
      body={
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-t border-border/60 px-2.5 py-2">
          <dt>Pass</dt>
          <dd>{segment.iteration}</dd>
          <dt>Duration</dt>
          <dd className="tabular-nums">{running ? 'still thinking' : elapsed || 'not recorded'}</dd>
          <dt>Outcome</dt>
          <dd>{outcome}</dd>
        </dl>
      }
    >
      {running ? (
        <span className="animate-agent-shimmer bg-gradient-to-r from-muted-foreground via-foreground to-muted-foreground bg-[length:200%_auto] bg-clip-text text-transparent">
          Thinking…
        </span>
      ) : (
        <span>Thought{elapsed && ` for ${elapsed}`}</span>
      )}
    </StepBlock>
  );
}

const PAYLOAD_MAX_CHARS = 20000;

function Payload({ label, text, error = false }: { label: string; text: string; error?: boolean }) {
  const shown = text.slice(0, PAYLOAD_MAX_CHARS);
  return (
    <div className="border-t border-border/60 px-2.5 py-2">
      <div className="mb-1 flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider">{label}</span>
        {shown.length < text.length && (
          <span className="text-[10px]">first {PAYLOAD_MAX_CHARS.toLocaleString()} characters</span>
        )}
        <CopyButton
          text={shown}
          label={`Copy ${label.toLowerCase()}`}
          className="ml-auto h-5 w-5"
        />
      </div>
      <pre className={cn(
        'max-h-56 overflow-auto whitespace-pre-wrap [overflow-wrap:anywhere] rounded-md bg-background/60 p-2 font-mono text-[11px] leading-relaxed',
        error ? 'text-red-300' : 'text-muted-foreground',
      )}>
        {shown}
      </pre>
    </div>
  );
}

export function ToolBlock({ segment }: { segment: ToolSegment }) {
  const [open, setOpen] = useState(false);
  const running = segment.status === 'running';
  const failed = segment.status === 'error';

  return (
    <StepBlock
      open={open}
      onToggle={() => setOpen((value) => !value)}
      icon={
        running ? <Spinner />
          : failed ? <X className="h-3.5 w-3.5 shrink-0 text-red-400" />
            : <Check className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
      }
      trailing={segment.durationMs != null && (
        <span className={cn('tabular-nums', running ? 'text-foreground' : failed && 'text-red-400')}>
          {formatDuration(segment.durationMs)}
        </span>
      )}
      body={
        <>
          <Payload label="Input" text={JSON.stringify(segment.arguments, null, 2) ?? ''} />
          {running ? (
            <p className="border-t border-border/60 px-2.5 py-2 text-[11px]">
              Waiting for the tool to finish…
            </p>
          ) : segment.result !== undefined && (
            <Payload
              label={failed ? 'Error' : 'Output'}
              text={formatResult(segment.result)}
              error={failed}
            />
          )}
        </>
      }
    >
      <ToolIcon tool={segment.tool} />
      <span className={cn('font-mono font-medium', failed ? 'text-red-400' : 'text-foreground')}>
        {segment.tool}
      </span>
      <span className="truncate">{summarizeArguments(segment.arguments)}</span>
    </StepBlock>
  );
}
