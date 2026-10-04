'use client';

/**
 * "Save to Asset Library" dialog: copies a project media file (p/... ref) into
 * a chosen library category, with title override. Duplicates are skipped by the
 * backend (content hash) and surfaced as an info toast.
 */
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { useAssetTree, useImportAsset } from '@/hooks/useAssets';
import { flattenTree } from './assetUtils';
import { extractError } from './AssetDetailView';

interface SaveToLibraryDialogProps {
  projectId: string;
  mediaRef: string | null; // p/{pid}/{dir}/{filename}
  kind: 'image' | 'video';
  defaultTitle: string;
  open: boolean;
  onClose: () => void;
}

export default function SaveToLibraryDialog({
  projectId,
  mediaRef,
  kind,
  defaultTitle,
  open,
  onClose,
}: SaveToLibraryDialogProps) {
  const letter = kind === 'image' ? 'i' : 'v';
  const { data: tree = [] } = useAssetTree();
  const importMutation = useImportAsset();
  const [cat, setCat] = useState(letter);
  const [title, setTitle] = useState(defaultTitle);

  useEffect(() => {
    if (open) {
      setCat(letter);
      setTitle(defaultTitle);
    }
  }, [open, letter, defaultTitle]);

  const options = flattenTree(tree ?? []).filter(
    (opt) => opt.value === letter || opt.value.startsWith(letter + '/')
  );

  const handleSave = () => {
    if (!mediaRef || !cat) return;
    importMutation.mutate(
      { ref: mediaRef, cat, title: title.trim() || undefined },
      {
        onSuccess: (result) => {
          if (result.saved.length > 0) {
            toast.success(`Saved “${result.saved[0].title}” to ${result.saved[0].category}`);
          } else if (result.skipped.length > 0) {
            toast.info(result.skipped[0].reason);
          }
          onClose();
        },
        onError: (e) => toast.error(`Save failed: ${extractError(e)}`),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Save to Asset Library</DialogTitle>
          <DialogDescription>
            Copies this {kind} from the project into your reusable library.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Category</Label>
            <Select value={cat} onValueChange={setCat}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-64">
                {options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="save-lib-title" className="text-xs text-muted-foreground">Title</Label>
            <Input
              id="save-lib-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" disabled={importMutation.isPending || !mediaRef} onClick={handleSave}>
            {importMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                Saving…
              </>
            ) : (
              'Save'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
