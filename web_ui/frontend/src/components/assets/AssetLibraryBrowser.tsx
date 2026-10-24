'use client';

/**
 * Asset library browser: folder tree sidebar + Explorer-style grid,
 * search, type filter, upload, category management, multi-select bulk bar.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Search,
  Folder,
  FolderPlus,
  Upload,
  HardDrive,
  Trash2,
  FolderInput,
  Sparkles,
  FilePlus,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
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
import GenerateAssetDialog from './GenerateAssetDialog';
import UploadZone from './UploadZone';
import AssetFolderTree from './AssetFolderTree';
import {
  useAssetLibraries,
  useUpdateAssetLibraries,
  useAssetTree,
  useAssets,
  useAssetSearch,
  useAssetGenerations,
  useCancelGeneration,
  useDeleteAsset,
  useCreateAssetCategory,
  useCreateAssetText,
  useMoveAsset,
  useDeleteAssetCategory,
  useMoveAssetCategory,
  useRenameAssetCategory,
} from '@/hooks/useAssets';
import { breadcrumbParts, flattenTree, humanizeCat, TYPE_META } from './assetUtils';
import { extractError } from './AssetDetailView';
import type { AssetEntry, AssetGenerationStatus, AssetTreeNode } from '@/types';
import { cn } from '@/lib/utils';

const TYPE_FILTERS: { value: string; label: string }[] = [
  { value: 'all', label: 'All types' },
  { value: 'image', label: 'Images' },
  { value: 'video', label: 'Videos' },
  { value: 'audio', label: 'Audio' },
  { value: 'music', label: 'Music' },
  { value: 'text', label: 'Text (Guides/Templates)' },
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
  const [showGenerate, setShowGenerate] = useState(false);
  const [showNewText, setShowNewText] = useState(false);

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

  // --- in-flight generations --------------------------------------------------
  // The generate dialog reports its start here and closes; the grid shows a
  // placeholder card per active generation in the browsed category until the
  // run settles (toast + list refresh). The generations query self-polls
  // (3s) while any run is queued/running; starting one invalidates it.
  const queryClient = useQueryClient();
  const knownGenIds = useRef<Set<string>>(new Set());
  const cancelGenMutation = useCancelGeneration();
  const { data: generations } = useAssetGenerations();

  const handleGenStarted = (gen: AssetGenerationStatus) => {
    knownGenIds.current.add(gen.id);
    queryClient.invalidateQueries({ queryKey: ['asset-generations'] });
  };

  useEffect(() => {
    if (!generations) return;
    for (const g of generations) {
      if (!knownGenIds.current.has(g.id) || g.status === 'queued' || g.status === 'running') continue;
      knownGenIds.current.delete(g.id);
      if (g.status === 'completed') {
        queryClient.invalidateQueries({ queryKey: ['assets'] });
        queryClient.invalidateQueries({ queryKey: ['asset-tree'] });
        queryClient.invalidateQueries({ queryKey: ['asset-search'] });
        toast.success(`Generated "${g.title}" — saved to ${humanizeCat(g.cat)}`);
      } else if (g.status === 'failed') {
        toast.error(`Generation failed: ${(g.error || 'unknown error').slice(0, 300)}`);
      } else {
        toast.info(`Generation cancelled: ${g.title ?? g.id}`);
      }
    }
  }, [generations, queryClient]);

  const activeGens = useMemo(
    () =>
      search.trim()
        ? []
        : (generations ?? []).filter(
            (g) =>
              (g.status === 'queued' || g.status === 'running') &&
              (g.cat === currentCat || (g.cat ?? '').startsWith(currentCat + '/'))
          ),
    [generations, currentCat, search]
  );

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
        <Button variant="outline" size="sm" onClick={() => setShowGenerate(true)}>
          <Sparkles className="w-4 h-4 mr-1.5 text-primary" />
          Generate
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowNewText(true)}>
          <FilePlus className="w-4 h-4 mr-1.5" />
          New Text
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
          ) : entries.length === 0 && subfolders.length === 0 && activeGens.length === 0 ? (
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
              {activeGens.map((g) => (
                <GeneratingAssetCard
                  key={g.id}
                  gen={g}
                  canceling={cancelGenMutation.isPending}
                  onCancel={() => cancelGenMutation.mutate(g.id)}
                />
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

      {/* Generate dialog */}
      <GenerateAssetDialog
        open={showGenerate}
        onOpenChange={setShowGenerate}
        defaultCat={currentCat}
        library={library}
        onStarted={handleGenStarted}
      />

      {/* New text (Guides/Templates) dialog */}
      <NewTextAssetDialog
        open={showNewText}
        onOpenChange={setShowNewText}
        defaultCat={currentCat}
        library={library}
      />

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

