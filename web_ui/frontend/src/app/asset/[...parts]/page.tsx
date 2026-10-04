'use client';

/**
 * Standalone asset detail page — the target of "Open in new window".
 * URL: /asset/i/9f3ab21c (the ref, same shape as the API scheme).
 */
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import AssetDetailView from '@/components/assets/AssetDetailView';
import { useAssetEntry } from '@/hooks/useAssets';

export default function AssetDetailPage() {
  const params = useParams();
  const raw = params?.parts;
  const ref = Array.isArray(raw) ? raw.join('/') : typeof raw === 'string' ? raw : '';

  const { data: entry, isLoading, error } = useAssetEntry(ref || null, true);

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/assets">
              <ArrowLeft className="w-4 h-4 mr-1" />
              Assets
            </Link>
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : error || !entry ? (
          <p className="text-center text-muted-foreground py-20">
            Asset not found: <code className="text-xs">{ref}</code>
          </p>
        ) : (
          <div className="border rounded-lg bg-card p-4">
            <h1 className="text-lg font-semibold mb-3 truncate">{entry.title}</h1>
            <AssetDetailView entry={entry} />
          </div>
        )}
      </div>
    </div>
  );
}
