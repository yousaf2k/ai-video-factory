/**
 * AddSceneDialog component - Manual scene creation form
 *
 * Collects the scene fields up front (matching the SceneCard edit form)
 * instead of appending a hard-coded placeholder. The parent performs the
 * save (whole-story PUT) and reports success so the dialog can close.
 */
import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SceneCharactersSelect } from "@/components/scenes/SceneCharactersSelect";
import { Scene } from "@/types";

interface AddSceneDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (scene: Scene) => Promise<boolean>;
  nextSceneNumber: number;
  availableCharacters?: string[];
}

const EMPTY_FORM = {
  location: "",
  characters: "",
  action: "",
  emotion: "",
  narration: "",
  scene_duration: "30",
  set_prompt: "",
  music_prompt: "",
};

export function AddSceneDialog({ open, onOpenChange, onAdd, nextSceneNumber, availableCharacters }: AddSceneDialogProps) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  // Reset the form every time the dialog is opened
  useEffect(() => {
    if (open) {
      setForm(EMPTY_FORM);
      setSubmitting(false);
    }
  }, [open]);

  const location = form.location.trim();
  const action = form.action.trim();
  const duration = parseInt(form.scene_duration, 10);
  const canSubmit = location.length > 0 && action.length > 0 && !Number.isNaN(duration) && duration >= 5;

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;

    const newScene: Scene = {
      location,
      characters: form.characters.trim(),
      action,
      emotion: form.emotion.trim(),
      narration: form.narration.trim(),
      scene_duration: duration,
    };
    if (form.set_prompt.trim()) newScene.set_prompt = form.set_prompt.trim();
    if (form.music_prompt.trim()) newScene.music_prompt = form.music_prompt.trim();

    setSubmitting(true);
    const success = await onAdd(newScene);
    setSubmitting(false);

    if (success) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Scene {nextSceneNumber}</DialogTitle>
          <DialogDescription>
            Fill in the details for the new scene. It will be appended to the end of the story — drag scenes to reorder afterwards.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 py-2">
          <div>
            <label className="text-xs text-muted-foreground">
              Location <span className="text-destructive">*</span>
            </label>
            <Input
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="mt-1 h-8 text-sm"
              placeholder="e.g. Rain-soaked city street at night"
              autoFocus
            />
          </div>

          <div className="md:col-span-2">
            <label className="text-xs text-muted-foreground">Characters (click to select from the story cast)</label>
            <div className="mt-1">
              <SceneCharactersSelect
                value={form.characters}
                onChange={(characters) => setForm({ ...form, characters })}
                availableCharacters={availableCharacters}
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground">
              Action <span className="text-destructive">*</span>
            </label>
            <Input
              value={form.action}
              onChange={(e) => setForm({ ...form, action: e.target.value })}
              className="mt-1 h-8 text-sm"
              placeholder="e.g. Maya searches the alley for clues"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground">Emotion</label>
            <Input
              value={form.emotion}
              onChange={(e) => setForm({ ...form, emotion: e.target.value })}
              className="mt-1 h-8 text-sm"
              placeholder="e.g. Tense, foreboding"
            />
          </div>

          <div className="md:col-span-2">
            <label className="text-xs text-muted-foreground">Narration</label>
            <Textarea
              value={form.narration}
              onChange={(e) => setForm({ ...form, narration: e.target.value })}
              className="mt-1 min-h-[60px] text-sm"
              placeholder="Voice-over text for this scene..."
            />
          </div>

          <div className="md:col-span-2">
            <label className="text-xs text-muted-foreground">Set Prompt (for background generation)</label>
            <Textarea
              value={form.set_prompt}
              onChange={(e) => setForm({ ...form, set_prompt: e.target.value })}
              className="mt-1 min-h-[40px] text-sm"
              placeholder="Describe the background explicitly..."
            />
          </div>

          <div className="md:col-span-2">
            <label className="text-xs text-muted-foreground">Music Prompt (scene background music)</label>
            <Textarea
              value={form.music_prompt}
              onChange={(e) => setForm({ ...form, music_prompt: e.target.value })}
              className="mt-1 min-h-[40px] text-sm"
              placeholder="Describe the music: warm hopeful strings, gentle piano, 70 BPM..."
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground">Duration (seconds)</label>
            <Input
              type="number"
              value={form.scene_duration}
              onChange={(e) => setForm({ ...form, scene_duration: e.target.value })}
              className="mt-1 h-8 text-sm"
              min="5"
            />
            {form.scene_duration !== "" && (Number.isNaN(duration) || duration < 5) && (
              <p className="mt-1 text-xs text-destructive">Duration must be at least 5 seconds.</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || submitting}>
            {submitting ? "Adding..." : "Add Scene"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
