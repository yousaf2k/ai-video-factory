/**
 * Shell that hosts the page content and the AI Agent dock.
 *
 * When the dock opens on desktop it PUSHES the page (the whole layout,
 * header included, gets left padding = dock width) instead of floating
 * over it. On narrow screens the dock still overlays.
 */
'use client';

import { useEffect, useState } from 'react';

import { AgentDock } from '@/components/agent/AgentDock';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'agent-dock-open';

export function AgentShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setOpen(window.localStorage.getItem(STORAGE_KEY) === '1');
  }, []);

  const toggle = (value: boolean) => {
    setOpen(value);
    window.localStorage.setItem(STORAGE_KEY, value ? '1' : '0');
  };

  return (
    <>
      <div
        className={cn(
          'min-h-screen bg-background transition-[padding] duration-200 ease-out',
          mounted && open && 'lg:pl-[380px]',
        )}
      >
        {children}
      </div>
      <AgentDock open={open} onOpenChange={toggle} />
    </>
  );
}
