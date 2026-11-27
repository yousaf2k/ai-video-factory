/**
 * Transcript list: user bubbles on the right, agent turns (working steps +
 * answer) on the left. Saved conversations and the live stream both render
 * through this one list.
 */
'use client';

import { memo } from 'react';
import { AlertCircle, Ban, Bot, Loader2 } from 'lucide-react';

import { AgentMarkdown, CopyButton } from '@/components/agent/AgentMarkdown';
import { ThinkingBlock, ToolBlock } from '@/components/agent/AgentSteps';
import { cn } from '@/lib/utils';
import type { AgentSegment, AgentTurnItem } from '@/types/agent';

const SHIMMER = 'animate-agent-shimmer bg-gradient-to-r from-muted-foreground via-foreground to-muted-foreground bg-[length:200%_auto] bg-clip-text text-transparent';

export function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap [overflow-wrap:anywhere] rounded-2xl rounded-br-md bg-primary/80 px-3.5 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-lg shadow-primary/20">
        {content}
      </div>
    </div>
  );
}

/** What a pass led to: the first step after its thinking row. */
function passOutcome(following: AgentSegment[]): string {
  const next = following.find((segment) => segment.kind !== 'narration');
  switch (next?.kind) {
    case 'tool': return `Called ${next.tool}`;
    case 'answer': return 'Wrote the reply';
    case 'error': return 'The run failed';
    default: return 'Interrupted';
  }
}

function Segment({ segment, following }: { segment: AgentSegment; following: AgentSegment[] }) {
  switch (segment.kind) {
    case 'thinking':
      return <ThinkingBlock segment={segment} outcome={passOutcome(following)} />;
    case 'narration':
      return (
        <div className="px-0.5">
          <AgentMarkdown muted>{segment.text}</AgentMarkdown>
        </div>
      );
    case 'tool':
      return <ToolBlock segment={segment} />;
    case 'answer':
      return (
        <div className="group relative rounded-2xl rounded-tl-md border border-border/70 bg-card px-3.5 py-2.5 shadow-sm">
          <AgentMarkdown>{segment.text}</AgentMarkdown>
          <CopyButton
            text={segment.text}
            label="Copy answer"
            className="absolute -top-3 right-2 border border-border bg-popover opacity-0 shadow-md group-hover:opacity-100 focus-visible:opacity-100"
          />
        </div>
      );
    case 'error':
      return (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-2 text-xs text-red-200">
          <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0 text-red-400" />
          <span className="[overflow-wrap:anywhere]">{segment.message}</span>
        </div>
      );
  }
}

export const AgentTurn = memo(function AgentTurn({ turn }: { turn: AgentTurnItem }) {
  // Busy, but between two steps (e.g. before the first event arrives).
  const waiting = turn.status === 'running'
    && !turn.segments.some(
      (segment) => (segment.kind === 'thinking' || segment.kind === 'tool') && segment.status === 'running',
    );

  return (
    <div className="flex gap-2.5">
      <div className="flex w-7 shrink-0 flex-col items-center">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-md shadow-primary/30">
          <Bot className="h-4 w-4" />
        </div>
        <div className="mt-1.5 w-px flex-1 rounded-full bg-border/70" />
      </div>
      <div className="min-w-0 flex-1 space-y-1.5 pb-1">
        {turn.segments.map((segment, index) => (
          <Segment key={index} segment={segment} following={turn.segments.slice(index + 1)} />
        ))}
        {turn.status === 'cancelled' && (
          <p className="flex items-center gap-1.5 px-1.5 py-1 text-xs text-muted-foreground">
            <Ban className="h-3.5 w-3.5" />
            Stopped
          </p>
        )}
        {waiting && (
          <p className="flex items-center gap-1.5 px-1.5 py-1 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className={SHIMMER}>Working…</span>
          </p>
        )}
      </div>
    </div>
  );
});

export function TranscriptEmpty({ state, detail }: {
  state: 'loading' | 'error' | 'welcome';
  detail?: string;
}) {
  if (state === 'loading') {
    return (
      <div className="space-y-3 px-3 py-4" aria-label="Loading conversation">
        {[16, 12, 20, 10, 14].map((height, index) => (
          <div
            key={index}
            className={cn('h-6 animate-pulse rounded-lg bg-muted/60', index % 2 ? 'ml-auto' : 'mr-auto')}
            style={{ width: `${height * 4}%` }}
          />
        ))}
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="px-6 py-10 text-center text-sm text-muted-foreground">
        <p className="font-medium text-foreground">Couldn&apos;t load this conversation.</p>
        {detail && <p className="mt-1 break-words text-xs">{detail}</p>}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-lg shadow-primary/30">
        <Bot className="h-6 w-6" />
      </div>
      <p className="mt-4 text-sm font-semibold">Ask me anything about your projects.</p>
      <p className="mt-1.5 max-w-[280px] text-xs leading-relaxed text-muted-foreground">
        I can create projects, fix shot prompts, generate stories &amp; media, manage the
        queue, edit workflows and directors, and search project files.
      </p>
      <p className="mt-4 max-w-[300px] rounded-xl border border-border/70 bg-card px-3 py-2 text-xs leading-relaxed text-muted-foreground">
        e.g. &ldquo;shot 4 video prompt — the character isn&apos;t doing it. Fix it and
        regenerate&rdquo;
      </p>
    </div>
  );
}
