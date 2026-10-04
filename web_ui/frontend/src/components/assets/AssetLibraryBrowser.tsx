'use client';

/**
 * Asset library browser: folder tree sidebar + Explorer-style grid,
 * search, type filter, upload, category management, multi-select bulk bar.
 */
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  Search,
  Folder,
  FolderPlus,
  Upload,
  HardDrive,
  Trash2,
  FolderInput,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import AssetCard from './AssetCard';
import AssetDetail from './AssetDetail';
import UploadZone from './UploadZone';
import AssetFolderTree from './AssetFolderTree';
import {
  useAssetLibraries,
  useUpdateAssetLibraries,
  useAssetTree,
  useAssets,
  useAssetSearch,
  useDeleteAsset,
  useCreateAssetCategory,
  useMoveAsset,
  useDeleteAssetCategory,
  useMoveAssetCategory,
  useRenameAssetCategory,
} from '@/hooks/useAssets';
import { breadcrumbParts, flattenTree } from './assetUtils';
import { extractError } from './AssetDetailView';
import type { AssetEntry, AssetTreeNode } from '@/types';
import { cn } from '@/lib/utils';

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: 'all', label: 'All types' },
  { value: 'image', label: 'Images' },
  { value: 'video', label: 'Videos' },
  { value: 'audio', label: 'Audio' },
  { value: 'music', label: 'Music' },
];

