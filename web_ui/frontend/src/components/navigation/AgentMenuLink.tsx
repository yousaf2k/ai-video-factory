'use client';

import Link from 'next/link';
import { Bot } from 'lucide-react';

export default function AgentMenuLink() {
  return (
    <Link
      href="/agent"
      className="flex items-center gap-1.5 text-sm font-medium hover:text-primary transition-colors"
    >
      <Bot className="h-4 w-4" />
      <span>Agent</span>
    </Link>
  );
}
