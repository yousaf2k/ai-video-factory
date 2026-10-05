'use client';

/**
 * Shared asset detail content: large preview, metadata, rename, move, delete.
 * Used inside the detail Dialog and by the standalone /asset/[...parts] page.
 */
import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import {
  ExternalLink,
  Trash2,
  Loader2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAssetEntry, useAssetText, useRenameAsset, useMoveAsset, useDeleteAsset, useAssetTree } from '@/hooks/useAssets';
import { formatBytes, flattenTree, TYPE_META } from './assetUtils';
import type { AssetEntry, ResolvedAssetRef } from '@/types';

interface AssetDetailViewProps {
  entry: AssetEntry | ResolvedAssetRef;
  library?: string;
  showOpenExternal?: boolean;
  onDeleted?: () => void;
}

export default function AssetDetailView(props: AssetDetailViewProps) {
  const { entry } = props;
  if ('kind' in entry && entry.kind === 'project') {
    return <ProjectRefDetail entry={entry} />;
  }
  return (
    <LibraryAssetDetail
      entry={entry as AssetEntry}
      library={props.library}
      showOpenExternal={props.showOpenExternal}
      onDeleted={props.onDeleted}
    />
  );
}

/** Read-only detail for another project's media (no rename/move/delete). */
function ProjectRefDetail({ entry }: { entry: ResolvedAssetRef }) {
  const { data: full } = useAssetEntry(entry.ref, true);
  const detail = (full ?? entry) as ResolvedAssetRef;
  const meta = TYPE_META_BY_TYPE[detail.type] ?? TYPE_META.i;
  const TypeIcon = meta.icon;
  const media = detail.media ?? {};
  const filename = detail.ref.split('/').slice(3).join('/');

  return (
    <div className="space-y-4">
      <div className="bg-muted/40 rounded-lg flex items-center justify-center p-3 min-h-[160px]">
        {detail.type === 'image' && detail.url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={detail.url} alt={detail.title} className="max-h-[45vh] w-auto max-w-full rounded-md object-contain" />
        )}
        {detail.type === 'video' && detail.url && (
          <video src={detail.url} controls className="max-h-[45vh] w-full rounded-md" />
        )}
        {(detail.type === 'audio' || detail.type === 'music') && detail.url && (
          <div className="w-full max-w-md flex flex-col items-center gap-3 py-6">
            <TypeIcon className="w-12 h-12 text-muted-foreground/60" />
            <audio src={detail.url} controls className="w-full" />
          </div>
        )}
      </div>
      {!detail.exists && (
        <p className="text-sm text-red-500">This media file no longer exists on disk.</p>
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <MetaItem label="File" value={filename} />
        <MetaItem label="Source" value={detail.source ? shortenProjectId(detail.source) : '—'} />
        <MetaItem label="Type" value={detail.type} />
        <MetaItem label="Size" value={formatBytes(detail.size_bytes ?? 0)} />
        {media.width != null && <MetaItem label="Dimensions" value={`${media.width} × ${media.height}`} />}
        {media.duration_sec != null && <MetaItem label="Duration" value={`${media.duration_sec}s`} />}
        {detail.modified_at && <MetaItem label="Modified" value={detail.modified_at.replace('T', ' ')} />}
        <MetaItem label="Ref" value={detail.ref} />
      </dl>
      <p className="text-xs text-muted-foreground border-t pt-3">
        This is a live reference to another project&apos;s media — it is not copied into the asset
        library and cannot be edited here.
      </p>
    </div>
  );
}

function shortenProjectId(pid: string): string {
  const m = pid.match(/(\d{4})(\d{2})(\d{2})/);
  return m ? `Project ${m[1]}-${m[2]}-${m[3]}` : pid;
}

const TYPE_META_BY_TYPE: Record<string, { label: string; badge: string; icon: typeof ExternalLink }> = {
  image: TYPE_META.i,
  video: TYPE_META.v,
  audio: TYPE_META.a,
  music: TYPE_META.m,
};

function LibraryAssetDetail({
  entry,
  library,
  showOpenExternal,
  onDeleted,
}: {
  entry: AssetEntry;
  library?: string;
  showOpenExternal?: boolean;
  onDeleted?: () => void;
}) {
  const { data: full } = useAssetEntry(entry.ref, true);
  const detail = (full ?? entry) as AssetEntry;

  const { data: tree } = useAssetTree(library);
  const renameMutation = useRenameAsset();
  const moveMutation = useMoveAsset();
  const deleteMutation = useDeleteAsset();

  const [title, setTitle] = useState(entry.title);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  useEffect(() => {
    setTitle(detail.title);
    setConfirmingDelete(false);
  }, [detail.ref, detail.title]);

  const meta = TYPE_META[detail.letter] ?? TYPE_META.i;
  const TypeIcon = meta.icon;
  const dirty = title.trim() !== detail.title && title.trim().length > 0;
  const media = detail.media ?? {};

  const handleRename = () => {
    if (!dirty) return;
    renameMutation.mutate(
      { ref: detail.ref, title: title.trim() },
      {
        onSuccess: () => toast.success('Asset renamed'),
        onError: (e) => toast.error(`Rename failed: ${extractError(e)}`),
      }
    );
  };

  const handleMove = (toCat: string) => {
    moveMutation.mutate(
      { ref: detail.ref, toCat },
      {
        onSuccess: () => toast.success(`Moved to ${toCat}`),
        onError: (e) => toast.error(`Move failed: ${extractError(e)}`),
      }
    );
  };

  const handleDelete = () => {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      setTimeout(() => setConfirmingDelete(false), 4000);
      return;
    }
    deleteMutation.mutate(
      { ref: detail.ref },
      {
        onSuccess: () => {
          toast.success('Asset deleted');
          onDeleted?.();
        },
        onError: (e) => toast.error(`Delete failed: ${extractError(e)}`),
      }
    );
  };

  return (
    <div className="space-y-4">
      {/* Preview */}
      <div className="bg-muted/40 rounded-lg flex items-center justify-center p-3 min-h-[160px]">
        {detail.letter === 'i' && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={detail.url}
            alt={detail.title}
            className="max-h-[45vh] w-auto max-w-full rounded-md object-contain"
          />
        )}
        {detail.letter === 'v' && (
          <video src={detail.url} controls className="max-h-[45vh] w-full rounded-md" />
        )}
        {(detail.letter === 'a' || detail.letter === 'm') && (
          <div className="w-full max-w-md flex flex-col items-center gap-3 py-6">
            <TypeIcon className="w-12 h-12 text-muted-foreground/60" />
            <audio src={detail.url} controls className="w-full" />
          </div>
        )}
        {detail.letter === 'g' && <TextPreview assetRef={detail.ref} />}
      </div>

      {/* Rename */}
      <div className="flex items-end gap-2">
        <div className="flex-1 space-y-1">
          <Label htmlFor="asset-title" className="text-xs text-muted-foreground">Title</Label>
          <Input
            id="asset-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRename()}
          />
        </div>
        <Button size="sm" disabled={!dirty || renameMutation.isPending} onClick={handleRename}>
          {renameMutation.isPending ? 'Saving…' : 'Rename'}
        </Button>
      </div>

      {/* Move */}
      <div className="flex items-end gap-2">
        <div className="flex-1 space-y-1">
          <Label className="text-xs text-muted-foreground">Move to category</Label>
          <Select onValueChange={handleMove} value="">
            <SelectTrigger>
              <SelectValue placeholder={`Current: ${detail.category}`} />
            </SelectTrigger>
            <SelectContent className="max-h-64">
              {flattenTree(tree ?? [])
                .filter((opt) => opt.value !== detail.cat && opt.value.startsWith(detail.letter + '/'))
                .map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Metadata */}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <MetaItem label="File" value={detail.filename} />
        <MetaItem label="Asset ID" value={detail.id} />
        <MetaItem label="Type" value={`${detail.type} (${detail.letter})`} />
        <MetaItem label="Size" value={formatBytes(detail.size_bytes)} />
        {media.width != null && (
          <MetaItem label="Dimensions" value={`${media.width} × ${media.height}`} />
        )}
        {media.duration_sec != null && (
          <MetaItem label="Duration" value={`${media.duration_sec}s`} />
        )}
        {detail.modified_at && <MetaItem label="Modified" value={detail.modified_at.replace('T', ' ')} />}
        <MetaItem label="Ref" value={detail.ref} />
      </dl>

      {/* Actions */}
      <div className="flex items-center gap-2 border-t pt-3">
        {showOpenExternal && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open(`/asset/${detail.ref}`, '_blank')}
          >
            <ExternalLink className="w-4 h-4 mr-1.5" />
            Open in new window
          </Button>
        )}
        <div className="ml-auto">
          <Button
            variant="destructive"
            size="sm"
            disabled={deleteMutation.isPending}
            onClick={handleDelete}
          >
            {deleteMutation.isPending ? (
              'Deleting…'
            ) : confirmingDelete ? (
              <>
                <Trash2 className="w-4 h-4 mr-1.5" />
                Confirm delete?
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4 mr-1.5" />
                Delete
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

/** Markdown/text preview for Guides assets (rendered from the file content). */
function TextPreview({ assetRef }: { assetRef: string }) {
  const { data, isLoading } = useAssetText(assetRef);
  if (isLoading) {
    return <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />;
  }
  return (
    <div className="w-full max-h-[45vh] overflow-auto rounded-md border bg-background p-4 text-sm [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:text-base [&_h2]:font-semibold [&_h3]:font-semibold [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_code]:bg-muted [&_code]:px-1 [&_code]:rounded [&_pre]:bg-muted [&_pre]:p-3 [&_pre]:rounded [&_a]:text-primary [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{data?.content ?? ''}</ReactMarkdown>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="truncate font-medium" title={value}>{value}</dd>
    </div>
  );
}

export function extractError(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  if (e instanceof Error) return e.message;
  return String(e);
}