export default function AssetLibraryBrowser() {
  // --- library selection ---------------------------------------------------
  const { data: libraries } = useAssetLibraries();
  const [library, setLibrary] = useState<string | undefined>(undefined);
  const [libraryReady, setLibraryReady] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('assets_library');
    if (saved && libraries?.some((l) => l.slug === saved)) setLibrary(saved);
    setLibraryReady(true);
  }, [libraries]);

  // --- tree + current category --------------------------------------------
  const { data: tree = [] } = useAssetTree(library);
  const [currentCat, setCurrentCat] = useState('i');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    const saved = libraryReady && localStorage.getItem('assets_last_cat');
    if (saved && /^[ivam]($|\/)/.test(saved)) setCurrentCat(saved);
  }, [libraryReady]);

  useEffect(() => {
    if (libraryReady) localStorage.setItem('assets_last_cat', currentCat);
  }, [currentCat, libraryReady]);

  useEffect(() => {
    if (library) localStorage.setItem('assets_library', library);
  }, [library]);

  // --- data -----------------------------------------------------------------
  const listing = useAssets(search.trim() ? null : currentCat, library);
  const searchResults = useAssetSearch(search.trim(), library);
  const loading = (search.trim() ? searchResults.isLoading : listing.isLoading) ?? false;
  const entries = useMemo(() => {
    const source = search.trim() ? searchResults.data ?? [] : listing.data ?? [];
    return source.filter((e) => typeFilter === 'all' || e.type === typeFilter);
  }, [search, searchResults.data, listing.data, typeFilter]);

  const currentNode = useMemo(
    () => findNode(tree, search.trim() ? '' : currentCat),
    [tree, currentCat, search]
  );
  const subfolders = search.trim() ? [] : currentNode?.children ?? [];

  // --- selection --------------------------------------------------------------
  const [selected, setSelected] = useState<Set<string>>(new Set());
  useEffect(() => {
    setSelected(new Set());
  }, [currentCat, search]);
  const toggleSelect = (ref: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(ref)) next.delete(ref);
      else next.add(ref);
      return next;
    });
  };

  // --- mutations ----------------------------------------------------------------
  const deleteMutation = useDeleteAsset();
  const moveMutation = useMoveAsset();
  const createCategoryMutation = useCreateAssetCategory();
  const updateLibrariesMutation = useUpdateAssetLibraries();
  const deleteCategoryMutation = useDeleteAssetCategory();
  const moveCategoryMutation = useMoveAssetCategory();
  const renameCategoryMutation = useRenameAssetCategory();

  const [detailEntry, setDetailEntry] = useState<AssetEntry | null>(null);

  const handleBulkDelete = async () => {
    const refs = Array.from(selected);
    let deleted = 0;
    for (const ref of refs) {
      try {
        await deleteMutation.mutateAsync({ ref });
        deleted++;
      } catch (e) {
        toast.error(`${ref}: ${extractError(e)}`);
      }
    }
    if (deleted > 0) toast.success(`Deleted ${deleted} asset${deleted > 1 ? 's' : ''}`);
    setSelected(new Set());
  };

  const handleBulkMove = (toCat: string) => {
    const refs = Array.from(selected);
    Promise.allSettled(refs.map((ref) => moveMutation.mutateAsync({ ref, toCat }))).then(
      (results) => {
        const ok = results.filter((r) => r.status === 'fulfilled').length;
        if (ok > 0) toast.success(`Moved ${ok} asset${ok > 1 ? 's' : ''} to ${toCat}`);
        results.forEach((r, i) => {
          if (r.status === 'rejected') toast.error(`${refs[i]}: ${extractError(r.reason)}`);
        });
        setSelected(new Set());
      }
    );
  };

  const handleDropAsset = (ref: string, toCat: string) => {
    moveMutation.mutate(
      { ref, toCat },
      {
        onSuccess: () => toast.success(`Moved to ${toCat}`),
        onError: (e) => toast.error(`Move failed: ${extractError(e)}`),
      }
    );
  };

  // --- new category dialog ---------------------------------------------------
  const [showNewCat, setShowNewCat] = useState(false);
  const [newCatName, setNewCatName] = useState('');
  const [newCatParent, setNewCatParent] = useState(currentCat);

  const openNewCatDialog = (parent: string) => {
    setNewCatParent(parent);
    setNewCatName('');
    setShowNewCat(true);
  };

  const handleCreateCategory = () => {
    const name = newCatName.trim();
    if (!name) return;
    createCategoryMutation.mutate(
      { cat: newCatParent, name, library },
      {
        onSuccess: (res) => {
          toast.success(`Created category ${res.cat}`);
          setShowNewCat(false);
          setNewCatName('');
          if (newCatParent === currentCat) setCurrentCat(res.cat);
        },
        onError: (e) => toast.error(`Create failed: ${extractError(e)}`),
      }
    );
  };

  // --- manage folders dialog ---------------------------------------------------
  const [showFolders, setShowFolders] = useState(false);
  const [folderPaths, setFolderPaths] = useState('');

  // --- category rename / move / delete -----------------------------------------
  const [catAction, setCatAction] = useState<{ node: AssetTreeNode; kind: 'rename' | 'move' | 'delete' } | null>(null);
  const [catName, setCatName] = useState('');
  const [catMoveTarget, setCatMoveTarget] = useState('');

  /** If the current category was inside the moved/renamed path, follow it. */
  const remapCurrentCat = (oldPath: string, newPath: string) => {
    setCurrentCat((prev) => {
      if (prev === oldPath) return newPath;
      if (prev.startsWith(oldPath + '/')) return newPath + prev.slice(oldPath.length);
      return prev;
    });
  };

  const handleRenameCategory = () => {
    if (!catAction || catAction.kind !== 'rename' || !catName.trim()) return;
    renameCategoryMutation.mutate(
      { cat: catAction.node.path, name: catName.trim(), library },
      {
        onSuccess: (res) => {
          toast.success(`Category renamed to ${res.new_cat}`);
          remapCurrentCat(res.cat, res.new_cat);
          setCatAction(null);
        },
        onError: (e) => toast.error(`Rename failed: ${extractError(e)}`),
      }
    );
  };

  const handleMoveCategory = () => {
    if (!catAction || catAction.kind !== 'move' || !catMoveTarget) return;
    moveCategoryMutation.mutate(
      { cat: catAction.node.path, toParent: catMoveTarget, library },
      {
        onSuccess: (res) => {
          toast.success(`Category moved to ${res.new_cat}`);
          remapCurrentCat(res.cat, res.new_cat);
          setCatAction(null);
        },
        onError: (e) => toast.error(`Move failed: ${extractError(e)}`),
      }
    );
  };

  const handleDeleteCategory = () => {
    if (!catAction || catAction.kind !== 'delete') return;
    const stats = categoryStats(catAction.node);
    deleteCategoryMutation.mutate(
      { cat: catAction.node.path, force: stats.assets > 0 || stats.subcategories > 0, library },
      {
        onSuccess: () => {
          toast.success(`Deleted category ${catAction.node.path}`);
          setCurrentCat((prev) =>
            prev === catAction.node.path || prev.startsWith(catAction.node.path + '/')
              ? catAction.node.letter
              : prev
          );
          setCatAction(null);
        },
        onError: (e) => toast.error(`Delete failed: ${extractError(e)}`),
      }
    );
  };

  const moveTargetOptions = catAction
    ? flattenTree(tree ?? []).filter((opt) => {
        if (opt.value !== catAction.node.letter && !opt.value.startsWith(catAction.node.letter + '/')) return false;
        if (opt.value === catAction.node.path) return false;
        if (opt.value.startsWith(catAction.node.path + '/')) return false;
        const parent = catAction.node.path.split('/').slice(0, -1).join('/');
        return opt.value !== parent;
      })
    : [];

  const openFoldersDialog = () => {
    setFolderPaths((libraries ?? []).map((l) => l.path).join(';'));
    setShowFolders(true);
  };

  const handleSaveFolders = () => {
    const paths = folderPaths.split(';').map((p) => p.trim()).filter(Boolean);
    updateLibrariesMutation.mutate(paths, {
      onSuccess: (libs) => {
        toast.success(`Saved ${libs.length} asset folder${libs.length > 1 ? 's' : ''}`);
        setShowFolders(false);
        if (libs.length && !libs.some((l) => l.slug === library)) setLibrary(libs[0].slug);
      },
      onError: (e) => toast.error(`Save failed: ${extractError(e)}`),
    });
  };

  // --- rendering -----------------------------------------------------------------
  const crumbs = breadcrumbParts(currentCat);

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search all assets…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
          {search && (
            <button
              className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
              onClick={() => setSearch('')}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[130px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TYPE_FILTERS.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {libraries && libraries.length > 1 && (
          <Select value={library ?? libraries[0].slug} onValueChange={setLibrary}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {libraries.map((l) => (
                <SelectItem key={l.slug} value={l.slug}>
                  {l.is_default ? `${l.name} (default)` : l.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowUpload((s) => !s)}
          className={cn(showUpload && 'bg-muted')}
        >
          <Upload className="w-4 h-4 mr-1.5" />
          Upload
        </Button>
        <Button variant="outline" size="sm" onClick={() => openNewCatDialog(currentCat)}>
          <FolderPlus className="w-4 h-4 mr-1.5" />
          New Category
        </Button>
        <Button variant="outline" size="sm" onClick={openFoldersDialog}>
          <HardDrive className="w-4 h-4 mr-1.5" />
          Folders
        </Button>
      </div>

      {/* Upload zone */}
      {showUpload && (
        <UploadZone cat={currentCat} library={library} onUploaded={() => setShowUpload(false)} />
      )}

      {/* Breadcrumb */}
      <div className="flex items-center gap-1 text-sm text-muted-foreground flex-wrap">
        {search.trim() ? (
          <span className="text-foreground">
            Search results for “{search}”{entries.length > 0 && ` (${entries.length})`}
          </span>
        ) : (
          <>
            {crumbs.map((label, i) => {
              const path = currentCat.split('/').slice(0, i + 1).join('/');
              const isLast = i === crumbs.length - 1;
              return (
                <span key={path} className="flex items-center gap-1">
                  {i > 0 && <span>/</span>}
                  <button
                    className={cn('hover:text-primary', isLast && 'text-foreground font-medium')}
                    onClick={() => setCurrentCat(path)}
                  >
                    {label}
                  </button>
                </span>
              );
            })}
            {currentNode && currentNode.count > 0 && (
              <span className="text-xs">· {currentNode.count} asset{currentNode.count > 1 ? 's' : ''}</span>
            )}
          </>
        )}
      </div>

      {/* Main area: tree + grid */}
      <div className="flex gap-4">
        {!search.trim() && (
          <div className="w-52 shrink-0 hidden md:block">
            <AssetFolderTree
              nodes={tree}
              selectedPath={currentCat}
              onSelect={setCurrentCat}
              onDropAsset={handleDropAsset}
              onAddSub={(node) => openNewCatDialog(node.path)}
              onRename={(node) => {
                setCatName(node.name);
                setCatAction({ node, kind: 'rename' });
              }}
              onMove={(node) => {
                setCatMoveTarget('');
                setCatAction({ node, kind: 'move' });
              }}
              onDelete={(node) => setCatAction({ node, kind: 'delete' })}
            />
          </div>
        )}

        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : entries.length === 0 && subfolders.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <Folder className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">
                {search.trim() ? 'No assets match your search.' : 'This category is empty.'}
              </p>
              {!search.trim() && (
                <p className="text-xs mt-1">Upload files or create a subcategory.</p>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {subfolders.map((node) => (
                <button
                  key={node.path}
                  className="aspect-square border rounded-lg bg-card flex flex-col items-center justify-center gap-2 text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors"
                  onClick={() => setCurrentCat(node.path)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const ref = e.dataTransfer.getData('text/plain');
                    if (ref) handleDropAsset(ref, node.path);
                  }}
                >
                  <Folder className="w-9 h-9" />
                  <span className="text-xs px-2 truncate w-full text-center">{node.name}</span>
                  {node.count > 0 && <span className="text-[10px]">{node.count} items</span>}
                </button>
              ))}
              {entries.map((entry) => (
                <AssetCard
                  key={entry.ref}
                  entry={entry}
                  selected={selected.has(entry.ref)}
                  selecting={selected.size > 0}
                  onToggleSelect={toggleSelect}
                  onOpen={setDetailEntry}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-background border shadow-lg rounded-full px-5 py-2.5 flex items-center gap-3">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <Select onValueChange={handleBulkMove} value="">
            <SelectTrigger className="w-[150px] h-8 text-xs">
              <SelectValue placeholder="Move to…" />
            </SelectTrigger>
            <SelectContent className="max-h-64">
              {flattenTree(tree ?? [])
                .filter((opt) => opt.value !== currentCat)
                .map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          <Button variant="destructive" size="sm" onClick={handleBulkDelete}>
            <Trash2 className="w-4 h-4 mr-1.5" />
            Delete
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Detail dialog */}
      <AssetDetail
        entry={detailEntry}
        library={library}
        onClose={() => setDetailEntry(null)}
        onDeleted={() => setDetailEntry(null)}
      />

      {/* New category dialog */}
      <Dialog open={showNewCat} onOpenChange={setShowNewCat}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>New category</DialogTitle>
            <DialogDescription>
              Created inside {breadcrumbParts(newCatParent).join(' / ')}
            </DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            placeholder="Category name"
            value={newCatName}
            onChange={(e) => setNewCatName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateCategory()}
          />
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowNewCat(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!newCatName.trim() || createCategoryMutation.isPending}
              onClick={handleCreateCategory}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manage folders dialog */}
      <Dialog open={showFolders} onOpenChange={setShowFolders}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Asset folders</DialogTitle>
            <DialogDescription>
              One folder per library, separated by semicolons. The first folder is the default.
            </DialogDescription>
          </DialogHeader>
          <textarea
            className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={folderPaths}
            onChange={(e) => setFolderPaths(e.target.value)}
            placeholder="E:/output/Assets;D:/MyStockPhotos"
          />
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowFolders(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={updateLibrariesMutation.isPending}
              onClick={handleSaveFolders}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Rename category dialog */}
      <Dialog open={catAction?.kind === 'rename'} onOpenChange={(o) => !o && setCatAction(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Rename category</DialogTitle>
            <DialogDescription className="truncate">{catAction?.node.path}</DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            value={catName}
            onChange={(e) => setCatName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRenameCategory()}
          />
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCatAction(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!catName.trim() || renameCategoryMutation.isPending}
              onClick={handleRenameCategory}
            >
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Move category dialog */}
      <Dialog open={catAction?.kind === 'move'} onOpenChange={(o) => !o && setCatAction(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Move category</DialogTitle>
            <DialogDescription className="truncate">
              Choose a new parent for {catAction?.node.name}
            </DialogDescription>
          </DialogHeader>
          <Select value={catMoveTarget} onValueChange={setCatMoveTarget}>
            <SelectTrigger>
              <SelectValue placeholder="New parent category…" />
            </SelectTrigger>
            <SelectContent className="max-h-64">
              {moveTargetOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCatAction(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!catMoveTarget || moveCategoryMutation.isPending}
              onClick={handleMoveCategory}
            >
              Move
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete category dialog */}
      <Dialog open={catAction?.kind === 'delete'} onOpenChange={(o) => !o && setCatAction(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete category</DialogTitle>
            <DialogDescription>
              Permanently delete <span className="font-medium">{catAction?.node.path}</span>
              {catAction && (
                <>
                  {' '}and everything in it — {categoryStats(catAction.node).assets} asset(s) across{' '}
                  {categoryStats(catAction.node).subcategories} subcategory(ies). This cannot be
                  undone.
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCatAction(null)}>
              Cancel
            </Button>
            <Button variant="destructive" size="sm" disabled={deleteCategoryMutation.isPending} onClick={handleDeleteCategory}>
              {deleteCategoryMutation.isPending ? 'Deleting…' : 'Delete permanently'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function findNode(nodes: AssetTreeNode[], path: string): AssetTreeNode | null {
  for (const node of nodes) {
    if (node.path === path) return node;
    const found = findNode(node.children, path);
    if (found) return found;
  }
  return null;
}

/** Recursive totals for a tree node (used for the delete confirmation). */
function categoryStats(node: AssetTreeNode): { assets: number; subcategories: number } {
  let assets = node.count;
  let subcategories = 0;
  const walk = (n: AssetTreeNode) => {
    for (const child of n.children) {
      subcategories += 1;
      assets += child.count;
      walk(child);
    }
  };
  walk(node);
  return { assets, subcategories };
}
