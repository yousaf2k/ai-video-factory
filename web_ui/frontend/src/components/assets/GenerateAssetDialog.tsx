'use client';

/**
 * Generate an image / video / sound asset straight into a library category.
 * Kind picks the target type folder; video needs a source image (i2v) and
 * sound needs a source video (MMAudio). Progress is polled until completed.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  Sparkles,
  Loader2,
  Image as ImageIcon,
  Film,
  Volume2,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useAssetTree,
  useAssets,
  useAssetGeneration,
  useGenerateOptions,
  useStartGeneration,
  useCancelGeneration,
} from '@/hooks/useAssets';
import { flattenTree } from './assetUtils';
import { extractError } from './AssetDetailView';
import type { AssetEntry, AssetGenerationStatus, GenerateAssetRequest } from '@/types';
import { cn } from '@/lib/utils';

const KINDS: { value: GenerateAssetRequest['kind']; label: string; letter: string; icon: typeof ImageIcon }[] = [
  { value: 'image', label: 'Image', letter: 'i', icon: ImageIcon },
  { value: 'video', label: 'Video', letter: 'v', icon: Film },
  { value: 'audio', label: 'Sound', letter: 'a', icon: Volume2 },
];

const KIND_LETTER: Record<string, string> = { image: 'i', video: 'v', audio: 'a' };

interface GenerateAssetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Category the user is currently browsing — pre-selected when it matches the kind */
  defaultCat?: string;
  library?: string;
}

