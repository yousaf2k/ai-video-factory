/**
 * SceneDialogueEditor - structured editor for a scene's scripted dialogue
 * ({speaker, line, delivery}, in playing order). These lines are spoken on
 * screen: shot planning places every one of them into the scene's shots.
 */
import { useId } from "react";
import { Plus, Trash2 } from "lucide-react";
import { DialogueLine } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface SceneDialogueEditorProps {
  value: DialogueLine[];
  onChange: (dialogue: DialogueLine[]) => void;
  availableCharacters?: string[];
}

// Spoken-word rate the pipeline plans with (core/dialogue.py)
const WORDS_PER_SECOND = 2.5;

export function SceneDialogueEditor({ value, onChange, availableCharacters = [] }: SceneDialogueEditorProps) {
  const listId = useId();

  const update = (index: number, patch: Partial<DialogueLine>) =>
    onChange(value.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)));

  const remove = (index: number) => onChange(value.filter((_, i) => i !== index));

  const addLine = () => {
    // A new line usually answers the previous one, so default to another speaker
    const lastSpeaker = value.length ? value[value.length - 1].speaker : "";
    const nextSpeaker = availableCharacters.find((name) => name !== lastSpeaker) ?? lastSpeaker;
    onChange([...value, { speaker: nextSpeaker, line: "", delivery: "" }]);
  };

  const words = value.reduce(
    (total, entry) => total + (entry.line.trim() ? entry.line.trim().split(/\s+/).length : 0),
    0,
  );

  return (
    <div className="mt-1 space-y-2">
      <datalist id={listId}>
        {availableCharacters.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>

      {value.map((entry, index) => (
        <div key={index} className="rounded-md border border-border/60 bg-background p-2 space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-5 shrink-0 text-right text-xs text-muted-foreground">{index + 1}</span>
            <Input
              list={listId}
              value={entry.speaker}
              onChange={(e) => update(index, { speaker: e.target.value })}
              placeholder="Speaker (character name)"
              className="h-8 text-sm font-semibold"
            />
            <Input
              value={entry.delivery ?? ""}
              onChange={(e) => update(index, { delivery: e.target.value })}
              placeholder="Delivery (whispered, defiant, laughing...)"
              className="h-8 text-sm"
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => remove(index)}
              className="h-8 w-8 shrink-0 text-destructive hover:text-destructive hover:bg-destructive/10"
              title="Remove line"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
          <Textarea
            dir="auto"
            value={entry.line}
            onChange={(e) => update(index, { line: e.target.value })}
            placeholder="The exact words the character says"
            className="min-h-[40px] text-sm"
          />
        </div>
      ))}

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={addLine} className="h-8 gap-1 text-xs">
          <Plus className="w-3.5 h-3.5" />
          Add line
        </Button>
        <span className="text-xs text-muted-foreground">
          {value.length} line{value.length === 1 ? "" : "s"} · {words} words · ~{(words / WORDS_PER_SECOND).toFixed(0)}s of speech
        </span>
      </div>
    </div>
  );
}
