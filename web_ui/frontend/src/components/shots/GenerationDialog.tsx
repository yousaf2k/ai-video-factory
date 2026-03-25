import React, { useState, useEffect } from "react";
import { X, RotateCw } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useConfig } from "@/hooks/useAgents";

export type GenerationType = "image" | "video";

export interface GenerationConfig {
  force?: boolean;
  mode?: string;
  workflow?: string;
  seed?: number | "";
  promptOverride?: string;
  appendImagePrompt?: string; // e.g. "default", "none", "start", "end"
}

interface GenerationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  type: GenerationType;
  projectId: string; // for caching local storage video mode if desired
  isPending?: boolean;
  onSubmit: (config: GenerationConfig) => void;
  title?: string;
  defaultPromptOverride?: string;
  hidePrompt?: boolean;
}

export function GenerationDialog({
  isOpen,
  onClose,
  type,
  projectId,
  isPending = false,
  onSubmit,
  title,
  defaultPromptOverride = "",
  hidePrompt = false,
}: GenerationDialogProps) {
  const { data: globalConfig } = useConfig();

  // Common State
  const [force, setForce] = useState(false);
  const [mode, setMode] = useState("comfyui");
  const [workflow, setWorkflow] = useState<string>("default");
  
  // Image Specific State
  const [seed, setSeed] = useState<number | "">("");
  const [promptOverride, setPromptOverride] = useState(defaultPromptOverride);

  // Video Specific State
  const [appendImagePrompt, setAppendImagePrompt] = useState("default");

  // Reset or initialize state
  useEffect(() => {
    if (isOpen) {
      setForce(false);
      setSeed("");
      setPromptOverride(defaultPromptOverride);
      setAppendImagePrompt("default");
      
      if (type === "image") {
        setMode("comfyui");
        if (globalConfig?.available_image_workflows?.length) {
          setWorkflow(globalConfig.available_image_workflows[0]);
        } else {
          setWorkflow("flux2");
        }
      } else {
        const savedVideoMode = localStorage.getItem(`video_mode_${projectId}`) || "comfyui";
        setMode(savedVideoMode);
        if (globalConfig?.available_video_workflows?.length) {
          setWorkflow(globalConfig.available_video_workflows[0]);
        } else {
          setWorkflow("wan22");
        }
      }
    }
  }, [isOpen, type, projectId, globalConfig]);

  if (!isOpen) return null;

  const handleSubmit = () => {
    onSubmit({
      force,
      mode,
      workflow,
      seed: type === "image" ? seed : undefined,
      promptOverride: type === "image" ? promptOverride : undefined,
      appendImagePrompt: type === "video" ? appendImagePrompt : undefined,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-sm w-full p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-lg font-semibold mb-4">
          {title || `Generate ${type === "image" ? "Image" : "Video"}`}
        </h2>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Input
              type="checkbox"
              id="regen-force"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="w-4 h-4 mr-2"
            />
            <label htmlFor="regen-force" className="text-sm">
              Force generation (ignore cache)
            </label>
          </div>

          {type === "image" && (
            <>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Generation Mode
                </label>
                <Select value={mode} onValueChange={setMode}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select Mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="comfyui">ComfyUI (Local)</SelectItem>
                    <SelectItem value="gemini">Gemini (Cloud)</SelectItem>
                    <SelectItem value="geminiweb">
                      GeminiWeb - Gemini Web (Browser)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {mode === "comfyui" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Workflow
                    </label>
                    <Select value={workflow} onValueChange={setWorkflow}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select Workflow" />
                      </SelectTrigger>
                      <SelectContent>
                        {globalConfig?.available_image_workflows?.map((wf) => (
                          <SelectItem key={wf} value={wf}>
                            {wf.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                          </SelectItem>
                        )) || (
                          <>
                            <SelectItem value="flux2">Flux 2</SelectItem>
                            <SelectItem value="flux">Flux</SelectItem>
                            <SelectItem value="sdxl">SDXL</SelectItem>
                            <SelectItem value="default">Default</SelectItem>
                          </>
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Noise Seed (Optional)
                    </label>
                    <Input
                      type="number"
                      value={seed}
                      onChange={(e) =>
                        setSeed(e.target.value === "" ? "" : parseInt(e.target.value))
                      }
                      placeholder="Random"
                    />
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Leave blank for automatic seed (1 for 1st version, random otherwise).
                    </p>
                  </div>
                </>
              )}

              {/* Prompt Override — visible for ALL image modes */}
              {!hidePrompt && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Prompt Override
                  </label>
                  <Textarea
                    value={promptOverride}
                    onChange={(e) => setPromptOverride(e.target.value)}
                    rows={4}
                    placeholder="Leave blank to use saved prompt…"
                    className="text-xs resize-y"
                  />
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Edits here are one-time only — they won't change the saved prompt.
                  </p>
                </div>
              )}
            </>
          )}

          {type === "video" && (
            <>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Generation Mode
                </label>
                <Select
                  value={mode}
                  onValueChange={(val) => {
                    setMode(val);
                    localStorage.setItem(`video_mode_${projectId}`, val);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="comfyui">ComfyUI (Local)</SelectItem>
                    <SelectItem value="geminiweb">
                      GeminiWeb - Gemini Web (Browser)
                    </SelectItem>
                    <SelectItem value="flowweb">
                      FlowWeb - Google Flow (Browser)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {mode === "comfyui" && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Video Workflow
                  </label>
                  <Select value={workflow} onValueChange={setWorkflow}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Video Workflow" />
                    </SelectTrigger>
                    <SelectContent>
                      {globalConfig?.available_video_workflows?.map((wf) => (
                        <SelectItem key={wf} value={wf}>
                          {wf}
                        </SelectItem>
                      )) || (
                        <SelectItem value="wan22">Wan 2.2</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="space-y-2 mt-4 border-t pt-4">
                <label className="block text-[10px] font-medium text-muted-foreground mb-1">
                  Append Image Prompt to Motion Prompt
                </label>
                <Select value={appendImagePrompt} onValueChange={setAppendImagePrompt}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select Position" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Use Config Default</SelectItem>
                    <SelectItem value="none">None (Do Not Append)</SelectItem>
                    <SelectItem value="start">Start (Image + Motion)</SelectItem>
                    <SelectItem value="end">End (Motion + Image)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isPending}
            className="flex items-center gap-2"
          >
            {isPending ? (
              <>
                <RotateCw className="w-3 h-3 animate-spin" />
                Processing...
              </>
            ) : (
              "Start"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
