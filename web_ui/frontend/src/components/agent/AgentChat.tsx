/**
 * Agent chat panel — shared by the left dock and the /agent page.
 */
'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { toast } from 'sonner';
import {
  ArrowDown, Bot, History, Loader2, PenLine, Send, Settings2, Square, X, Zap,
} from 'lucide-react';

import { AgentTurn, TranscriptEmpty, UserBubble } from '@/components/agent/AgentTranscript';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  useAgentChatStream, useAgentConversation, useAgentConfig, useDeleteAgentConversation,
  useUpdateAgentConfig,
} from '@/hooks/useAgent';
import { buildLiveTurn, buildTranscript } from '@/lib/agentTranscript';
import type { ContextUsage, TranscriptItem } from '@/types/agent';
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

const COMPOSER_MAX_HEIGHT = 160;

export function AgentChat({ className }: { className?: string }) {
  const pathname = usePathname();
  const projectId = useMemo(() => {
    const match = pathname?.match(/^\/projects\/([^/]+)/);
    return match?.[1] ?? null;
  }, [pathname]);

  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [listOpen, setListOpen] = useState(false);
  /** Drives the timers of the turn that is streaming. */
  const [now, setNow] = useState(Date.now());
  /** Follow the bottom of the transcript unless the user scrolled up. */
  const [stickToBottom, setStickToBottom] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { data: configData } = useAgentConfig();
  const updateConfig = useUpdateAgentConfig();
  const conversationQuery = useAgentConversation(selectedConversation);
  const conversation = conversationQuery.data;
  const deleteConversation = useDeleteAgentConversation();

  const stream = useAgentChatStream({ onConversation: setSelectedConversation });
  const { live, setConversation } = stream;
  const running = stream.runState !== 'idle';

  // Point the socket at the conversation shown (null = the next message starts a new one).
  useEffect(() => {
    setConversation(selectedConversation);
    setStickToBottom(true);
  }, [selectedConversation, setConversation]);

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
    if (!running) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);

  // The live turn stands in for its saved copy: the engine saves a turn only
  // once it has ended, and the refetched transcript takes over from there.
  const savedMessages = conversation?.messages;
  const showLive = !!live
    && live.conversationId === selectedConversation
    && !(savedMessages && savedMessages.length > live.baseCount);

  const items = useMemo<TranscriptItem[]>(() => {
    const saved = buildTranscript(savedMessages);
    if (!live || !showLive) return saved;
    return [
      ...saved,
      { kind: 'user', content: live.message },
      buildLiveTurn(live, running, now),
    ];
  }, [savedMessages, live, showLive, running, now]);
  // Saved items only ever append, so the position tells blocks of the live
  // turn from their saved copy apart without resetting what the user opened.
  const itemKeyPrefix = selectedConversation ?? live?.conversationId ?? 'draft';

  const handleScroll = () => {
    const el = scrollRef.current;
    if (el) setStickToBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80);
  };

  useLayoutEffect(() => {
    if (stickToBottom) {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    }
  }, [items, stickToBottom]);

  const jumpToLatest = () => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight });
    setStickToBottom(true);
  };

  // Grow the composer with its text, up to a cap.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, COMPOSER_MAX_HEIGHT)}px`;
  }, [input]);

  const conversationPending = !!selectedConversation && conversationQuery.isPending;
  // A message is only safe to send once the conversation it lands in is loaded.
  const canSend = stream.connected && !running && (!selectedConversation || !!conversation)
    && input.trim().length > 0;

  const handleSend = () => {
    const message = input.trim();
    if (!canSend) return;
    if (!stream.sendMessage(message, projectId, savedMessages?.length ?? 0)) {
      toast.error('Agent socket not connected — is the backend running?');
      return;
    }
    setInput('');
    setStickToBottom(true);
  };

  const handleNewChat = () => {
    setSelectedConversation(null);
    setListOpen(false);
  };

  const usage = (showLive && stream.contextUsage) || conversation?.context_usage;
  const emptyState = conversationQuery.isError ? 'error'
    : conversationPending ? 'loading' : 'welcome';

  return (
    <div className={cn('flex h-full min-h-0 flex-col bg-background', className)}>
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-md shadow-primary/30">
          <Bot className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold">AI Agent</span>
        {projectId && (
          <span className="truncate rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground" title={projectId}>
            {projectId}
          </span>
        )}
        <div className="ml-auto flex items-center gap-0.5">
          {usage && <ContextRing usage={usage} />}
          <span
            className={cn('mr-1 h-2 w-2 rounded-full', stream.connected ? 'bg-emerald-500' : 'bg-red-400')}
            title={stream.connected ? 'Connected' : 'Disconnected'}
          />
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              title="Conversations"
              aria-expanded={listOpen}
              onClick={() => setListOpen((v) => !v)}
            >
              <History className="h-4 w-4" />
            </Button>
            {listOpen && (
              <>
                <button
                  type="button"
                  aria-label="Close conversations list"
                  className="fixed inset-0 z-40 cursor-default"
                  onClick={() => setListOpen(false)}
                />
                <div className="absolute right-0 z-50 mt-1 max-h-80 w-72 overflow-auto rounded-lg border bg-popover p-1 shadow-lg">
                  {(configData?.conversations ?? []).length === 0 && (
                    <p className="px-2 py-1.5 text-xs text-muted-foreground">No conversations yet</p>
                  )}
                  {(configData?.conversations ?? []).map((c) => (
                    <div
                      key={c.id}
                      className={cn(
                        'group flex items-center gap-1 rounded-md px-2 py-1.5 text-xs hover:bg-accent',
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
              </>
            )}
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" title="New chat" onClick={handleNewChat}>
            <PenLine className="h-4 w-4" />
          </Button>
          <Link href="/agent" title="Agent settings">
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <Settings2 className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Transcript */}
      <div className="relative min-h-0 flex-1">
        <div ref={scrollRef} onScroll={handleScroll} className="h-full overflow-y-auto">
          {items.length === 0 ? (
            <TranscriptEmpty
              state={emptyState}
              detail={conversationQuery.error instanceof Error ? conversationQuery.error.message : undefined}
            />
          ) : (
            <div className="flex flex-col gap-5 px-3 py-4" aria-label="Conversation">
              {items.map((item, index) => (
                <div key={`${itemKeyPrefix}-${index}`}>
                  {item.kind === 'user'
                    ? <UserBubble content={item.content} />
                    : <AgentTurn turn={item} />}
                </div>
              ))}
            </div>
          )}
        </div>
        {!stickToBottom && (
          <button
            type="button"
            onClick={jumpToLatest}
            aria-label="Jump to latest"
            title="Jump to latest"
            className="absolute bottom-3 left-1/2 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border bg-popover text-muted-foreground shadow-lg transition-colors hover:text-foreground"
          >
            <ArrowDown className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Input */}
      <div className="shrink-0 border-t p-2.5">
        <div className={cn(
          'rounded-xl border bg-card transition-[border-color,box-shadow]',
          'focus-within:border-primary/60 focus-within:shadow-[0_0_0_1px_hsl(var(--primary)/0.35)]',
          !stream.connected && 'opacity-60',
        )}>
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={stream.connected ? 'Ask the agent…' : 'Connecting to backend…'}
            rows={1}
            className="max-h-40 min-h-6 resize-none overflow-y-auto border-0 bg-transparent px-3 pb-1 pt-2.5 text-sm shadow-none focus-visible:ring-0"
            disabled={!stream.connected}
          />
          <div className="flex items-center gap-2 px-2 pb-2 pt-0.5">
            {configData?.config.effort_supported && (
              <Select
                value={configData.config.effort || '__auto__'}
                onValueChange={(v) =>
                  updateConfig.mutate({ effort: v === '__auto__' ? '' : v })}
              >
                <SelectTrigger
                  className="h-7 w-[104px] rounded-full border-none bg-muted text-[11px]"
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
            {running ? (
              <Button
                variant="destructive"
                size="icon"
                className="ml-auto h-8 w-8 rounded-full"
                onClick={stream.stop}
                disabled={stream.runState === 'stopping'}
                title={stream.runState === 'stopping' ? 'Stopping…' : 'Stop'}
              >
                {stream.runState === 'stopping'
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <Square className="h-3.5 w-3.5 fill-current" />}
              </Button>
            ) : (
              <Button
                size="icon"
                className="ml-auto h-8 w-8 rounded-full"
                onClick={handleSend}
                disabled={!canSend}
                title="Send"
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
          Enter to send · Shift + Enter for a new line
        </p>
      </div>
    </div>
  );
}
