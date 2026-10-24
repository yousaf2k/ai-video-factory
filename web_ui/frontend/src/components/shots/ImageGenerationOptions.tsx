'use client';

/**
 * Shared image-generation options — the single source of the image mode /
 * workflow / seed / Gemini Web picker UI. Used by the project shot
 * GenerationDialog (type="image") and the Asset library GenerateAssetDialog
 * so both offer exactly the same options.
 *
 * `projectKey` scopes the localStorage persistence the same way the shot
 * dialog scopes it by projectId ("assets" for the library dialog).
 */
import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { useConfig } from "@/hooks/useDirectors";
import {
  GEMINI_MODELS,
  GEMINI_THINKING,
  DEFAULT_GEMINI_MODEL,
  DEFAULT_GEMINI_THINKING,
  decodeLegacyGeminiMode,
} from "@/lib/geminiModes";

export interface ImageGenerationOptionsValue {
  mode: string; // comfyui | gemini | geminiweb | flow
  workflow: string; // comfyui workflow key
  seed: number | "";
  geminiModel: string; // geminiweb picker value
  geminiThinking: string; // geminiweb thinking level
}

/** Fields shared by both dialogs' submit payloads. */
export function imageOptionsToRequest(value: ImageGenerationOptionsValue) {
  return {
    mode: value.mode,
    workflow: value.mode === "comfyui" ? value.workflow : undefined,
    seed: value.mode === "comfyui" && value.seed !== "" ? value.seed : undefined,
    gemini_mode:
      value.mode === "geminiweb"
        ? `${value.geminiModel}|${value.geminiThinking}`
        : undefined,
    gemini_model: value.mode === "geminiweb" ? value.geminiModel : undefined,
    gemini_thinking: value.mode === "geminiweb" ? value.geminiThinking : undefined,
  };
}

/**
 * Owns the image option state. Re-initializes from localStorage + global
 * config whenever `active` turns true (dialog opened on the image type).
 * Every change is persisted back, keyed by `projectKey`.
 */
export function useImageGenerationOptions(projectKey: string, active: boolean) {
  const { data: globalConfig } = useConfig();

  const [mode, setMode] = useState("comfyui");
  const [workflow, setWorkflow] = useState<string>("flux2");
  const [seed, setSeed] = useState<number | "">("");
  const [geminiModel, setGeminiModel] = useState(DEFAULT_GEMINI_MODEL);
  const [geminiThinking, setGeminiThinking] = useState(DEFAULT_GEMINI_THINKING);

  useEffect(() => {
    if (!active) return;

    const savedMode = localStorage.getItem(`image_mode_${projectKey}`) || "comfyui";
    setMode(savedMode);

    const savedWf = localStorage.getItem(`image_workflow_${projectKey}`);
    if (
      savedWf &&
      (!globalConfig?.available_image_workflows ||
        globalConfig.available_image_workflows.includes(savedWf))
    ) {
      setWorkflow(savedWf);
    } else if (globalConfig?.available_image_workflows?.length) {
      setWorkflow(globalConfig.available_image_workflows[0]);
    } else {
      setWorkflow("flux2");
    }

    const legacyPair = decodeLegacyGeminiMode(
      localStorage.getItem(`gemini_mode_${projectKey}`)
    );
    setGeminiModel(
      localStorage.getItem(`gemini_model_${projectKey}`) ||
        legacyPair.model ||
        globalConfig?.geminiweb_model ||
        DEFAULT_GEMINI_MODEL
    );
    setGeminiThinking(
      localStorage.getItem(`gemini_thinking_${projectKey}`) ||
        legacyPair.thinking ||
        globalConfig?.geminiweb_thinking ||
        DEFAULT_GEMINI_THINKING
    );
  }, [active, projectKey, globalConfig]);

  const value: ImageGenerationOptionsValue = {
    mode,
    workflow,
    seed,
    geminiModel,
    geminiThinking,
  };

  return {
    value,
    selectMode: (val: string) => {
      setMode(val);
      localStorage.setItem(`image_mode_${projectKey}`, val);
    },
    selectWorkflow: (val: string) => {
      setWorkflow(val);
      localStorage.setItem(`image_workflow_${projectKey}`, val);
    },
    changeSeed: (val: number | "") => setSeed(val),
    selectGeminiModel: (val: string) => {
      setGeminiModel(val);
      localStorage.setItem(`gemini_model_${projectKey}`, val);
    },
    selectGeminiThinking: (val: string) => {
      setGeminiThinking(val);
      localStorage.setItem(`gemini_thinking_${projectKey}`, val);
    },
  };
}

export function ImageGenerationOptions({
  value,
  onSelectMode,
  onSelectWorkflow,
  onSeedChange,
  onSelectGeminiModel,
  onSelectGeminiThinking,
}: {
  value: ImageGenerationOptionsValue;
  onSelectMode: (val: string) => void;
  onSelectWorkflow: (val: string) => void;
  onSeedChange: (val: number | "") => void;
  onSelectGeminiModel: (val: string) => void;
  onSelectGeminiThinking: (val: string) => void;
}) {
  const { data: globalConfig } = useConfig();

  return (
    <>
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          Generation Mode
        </label>
        <Select value={value.mode} onValueChange={onSelectMode}>
          <SelectTrigger>
            <SelectValue placeholder="Select Mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="comfyui">ComfyUI (Local)</SelectItem>
            <SelectItem value="gemini">Gemini (Cloud)</SelectItem>
            <SelectItem value="geminiweb">
              GeminiWeb - Gemini Web (Browser)
            </SelectItem>
            <SelectItem value="flow">
              Flow - Google Flow (Browser)
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {value.mode === "flow" && (
        <div className="rounded-md border border-border/50 p-3 text-xs">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Model</span>
              <span className="font-medium">
                {globalConfig?.flow_image_model || "Nano Banana 2.1"}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Director Mode</span>
              <span className="font-medium">Off (default)</span>
            </div>
          </div>
        </div>
      )}

      {value.mode === "geminiweb" && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Gemini Model
            </label>
            <Select value={value.geminiModel} onValueChange={onSelectGeminiModel}>
              <SelectTrigger>
                <SelectValue placeholder="Select Gemini Model" />
              </SelectTrigger>
              <SelectContent>
                {GEMINI_MODELS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Extended Thinking
            </label>
            <Select value={value.geminiThinking} onValueChange={onSelectGeminiThinking}>
              <SelectTrigger>
                <SelectValue placeholder="Select Thinking Level" />
              </SelectTrigger>
              <SelectContent>
                {GEMINI_THINKING.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {value.mode === "comfyui" && (
        <>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Workflow
            </label>
            <Select value={value.workflow} onValueChange={onSelectWorkflow}>
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
              value={value.seed}
              onChange={(e) =>
                onSeedChange(e.target.value === "" ? "" : parseInt(e.target.value))
              }
              placeholder="Random"
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              Leave blank for automatic seed (1 for 1st version, random otherwise).
            </p>
          </div>
        </>
      )}
    </>
  );
}
