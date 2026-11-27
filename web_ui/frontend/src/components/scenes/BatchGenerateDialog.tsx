'use client';

/**
 * Batch generation for the edit-story page: pick what to generate
 * (character reference sheets, prop sheets, scene backgrounds, scene music,
 * narration), then configure the image / music / voice options and queue
 * everything. Only eligible items are generated — a character needs a
 * prompt, a prop an image_prompt, a scene a set_prompt (or location on r2v)
 * for backgrounds, a music_prompt for music, and narration text for TTS.
 */
import { useMemo, useRef, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { GenerationDialog, type GenerationConfig } from '@/components/shots/GenerationDialog';
import { api } from '@/services/api';
import { Story } from '@/types';
import { ProjectType } from '@/types';
import { toast } from 'sonner';
import {
  UserCircle,
  Package,
  Image as ImageIcon,
  Music2,
  Volume2,
  Loader2,
  ListChecks,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface BatchGenerateDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  story: Story;
  isR2V?: boolean;
}

type CatKey = 'characters' | 'props' | 'backgrounds' | 'music' | 'narration';
type OptionKind = 'image' | 'music' | 'voice';

interface VoiceConfig {
  method: string;
  workflow: string;
  voice: string;
}

export default function BatchGenerateDialog({
  open,
  onClose,
  projectId,
  story,
  isR2V = false,
}: BatchGenerateDialogProps) {
  const isTvN = story.project_type === ProjectType.ThenVsNow;

  // Eligible targets per category (only items that carry a prompt)
  const targets = useMemo(() => {
    const characterTargets: { index: number; variant: 'character' | 'then' | 'now' }[] = [];
    (story.characters || []).forEach((c, idx) => {
      if (isTvN) {
        if ((c.then_prompt || '').trim()) characterTargets.push({ index: idx, variant: 'then' });
        if ((c.now_prompt || '').trim()) characterTargets.push({ index: idx, variant: 'now' });
      } else if ((c.image_prompt || '').trim()) {
        characterTargets.push({ index: idx, variant: 'character' });
      }
    });

    const propTargets = (story.props || [])
      .map((p, idx) => ({ index: idx, hasPrompt: !!(p.image_prompt || '').trim() }))
      .filter((t) => t.hasPrompt);

    const scenes = story.scenes || [];
    const sceneIdOf = (idx: number) => scenes[idx]?.scene_id ?? idx;
    const backgroundTargets = scenes
      .map((s, idx) => ({
        sceneId: sceneIdOf(idx),
        eligible: !!(s.set_prompt || '').trim() || (isR2V && !!(s.location || '').trim()),
      }))
      .filter((t) => t.eligible);
    const musicTargets = scenes
      .map((s, idx) => ({ sceneId: sceneIdOf(idx), eligible: !!(s.music_prompt || '').trim() }))
      .filter((t) => t.eligible);
    const narrationTargets = scenes
      .map((s, idx) => ({ index: idx, eligible: !!(s.narration || '').trim() }))
      .filter((t) => t.eligible);

    return { characterTargets, propTargets, backgroundTargets, musicTargets, narrationTargets };
  }, [story, isTvN]);

  const categories: { key: CatKey; label: string; description: string; count: number; icon: typeof UserCircle }[] = [
    {
      key: 'characters',
      label: 'Character Reference Sheet',
      description: 'Reference sheets for characters that have a prompt',
      count: targets.characterTargets.length,
      icon: UserCircle,
    },
    {
      key: 'props',
      label: 'Prop Reference Sheet',
      description: 'Product sheets for props that have a prompt',
      count: targets.propTargets.length,
      icon: Package,
    },
    {
      key: 'backgrounds',
      label: 'Background Images',
      description: isR2V
        ? 'Background sheets for scenes with a set_prompt or location'
        : 'Backgrounds for scenes with a set_prompt',
      count: targets.backgroundTargets.length,
      icon: ImageIcon,
    },
    {
      key: 'music',
      label: 'Background Music',
      description: 'Scene music for scenes that have a music prompt',
      count: targets.musicTargets.length,
      icon: Music2,
    },
    {
      key: 'narration',
      label: 'Narration',
      description: 'Voice-over for scenes that have narration text',
      count: targets.narrationTargets.length,
      icon: Volume2,
    },
  ];

  const [selected, setSelected] = useState<Record<CatKey, boolean>>({
    characters: true,
    props: true,
    backgrounds: true,
    music: true,
    narration: true,
  });
  const anySelected = categories.some((c) => c.count > 0 && selected[c.key]);

  // Step 2: sequential option dialogs — image (chars/props/backgrounds),
  // then music, then narration voice
  const [optionQueue, setOptionQueue] = useState<OptionKind[]>([]);
  // Accumulated across the sequential option dialogs — a ref so the final
  // execute call sees every config even when the last dialog submits
  const configsRef = useRef<{ image?: GenerationConfig; music?: GenerationConfig; voice?: VoiceConfig }>({});
  const [executing, setExecuting] = useState(false);

  const activeOption = optionQueue[0] ?? null;
  const imageSelected =
    (selected.characters && targets.characterTargets.length > 0) ||
    (selected.props && targets.propTargets.length > 0) ||
    (selected.backgrounds && targets.backgroundTargets.length > 0);

  const handleContinue = () => {
    configsRef.current = {};
    const queue: OptionKind[] = [];
    if (imageSelected) queue.push('image');
    if (selected.music && targets.musicTargets.length > 0) queue.push('music');
    if (selected.narration && targets.narrationTargets.length > 0) queue.push('voice');
    if (queue.length === 0) return;
    // A queue of one goes straight to execution after its dialog closes
    setOptionQueue(queue);
  };

  const handleOptionDone = (kind: OptionKind, cfg: any) => {
    configsRef.current[kind] = cfg;
    const rest = optionQueue.slice(1);
    setOptionQueue(rest);
    if (rest.length === 0) {
      handleExecute(configsRef.current);
    }
  };

  const handleExecute = async (configs: { image?: GenerationConfig; music?: GenerationConfig; voice?: VoiceConfig }) => {
    const imageCfg = configs.image;
    const musicCfg = configs.music;
    const voiceCfg = configs.voice;
    setExecuting(true);
    const parts: string[] = [];
    const failures: string[] = [];

    const seed = typeof imageCfg?.seed === 'number' ? imageCfg.seed : undefined;
    const imageRequest = (variant: string = 'character') => ({
      variant,
      image_mode: imageCfg?.mode,
      image_workflow: imageCfg?.workflow,
      seed,
      gemini_mode: imageCfg?.gemini_mode,
      gemini_model: imageCfg?.gemini_model,
      gemini_thinking: imageCfg?.gemini_thinking,
    });

    // Character reference sheets
    if (selected.characters && targets.characterTargets.length > 0) {
      let ok = 0;
      for (const t of targets.characterTargets) {
        try {
          await api.generateCharacterReferenceImage(projectId, t.index, imageRequest(t.variant));
          ok++;
        } catch {
          failures.push(`character #${t.index + 1}`);
        }
      }
      if (ok) parts.push(`${ok} character reference sheet${ok > 1 ? 's' : ''}`);
    }

    // Prop reference sheets
    if (selected.props && targets.propTargets.length > 0) {
      let ok = 0;
      for (const t of targets.propTargets) {
        try {
          await api.generatePropReferenceImage(projectId, t.index, imageRequest());
          ok++;
        } catch {
          failures.push(`prop #${t.index + 1}`);
        }
      }
      if (ok) parts.push(`${ok} prop sheet${ok > 1 ? 's' : ''}`);
    }

    // Scene backgrounds
    if (selected.backgrounds && targets.backgroundTargets.length > 0) {
      let ok = 0;
      for (const t of targets.backgroundTargets) {
        try {
          await api.generateSceneBackground(projectId, t.sceneId, {
            seed,
            workflow: imageCfg?.workflow,
            image_model: imageCfg?.mode,
          });
          ok++;
        } catch {
          failures.push(`scene background #${t.sceneId + 1}`);
        }
      }
      if (ok) parts.push(`${ok} background${ok > 1 ? 's' : ''}`);
    }

    // Scene music
    if (selected.music && targets.musicTargets.length > 0 && musicCfg) {
      let ok = 0;
      for (const t of targets.musicTargets) {
        try {
          await api.generateSceneMusic(projectId, t.sceneId, {
            force: true,
            mode: musicCfg.musicMode,
            workflow: musicCfg.musicWorkflow,
          });
          ok++;
        } catch {
          failures.push(`scene music #${t.sceneId + 1}`);
        }
      }
      if (ok) parts.push(`${ok} scene music track${ok > 1 ? 's' : ''}`);
    }

    // Narration (single batch call)
    if (selected.narration && targets.narrationTargets.length > 0 && voiceCfg) {
      try {
        await api.batchGenerateNarration(
          projectId,
          targets.narrationTargets.map((t) => t.index),
          {
            tts_method: voiceCfg.method,
            tts_workflow: voiceCfg.method === 'comfyui' ? voiceCfg.workflow : undefined,
            voice: voiceCfg.voice,
          }
        );
        parts.push(`${targets.narrationTargets.length} narration${targets.narrationTargets.length > 1 ? 's' : ''}`);
      } catch {
        failures.push('narration batch');
      }
    }

    setExecuting(false);
    setOptionQueue([]);
    if (parts.length) {
      toast.success(`Queued: ${parts.join(', ')}`, {
        description: failures.length ? `Failed to queue: ${failures.join(', ')}` : 'Track progress in the queue panel.',
      });
    } else {
      toast.error('Nothing was queued', {
        description: failures.length ? `Failed to queue: ${failures.join(', ')}` : undefined,
      });
    }
    onClose();
  };

  const resetAndClose = () => {
    if (executing) return;
    setOptionQueue([]);
    configsRef.current = {};
    onClose();
  };

  // While an option dialog is active the Radix checkbox dialog is unmounted —
  // a Radix modal sets pointer-events:none on <body>, which would make the
  // plain-overlay option dialogs visible but unclickable.
  const showSelectStep = open && optionQueue.length === 0;

  return (
    <>
      {showSelectStep && (
        <Dialog open onOpenChange={(o) => { if (!o) resetAndClose(); }}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ListChecks className="w-5 h-5 text-primary" />
                Batch Generate
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-2 py-1">
              {categories.map((c) => {
                const Icon = c.icon;
                const disabled = c.count === 0;
                return (
                  <label
                    key={c.key}
                    className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                      disabled
                        ? 'opacity-50 cursor-not-allowed border-border/50'
                        : 'cursor-pointer hover:border-primary/40 border-border'
                    } ${selected[c.key] && !disabled ? 'bg-primary/5 border-primary/40' : ''}`}
                  >
                    <input
                      type="checkbox"
                      className="w-4 h-4 accent-primary shrink-0"
                      checked={selected[c.key] && !disabled}
                      disabled={disabled}
                      onChange={(e) => setSelected((prev) => ({ ...prev, [c.key]: e.target.checked }))}
                    />
                    <Icon className="w-5 h-5 text-primary shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{c.label}</p>
                      <p className="text-xs text-muted-foreground truncate">{c.description}</p>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${
                      c.count > 0 ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                    }`}>
                      {c.count}
                    </span>
                  </label>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Only items with prompts are generated — the count shows how many qualify.
            </p>
            <DialogFooter>
              <Button variant="outline" onClick={resetAndClose}>Cancel</Button>
              <Button onClick={handleContinue} disabled={!anySelected}>Continue</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Step 2 overlays — shown sequentially, one per generation kind */}
      {activeOption === 'image' && (
        <GenerationDialog
          isOpen
          onClose={resetAndClose}
          type="image"
          projectId={projectId}
          title="Batch Image Options"
          hidePrompt
          onSubmit={(cfg) => handleOptionDone('image', cfg)}
        />
      )}
      {activeOption === 'music' && (
        <GenerationDialog
          isOpen
          onClose={resetAndClose}
          type="music"
          projectId={projectId}
          title="Batch Music Options"
          hidePrompt
          onSubmit={(cfg) => handleOptionDone('music', cfg)}
        />
      )}
      {activeOption === 'voice' && (
        <VoiceOptionsDialog
          open
          onClose={resetAndClose}
          executing={executing}
          isLast={optionQueue.length === 1}
          onSubmit={(cfg) => handleOptionDone('voice', cfg)}
        />
      )}
    </>
  );
}

// =====================================================================
// Voice options (mirrors the per-scene narration dialog in SceneCard)
// =====================================================================

function VoiceOptionsDialog({
  open,
  onClose,
  executing,
  onSubmit,
  isLast,
}: {
  open: boolean;
  onClose: () => void;
  executing: boolean;
  /** Parent queues execution when the last option dialog submits */
  onSubmit: (cfg: VoiceConfig) => void;
  isLast: boolean;
}) {
  const [method, setMethod] = useState('local');
  const [workflow, setWorkflow] = useState('default');
  const [voice, setVoice] = useState('en-US-AriaNeural');

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Batch Voice Options</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid grid-cols-4 items-center gap-3">
            <label className="text-right text-sm">Method</label>
            <Select value={method} onValueChange={(v) => { setMethod(v); setVoice(v === 'local' ? 'en-US-AriaNeural' : v === 'elevenlabs' ? 'premade/adam' : 'default_female.wav'); }}>
              <SelectTrigger className="col-span-3">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="local">Local TTS (Edge)</SelectItem>
                <SelectItem value="elevenlabs">ElevenLabs API</SelectItem>
                <SelectItem value="comfyui">ComfyUI Workflow</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {method === 'comfyui' && (
            <div className="grid grid-cols-4 items-center gap-3">
              <label className="text-right text-sm">Workflow</label>
              <Select value={workflow} onValueChange={setWorkflow}>
                <SelectTrigger className="col-span-3">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Default TTS</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="grid grid-cols-4 items-center gap-3">
            <label className="text-right text-sm">Voice</label>
            <Select value={voice} onValueChange={setVoice}>
              <SelectTrigger className="col-span-3">
                <SelectValue placeholder="Select Voice" />
              </SelectTrigger>
              <SelectContent>
                {method === 'local' ? (
                  <>
                    <SelectItem value="en-US-AriaNeural">Aria (Female)</SelectItem>
                    <SelectItem value="en-US-GuyNeural">Guy (Male)</SelectItem>
                    <SelectItem value="en-GB-SoniaNeural">Sonia (UK Female)</SelectItem>
                    <SelectItem value="en-GB-RyanNeural">Ryan (UK Male)</SelectItem>
                    <SelectItem value="ur-PK-UzmaNeural">Uzma (Urdu Female)</SelectItem>
                    <SelectItem value="ur-PK-AsadNeural">Asad (Urdu Male)</SelectItem>
                    <SelectItem value="ur-IN-GulNeural">Gul (Urdu India Female)</SelectItem>
                    <SelectItem value="ur-IN-SalmanNeural">Salman (Urdu India Male)</SelectItem>
                  </>
                ) : method === 'elevenlabs' ? (
                  <>
                    <SelectItem value="premade/adam">Adam (Deep Engine)</SelectItem>
                    <SelectItem value="premade/antoni">Antoni (Soothing)</SelectItem>
                    <SelectItem value="premade/bella">Bella (Soft)</SelectItem>
                  </>
                ) : (
                  <>
                    <SelectItem value="default_female.wav">Default Female</SelectItem>
                    <SelectItem value="default_male.wav">Default Male</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => onSubmit({ method, workflow, voice })}
            disabled={executing}
          >
            {executing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Queuing…
              </>
            ) : isLast ? (
              'Start Batch Generation'
            ) : (
              'Next'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
