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
  generateSoundFX?: boolean;
  draftLowResVideo?: boolean;
  resolution?: string;
  gemini_mode?: string;
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
  isFLFI2V?: boolean;
  isThenImage?: boolean;
  defaultUseOverride?: boolean;
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
  isFLFI2V = false,
  isThenImage = false,
  defaultUseOverride = false,
}: GenerationDialogProps) {
  const { data: globalConfig } = useConfig();

  // Common State
  const [force, setForce] = useState(false);
  const [mode, setMode] = useState("comfyui");
  const [workflow, setWorkflow] = useState<string>("default");
  const [geminiMode, setGeminiMode] = useState("Fast");
  
  // Image Specific State
  const [seed, setSeed] = useState<number | "">("");
  const [promptOverride, setPromptOverride] = useState(defaultPromptOverride);

  const [appendImagePrompt, setAppendImagePrompt] = useState("default");
  const [generateSoundFX, setGenerateSoundFX] = useState(false);
  const [draftLowResVideo, setDraftLowResVideo] = useState(false);
  const [resolution, setResolution] = useState("720p");
  
  // Override toggle and custom prompt
  const [useOverride, setUseOverride] = useState(defaultUseOverride);
  const DEFAULT_VIDEO_PROMPT = "(cinematic quality, consistent style), slowly departing the scene from the character's appearance, transitioning towards the next scene. focus on the departure motion and environment shift.";
  const DEFAULT_THEN_PROMPT = "Remove only the person standing on the right side of this reference image. No change in background set or environment, no side angle, no profile view, no tilt. Make the left person looking directly into camera in center of the frame with happy, cheerful smiling expressions. Do NOT remove or change any background crew members, equipment, or props. ";

  // Reset or initialize state
  useEffect(() => {
    if (isOpen) {
      setGenerateSoundFX(false);
      setDraftLowResVideo(false);
      setUseOverride(defaultUseOverride);
      setPromptOverride(defaultUseOverride && isThenImage ? DEFAULT_THEN_PROMPT : (defaultPromptOverride || ""));
      
      if (type === "image") {
        const savedImageMode = localStorage.getItem(`image_mode_${projectId}`) || "comfyui";
        setMode(savedImageMode);
        
        const savedImageWf = localStorage.getItem(`image_workflow_${projectId}`);
        if (savedImageWf && (!globalConfig?.available_image_workflows || globalConfig.available_image_workflows.includes(savedImageWf))) {
          setWorkflow(savedImageWf);
        } else if (globalConfig?.available_image_workflows?.length) {
          setWorkflow(globalConfig.available_image_workflows[0]);
        } else {
          setWorkflow("flux2");
        }
        
        const savedGeminiMode = localStorage.getItem(`gemini_mode_${projectId}`) || globalConfig?.geminiweb_default_mode || "Fast";
        setGeminiMode(savedGeminiMode);
      } else {
        const savedVideoMode = localStorage.getItem(`video_mode_${projectId}`) || "comfyui";
        setMode(savedVideoMode);
        
        const savedVideoWf = localStorage.getItem(`video_workflow_${projectId}`);
        if (savedVideoWf && (!globalConfig?.available_video_workflows || globalConfig.available_video_workflows.includes(savedVideoWf))) {
          setWorkflow(savedVideoWf);
        } else if (globalConfig?.available_video_workflows?.length) {
          setWorkflow(globalConfig.available_video_workflows[0]);
        } else {
          setWorkflow("wan22");
        }
        
        const savedAppend = localStorage.getItem(`video_append_${projectId}`);
        if (savedAppend) setAppendImagePrompt(savedAppend);
        
        const savedSoundFX = localStorage.getItem(`video_soundfx_${projectId}`);
        if (savedSoundFX) setGenerateSoundFX(savedSoundFX === "true");
        
        const savedDraft = localStorage.getItem(`video_draft_${projectId}`);
        if (savedDraft) setDraftLowResVideo(savedDraft === "true");

        const savedRes = localStorage.getItem(`video_resolution_${projectId}`);
        if (savedRes) setResolution(savedRes);

        const savedGeminiMode = localStorage.getItem(`gemini_mode_${projectId}`) || globalConfig?.geminiweb_default_mode || "Fast";
        setGeminiMode(savedGeminiMode);
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
      promptOverride: (type === "image" || useOverride) ? (promptOverride || undefined) : undefined,
      appendImagePrompt: type === "video" ? appendImagePrompt : undefined,
      generateSoundFX: type === "video" ? generateSoundFX : undefined,
      draftLowResVideo: type === "video" ? draftLowResVideo : undefined,
      resolution: type === "video" ? resolution : undefined,
      gemini_mode: mode === "geminiweb" ? geminiMode : undefined,
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
                <Select
                  value={mode}
                  onValueChange={(val) => {
                    setMode(val);
                    localStorage.setItem(`image_mode_${projectId}`, val);
                  }}
                >
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

              {mode === "geminiweb" && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Gemini Mode
                  </label>
                  <Select
                    value={geminiMode}
                    onValueChange={(val) => {
                      setGeminiMode(val);
                      localStorage.setItem(`gemini_mode_${projectId}`, val);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Gemini Mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Fast">Fast</SelectItem>
                      <SelectItem value="Thinking">Thinking</SelectItem>
                      <SelectItem value="Pro">Pro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {mode === "comfyui" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Workflow
                    </label>
                    <Select
                      value={workflow}
                      onValueChange={(val) => {
                        setWorkflow(val);
                        localStorage.setItem(`image_workflow_${projectId}`, val);
                      }}
                    >
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
                <div className="space-y-4 pt-4 border-t">
                  {/* Then Prompt Override — ONLY for THEN image of FLFI2V projects */}
                  {isFLFI2V && isThenImage && (
                    <div className="flex items-center gap-2">
                      <Input
                        type="checkbox"
                        id="regen-override-then"
                        checked={useOverride}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setUseOverride(checked);
                          if (checked && (!promptOverride || promptOverride === defaultPromptOverride)) {
                            setPromptOverride(DEFAULT_THEN_PROMPT);
                          } else if (!checked) {
                            setPromptOverride(defaultPromptOverride || "");
                          }
                        }}
                        className="w-4 h-4 mr-2"
                      />
                      <label htmlFor="regen-override-then" className="text-sm font-semibold">
                        Then Prompt Override
                      </label>
                    </div>
                  )}

                  {(!isFLFI2V || !isThenImage || useOverride) && (
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
              
              {mode === "geminiweb" && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Gemini Mode
                  </label>
                  <Select
                    value={geminiMode}
                    onValueChange={(val) => {
                      setGeminiMode(val);
                      localStorage.setItem(`gemini_mode_${projectId}`, val);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Gemini Mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Fast">Fast</SelectItem>
                      <SelectItem value="Thinking">Thinking</SelectItem>
                      <SelectItem value="Pro">Pro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
              
              {mode === "comfyui" && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Video Workflow
                  </label>
                  <Select
                    value={workflow}
                    onValueChange={(val) => {
                      setWorkflow(val);
                      localStorage.setItem(`video_workflow_${projectId}`, val);
                    }}
                  >
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
                <Select
                  value={appendImagePrompt}
                  onValueChange={(val) => {
                    setAppendImagePrompt(val);
                    localStorage.setItem(`video_append_${projectId}`, val);
                  }}
                >
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

              <div className="flex items-center gap-2">
                <Input
                  type="checkbox"
                  id="regen-soundfx"
                  checked={generateSoundFX}
                  onChange={(e) => {
                    setGenerateSoundFX(e.target.checked);
                    localStorage.setItem(`video_soundfx_${projectId}`, e.target.checked.toString());
                  }}
                  className="w-4 h-4 mr-2"
                />
                <label htmlFor="regen-soundfx" className="text-sm">
                  🔊 Generate Sound FX after video
                </label>
              </div>

              <div className="space-y-1 mt-4 border-t pt-4">
                <label className="block text-[10px] font-medium text-muted-foreground mb-1">
                  Video Resolution
                </label>
                <Select
                  value={resolution}
                  onValueChange={(val) => {
                    setResolution(val);
                    localStorage.setItem(`video_resolution_${projectId}`, val);
                  }}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select Resolution" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="480p">480p (Fast)</SelectItem>
                    <SelectItem value="720p">720p (HD)</SelectItem>
                    <SelectItem value="1080p">1080p (Full HD)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Departure Prompt Override — ONLY for FLFI2V projects */}
              {isFLFI2V && (
                <div className="space-y-4 pt-4 border-t">
                  <div className="flex items-center gap-2">
                    <Input
                      type="checkbox"
                      id="regen-override"
                      checked={useOverride}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setUseOverride(checked);
                        if (checked && !promptOverride) {
                          setPromptOverride(DEFAULT_VIDEO_PROMPT);
                        }
                      }}
                      className="w-4 h-4 mr-2"
                    />
                    <label htmlFor="regen-override" className="text-sm font-semibold">
                      Override the prompt
                    </label>
                  </div>

                  {useOverride && (
                    <div className="space-y-1">
                      <label className="text-[10px] font-medium text-muted-foreground">
                        Custom Departure Prompt
                      </label>
                      <Textarea
                        className="text-xs min-h-[80px]"
                        value={promptOverride}
                        onChange={(e) => setPromptOverride(e.target.value)}
                        placeholder="Enter custom departure/motion prompt..."
                      />
                      <p className="text-[10px] text-muted-foreground italic">
                        If unchecked, the prompt from shot JSON will be used.
                      </p>
                    </div>
                  )}
                </div>
              )}
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
