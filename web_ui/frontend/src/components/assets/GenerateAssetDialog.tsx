'use client';

/**
 * Generate an image / video / sound asset straight into a library category.
 * Kind picks the target type folder; video needs a source image (i2v) and
 * sound needs a source video (MMAudio). Starting a generation reports it via
 * `onStarted` and closes — progress shows as a placeholder card in the grid.
 */
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  Sparkles,
  Loader2,
  Image as ImageIcon,
  Film,
  Volume2,
  ChevronDown,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
  useTemplateText,
  useGenerateOptions,
  useStartGeneration,
} from '@/hooks/useAssets';
import {
  ImageGenerationOptions,
  imageOptionsToRequest,
  useImageGenerationOptions,
} from '@/components/shots/ImageGenerationOptions';
import { flattenTree, humanizeCat } from './assetUtils';
import { extractError } from './AssetDetailView';
import type { AssetGenerationStatus, AssetEntry, GenerateAssetRequest } from '@/types';
import { cn } from '@/lib/utils';

const KINDS: { value: GenerateAssetRequest['kind']; label: string; letter: string; icon: typeof ImageIcon }[] = [
  { value: 'image', label: 'Image', letter: 'i', icon: ImageIcon },
  { value: 'video', label: 'Video', letter: 'v', icon: Film },
  { value: 'audio', label: 'Sound', letter: 'a', icon: Volume2 },
];

const KIND_LETTER: Record<string, string> = { image: 'i', video: 'v', audio: 'a' };

// localStorage key scoping for the shared image options — the asset dialog
// persists its mode/workflow/Gemini picks the same way project dialogs do.
const ASSET_OPTIONS_KEY = 'assets';

interface GenerateAssetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Category the user is currently browsing — pre-selected when it matches the kind */
  defaultCat?: string;
  library?: string;
  /** Called once a generation is accepted; the dialog then closes and the
      browser grid shows a placeholder card for it. */
  onStarted?: (gen: AssetGenerationStatus) => void;
}

