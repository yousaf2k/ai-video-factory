'use client';

/**
 * Global asset library browser page
 */
import AssetLibraryBrowser from '@/components/assets/AssetLibraryBrowser';

export default function AssetsPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-4">
        <h1 className="text-2xl font-bold">Assets</h1>
        <p className="text-sm text-muted-foreground">
          Browse, upload and organize reusable images, videos, audio and music across projects.
          Files are stored as <code className="text-xs">{'{id}-{Title}.{ext}'}</code> inside their
          category folders.
        </p>
      </div>
      <AssetLibraryBrowser />
    </div>
  );
}
