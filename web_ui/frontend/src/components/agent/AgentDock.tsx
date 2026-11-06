/**
 * AI Agent Assistant dock — left-edge handle + slide-in chat panel.
 * Controlled by AgentShell: on desktop the shell pushes the page aside,
 * so this panel only needs to occupy the space the shell reserved
 * (overlay on narrow screens).
 */
'use client';

import { Bot, X } from 'lucide-react';

import { AgentChat } from '@/components/agent/AgentChat';
import { cn } from '@/lib/utils';

export function AgentDock({ open, onOpenChange }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <>
      {/* Left-edge handle */}
      <button
        type="button"
        aria-label={open ? 'Close AI Agent panel' : 'Open AI Agent panel'}
        onClick={() => onOpenChange(!open)}
        className={cn(
          'fixed left-0 top-1/2 z-40 -translate-y-1/2 rounded-r-xl border border-l-0 bg-primary px-1.5 py-4 text-primary-foreground shadow-lg transition-transform hover:scale-105',
          open && 'translate-x-[min(380px,92vw)]',
        )}
        title="AI Agent Assistant"
      >
        <Bot className="h-5 w-5" />
      </button>

      {/* Chat panel */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-[380px] max-w-[92vw] border-r bg-card shadow-2xl transition-transform duration-200 ease-out',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <button
          type="button"
          aria-label="Close panel"
          onClick={() => onOpenChange(false)}
          className="absolute -right-3 top-3 z-10 rounded-full border bg-background p-1 shadow"
        >
          <X className="h-4 w-4" />
        </button>
        <AgentChat className="h-full" />
      </div>
    </>
  );
}
