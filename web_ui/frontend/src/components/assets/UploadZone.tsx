'use client';

/**
 * Drag-and-drop / click upload zone for assets into one category.
 */
import { useState, useRef } from 'react';
import { toast } from 'sonner';
import { Upload, Loader2 } from 'lucide-react';
import { useUploadAssets } from '@/hooks/useAssets';
import { extractError } from './AssetDetailView';

interface UploadZoneProps {
  cat: string;
  library?: string;
  onUploaded?: () => void;
}

export default function UploadZone({ cat, library, onUploaded }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const uploadMutation = useUploadAssets();

  const uploadFiles = (files: FileList | File[]) => {
    const list = Array.from(files);
    if (list.length === 0) return;
    uploadMutation.mutate(
      { cat, files: list, library },
      {
        onSuccess: (result) => {
          if (result.saved.length > 0) {
            toast.success(`Added ${result.saved.length} asset${result.saved.length > 1 ? 's' : ''} to ${cat}`);
          }
          result.rerouted.forEach((r) =>
            toast.info(`${r.filename} is a different type — saved under ${r.to}`)
          );
          result.skipped.forEach((s) => toast.error(`${s.filename}: ${s.reason}`));
          onUploaded?.();
        },
        onError: (e) => toast.error(`Upload failed: ${extractError(e)}`),
      }
    );
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
        dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        uploadFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*,video/*,audio/*"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) uploadFiles(e.target.files);
          e.target.value = '';
        }}
      />
      {uploadMutation.isPending ? (
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Uploading…
        </div>
      ) : (
        <>
          <Upload className="w-6 h-6 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Drag files here or click to upload into <span className="font-medium">{cat}</span>
          </p>
          <p className="text-xs text-muted-foreground/70 mt-1">
            Images, videos and audio — files are routed to the matching type folder automatically
          </p>
        </>
      )}
    </div>
  );
}
