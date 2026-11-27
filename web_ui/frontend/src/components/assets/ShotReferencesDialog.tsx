'use client';

/**
 * Per-shot references dialog: three tabs
 *  - Project Assets: the project's asset pool, click a tile to attach/detach
 *  - Asset Library: browse the library, multi-select to add (to pool / to shot)
 *  - Project Library: browse all projects' media and attach it in place
 */
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  Film,
  Music,
  Volume2,
  Image as ImageIcon,
  Check,
  ExternalLink,
  Trash2,
  Folder,
  Loader2,
  X,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import AssetFolderTree from './AssetFolderTree';
import { TYPE_META } from './assetUtils';
import { extractError } from './AssetDetailView';
import {
  useAssetTree,
  useAssets,
  useProjectAssets,
  useAddProjectAssets,
  useRemoveProjectAsset,
  useShotReferences,
  useAddShotReferences,
  useRemoveShotReference,
  useReferenceAsSource,
  useProjectMedia,
  useImportAsset,
} from '@/hooks/useAssets';
import { useProjects } from '@/hooks/useProjects';
import { usePersistedState } from '@/hooks/usePersistedState';
import type { AssetEntry, AssetTreeNode, Character, Prop, ResolvedAssetRef, Scene, Shot } from '@/types';
import { cn, getMediaUrl, projectMediaRef } from '@/lib/utils';

const TYPE_META_BY_TYPE: Record<string, { label: string; badge: string; icon: typeof Film }> = {
  image: TYPE_META.i,
  video: TYPE_META.v,
  audio: TYPE_META.a,
  music: TYPE_META.m,
};

const TYPE_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'image', label: 'Images' },
  { value: 'video', label: 'Videos' },
  { value: 'audio', label: 'Audio' },
  { value: 'music', label: 'Music' },
];

interface ShotReferencesDialogProps {
  projectId: string;
  shot: Shot;
  open: boolean;
  onClose: () => void;
  /** Story cast — for the Characters, Backgrounds & Props tab */
  characters?: Character[];
  /** Story scenes — for the Characters, Backgrounds & Props tab */
  scenes?: Scene[];
  /** Story props — for the Characters, Backgrounds & Props tab */
  props?: Prop[];
}

