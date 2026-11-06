/**
 * Agent chat panel — shared by the left dock and the /agent page.
 */
'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Bot, Check, ChevronDown, Loader2, MessageSquarePlus, Send, Settings2, Square, Wrench, X, Zap,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  useAgentChatStream, useAgentConversation, useAgentConfig, useDeleteAgentConversation,
  useUpdateAgentConfig,
} from '@/hooks/useAgent';
import type { AgentStreamEvent, ContextUsage, TimedAgentEvent } from '@/types/agent';
import { cn } from '@/lib/utils';

function ContextRing({ usage }: { usage: ContextUsage }) {
  const radius = 10;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(usage.percent, 100);
  const color = pct > 85
    ? 'text-red-400'
    : pct > 60 ? 'text-amber-500' : 'text-emerald-400';
  return (
    <div
      className="relative h-7 w-7 shrink-0"
      title={`Context used: ≈${usage.est_tokens.toLocaleString()} / ${usage.limit_tokens.toLocaleString()} tokens (${usage.percent}%) — estimate`}
    >
      <svg viewBox="0 0 28 28" className="h-7 w-7 -rotate-90">
        <circle cx="14" cy="14" r={radius} className="stroke-muted" strokeWidth="3" fill="none" />
        <circle
          cx="14" cy="14" r={radius}
          className={cn('stroke-current transition-[stroke-dashoffset]', color)}
          strokeWidth="3" fill="none" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - pct / 100)}
        />
      </svg>
      <span className={cn(
        'absolute inset-0 flex items-center justify-center text-[8px] font-semibold tabular-nums',
        color,
      )}>
        {Math.round(pct)}
      </span>
    </div>
  );
}

/**
 * Live activity ticker: one constantly-updating status line while the agent
 * works; click to expand the full step-by-step log of the current run.
 */
