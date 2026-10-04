'use client';

/**
 * Compact asset tile for the library grid (thumbnail, type badge,
 * multi-select checkbox, hover actions).
 */
import { Maximize2, Trash2 } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import type { AssetEntry } from '@/types';
import { TYPE_META } from './assetUtils';

interface AssetCardProps {
  entry: AssetEntry;
  selected?: boolean;
  selecting?: boolean;
  onToggleSelect?: (ref: string) => void;
  onOpen?: (entry: AssetEntry) => void;
  onDelete?: (entry: AssetEntry) => void;
}

export default function AssetCard({
  entry,
  selected,
  selecting,
  onToggleSelect,
  onOpen,
  onDelete,
}: AssetCardProps) {
  const meta = TYPE_META[entry.letter] ?? TYPE_META.i;
  const TypeIcon = meta.icon;
  const isImage = entry.letter === 'i';
  const thumb = isImage ? entry.url : entry.thumb_url;

  return (
    <div
      className={cn(
        'relative group border rounded-lg overflow-hidden bg-card hover:border-primary/50 transition-colors cursor-pointer',
        selected && 'border-primary ring-2 ring-primary/30'
      )}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', entry.ref);
        e.dataTransfer.effectAllowed = 'move';
      }}
      onClick={() => {
        if (selecting && onToggleSelect) onToggleSelect(entry.ref);
        else onOpen?.(entry);
      }}
    >
      {/* Media area */}
      <div className="aspect-square bg-muted flex items-center justify-center overflow-hidden">
        {thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumb}
            alt={entry.title}
            loading="lazy"
            className="w-full h-full object-cover"
          />
        ) : (
          <TypeIcon className="w-10 h-10 text-muted-foreground/60" />
        )}

        {/* Type badge */}
        <span
          className={cn(
            'absolute bottom-1 left-1 text-[9px] px-1 py-0.5 rounded text-white font-semibold',
            meta.badge
          )}
        >
          {meta.label}
        </span>

        {/* Multi-select checkbox */}
        {selecting && onToggleSelect && (
          <div className="absolute top-1.5 left-1.5" onClick={(e) => e.stopPropagation()}>
            <Checkbox checked={!!selected} onCheckedChange={() => onToggleSelect(entry.ref)} />
          </div>
        )}

        {/* Hover actions */}
        <div
          className="absolute top-1.5 right-1.5 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          {onOpen && (
            <button
              className="p-1 rounded bg-black/60 text-white hover:bg-black/80"
              title="Open details"
              onClick={() => onOpen(entry)}
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              className="p-1 rounded bg-black/60 text-white hover:bg-red-600"
              title="Delete asset"
              onClick={() => onDelete(entry)}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Title */}
      <div className="p-2">
        <p className="text-xs font-medium truncate" title={`${entry.title} — ${entry.filename}`}>
          {entry.title}
        </p>
      </div>
    </div>
  );
}
