/**
 * AI Agent Assistant page — full-height chat on the left, settings on the right.
 */
'use client';

import { AgentChat } from '@/components/agent/AgentChat';
import { AgentSettings } from '@/components/agent/AgentSettings';

export default function AgentPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="mb-1 text-2xl font-bold">AI Agent Assistant</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Ask anything about your projects — the agent operates the pipeline through tools,
        skills and MCP servers. Also available as the left-edge dock on every page.
      </p>
      <div className="grid gap-6 lg:grid-cols-[minmax(380px,1fr)_minmax(420px,1.1fr)]">
        <div className="h-[calc(100vh-220px)] min-h-[480px] rounded-lg border">
          <AgentChat className="rounded-lg" />
        </div>
        <div className="rounded-lg border p-4">
          <AgentSettings />
        </div>
      </div>
    </div>
  );
}