function LiveActivity({ events, busy }: { events: TimedAgentEvent[]; busy: boolean }) {
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(Date.now());
  const listRef = useRef<HTMLDivElement>(null);

  const meaningful = events.filter(
    (e) => !['final', 'done', 'context_usage', 'pong'].includes(e.type),
  );
  const finished = events.some((e) => e.type === 'done');
  const started = meaningful.length > 0 || busy;

  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  useEffect(() => {
    if (open && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [events.length, open]);

  if (!started) return null;

  const firstTs = meaningful[0]?.ts ?? Date.now();
  const lastTs = events[events.length - 1]?.ts ?? Date.now();
  const elapsed = Math.max(0, Math.round(((finished ? lastTs : now) - firstTs) / 1000));

  // Ticker text = latest meaningful event
  let status = 'Thinking…';
  let failed = false;
  for (let i = meaningful.length - 1; i >= 0; i--) {
    const e = meaningful[i];
    if (e.type === 'tool_start') { status = `Running ${e.tool}…`; break; }
    if (e.type === 'tool_result') { status = `${e.ok ? '✓' : '✗'} ${e.tool}`; failed = !e.ok; break; }
    if (e.type === 'llm_start') { status = `Thinking${e.model ? ` · ${e.model}` : ''}…`; break; }
    if (e.type === 'error') { status = `Error: ${e.message.slice(0, 80)}`; failed = true; break; }
  }

  const toolCount = meaningful.filter((e) => e.type === 'tool_result').length;

  return (
    <div className="max-w-[92%] rounded-lg border bg-muted/30 text-xs">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left hover:bg-muted/60"
      >
        {busy ? (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />
        ) : (
          <Check className={cn('h-3.5 w-3.5 shrink-0', failed ? 'text-red-400' : 'text-emerald-400')} />
        )}
        <span className={cn('truncate', failed && 'text-red-400')}>
          {busy
            ? status
            : `${toolCount} tool call${toolCount === 1 ? '' : 's'}${failed ? ' — one failed' : ' completed'}`}
        </span>
        <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">{elapsed}s</span>
        <ChevronDown className={cn('h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div ref={listRef} className="max-h-64 space-y-1.5 overflow-y-auto border-t px-2.5 py-2">
          {meaningful.map((event, i) => {
            if (event.type === 'tool_start' || event.type === 'tool_result') {
              return <ToolEvent key={i} event={event} />;
            }
            if (event.type === 'llm_start') {
              return (
                <p key={i} className="px-1 text-[11px] italic text-muted-foreground">
                  thinking (pass {event.iteration})…
                </p>
              );
            }
            if (event.type === 'error') {
              return <p key={i} className="px-1 text-[11px] text-red-400">{event.message}</p>;
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}

function ToolEvent({ event }: { event: AgentStreamEvent }) {
  const [open, setOpen] = useState(false);
  if (event.type === 'tool_start') {
    return (
      <div className="rounded-md border bg-muted/40 px-2.5 py-1.5 text-xs">
        <span className="inline-flex items-center gap-1.5 font-medium text-amber-500">
          <Wrench className="h-3 w-3" /> {event.tool}
        </span>
        <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-all text-[11px] text-muted-foreground">
          {JSON.stringify(event.arguments, null, 2)}
        </pre>
      </div>
    );
  }
  if (event.type === 'tool_result') {
    const text = typeof event.result === 'string'
      ? event.result
      : JSON.stringify(event.result, null, 2);
    return (
      <div className="rounded-md border bg-muted/40 px-2.5 py-1.5 text-xs">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1.5 font-medium"
        >
          {event.ok ? (
            <span className="text-emerald-400">✓ {event.tool}</span>
          ) : (
            <span className="text-red-400">✗ {event.tool}</span>
          )}
          <ChevronDown className={cn('h-3 w-3 transition-transform', open && 'rotate-180')} />
        </button>
        {open && (
          <pre className="mt-1 max-h-52 overflow-auto whitespace-pre-wrap break-all text-[11px] text-muted-foreground">
            {text?.slice(0, 4000)}
          </pre>
        )}
      </div>
    );
  }
  return null;
}

export function AgentChat({ className }: { className?: string }) {
  const pathname = usePathname();
  const projectId = useMemo(() => {
    const match = pathname?.match(/^\/projects\/([^/]+)/);
    return match?.[1] ?? null;
  }, [pathname]);

  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [streamFinal, setStreamFinal] = useState<string | null>(null);
  const [listOpen, setListOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: configData } = useAgentConfig();
  const updateConfig = useUpdateAgentConfig();
  const { data: conversation } = useAgentConversation(selectedConversation);
  const deleteConversation = useDeleteAgentConversation();

  const stream = useAgentChatStream({
    onFinal: (_id, content) => setStreamFinal(content),
  });

  // When the user picks a conversation, bind the socket to it.
  useEffect(() => {
    stream.setConversation(selectedConversation);
    setStreamFinal(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedConversation]);

  // On mount, auto-load the most recent conversation (once — an explicit
  // "New chat" afterwards must stay blank).
  const didAutoSelect = useRef(false);
  useEffect(() => {
    if (didAutoSelect.current) return;
    const conversations = configData?.conversations;
    if (!conversations) return; // still loading
    didAutoSelect.current = true;
    if (conversations.length > 0 && !selectedConversation) {
      setSelectedConversation(conversations[0].id); // list is sorted by updated_at desc
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configData?.conversations]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [conversation?.messages?.length, stream.liveEvents.length, streamFinal]);

  const handleSend = () => {
    const message = input.trim();
    if (!message || stream.busy) return;
    setStreamFinal(null);
    stream.sendMessage(message, projectId);
    setInput('');
  };

  const handleNewChat = () => {
    setSelectedConversation(null);
    stream.resetConversation();
    setStreamFinal(null);
  };

  return (
    <div className={cn('flex h-full min-h-0 flex-col bg-background', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Bot className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold">AI Agent</span>
        {projectId && (
          <span className="truncate rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
            {projectId}
          </span>
        )}
        <div className="ml-auto flex items-center gap-1">
          {(stream.contextUsage ?? conversation?.context_usage) && (
            <ContextRing usage={(stream.contextUsage ?? conversation?.context_usage)!} />
          )}
          <span
            className={cn(
              'mr-1 h-2 w-2 rounded-full',
              stream.connected ? 'bg-emerald-500' : 'bg-red-400',
            )}
            title={stream.connected ? 'Connected' : 'Disconnected'}
          />
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              title="Conversations"
              onClick={() => setListOpen((v) => !v)}
            >
              <MessageSquarePlus className="h-4 w-4" />
            </Button>
            {listOpen && (
              <div className="absolute right-0 z-50 mt-1 max-h-80 w-72 overflow-auto rounded-md border bg-popover p-1 shadow-md">
                {(configData?.conversations ?? []).length === 0 && (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">No conversations yet</p>
                )}
                {(configData?.conversations ?? []).map((c) => (
                  <div
                    key={c.id}
                    className={cn(
                      'group flex items-center gap-1 rounded px-2 py-1.5 text-xs hover:bg-accent',
                      c.id === selectedConversation && 'bg-accent',
                    )}
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => {
                        setSelectedConversation(c.id);
                        setListOpen(false);
                      }}
                    >
                      <span className="block truncate font-medium">{c.title}</span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {c.message_count} messages · {c.updated_at?.slice(0, 16).replace('T', ' ')}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="opacity-0 transition-opacity group-hover:opacity-100"
                      title="Delete conversation"
                      onClick={() => {
                        deleteConversation.mutate(c.id);
                        if (c.id === selectedConversation) handleNewChat();
                      }}
                    >
                      <X className="h-3.5 w-3.5 text-muted-foreground hover:text-red-400" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" title="New chat" onClick={handleNewChat}>
            <MessageSquarePlus className="h-4 w-4" />
          </Button>
          <Link href="/agent" title="Agent settings">
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <Settings2 className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Transcript */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
        {!conversation && stream.liveEvents.length === 0 && !streamFinal && (
          <div className="px-2 py-6 text-center text-xs text-muted-foreground">
            <Bot className="mx-auto mb-2 h-8 w-8 opacity-30" />
            <p className="font-medium text-foreground">Ask me anything about your projects.</p>
            <p className="mt-1">
              I can create projects, fix shot prompts, generate stories & media,
              manage the queue, edit workflows/directors and search project files.
            </p>
            <p className="mt-2 opacity-70">
              e.g. “shot 4 video prompt the character is not doing it — fix it and regenerate”
            </p>
          </div>
        )}

        {(conversation?.messages ?? [])
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((message, i) => (
            <div
              key={i}
              className={cn(
                'max-w-[92%] rounded-lg px-3 py-2 text-sm',
                message.role === 'user'
                  ? 'ml-auto bg-primary text-primary-foreground'
                  : 'bg-muted',
              )}
            >
              {message.role === 'assistant' ? (
                <div className="prose prose-sm prose-invert max-w-none break-words whitespace-pre-wrap [&_p]:m-0 [&_p]:whitespace-pre-wrap">
                  <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap break-words">{message.content}</p>
              )}
            </div>
          ))}

        {/* Live activity: single updating ticker line, click to expand the full log */}
        <LiveActivity events={stream.liveEvents} busy={stream.busy} />

        {streamFinal && (
          <div className="max-w-[92%] rounded-lg bg-muted px-3 py-2 text-sm">
            <div className="prose prose-sm prose-invert max-w-none break-words whitespace-pre-wrap [&_p]:m-0 [&_p]:whitespace-pre-wrap">
              <Markdown remarkPlugins={[remarkGfm]}>{streamFinal}</Markdown>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-2.5">
        <div className="flex items-end gap-2">
          {configData?.config.effort_supported && (
            <Select
              value={configData.config.effort || '__auto__'}
              onValueChange={(v) =>
                updateConfig.mutate({ effort: v === '__auto__' ? '' : v })}
            >
              <SelectTrigger
                className="h-[44px] w-[104px] shrink-0 text-xs"
                title="Reasoning effort — Auto uses the model's default"
              >
                <Zap className="h-3.5 w-3.5 shrink-0 text-amber-500" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__auto__">Auto</SelectItem>
                {configData.config.effort_options.map((e) => (
                  <SelectItem key={e} value={e}>
                    {e.charAt(0).toUpperCase() + e.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={
              stream.connected
                ? 'Ask the agent… (Enter to send, Shift+Enter for a new line)'
                : 'Connecting to backend…'
            }
            rows={2}
            className="max-h-32 min-h-[44px] resize-none text-sm"
            disabled={!stream.connected}
          />
          {stream.busy ? (
            <Button variant="destructive" size="icon" onClick={stream.stop} title="Stop">
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button size="icon" onClick={handleSend} disabled={!input.trim() || !stream.connected} title="Send">
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
