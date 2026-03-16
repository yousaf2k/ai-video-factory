'use client';

import React from 'react';
import Link from 'next/link';
import { List } from 'lucide-react';
import { useQueue } from '../../hooks/useQueue';

export default function QueueMenuLink() {
  const [mounted, setMounted] = React.useState(false);
  const { statistics } = useQueue({ enabled: true });

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const count = statistics?.queued || 0;

  return (
    <Link 
      href="/queue" 
      className="text-sm font-medium hover:text-primary transition-colors flex items-center gap-1.5 group"
    >
      <List className="w-4 h-4" />
      <span>Queue</span>
      {mounted && count > 0 && (
        <span className="bg-primary/10 text-primary text-xs font-semibold px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center animate-in zoom-in-50 duration-200">
          {count}
        </span>
      )}
    </Link>
  );
}