/** Create a new Guides/Templates text asset: category + title + content. */
function NewTextAssetDialog({
  open,
  onOpenChange,
  defaultCat,
  library,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultCat: string;
  library?: string;
}) {
  const { data: tree = [] } = useAssetTree(library);
  const createMutation = useCreateAssetText();
  const [cat, setCat] = useState('t');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');

  const isTextCat = (c: string) => c === 'g' || c === 't' || c.startsWith('g/') || c.startsWith('t/');
  const catOptions = useMemo(
    () => flattenTree(tree).filter((opt) => isTextCat(opt.value)),
    [tree]
  );

  // Reset whenever the dialog opens; preselect the browsed text category
  useEffect(() => {
    if (!open) return;
    setTitle('');
    setContent('');
    setCat(isTextCat(defaultCat) ? defaultCat : 't');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, defaultCat]);

  const submit = () => {
    createMutation.mutate(
      { cat, title: title.trim(), content, library },
      {
        onSuccess: (entry) => {
          toast.success(`Created "${entry.title}" in ${humanizeCat(entry.cat)}`);
          onOpenChange(false);
        },
        onError: (e) => toast.error(`Create failed: ${extractError(e)}`),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FilePlus className="w-4 h-4 text-primary" />
            New text asset
          </DialogTitle>
          <DialogDescription>
            Create a Guide or Template text file. Templates use {'{placeholder}'} fields the
            Generate dialog fills in.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Category</Label>
              <Select value={cat} onValueChange={setCat}>
                <SelectTrigger>
                  <SelectValue placeholder="Category…" />
                </SelectTrigger>
                <SelectContent className="max-h-56">
                  {catOptions.length === 0 && (
                    <div className="px-3 py-2 text-xs text-muted-foreground">No text categories yet</div>
                  )}
                  {catOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Title</Label>
              <Input
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Cinematic shot"
                onKeyDown={(e) => e.key === 'Enter' && title.trim() && submit()}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Content</Label>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              spellCheck={false}
              placeholder={'Write the text. {placeholders} like {subject}; {Style:Ghibli|Pixar} becomes a dropdown; {@Styles\\Style} inlines another template.'}
              className="min-h-[180px] font-mono text-xs leading-relaxed"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={!title.trim() || createMutation.isPending} onClick={submit}>
            {createMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                Creating…
              </>
            ) : (
              'Create'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const GEN_KIND_LETTER: Record<string, string> = { image: 'i', video: 'v', audio: 'a' };

/** In-grid placeholder for a running library generation: spinner, progress,
 * prompt snippet and an inline cancel — the UI stays usable while it runs. */
function GeneratingAssetCard({
  gen,
  onCancel,
  canceling,
}: {
  gen: AssetGenerationStatus;
  onCancel: () => void;
  canceling: boolean;
}) {
  const meta = TYPE_META[GEN_KIND_LETTER[gen.kind]] ?? TYPE_META.i;
  const Icon = meta.icon;
  return (
    <div className="relative border border-primary/40 rounded-lg overflow-hidden bg-card">
      <div className="relative aspect-square bg-muted flex flex-col items-center justify-center gap-2 p-3">
        <Icon className="w-8 h-8 text-muted-foreground/40" />
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        <div className="w-full space-y-1">
          <Progress value={gen.progress} />
          <p className="text-[10px] text-center text-muted-foreground">
            {gen.progress}% · {gen.status}
          </p>
        </div>
        <span
          className={cn(
            'absolute top-1.5 left-1.5 text-[9px] px-1 py-0.5 rounded text-white font-semibold',
            meta.badge
          )}
        >
          {meta.label}
        </span>
        <button
          className="absolute top-1.5 right-1.5 p-1 rounded bg-black/60 text-white hover:bg-red-600 disabled:opacity-50"
          title="Cancel generation"
          disabled={canceling}
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="p-2">
        <p className="text-xs font-medium truncate">{gen.title || 'Generating…'}</p>
        <p className="text-[10px] text-muted-foreground truncate" title={gen.prompt}>
          {gen.prompt}
        </p>
      </div>
    </div>
  );
}
