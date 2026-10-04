/**
 * Shared helpers for asset library components
 */
import { Image as ImageIcon, Film, Volume2, Music, type LucideIcon } from 'lucide-react';

export const LETTER_FOLDER: Record<string, string> = {
  i: 'Images',
  v: 'Videos',
  a: 'Audio',
  m: 'Music',
};

export const TYPE_META: Record<string, { label: string; badge: string; icon: LucideIcon }> = {
  i: { label: 'IMG', badge: 'bg-sky-500', icon: ImageIcon },
  v: { label: 'VID', badge: 'bg-violet-500', icon: Film },
  a: { label: 'SFX', badge: 'bg-amber-500', icon: Volume2 },
  m: { label: 'MUS', badge: 'bg-emerald-500', icon: Music },
};

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/** "i/Characters/City" -> ["Images", "Characters", "City"] */
export function breadcrumbParts(cat: string): string[] {
  const parts = cat.split('/').filter(Boolean);
  if (parts.length === 0) return [];
  return [LETTER_FOLDER[parts[0]] ?? parts[0], ...parts.slice(1)];
}

/** Flatten a category tree into Select options {value, label} */
export function flattenTree(
  nodes: { name: string; path: string; children: { path: string; name: string }[] }[],
  prefix = ''
): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = [];
  for (const node of nodes) {
    out.push({ value: node.path, label: prefix ? `${prefix} / ${node.name}` : node.name });
    if ('children' in node && node.children?.length) {
      out.push(...flattenTree(node.children as never, out[out.length - 1].label));
    }
  }
  return out;
}
