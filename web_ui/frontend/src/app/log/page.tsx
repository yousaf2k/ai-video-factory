/**
 * Logs Page - structured view of pipeline logs.
 *
 * Phase 1: LLM call log. The top section lists LLM calls (inputs); selecting
 * one shows its full input/output in the bottom section. The center splitter
 * is draggable to resize the two sections.
 */
'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLLMLogs, useLLMLogDetail } from '../../hooks/useLLMLogs';
import { LLMLogEntrySummary } from '../../types';
import { Button } from '@/components/ui/button';
import { ConfirmDialog, useConfirmDialog } from '@/components/ui/confirm-dialog';
import {
  AlertCircle,
  Check,
  Copy,
  Loader2,
  MousePointerClick,
  RefreshCw,
  ScrollText,
  Trash2,
} from 'lucide-react';

const MIN_TOP_PERCENT = 15;
const MAX_TOP_PERCENT = 85;
const DEFAULT_TOP_PERCENT = 45;

const formatTime = (iso: string) => {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const time = d.toLocaleTimeString([], { hour12: false });
  if (d.toDateString() === new Date().toDateString()) return time;
  return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${time}`;
};

const formatChars = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));

export default function LogPage() {
  const { entries, total, isLoading, error, refetch, clearLogs, isClearing } = useLLMLogs();
  const { showDialog, dialogProps } = useConfirmDialog();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: detail, isLoading: detailLoading } = useLLMLogDetail(selectedId);

  const [detailTab, setDetailTab] = useState<'output' | 'input'>('output');
  const [copied, setCopied] = useState(false);

  // Split state (top section height as % of the page), persisted to localStorage
  const [topPercent, setTopPercent] = useState(DEFAULT_TOP_PERCENT);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const topPercentRef = useRef(topPercent);
  topPercentRef.current = topPercent;

  // Restore split position
  useEffect(() => {
    const saved = localStorage.getItem('log-split-percent');
    if (saved) {
      const v = parseFloat(saved);
      if (!isNaN(v) && v >= MIN_TOP_PERCENT && v <= MAX_TOP_PERCENT) {
        setTopPercent(v);
      }
    }
  }, []);

  // Auto-select the newest entry once the list loads
  useEffect(() => {
    if (!selectedId && entries.length > 0) {
      setSelectedId(entries[0].id);
    }
  }, [entries, selectedId]);

  // Drop the selection if the selected entry no longer exists (e.g. after Clear)
  useEffect(() => {
    if (selectedId && entries.length > 0 && !entries.some((e) => e.id === selectedId)) {
      setSelectedId(entries[0].id);
    }
    if (selectedId && entries.length === 0) {
      setSelectedId(null);
    }
  }, [entries, selectedId]);

  // Draggable splitter
  const handleDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    if (!isDragging) return;

    const onMove = (e: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect || rect.height === 0) return;
      const pct = ((e.clientY - rect.top) / rect.height) * 100;
      setTopPercent(Math.min(MAX_TOP_PERCENT, Math.max(MIN_TOP_PERCENT, pct)));
    };
    const onUp = () => {
      setIsDragging(false);
      localStorage.setItem('log-split-percent', String(topPercentRef.current));
    };

    document.body.style.cursor = 'row-resize';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      document.body.style.cursor = '';
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isDragging]);

  const handleClear = async () => {
    const confirmed = await showDialog({
      title: 'Clear LLM Call Log',
      description: `Delete all ${total} LLM call log entries? This cannot be undone.`,
      type: 'delete',
      confirmText: 'Clear Log',
    });
    if (confirmed) {
      clearLogs();
      setSelectedId(null);
    }
  };

  const copyVisibleContent = useCallback(async () => {
    if (!detail) return;
    const content = detailTab === 'input' ? detail.prompt : detail.output || detail.error || '';
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable — ignore
    }
  }, [detail, detailTab]);

  return (
    <div
      ref={containerRef}
      className={`flex flex-col bg-background ${isDragging ? 'select-none' : ''}`}
      style={{ height: 'calc(100vh - 61px)' }}
    >
      {/* Toolbar */}
      <div className="flex shrink-0 items-center justify-between border-b bg-card px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-foreground">Logs</h1>
          <div className="flex items-center rounded-md bg-muted p-0.5">
            <span className="rounded bg-background px-2.5 py-1 text-xs font-medium shadow-sm">
              LLM Calls
            </span>
          </div>
          {total > 0 && (
            <span className="text-xs text-muted-foreground">
              {total} call{total === 1 ? '' : 's'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => refetch()} title="Refresh">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            disabled={isClearing || total === 0}
            className="text-destructive hover:text-destructive"
            title="Clear LLM call log"
          >
            {isClearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Clear
          </Button>
        </div>
      </div>

      {/* Top section: list of LLM calls (inputs) */}
      <div className="shrink-0 overflow-y-auto" style={{ height: `${topPercent}%` }}>
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading LLM calls...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex h-full items-center justify-center p-6">
            <div className="text-center">
              <AlertCircle className="mx-auto mb-2 h-6 w-6 text-destructive" />
              <p className="text-sm text-destructive">Failed to load LLM call log</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          </div>
        ) : entries.length === 0 ? (
          <div className="flex h-full items-center justify-center p-6">
            <div className="max-w-md text-center">
              <ScrollText className="mx-auto mb-2 h-8 w-8 text-muted-foreground/40" />
              <h3 className="mb-1 font-medium text-foreground">No LLM calls logged yet</h3>
              <p className="text-sm text-muted-foreground">
                Generate a story or video and every LLM request/response will appear here.
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Column header */}
            <div className="sticky top-0 z-10 flex items-center gap-3 border-b bg-card/95 px-4 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground backdrop-blur">
              <span className="w-2 shrink-0" />
              <span className="w-[88px] shrink-0">Time</span>
              <span className="w-24 shrink-0">Provider</span>
              <span className="w-52 shrink-0">Model</span>
              <span className="w-12 shrink-0 text-right">Time</span>
              <span className="flex-1">Input Preview</span>
              <span className="w-14 shrink-0 text-right">Out</span>
            </div>
            {entries.map((entry) => (
              <LogEntryRow
                key={entry.id}
                entry={entry}
                selected={entry.id === selectedId}
                onSelect={() => setSelectedId(entry.id)}
              />
            ))}
          </>
        )}
      </div>

      {/* Draggable center splitter */}
      <div
        role="separator"
        aria-orientation="horizontal"
        onMouseDown={handleDragStart}
        onDoubleClick={() => setTopPercent(DEFAULT_TOP_PERCENT)}
        className="group flex h-2 shrink-0 cursor-row-resize items-center justify-center border-y bg-muted/40 transition-colors hover:bg-primary/20"
        title="Drag to resize · double-click to reset"
      >
        <div className="h-0.5 w-12 rounded-full bg-border transition-colors group-hover:bg-primary/60" />
      </div>

      {/* Bottom section: detail of the selected call */}
      <div className="flex min-h-0 flex-1 flex-col">
        {!selectedId ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center text-muted-foreground">
              <MousePointerClick className="mx-auto mb-2 h-8 w-8 opacity-40" />
              <p className="text-sm">Select an LLM call above to view its input and output</p>
            </div>
          </div>
        ) : detailLoading || !detail ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (
          <>
            {/* Detail header */}
            <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 py-2">
              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {detail.provider}
              </span>
              <span className="max-w-[300px] truncate text-xs text-muted-foreground" title={detail.model}>
                {detail.model}
              </span>
              <span className="text-xs text-muted-foreground">·</span>
              <span className="text-xs tabular-nums text-muted-foreground" title={detail.timestamp}>
                {new Date(detail.timestamp).toLocaleString()}
              </span>
              <span className="text-xs text-muted-foreground">·</span>
              <span className="text-xs tabular-nums text-muted-foreground">
                {detail.elapsed_sec.toFixed(1)}s
              </span>
              <span className="text-xs text-muted-foreground">·</span>
              <span className="text-xs tabular-nums text-muted-foreground">
                {formatChars(detail.prompt_chars)} in / {formatChars(detail.output_chars)} out
              </span>
              {detail.response_format && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground">
                  {detail.response_format}
                </span>
              )}
              {detail.status === 'error' && (
                <span className="flex items-center gap-1 rounded bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium uppercase text-destructive">
                  <AlertCircle className="h-3 w-3" />
                  Error
                </span>
              )}

              <div className="ml-auto flex items-center gap-1">
                <Button
                  variant={detailTab === 'output' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setDetailTab('output')}
                >
                  Output
                </Button>
                <Button
                  variant={detailTab === 'input' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setDetailTab('input')}
                >
                  Input
                </Button>
                <Button variant="ghost" size="icon" onClick={copyVisibleContent} title="Copy">
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Error banner */}
            {detail.status === 'error' && detail.error && (
              <div className="flex shrink-0 items-start gap-2 border-b bg-destructive/10 px-4 py-2">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
                <span className="break-words text-xs text-destructive">{detail.error}</span>
              </div>
            )}

            {/* Body */}
            <div className="min-h-0 flex-1 overflow-auto p-4">
              <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-foreground">
                {detailTab === 'input'
                  ? detail.prompt
                  : detail.status === 'error'
                    ? detail.error || 'No output — the call failed.'
                    : detail.output || ''}
              </pre>
            </div>
          </>
        )}
      </div>

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}

interface LogEntryRowProps {
  entry: LLMLogEntrySummary;
  selected: boolean;
  onSelect: () => void;
}

function LogEntryRow({ entry, selected, onSelect }: LogEntryRowProps) {
  const isError = entry.status === 'error';
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-center gap-3 border-l-2 px-4 py-1.5 text-left text-sm transition-colors ${
        selected
          ? 'border-l-primary bg-primary/10'
          : 'border-l-transparent hover:bg-muted/50'
      }`}
      title={entry.prompt_preview}
    >
      <span
        className={`h-2 w-2 shrink-0 rounded-full ${
          isError ? 'bg-destructive' : 'bg-green-500'
        }`}
      />
      <span className="w-[88px] shrink-0 truncate font-mono text-xs tabular-nums text-muted-foreground">
        {formatTime(entry.timestamp)}
      </span>
      <span className="w-24 shrink-0 truncate text-xs font-medium text-foreground">
        {entry.provider}
      </span>
      <span className="w-52 shrink-0 truncate text-xs text-muted-foreground" title={entry.model}>
        {entry.model}
      </span>
      <span className="w-12 shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
        {entry.elapsed_sec.toFixed(1)}s
      </span>
      <span
        className={`flex-1 truncate text-xs ${isError ? 'italic text-destructive/80' : 'text-muted-foreground'}`}
      >
        {isError ? entry.error || entry.prompt_preview : entry.prompt_preview || '(empty prompt)'}
      </span>
      <span className="w-14 shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
        {formatChars(entry.output_chars)}
      </span>
    </button>
  );
}