export default function GenerateAssetDialog({
  open,
  onOpenChange,
  defaultCat,
  library,
}: GenerateAssetDialogProps) {
  const queryClient = useQueryClient();
  const { data: options } = useGenerateOptions();
  const { data: tree = [] } = useAssetTree(library);
  const startMutation = useStartGeneration();
  const cancelMutation = useCancelGeneration();

  const [kind, setKind] = useState<GenerateAssetRequest['kind']>('image');
  const [cat, setCat] = useState<string>('');
  const [prompt, setPrompt] = useState('');
  const [title, setTitle] = useState('');
  const [workflow, setWorkflow] = useState<string>('default');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [duration, setDuration] = useState('5');
  const [seed, setSeed] = useState('');
  const [imageRef, setImageRef] = useState('');
  const [videoRef, setVideoRef] = useState('');
  const [genId, setGenId] = useState<string | null>(null);
  const notifiedRef = useRef(false);

  // Poll the active generation; null when the dialog shows the form
  const { data: gen } = useAssetGeneration(genId);
  const status = genId ? gen?.status ?? 'queued' : null;
  const finished = status === 'completed' || status === 'failed' || status === 'cancelled';

  const letter = KIND_LETTER[kind];
  const catOptions = useMemo(
    () => flattenTree(tree ?? []).filter((opt) => opt.value === letter || opt.value.startsWith(letter + '/')),
    [tree, letter]
  );
  const workflowOptions =
    kind === 'image' ? options?.image_workflows : kind === 'video' ? options?.video_workflows : options?.soundfx_workflows;

  // Reset the form whenever the dialog opens
  useEffect(() => {
    if (!open) return;
    setPrompt('');
    setTitle('');
    setWorkflow('default');
    setAspectRatio('16:9');
    setDuration('5');
    setSeed('');
    setImageRef('');
    setVideoRef('');
    setGenId(null);
    notifiedRef.current = false;
  }, [open]);

  // Keep the target category valid for the chosen kind; prefer the browsed category
  useEffect(() => {
    if (!open || !letter) return;
    const current = cat || defaultCat || '';
    setCat(current === letter || current.startsWith(letter + '/') ? current : letter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [letter, defaultCat, open]);

  // On completion: refresh the library views and notify once
  useEffect(() => {
    if (gen?.status === 'completed' && !notifiedRef.current) {
      notifiedRef.current = true;
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset-tree'] });
      queryClient.invalidateQueries({ queryKey: ['asset-search'] });
      toast.success(`Generated "${gen.title}" — saved to ${gen.cat}`);
    }
  }, [gen, queryClient]);

  const busy = startMutation.isPending;

  const handleSubmit = () => {
    if (!prompt.trim()) return;
    const request: GenerateAssetRequest = {
      kind,
      prompt: prompt.trim(),
      cat,
      library,
    };
    if (title.trim()) request.title = title.trim();
    if (workflow && workflow !== 'default') request.workflow = workflow;
    if (kind !== 'audio') request.aspect_ratio = aspectRatio;
    if (kind === 'video') request.duration = parseFloat(duration) || undefined;
    if (kind === 'video' && imageRef) request.image_ref = imageRef;
    if (kind === 'audio' && videoRef) request.video_ref = videoRef;
    if (kind === 'image' && seed.trim()) request.seed = parseInt(seed, 10);

    startMutation.mutate(request, {
      onSuccess: (started) => {
        notifiedRef.current = false;
        setGenId(started.id);
      },
      onError: (e) => toast.error(`Generate failed: ${extractError(e)}`),
    });
  };

  const closeGuard = (next: boolean) => {
    // Don't close over a still-running generation by accident
    if (!next && genId && !finished) return;
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={closeGuard}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            Generate asset
          </DialogTitle>
          <DialogDescription>
            Generate with the configured pipeline and save into the asset library.
          </DialogDescription>
        </DialogHeader>

        {!genId ? (
          <div className="space-y-4">
            {/* Kind selector */}
            <div className="grid grid-cols-3 gap-2">
              {KINDS.map((k) => {
                const Icon = k.icon;
                return (
                  <button
                    key={k.value}
                    type="button"
                    onClick={() => setKind(k.value)}
                    className={cn(
                      'flex flex-col items-center gap-1 rounded-lg border p-3 text-sm transition-colors',
                      kind === k.value
                        ? 'border-primary bg-primary/5 text-foreground'
                        : 'text-muted-foreground hover:border-primary/50'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {k.label}
                  </button>
                );
              })}
            </div>

            {/* Target category */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Save to category</Label>
              <Select value={cat} onValueChange={setCat}>
                <SelectTrigger>
                  <SelectValue placeholder="Category…" />
                </SelectTrigger>
                <SelectContent className="max-h-56">
                  {catOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Prompt */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">
                {kind === 'audio' ? 'Sound description' : kind === 'video' ? 'Motion prompt' : 'Image prompt'}
              </Label>
              <Textarea
                autoFocus
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={
                  kind === 'audio'
                    ? 'e.g. heavy rain on a window, distant thunder'
                    : kind === 'video'
                    ? 'e.g. slow cinematic pan across the skyline at dusk'
                    : 'e.g. a weathered lighthouse on a rocky coast, golden hour'
                }
                className="min-h-[70px]"
              />
            </div>

            {/* Source asset pickers */}
            {kind === 'video' && (
              <SourceRefPicker
                label="Source image (first frame)"
                letter="i"
                library={library}
                value={imageRef}
                onChange={setImageRef}
              />
            )}
            {kind === 'audio' && (
              <SourceRefPicker
                label="Source video"
                letter="v"
                library={library}
                value={videoRef}
                onChange={setVideoRef}
              />
            )}

            {/* Options row */}
            <div className="grid grid-cols-2 gap-3">
              {kind !== 'audio' && (
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Aspect ratio</Label>
                  <Select value={aspectRatio} onValueChange={setAspectRatio}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(options?.aspect_ratios ?? ['16:9']).map((r) => (
                        <SelectItem key={r} value={r}>
                          {r}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              {kind === 'video' && (
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Duration (s)</Label>
                  <Input
                    type="number"
                    min={1}
                    max={15}
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                  />
                </div>
              )}
              {kind === 'image' && (
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Seed (optional)</Label>
                  <Input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    placeholder="random"
                  />
                </div>
              )}
            </div>

            {/* Workflow */}
            {(workflowOptions?.length ?? 0) > 0 && (
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Workflow</Label>
                <Select value={workflow} onValueChange={setWorkflow}>
                  <SelectTrigger>
                    <SelectValue placeholder="Configured default" />
                  </SelectTrigger>
                  <SelectContent className="max-h-56">
                    <SelectItem value="default">Configured default</SelectItem>
                    {workflowOptions!.map((w) => (
                      <SelectItem key={w.key} value={w.key}>
                        {w.key}
                        {w.description ? ` — ${w.description.slice(0, 60)}` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Title */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Title (optional)</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Defaults to the first words of the prompt"
              />
            </div>
          </div>
        ) : (
          <ResultPanel gen={gen ?? null} onDone={() => { setGenId(null); onOpenChange(false); }} onRetry={() => setGenId(null)} />
        )}

        <DialogFooter>
          {!genId ? (
            <>
              <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={!prompt.trim() || busy || !cat || (kind === 'video' && !imageRef) || (kind === 'audio' && !videoRef)}
                onClick={handleSubmit}
              >
                {busy ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                    Starting…
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-1.5" />
                    Generate
                  </>
                )}
              </Button>
            </>
          ) : (
            !finished && (
              <Button
                variant="outline"
                size="sm"
                disabled={cancelMutation.isPending}
                onClick={() => genId && cancelMutation.mutate(genId)}
              >
                Stop
              </Button>
            )
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Pick a source asset of one type: category dropdown -> asset dropdown. */
function SourceRefPicker({
  label,
  letter,
  library,
  value,
  onChange,
}: {
  label: string;
  letter: string;
  library?: string;
  value: string;
  onChange: (ref: string) => void;
}) {
  const { data: tree = [] } = useAssetTree(library);
  const catOptions = useMemo(
    () => flattenTree(tree ?? []).filter((opt) => opt.value === letter || opt.value.startsWith(letter + '/')),
    [tree, letter]
  );
  const [cat, setCat] = useState(letter);
  const { data: entries = [] } = useAssets(cat, library);

  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <div className="grid grid-cols-2 gap-2">
        <Select value={cat} onValueChange={setCat}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="max-h-56">
            {catOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger>
            <SelectValue placeholder="Select asset…" />
          </SelectTrigger>
          <SelectContent className="max-h-56">
            {entries.length === 0 && (
              <div className="px-3 py-2 text-xs text-muted-foreground">No assets in this category</div>
            )}
            {entries.map((e: AssetEntry) => (
              <SelectItem key={e.ref} value={e.ref}>
                {e.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

/** Live status while the generation runs; final result once it settles. */
function ResultPanel({
  gen,
  onDone,
  onRetry,
}: {
  gen: AssetGenerationStatus | null;
  onDone: () => void;
  onRetry: () => void;
}) {
  if (!gen || gen.status === 'queued' || gen.status === 'running') {
    const progress = gen?.progress ?? 0;
    return (
      <div className="space-y-3 py-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Generating {gen?.kind ?? 'asset'}… this can take a while
        </div>
        <Progress value={progress} />
        <p className="text-xs text-muted-foreground">{progress}%</p>
        <p className="text-xs text-muted-foreground truncate" title={gen?.prompt}>
          {gen?.prompt}
        </p>
      </div>
    );
  }

  if (gen.status === 'completed') {
    return (
      <div className="space-y-3 py-2">
        <div className="flex items-center gap-2 text-sm text-green-600">
          <CheckCircle2 className="w-4 h-4" />
          Saved to {gen.cat}
        </div>
        {gen.kind === 'image' && gen.url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={gen.url} alt={gen.title ?? ''} className="max-h-[35vh] w-auto max-w-full rounded-md object-contain" />
        )}
        {gen.title && <p className="text-sm font-medium">{gen.title}</p>}
        <Button size="sm" onClick={onDone}>
          Done
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3 py-4">
      <div className="flex items-center gap-2 text-sm text-red-500">
        <XCircle className="w-4 h-4" />
        {gen.status === 'cancelled' ? 'Generation cancelled' : 'Generation failed'}
      </div>
      {gen.error && <p className="text-xs text-muted-foreground break-words">{gen.error}</p>}
      <Button variant="outline" size="sm" onClick={onRetry}>
        Back to form
      </Button>
    </div>
  );
}