export default function ShotReferencesDialog({ projectId, shot, open, onClose, characters, scenes, props: storyProps }: ShotReferencesDialogProps) {
  // Remember the last tab the user used, per project
  const [tab, setTab] = usePersistedState<'story' | 'project' | 'library' | 'projects'>(`references_tab_${projectId}`, 'project');
  const shotId = shot.id ?? shot.index;

  const { data: attached = [] } = useShotReferences(projectId, open ? shotId : null);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-0 overflow-hidden bg-card border-border">
        <DialogHeader className="p-4 pb-3 border-b">
          <DialogTitle className="text-base flex items-center gap-2">
            Shot {shot.index} — References
            {attached.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-sky-500 text-white font-bold">
                {attached.length}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        {/* Segmented tabs */}
        <div className="px-4 pt-3">
          <div className="flex items-center bg-muted/40 p-1 rounded-lg border shadow-sm w-fit">
            {([
              { key: 'story', label: 'Characters, Backgrounds & Props' },
              { key: 'project', label: 'Project Assets' },
              { key: 'library', label: 'Asset Library' },
              { key: 'projects', label: 'Project Library' },
            ] as const).map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  'flex items-center gap-1.5 text-xs font-semibold px-4 py-1.5 rounded-md transition-all',
                  tab === t.key
                    ? 'bg-background text-blue-600 shadow-sm ring-1 ring-border'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3 flex flex-col">
          {tab === 'story' && (
            <StoryRefsTab projectId={projectId} shotId={shotId} attached={attached} scenes={scenes} characters={characters} props={storyProps} />
          )}
          {tab === 'project' && (
            <ProjectAssetsTab projectId={projectId} shotId={shotId} shot={shot} attached={attached} />
          )}
          {tab === 'library' && (
            <LibraryPickerTab projectId={projectId} shotId={shotId} attachedRefs={attached.map((a) => a.ref)} />
          )}
          {tab === 'projects' && (
            <ProjectLibraryTab projectId={projectId} shotId={shotId} attachedRefs={attached.map((a) => a.ref)} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// =====================================================================
// Shared pick card
// =====================================================================

interface PickCardProps {
  entry: ResolvedAssetRef;
  attached?: boolean;
  selected?: boolean;
  selecting?: boolean;
  onToggle?: (ref: string) => void;
  onOpenDetail?: (ref: string) => void;
  onRemove?: (ref: string) => void;
  onUseAsSource?: (ref: string, slot: 'then' | 'now') => void;
}

function AssetPickCard({ entry, attached, selected, selecting, onToggle, onOpenDetail, onRemove, onUseAsSource }: PickCardProps) {
  const meta = TYPE_META_BY_TYPE[entry.type] ?? TYPE_META.i;
  const TypeIcon = meta.icon;
  const isImage = entry.type === 'image';
  const thumb = entry.thumb_url || (isImage ? entry.url : null);

  return (
    <div
      className={cn(
        'relative group border rounded-lg overflow-hidden bg-card transition-colors cursor-pointer',
        attached ? 'border-sky-500 ring-2 ring-sky-500/30' : 'hover:border-primary/50',
        selected && 'border-primary ring-2 ring-primary/30'
      )}
      onClick={() => onToggle?.(entry.ref)}
    >
      <div className="aspect-video bg-muted flex items-center justify-center overflow-hidden">
        {!entry.exists ? (
          <div className="flex flex-col items-center gap-1 text-red-500/80">
            <X className="w-6 h-6" />
            <span className="text-[10px]">Missing</span>
          </div>
        ) : isImage && thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt={entry.title} loading="lazy" className="w-full h-full object-cover" />
        ) : entry.type === 'video' ? (
          <video src={entry.url} preload="metadata" muted className="w-full h-full object-cover" />
        ) : (
          <TypeIcon className="w-8 h-8 text-muted-foreground/60" />
        )}

        <span className={cn('absolute bottom-1 left-1 text-[9px] px-1 py-0.5 rounded text-white font-semibold', meta.badge)}>
          {meta.label}
        </span>

        {attached && (
          <span className="absolute top-1 left-1 w-4 h-4 rounded-full bg-sky-500 text-white flex items-center justify-center">
            <Check className="w-3 h-3" />
          </span>
        )}
        {selecting && (
          <div className="absolute top-1 left-1" onClick={(e) => e.stopPropagation()}>
            <Checkbox checked={!!selected} onCheckedChange={() => onToggle?.(entry.ref)} />
          </div>
        )}

        <div
          className="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          {onOpenDetail && entry.exists && (
            <button
              className="p-1 rounded bg-black/60 text-white hover:bg-black/80"
              title="Open in new window"
              onClick={() => onOpenDetail(entry.ref)}
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}
          {onRemove && (
            <button
              className="p-1 rounded bg-black/60 text-white hover:bg-red-600"
              title="Remove from project assets (also detaches it from all shots)"
              onClick={() => onRemove(entry.ref)}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onUseAsSource && entry.type === 'video' && attached && (
            <>
              <button
                className="px-1 py-0.5 rounded bg-black/60 text-white hover:bg-sky-600 text-[9px] font-bold"
                title="Use as THEN (meeting) source for this FLFI2V shot"
                onClick={() => onUseAsSource(entry.ref, 'then')}
              >
                THEN
              </button>
              <button
                className="px-1 py-0.5 rounded bg-black/60 text-white hover:bg-violet-600 text-[9px] font-bold"
                title="Use as NOW (departure) source for this FLFI2V shot"
                onClick={() => onUseAsSource(entry.ref, 'now')}
              >
                NOW
              </button>
            </>
          )}
        </div>
      </div>
      <div className="p-1.5">
        <p className="text-xs font-medium truncate" title={entry.title}>
          {entry.title}
        </p>
        {entry.kind === 'project' && entry.source && (
          <p className="text-[10px] text-muted-foreground truncate">from {shortenProjectId(entry.source)}</p>
        )}
      </div>
    </div>
  );
}

function shortenProjectId(pid: string): string {
  // project_20260927_125800 -> "Project 2026-09-27"
  const m = pid.match(/(\d{4})(\d{2})(\d{2})/);
  return m ? `Project ${m[1]}-${m[2]}-${m[3]}` : pid;
}

// =====================================================================
// Tab 1: Project Assets (the pool; click a tile to attach/detach)
// =====================================================================

function ProjectAssetsTab({
  projectId,
  shotId,
  shot,
  attached,
}: {
  projectId: string;
  shotId: string | number;
  shot: Shot;
  attached: ResolvedAssetRef[];
}) {
  const { data: pool = [], isLoading } = useProjectAssets(projectId);
  const attach = useAddShotReferences(projectId, shotId);
  const detach = useRemoveShotReference(projectId, shotId);
  const removePool = useRemoveProjectAsset(projectId);
  const useAsSource = useReferenceAsSource(projectId, shotId);
  const [armedRemove, setArmedRemove] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState('all');

  const attachedRefs = useMemo(() => new Set(attached.map((a) => a.ref)), [attached]);
  const visible = pool.filter((e) => typeFilter === 'all' || e.type === typeFilter);

  const handleToggle = (ref: string) => {
    if (attachedRefs.has(ref)) detach.mutate(ref);
    else attach.mutate([ref]);
  };

  const handleUseAsSource = (ref: string, slot: 'then' | 'now') => {
    useAsSource.mutate(
      { ref, slot },
      {
        onSuccess: (res) =>
          toast.success(
            `Set as ${slot === 'then' ? 'THEN (meeting)' : 'NOW (departure)'} video source for shot ${shot.index}`
          ),
        onError: (e) => toast.error(`Failed to set source: ${extractError(e)}`),
      }
    );
  };

  const handleRemove = (ref: string) => {
    if (armedRemove !== ref) {
      setArmedRemove(ref);
      setTimeout(() => setArmedRemove((cur) => (cur === ref ? null : cur)), 3000);
      return;
    }
    setArmedRemove(null);
    removePool.mutate(
      { ref, strip: true },
      {
        onSuccess: () => toast.success('Removed from project assets'),
        onError: (e) => toast.error(`Remove failed: ${extractError(e)}`),
      }
    );
  };

  if (isLoading) return <LoadingBlock />;

  return (
    <div className="space-y-5">
      {/* Attached to this shot — every ref currently attached (sync-attached
          and manual). Click a card to detach; refs attached automatically by
          the reference sync re-appear on the next sync. */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Attached to this shot ({attached.length})
        </h3>
        {attached.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {attached.map((entry) => (
              <AssetPickCard
                key={entry.ref}
                entry={entry}
                attached
                onToggle={handleToggle}
                onOpenDetail={(ref) => window.open(`/asset/${ref}`, '_blank')}
              />
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Nothing attached yet — click a tile below, or use the Characters, Backgrounds &amp; Props tab.
          </p>
        )}
      </div>

      {/* Project asset pool — click a tile to attach/detach */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Project asset pool
        </h3>
        <TypeFilterRow value={typeFilter} onChange={setTypeFilter} />
        {visible.length === 0 ? (
          <EmptyBlock text="No project assets yet — add some from the Asset Library or Project Library tabs." />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {visible.map((entry) => (
              <AssetPickCard
                key={entry.ref}
                entry={entry}
                attached={attachedRefs.has(entry.ref)}
                onToggle={handleToggle}
                onOpenDetail={(ref) => window.open(`/asset/${ref}`, '_blank')}
                onRemove={handleRemove}
                onUseAsSource={shot.is_flfi2v ? handleUseAsSource : undefined}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// =====================================================================
// Tab: Characters & Backgrounds (attach the story's own reference sheets)
// =====================================================================

function storyRefEntry(projectId: string, title: string, path: string | null | undefined): ResolvedAssetRef | null {
  const ref = projectMediaRef(projectId, path);
  if (!ref) return null;
  const url = getMediaUrl(path ?? null);
  return {
    ref,
    kind: 'project',
    title,
    type: 'image',
    url,
    thumb_url: url,
    exists: true,
    source: projectId,
  };
}

function StoryRefsTab({
  projectId,
  shotId,
  attached,
  scenes,
  characters,
  props: storyProps,
}: {
  projectId: string;
  shotId: string | number;
  attached: ResolvedAssetRef[];
  scenes?: Scene[];
  characters?: Character[];
  props?: Prop[];
}) {
  const attach = useAddShotReferences(projectId, shotId);
  const detach = useRemoveShotReference(projectId, shotId);
  const attachedRefs = useMemo(() => new Set(attached.map((a) => a.ref)), [attached]);

  const handleToggle = (ref: string) => {
    if (attachedRefs.has(ref)) {
      detach.mutate(ref);
    } else {
      attach.mutate([ref], {
        onSuccess: () => toast.success('Reference attached to shot'),
        onError: (e) => toast.error(`Attach failed: ${extractError(e)}`),
      });
    }
  };

  const characterEntries = (characters || [])
    .map((c) => ({
      name: c.name || 'Character',
      entry: storyRefEntry(projectId, `${c.name || 'Character'} — character sheet`, c.character_reference_image_path),
    }))
    .filter((x) => x.entry !== null) as { name: string; entry: ResolvedAssetRef }[];

  const missingSheets = (characters || []).filter((c) => !projectMediaRef(projectId, c.character_reference_image_path));

  const backgroundEntries = (scenes || [])
    .map((s, i) => ({
      sceneId: s.scene_id ?? i,
      entry: storyRefEntry(
        projectId,
        `Scene ${(s.scene_id ?? i) + 1} background${s.location ? ` — ${s.location.slice(0, 40)}` : ''}`,
        s.background_image_path
      ),
    }))
    .filter((x) => x.entry !== null) as { sceneId: number; entry: ResolvedAssetRef }[];

  const missingBackgrounds = (scenes || []).filter((s) => !projectMediaRef(projectId, s.background_image_path));

  const propEntries = (storyProps || [])
    .map((p) => ({
      name: p.name || 'Prop',
      entry: storyRefEntry(projectId, `${p.name || 'Prop'} — prop sheet`, p.reference_image_path),
    }))
    .filter((x) => x.entry !== null) as { name: string; entry: ResolvedAssetRef }[];

  const missingPropSheets = (storyProps || []).filter((p) => !projectMediaRef(projectId, p.reference_image_path));

  const renderGroup = (
    heading: string,
    items: { key: string; entry: ResolvedAssetRef }[],
    missingHint: string | null
  ) => (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{heading}</h3>
      {items.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {items.map(({ key, entry }) => (
            <AssetPickCard
              key={key}
              entry={entry}
              attached={attachedRefs.has(entry.ref)}
              onToggle={handleToggle}
              onOpenDetail={(ref) => window.open(`/asset/${ref}`, '_blank')}
            />
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">{missingHint}</p>
      )}
    </div>
  );

  return (
    <div className="space-y-5">
      <p className="text-xs text-muted-foreground">
        Attach the story's own references to this shot. Attached refs always use the project's
        current sheet/background files, so regenerating a sheet keeps the reference in sync.
      </p>

      {renderGroup(
        'Characters',
        characterEntries.map((x) => ({ key: x.entry.ref, entry: x.entry })),
        missingSheets.length > 0
          ? `No reference sheet yet for: ${missingSheets.map((c) => c.name).join(', ')} — generate one from the project editor.`
          : 'No characters defined in the story.'
      )}

      {renderGroup(
        'Scene Backgrounds',
        backgroundEntries.map((x) => ({ key: x.entry.ref, entry: x.entry })),
        missingBackgrounds.length > 0
          ? `${missingBackgrounds.length} scene(s) have no background yet — generate one from the project editor.`
          : 'No scenes defined in the story.'
      )}

      {renderGroup(
        'Props',
        propEntries.map((x) => ({ key: x.entry.ref, entry: x.entry })),
        missingPropSheets.length > 0
          ? `No reference sheet yet for: ${missingPropSheets.map((p) => p.name).join(', ')} — generate one from the project editor.`
          : 'No props defined in the story.'
      )}
    </div>
  );
}

// =====================================================================
// Tab 2: Asset Library (browse + multi-select add)
// =====================================================================

function LibraryPickerTab({
  projectId,
  shotId,
  attachedRefs,
}: {
  projectId: string;
  shotId: string | number;
  attachedRefs: string[];
}) {
  const [cat, setCat] = useState('i');
  const { data: tree = [] } = useAssetTree();
  const { data: entries = [], isLoading } = useAssets(cat);
  const addPool = useAddProjectAssets(projectId);
  const addRefs = useAddShotReferences(projectId, shotId);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => setSelected(new Set()), [cat]);

  const currentNode = findTreeNode(tree, cat);
  const visible = entries.filter((e) => typeFilter === 'all' || e.type === typeFilter);

  const toResolved = (e: AssetEntry): ResolvedAssetRef => ({
    ref: e.ref,
    kind: 'library',
    title: e.title,
    type: e.type,
    letter: e.letter,
    url: e.url,
    thumb_url: e.thumb_url,
    source: e.library,
    exists: true,
    size_bytes: e.size_bytes,
    modified_at: e.modified_at,
  });

  const addSelected = async (alsoAttach: boolean) => {
    const refs = Array.from(selected);
    try {
      await addPool.mutateAsync(refs);
      if (alsoAttach) await addRefs.mutateAsync(refs);
      toast.success(
        alsoAttach
          ? `Added ${refs.length} reference${refs.length > 1 ? 's' : ''} to the shot`
          : `Added ${refs.length} asset${refs.length > 1 ? 's' : ''} to project assets`
      );
      setSelected(new Set());
    } catch (e) {
      toast.error(`Add failed: ${extractError(e)}`);
    }
  };

  return (
    <div className="flex-1 flex flex-col space-y-3">
      <TypeFilterRow value={typeFilter} onChange={setTypeFilter} />
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="w-48 shrink-0 hidden md:block overflow-y-auto">
          <AssetFolderTree nodes={tree} selectedPath={cat} onSelect={setCat} />
        </div>
        <div className="flex-1 min-w-0 overflow-y-auto">
          {isLoading ? (
            <LoadingBlock />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {(currentNode?.children ?? []).map((node) => (
                <FolderTile key={node.path} node={node} onClick={() => setCat(node.path)} />
              ))}
              {visible.map((entry) => (
                <AssetPickCard
                  key={entry.ref}
                  entry={toResolved(entry)}
                  selecting
                  selected={selected.has(entry.ref)}
                  attached={attachedRefs.includes(entry.ref)}
                  onToggle={(ref) =>
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (next.has(ref)) next.delete(ref);
                      else next.add(ref);
                      return next;
                    })
                  }
                  onOpenDetail={(ref) => window.open(`/asset/${ref}`, '_blank')}
                />
              ))}
              {visible.length === 0 && (currentNode?.children ?? []).length === 0 && (
                <div className="col-span-full">
                  <EmptyBlock text="This category is empty." />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {selected.size > 0 && (
        <div className="bg-background border rounded-lg shadow-lg px-4 py-2.5 flex items-center gap-2">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" size="sm" disabled={addPool.isPending} onClick={() => addSelected(false)}>
              Add {selected.size} to Project Assets
            </Button>
            <Button size="sm" disabled={addPool.isPending || addRefs.isPending} onClick={() => addSelected(true)}>
              Add to Shot
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// =====================================================================
// Tab 3: Project Library (browse all projects' media)
// =====================================================================

function ProjectLibraryTab({
  projectId,
  shotId,
  attachedRefs,
}: {
  projectId: string;
  shotId: string | number;
  attachedRefs: string[];
}) {
  const { data: projects = [], isLoading: projectsLoading } = useProjects();
  const [selectedPid, setSelectedPid] = useState<string>(projectId);
  const [typeFilter, setTypeFilter] = useState('all');
  const { data: media = [], isLoading: mediaLoading } = useProjectMedia(selectedPid, true);
  const addPool = useAddProjectAssets(projectId);
  const addRefs = useAddShotReferences(projectId, shotId);
  const importAsset = useImportAsset();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => setSelected(new Set()), [selectedPid, typeFilter]);

  const sortedProjects = useMemo(() => {
    const current = projects.filter((p) => p.project_id === projectId);
    const others = projects.filter((p) => p.project_id !== projectId);
    return [...current, ...others];
  }, [projects, projectId]);

  const visible = media.filter((e) => typeFilter === 'all' || e.type === typeFilter);

  const addSelected = async (alsoAttach: boolean) => {
    const refs = Array.from(selected);
    try {
      await addPool.mutateAsync(refs);
      if (alsoAttach) await addRefs.mutateAsync(refs);
      toast.success(
        alsoAttach
          ? `Added ${refs.length} reference${refs.length > 1 ? 's' : ''} to the shot`
          : `Added ${refs.length} asset${refs.length > 1 ? 's' : ''} to project assets`
      );
      setSelected(new Set());
    } catch (e) {
      toast.error(`Add failed: ${extractError(e)}`);
    }
  };

  const saveSelectedToLibrary = async () => {
    const byType = media.filter((m) => selected.has(m.ref));
    let saved = 0, duplicates = 0, failed = 0;
    for (const entry of byType) {
      try {
        const result = await importAsset.mutateAsync({
          ref: entry.ref,
          cat: entry.type === 'video' ? 'v' : 'i',
        });
        saved += result.saved.length;
        duplicates += result.skipped.length;
      } catch {
        failed++;
      }
    }
    if (saved > 0) toast.success(`Saved ${saved} asset${saved > 1 ? 's' : ''} to the library`);
    if (duplicates > 0) toast.info(`${duplicates} duplicate${duplicates > 1 ? 's' : ''} skipped (already in the library)`);
    if (failed > 0) toast.error(`${failed} failed`);
    setSelected(new Set());
  };

  return (
    <div className="flex-1 flex flex-col space-y-3">
      <TypeFilterRow value={typeFilter} onChange={setTypeFilter} />
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="w-52 shrink-0 space-y-1 overflow-y-auto">
          {projectsLoading && <LoadingBlock />}
          {sortedProjects.map((p) => (
            <button
              key={p.project_id}
              className={cn(
                'w-full text-left px-2 py-1.5 rounded-md text-sm flex items-center gap-2 hover:bg-muted',
                selectedPid === p.project_id && 'bg-muted font-medium text-primary'
              )}
              onClick={() => setSelectedPid(p.project_id)}
            >
              <Folder className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate flex-1">{shortenProjectId(p.project_id)}</span>
              {p.project_id === projectId && (
                <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/15 text-emerald-600 shrink-0">
                  this project
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="flex-1 min-w-0 overflow-y-auto">
          {mediaLoading ? (
            <LoadingBlock />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {visible.map((entry) => (
                <AssetPickCard
                  key={entry.ref}
                  entry={entry}
                  selecting
                  selected={selected.has(entry.ref)}
                  attached={attachedRefs.includes(entry.ref)}
                  onToggle={(ref) =>
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (next.has(ref)) next.delete(ref);
                      else next.add(ref);
                      return next;
                    })
                  }
                  onOpenDetail={(ref) => window.open(`/asset/${ref}`, '_blank')}
                />
              ))}
              {visible.length === 0 && (
                <div className="col-span-full">
                  <EmptyBlock text="This project has no media yet." />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {selected.size > 0 && (
        <div className="bg-background border rounded-lg shadow-lg px-4 py-2.5 flex items-center gap-2">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" size="sm" disabled={addPool.isPending} onClick={() => addSelected(false)}>
              Add {selected.size} to Project Assets
            </Button>
            <Button variant="outline" size="sm" disabled={importAsset.isPending} onClick={saveSelectedToLibrary}>
              Save {selected.size} to Library
            </Button>
            <Button size="sm" disabled={addPool.isPending || addRefs.isPending} onClick={() => addSelected(true)}>
              Add to Shot
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// =====================================================================
// Small shared pieces
// =====================================================================

function TypeFilterRow({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {TYPE_FILTERS.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={cn(
            'text-xs px-2.5 py-1 rounded-full border transition-colors',
            value === t.value
              ? 'bg-primary text-primary-foreground border-primary'
              : 'text-muted-foreground hover:text-foreground border-border'
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function FolderTile({ node, onClick }: { node: AssetTreeNode; onClick: () => void }) {
  return (
    <button
      className="aspect-video border rounded-lg bg-card flex flex-col items-center justify-center gap-1.5 text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors"
      onClick={onClick}
    >
      <Folder className="w-7 h-7" />
      <span className="text-xs px-2 truncate w-full text-center">{node.name}</span>
    </button>
  );
}

function LoadingBlock() {
  return (
    <div className="flex items-center justify-center py-16 text-muted-foreground">
      <Loader2 className="w-6 h-6 animate-spin" />
    </div>
  );
}

function EmptyBlock({ text }: { text: string }) {
  return (
    <div className="text-center py-14 text-muted-foreground">
      <p className="text-sm">{text}</p>
    </div>
  );
}

function findTreeNode(nodes: AssetTreeNode[], path: string): AssetTreeNode | null {
  for (const node of nodes) {
    if (node.path === path) return node;
    const found = findTreeNode(node.children, path);
    if (found) return found;
  }
  return null;
}
