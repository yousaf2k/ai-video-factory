'use client';

/**
 * Asset detail dialog (Radix) wrapping the shared AssetDetailView.
 */
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import AssetDetailView from './AssetDetailView';
import type { AssetEntry } from '@/types';

interface AssetDetailProps {
  entry: AssetEntry | null;
  library?: string;
  onClose: () => void;
  onDeleted?: () => void;
}

export default function AssetDetail({ entry, library, onClose, onDeleted }: AssetDetailProps) {
  return (
    <Dialog open={!!entry} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="truncate pr-6">{entry?.title}</DialogTitle>
          <DialogDescription className="truncate">{entry?.category}</DialogDescription>
        </DialogHeader>
        {entry && (
          <AssetDetailView
            entry={entry}
            library={library}
            showOpenExternal
            onDeleted={onDeleted}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
