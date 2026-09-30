'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

/**
 * Header "Editor" link that stays project-aware:
 * when the user is on a project page (/projects/[id] or a sub-page),
 * it opens the editor for that project instead of the bare editor.
 */
export default function EditorMenuLink() {
  const pathname = usePathname();
  const match = pathname?.match(/^\/projects\/([^/]+)/);
  const projectId = match?.[1];
  const href = projectId ? `/editor/${projectId}` : '/editor';

  return (
    <Link
      href={href}
      className="text-sm font-medium hover:text-primary transition-colors"
    >
      Editor
    </Link>
  );
}
