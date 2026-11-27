'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { AssetEntry } from '@/types';
import { flattenTree } from './assetUtils';
import { Search, Image as ImageIcon } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

interface AssetPickerDialogProps {
  open: boolean;
  onClose: () => void;
  /** Called with the picked entry; the dialog closes itself beforehand */
  onSelect: (entry: AssetEntry) => void;
  title?: string;
}

/**
 * Generic Asset Library image picker: category tree + text search on top,
 * thumbnail grid below. Used to attach existing library images (e.g. as prop
 * reference sheets) without uploading or generating anew.
 */
export default function AssetPickerDialog({
  open,
  onClose,
  onSelect,
  title = 'Choose from Asset Library'
}: AssetPickerDialogProps) {
  const [categories, setCategories] = useState<{ value: string; label: string }[]>([]);
  const [cat, setCat] = useState('i');
  const [entries, setEntries] = useState<AssetEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  // Image categories only (value "i" or "i/...")
  useEffect(() => {
    if (!open) return;
    api
      .getAssetTree()
      .then((tree) => {
        const opts = flattenTree(tree as never).filter(
          (o) => o.value === 'i' || o.value.startsWith('i/')
        );
        setCategories(opts.length > 0 ? opts : [{ value: 'i', label: 'Images' }]);
      })
      .catch(() => setCategories([{ value: 'i', label: 'Images' }]));
  }, [open]);

  const loadEntries = useMemo(
    () =>
      async (category: string, query: string) => {
        setLoading(true);
        try {
          if (query.trim()) {
            setEntries(await api.searchAssets(query.trim(), undefined, 'image'));
          } else {
            setEntries(await api.listAssets(category));
          }
        } catch (error) {
          console.error('Failed to fetch library assets:', error);
          setEntries([]);
        } finally {
          setLoading(false);
        }
      },
    []
  );

  useEffect(() => {
    if (!open) return;
    loadEntries(cat, search);
  }, [open, cat, search, loadEntries]);

  const mediaUrl = (entry: AssetEntry) => `${API_BASE}${entry.thumb_url || entry.url}`;

  const handlePick = (entry: AssetEntry) => {
    onSelect(entry);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-3xl h-[70vh] flex flex-col p-0 overflow-hidden bg-card border-border">
        <DialogHeader className="px-4 pt-4 pb-3 border-b border-border/60">
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        <div className="flex gap-2 px-4 py-3 border-b border-border/60">
          <select
            className="h-9 rounded-md border border-input bg-background px-2 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-primary max-w-[220px]"
            value={cat}
            onChange={(e) => { setCat(e.target.value); setSearch(''); }}
            disabled={!!search.trim()}
          >
            {categories.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search the whole library…"
              className="h-9 pl-8 text-xs"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 bg-muted/10">
          {loading ? (
            <div className="h-32 flex items-center justify-center text-sm text-muted-foreground">
              Loading library…
            </div>
          ) : entries.length === 0 ? (
            <div className="h-32 flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
              <ImageIcon className="w-8 h-8 opacity-40" />
              {search.trim() ? 'No images match your search.' : 'No images in this category.'}
            </div>
          ) : (
            <div className="grid grid-cols-3 md:grid-cols-4 gap-3">
              {entries.map((entry) => (
                <button
                  key={entry.ref}
                  onClick={() => handlePick(entry)}
                  title={entry.title}
                  className="group relative rounded-lg overflow-hidden border border-border/50 bg-black/20 hover:border-primary/60 transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <img
                    src={mediaUrl(entry)}
                    alt={entry.title}
                    loading="lazy"
                    className="w-full aspect-square object-cover"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-black/60 px-2 py-1 text-[10px] text-white truncate text-left opacity-0 group-hover:opacity-100 transition-opacity">
                    {entry.title}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
