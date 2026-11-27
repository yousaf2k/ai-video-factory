/**
 * Markdown renderer for agent output (answers and working notes).
 */
'use client';

import { useState } from 'react';
import Markdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy } from 'lucide-react';

import { cn } from '@/lib/utils';

export function CopyButton({ text, label, className }: {
  text: string;
  label: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable (insecure origin) — nothing to report
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      title={copied ? 'Copied' : label}
      aria-label={label}
      className={cn(
        'inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
        className,
      )}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

const COMPONENTS: Components = {
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg border border-border/60 bg-background/70 p-2.5 font-mono text-xs leading-relaxed [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-inherit">
      {children}
    </pre>
  ),
  code: ({ children }) => (
    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em] text-foreground">
      {children}
    </code>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table>{children}</table>
    </div>
  ),
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-2">
      {children}
    </a>
  ),
};

export function AgentMarkdown({ children, muted = false }: { children: string; muted?: boolean }) {
  return (
    <div
      className={cn(
        'prose prose-sm prose-invert max-w-none break-words whitespace-pre-wrap',
        '[&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0',
        '[&_h1]:my-2 [&_h2]:my-2 [&_h3]:my-2 [&_h4]:my-2',
        '[&_h1]:text-[15px] [&_h2]:text-[15px] [&_h3]:text-sm [&_h4]:text-sm',
        muted && '[--tw-prose-body:hsl(var(--muted-foreground))] [--tw-prose-bold:hsl(var(--foreground))] [--tw-prose-headings:hsl(var(--foreground))]',
      )}
    >
      <Markdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>{children}</Markdown>
    </div>
  );
}
