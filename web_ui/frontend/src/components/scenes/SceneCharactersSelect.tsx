/**
 * SceneCharactersSelect component - Multi-select of story characters for a scene
 *
 * A scene stores its characters as a comma-separated string. The story roster
 * is rendered as toggleable chips; names not on the roster (free text from
 * older scenes or minor characters) are preserved as removable custom chips,
 * and new custom names can be added via the input.
 */
import { useMemo, useState } from "react";
import { Plus, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface SceneCharactersSelectProps {
  value: string;
  onChange: (value: string) => void;
  availableCharacters?: string[];
}

export function SceneCharactersSelect({ value, onChange, availableCharacters = [] }: SceneCharactersSelectProps) {
  const [customInput, setCustomInput] = useState("");
  const selected = useMemo(
    () => value.split(",").map((s) => s.trim()).filter(Boolean),
    [value]
  );

  const toggle = (name: string) => {
    const next = selected.includes(name)
      ? selected.filter((n) => n !== name)
      : [...selected, name];
    onChange(next.join(", "));
  };

  const addCustom = () => {
    const name = customInput.trim();
    if (name && !selected.includes(name)) {
      onChange([...selected, name].join(", "));
    }
    setCustomInput("");
  };

  // Names typed freely that are not part of the story roster
  const custom = selected.filter((name) => !availableCharacters.includes(name));

  return (
    <div className="space-y-2">
      {availableCharacters.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {availableCharacters.map((name) => {
            const isSelected = selected.includes(name);
            return (
              <button
                key={name}
                type="button"
                onClick={() => toggle(name)}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
                  isSelected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:border-primary hover:text-primary"
                )}
              >
                {name}
              </button>
            );
          })}
        </div>
      )}

      {custom.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {custom.map((name) => (
            <span
              key={name}
              className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2.5 py-0.5 text-xs text-foreground"
            >
              {name}
              <button
                type="button"
                onClick={() => toggle(name)}
                className="text-muted-foreground hover:text-destructive"
                title={`Remove ${name}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <Input
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addCustom();
            }
          }}
          placeholder="Add a character not listed above..."
          className="h-8 text-sm"
        />
        <button
          type="button"
          onClick={addCustom}
          disabled={!customInput.trim()}
          className="shrink-0 h-8 w-8 rounded-md border border-border flex items-center justify-center text-muted-foreground hover:border-primary hover:text-primary disabled:opacity-50 disabled:hover:border-border disabled:hover:text-muted-foreground transition-colors"
          title="Add character"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