export default function GenerateAssetDialog({
  open,
  onOpenChange,
  defaultCat,
  library,
  onStarted,
}: GenerateAssetDialogProps) {
  const { data: options } = useGenerateOptions();
  const { data: tree = [] } = useAssetTree(library);
  const startMutation = useStartGeneration();

  const [kind, setKind] = useState<GenerateAssetRequest['kind']>('image');
  const [cat, setCat] = useState<string>('');
  const [prompt, setPrompt] = useState('');
  const [title, setTitle] = useState('');
  const [workflow, setWorkflow] = useState<string>('default');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [duration, setDuration] = useState('5');
  const [imageRef, setImageRef] = useState('');
  const [videoRef, setVideoRef] = useState('');
  // Reference images (like shot reference_asset_ids) — resolved to paths
  // server-side and injected into reference slots of image/video workflows.
  const [refRefs, setRefRefs] = useState<string[]>([]);

  // Same image options the project's image generation dialog offers
  // (mode, workflow, seed, Gemini Web model/thinking, Flow info).
  const imgOpts = useImageGenerationOptions(ASSET_OPTIONS_KEY, open && kind === 'image');

  // Prompt template — a 't' (Templates) text asset with {placeholder} fields.
  // When one is selected its filled text replaces the free-form prompt.
  const [tplCat, setTplCat] = useState('t');
  const [tplRef, setTplRef] = useState('none');
  const [tplValues, setTplValues] = useState<Record<string, string>>({});
  const templateActive = tplRef !== 'none';
  const { data: tplEntries = [] } = useAssets(tplCat, library);
  const {
    data: tplText,
    isLoading: tplLoading,
    error: tplError,
  } = useTemplateText(templateActive ? tplRef : null);
  const tplContent = tplText?.content ?? '';

  // Template fields parsed from {placeholder} tokens. A token may carry
  // predefined choices after a colon with pipe separators, e.g.
  // {Style:Studio Ghibli|3D Pixar|2D Anime} — label "Style", dropdown with
  // those three values. Plain {name} tokens stay free-text inputs.
  const fields = useMemo<TemplateField[]>(() => parseTemplateFields(tplContent), [tplContent]);

  /** The special {Name} placeholder is filled from the (mandatory) asset title. */
  const isNameField = (f: TemplateField) => f.name.toLowerCase() === 'name';

  // Template with every filled field substituted; blanks stay literal.
  // {Name} tokens take their value from the title, not tplValues.
  const filledTemplate = useMemo(
    () =>
      fields.reduce((text, f) => {
        const val = isNameField(f) ? title.trim() : (tplValues[f.raw] ?? '').trim();
        return val ? text.split(`{${f.raw}}`).join(val) : text;
      }, tplContent),
    [fields, tplContent, tplValues, title]
  );

  // What the Generate button will send as the prompt
  const effectivePrompt = (templateActive ? filledTemplate : prompt).trim();

  const letter = KIND_LETTER[kind];
  const catOptions = useMemo(
    () => flattenTree(tree ?? []).filter((opt) => opt.value === letter || opt.value.startsWith(letter + '/')),
    [tree, letter]
  );
  const tplCatOptions = useMemo(
    () => flattenTree(tree ?? []).filter((opt) => opt.value === 't' || opt.value.startsWith('t/')),
    [tree]
  );
  const workflowOptions =
    kind === 'video' ? options?.video_workflows : kind === 'audio' ? options?.soundfx_workflows : undefined;

  // Reset the form whenever the dialog opens
  useEffect(() => {
    if (!open) return;
    setPrompt('');
    setTitle('');
    setWorkflow('default');
    setAspectRatio('16:9');
    setDuration('5');
    setImageRef('');
    setVideoRef('');
    setRefRefs([]);
    setTplRef('none');
    setTplValues({});
  }, [open]);

  // Switching template file (or category) restarts the placeholder values
  useEffect(() => {
    setTplValues({});
  }, [tplRef]);

  // Dropdown fields default to their first option so the filled template is
  // immediately valid; free-text fields stay blank (blank stays literal).
  // {Name} is skipped — it's driven by the title. tplValues is deliberately
  // not a dependency — only missing keys are filled.
  useEffect(() => {
    if (!templateActive) return;
    const defaults: Record<string, string> = {};
    for (const f of fields) {
      if (isNameField(f)) continue;
      if (f.options.length > 0 && tplValues[f.raw] === undefined) defaults[f.raw] = f.options[0];
    }
    if (Object.keys(defaults).length > 0) setTplValues((v) => ({ ...v, ...defaults }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fields, templateActive]);

  // Keep the target category valid for the chosen kind; prefer the browsed category
  useEffect(() => {
    if (!open || !letter) return;
    const current = cat || defaultCat || '';
    setCat(current === letter || current.startsWith(letter + '/') ? current : letter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [letter, defaultCat, open]);

  const busy = startMutation.isPending;

  const handleSubmit = () => {
    // Template mode sends the filled template; free mode sends the textarea
    const finalPrompt = (templateActive ? filledTemplate : prompt).trim();
    if (!finalPrompt) return;
    const request: GenerateAssetRequest = {
      kind,
      prompt: finalPrompt,
      cat,
      library,
    };
    if (title.trim()) request.title = title.trim();
    if (kind !== 'audio') request.aspect_ratio = aspectRatio;
    if (kind === 'video') request.duration = parseFloat(duration) || undefined;
    if (kind === 'video' && imageRef) request.image_ref = imageRef;
    if (kind === 'audio' && videoRef) request.video_ref = videoRef;
    if (kind !== 'audio' && refRefs.length > 0) request.reference_refs = refRefs;

    if (kind === 'image') {
      // Same fields the project image dialog submits
      const opts = imageOptionsToRequest(imgOpts.value);
      request.mode = opts.mode;
      if (opts.workflow) request.workflow = opts.workflow;
      if (opts.seed !== undefined) request.seed = opts.seed;
      if (opts.gemini_model) request.gemini_model = opts.gemini_model;
      if (opts.gemini_thinking) request.gemini_thinking = opts.gemini_thinking;
    } else if (workflow && workflow !== 'default') {
      request.workflow = workflow;
    }

    startMutation.mutate(request, {
      onSuccess: (started) => {
        onStarted?.(started);
        toast.success(`Generating "${started.title}" in ${humanizeCat(started.cat)} — track it in the grid`);
        onOpenChange(false);
      },
      onError: (e) => toast.error(`Generate failed: ${extractError(e)}`),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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

            {/* Asset title + aspect ratio — title is mandatory and fills a
                {Name} placeholder */}
            <div className="grid grid-cols-2 gap-3">
              <div className={cn('space-y-1.5', kind === 'audio' && 'col-span-2')}>
                <Label className="text-xs text-muted-foreground">Title</Label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Suzuki Jimmy reference sheet"
                  autoFocus
                />
                <p className="text-[10px] text-muted-foreground">
                  Required. Fills a {'{Name}'} placeholder when present.
                </p>
              </div>
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
            </div>

            {/* Prompt template — pick a Templates (t) text asset and fill its
                {placeholders}; the filled text is sent as the prompt */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Prompt template (optional)</Label>
              <div className="grid grid-cols-2 gap-2">
                <Select
                  value={tplCat}
                  onValueChange={(v) => {
                    setTplCat(v);
                    setTplRef('none');
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-56">
                    {tplCatOptions.length === 0 && (
                      <div className="px-3 py-2 text-xs text-muted-foreground">No Templates category yet</div>
                    )}
                    {tplCatOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={tplRef} onValueChange={setTplRef}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select template…" />
                  </SelectTrigger>
                  <SelectContent className="max-h-56">
                    <SelectItem value="none">None — free prompt</SelectItem>
                    {tplEntries.map((e: AssetEntry) => (
                      <SelectItem key={e.ref} value={e.ref}>
                        {e.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Template placeholders */}
            {templateActive && (
              <div className="space-y-3 rounded-md border border-border/60 p-3">
                {tplLoading && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Loading template…
                  </div>
                )}
                {!tplLoading && tplError && (
                  <p className="text-xs text-red-500 break-words">
                    Failed to load template: {extractError(tplError)}
                  </p>
                )}
                {!tplLoading && !tplError && fields.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    No {'{placeholders}'} found — the template text will be sent as-is.
                  </p>
                )}
                {fields.filter((f) => !isNameField(f)).map((f) => (
                  <div key={f.raw} className="space-y-1">
                    <Label className="text-xs font-medium">{humanizePlaceholder(f.name)}</Label>
                    {f.options.length > 0 ? (
                      <Select
                        value={tplValues[f.raw] ?? f.options[0]}
                        onValueChange={(v) => setTplValues((vals) => ({ ...vals, [f.raw]: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="max-h-56">
                          {f.options.map((o) => (
                            <SelectItem key={o} value={o}>
                              {o}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={tplValues[f.raw] ?? ''}
                        onChange={(e) => setTplValues((vals) => ({ ...vals, [f.raw]: e.target.value }))}
                        placeholder={f.name}
                      />
                    )}
                  </div>
                ))}
                {!tplLoading && !tplError && tplContent && (
                  <details className="group">
                    <summary className="flex cursor-pointer select-none items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground">
                      <span className="flex items-center gap-1">
                        <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                        Template source (references inlined)
                      </span>
                    </summary>
                    <p className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-muted/40 p-2 text-xs text-muted-foreground break-words">
                      {tplContent}
                    </p>
                  </details>
                )}
                {!tplLoading && !tplError && filledTemplate && (
                  <details className="group">
                    <summary className="flex cursor-pointer select-none items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground">
                      <span className="flex items-center gap-1">
                        <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                        Final prompt
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          // Copy to the free-form box without toggling the section
                          e.preventDefault();
                          e.stopPropagation();
                          const filled = filledTemplate.trim();
                          if (!filled) return;
                          setPrompt(filled);
                          setTplRef('none'); // reveals the free-form textarea
                        }}
                        className="normal-case text-[10px] text-primary hover:underline"
                        title="Copy this prompt into the free-form prompt box for direct editing"
                      >
                        Edit as free prompt
                      </button>
                    </summary>
                    <p className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-muted/40 p-2 text-xs text-muted-foreground break-words">
                      {filledTemplate}
                    </p>
                  </details>
                )}
              </div>
            )}

            {/* Free-form prompt — hidden while a template drives the prompt */}
            {!templateActive && (
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
            )}

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

            {/* Reference images (like shot references) — injected into the
                reference slots of image / r2v video workflows */}
            {kind !== 'audio' && (
              <details className="group rounded-md border border-border/60">
                <summary className="flex cursor-pointer select-none items-center gap-1 px-3 py-2 text-xs text-muted-foreground hover:text-foreground">
                  <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                  References
                  {refRefs.length > 0 && <span className="font-medium">({refRefs.length} selected)</span>}
                </summary>
                <div className="px-3 pb-3">
                  <ReferencesPicker letter="i" library={library} value={refRefs} onChange={setRefRefs} />
                </div>
              </details>
            )}

            {/* Image options — the exact same UI as the project's image
                generation dialog (mode, workflow, seed, Gemini Web picker) */}
            {kind === 'image' && (
              <ImageGenerationOptions
                value={imgOpts.value}
                onSelectMode={imgOpts.selectMode}
                onSelectWorkflow={imgOpts.selectWorkflow}
                onSeedChange={imgOpts.changeSeed}
                onSelectGeminiModel={imgOpts.selectGeminiModel}
                onSelectGeminiThinking={imgOpts.selectGeminiThinking}
              />
            )}

            {/* Options row — aspect ratio lives up top beside Title */}
            <div className="grid grid-cols-2 gap-3">
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
            </div>

            {/* Workflow (video / audio — images pick their workflow in the
                shared image options above) */}
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

          </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={
              !effectivePrompt ||
              !title.trim() ||
              (templateActive && tplLoading) ||
              busy ||
              !cat ||
              (kind === 'video' && !imageRef) ||
              (kind === 'audio' && !videoRef)
            }
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
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** One {placeholder} occurrence in a template. */
interface TemplateField {
  /** Full inner text, unique per token — the key into the values map */
  raw: string;
  /** Label part before the colon (or the whole token when no colon) */
  name: string;
  /** Pipe-separated choices after the colon; empty = free-text input */
  options: string[];
}

/**
 * Parse {placeholder} tokens in first-appearance order, deduped.
 * "{Style:Studio Ghibli|3D Pixar|2D Anime}" -> name "Style", dropdown options
 * ["Studio Ghibli", "3D Pixar", "2D Anime"]; "{subject}" -> free text.
 * The colon splits once, so values may contain colons ("16:9").
 */
function parseTemplateFields(content: string): TemplateField[] {
  if (!content) return [];
  const seen = new Set<string>();
  const out: TemplateField[] = [];
  for (const m of content.matchAll(/\{([^{}\n]+?)\}/g)) {
    const raw = m[1].trim();
    if (!raw || seen.has(raw)) continue;
    seen.add(raw);
    const colon = raw.indexOf(':');
    const name = (colon === -1 ? raw : raw.slice(0, colon)).trim() || raw;
    const options =
      colon === -1
        ? []
        : raw
            .slice(colon + 1)
            .split('|')
            .map((o) => o.trim())
            .filter(Boolean);
    out.push({ raw, name, options });
  }
  return out;
}

/** "cinematic_style" -> "Cinematic Style" for placeholder input labels */
function humanizePlaceholder(name: string): string {
  return name
    .replace(/[_-]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
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

/** Multi-select picker for reference image assets (like shot references).
 * References are always images — the backend injects their paths into the
 * reference slots of image / r2v video workflows. */
function ReferencesPicker({
  letter,
  library,
  value,
  onChange,
}: {
  letter: string;
  library?: string;
  value: string[];
  onChange: (refs: string[]) => void;
}) {
  const { data: tree = [] } = useAssetTree(library);
  const catOptions = useMemo(
    () => flattenTree(tree).filter((opt) => opt.value === letter || opt.value.startsWith(letter + '/')),
    [tree, letter]
  );
  const [cat, setCat] = useState(letter);
  const { data: entries = [] } = useAssets(cat, library);

  const toggle = (ref: string) =>
    onChange(value.includes(ref) ? value.filter((r) => r !== ref) : [...value, ref]);

  return (
    <div className="space-y-2">
      <Select value={cat} onValueChange={setCat}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue placeholder="Browse category…" />
        </SelectTrigger>
        <SelectContent className="max-h-56">
          {catOptions.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="max-h-40 overflow-auto rounded border border-border/60 divide-y divide-border/50">
        {entries.length === 0 && (
          <div className="px-3 py-2 text-xs text-muted-foreground">No assets in this category</div>
        )}
        {entries.map((e: AssetEntry) => (
          <label
            key={e.ref}
            className="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-muted/40"
          >
            <Checkbox checked={value.includes(e.ref)} onCheckedChange={() => toggle(e.ref)} />
            <span className="truncate">{e.title}</span>
          </label>
        ))}
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {value.map((ref) => (
            <span key={ref} className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[10px]">
              {ref}
              <button
                type="button"
                onClick={() => toggle(ref)}
                className="text-muted-foreground hover:text-foreground"
                title="Remove reference"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
