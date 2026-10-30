/**
 * Global Configuration Page
 *
 * Renders every env-backed setting from the backend registry
 * (web_ui/backend/api/config_api.py `_CONFIG_FIELDS`) in collapsible
 * sections grouped by concern. One Save button writes the whole form.
 */
"use client";

import { useState, useMemo } from "react";
import { toast } from "sonner";
import { useConfig, useUpdateConfig } from "@/hooks/useDirectors";
import {
  Save,
  RefreshCw,
  ArrowLeft,
  Globe,
  Brain,
  Clapperboard,
  Crop,
  Server,
  Mic,
  Gauge,
  Droplets,
  FolderOpen,
  Network,
  ChevronsUpDown,
  KeyRound,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Collapsible } from "@/components/ui/collapsible";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GEMINI_MODELS, GEMINI_THINKING } from "@/lib/geminiModes";
import { FLOW_MODELS, FLOW_OUTPUTS, DEFAULT_FLOW_MODEL, DEFAULT_FLOW_OUTPUTS } from "@/lib/flowModes";

// ---------------------------------------------------------------------------
// Editable field keys (must match the backend _CONFIG_FIELDS registry) and
// their client-side fallbacks, used to initialize the form.
// ---------------------------------------------------------------------------
const EDITABLE_KEYS = [
  "llm_provider", "gemini_model", "gemini_base_url", "openai_model",
  "openai_base_url", "qwen_model", "qwen_base_url", "kimi_model",
  "kimi_base_url", "zhipu_model", "zhipu_base_url",
  "deepseek_model", "deepseek_base_url", "ollama_base_url", "ollama_model",
  "lmstudio_base_url", "lmstudio_model",
  "llm_max_tokens", "shot_generation_batch_size", "max_parallel_batch_threads",
  // Per-provider generation tuning overrides (blank = inherit the global value)
  ...(["gemini", "openai", "zhipu", "qwen", "kimi", "deepseek", "ollama", "lmstudio"].flatMap(
    (p) => [`${p}_max_tokens`, `${p}_shot_batch_size`, `${p}_parallel_batch_threads`]
  )),
  "gemini_api_key", "openai_api_key", "zhipu_api_key", "qwen_api_key",
  "kimi_api_key", "deepseek_api_key", "elevenlabs_api_key",
  "image_generation_mode", "image_workflow", "video_generation_mode",
  "video_workflow", "soundfx_workflow", "prompt_mode",
  "comfy_url", "comfy_output_dir", "comfy_input_dir",
  "image_aspect_ratio", "image_resolution", "video_aspect_ratio",
  "video_resolution", "target_video_length", "default_shot_length",
  "generate_narration", "tts_method", "tts_voice", "elevenlabs_model",
  "elevenlabs_stability", "elevenlabs_similarity",
  "concurrent_comfyui_limit", "concurrent_gemini_limit",
  "concurrent_geminiweb_limit", "concurrent_default_limit",
  "concurrent_generation_limit", "flow_project_concurrency",
  "video_render_timeout", "image_generation_max_retries",
  "image_generation_retry_delay", "continue_on_partial_image_failure",
  "playwright_browser", "geminiweb_model", "geminiweb_thinking",
  "geminiweb_timeout", "geminiweb_chat_lock_timeout", "geminiweb_chrome_profile",
  "flowweb_url", "flowweb_timeout", "flow_image_model", "flow_image_outputs",
  "watermark_removal_method", "gemini_watermark_tool_image",
  "gemini_watermark_tool_video",
  "output_dir", "asset_library_dirs",
  "web_ui_enabled", "backend_host", "backend_port", "backend_bind_host",
  "frontend_host", "frontend_port", "frontend_bind_host", "web_ui_cors_origins",
] as const;

// Numeric fields: blank inputs are dropped from the payload instead of
// overwriting values with 0.
const NUMERIC_KEYS = new Set([
  "llm_max_tokens", "shot_generation_batch_size", "max_parallel_batch_threads",
  "target_video_length", "default_shot_length", "elevenlabs_stability",
  "elevenlabs_similarity", "concurrent_comfyui_limit", "concurrent_gemini_limit",
  "concurrent_geminiweb_limit", "concurrent_default_limit",
  "concurrent_generation_limit", "flow_project_concurrency",
  "video_render_timeout", "image_generation_max_retries",
  "image_generation_retry_delay", "geminiweb_timeout",
  "geminiweb_chat_lock_timeout", "flowweb_timeout",
  "backend_port", "frontend_port",
]);

// Secret fields: sent as-is; the backend ignores empty values ("keep key").
const SECRET_KEYS = new Set([
  "gemini_api_key", "openai_api_key", "zhipu_api_key", "qwen_api_key",
  "kimi_api_key", "deepseek_api_key", "elevenlabs_api_key",
]);

const DEFAULTS: Record<string, string | number | boolean> = {
  llm_provider: "gemini",
  gemini_model: "gemini-3.5-flash-lite",
  openai_model: "gpt-4o",
  qwen_model: "qwen-max",
  kimi_model: "kimi-labs",
  zhipu_model: "glm-5.3",
  deepseek_model: "deepseek-chat",
  deepseek_base_url: "https://api.deepseek.com",
  ollama_base_url: "http://localhost:11434",
  ollama_model: "llama2",
  lmstudio_base_url: "http://localhost:1234",
  lmstudio_model: "lmstudio-community/qwen2",
  llm_max_tokens: 16384,
  shot_generation_batch_size: 1,
  max_parallel_batch_threads: 5,
  image_generation_mode: "comfyui",
  video_generation_mode: "comfyui",
  prompt_mode: "video",
  comfy_url: "http://127.0.0.1:8188",
  image_aspect_ratio: "16:9",
  image_resolution: "2048",
  video_aspect_ratio: "16:9",
  video_resolution: "1280",
  target_video_length: 600,
  default_shot_length: 5,
  generate_narration: false,
  tts_method: "local",
  tts_voice: "en-US-AriaNeural",
  elevenlabs_model: "eleven_multilingual_v2",
  elevenlabs_stability: 0.5,
  elevenlabs_similarity: 0.75,
  concurrent_comfyui_limit: 1,
  concurrent_gemini_limit: 2,
  concurrent_geminiweb_limit: 1,
  concurrent_default_limit: 1,
  concurrent_generation_limit: 1,
  flow_project_concurrency: 2,
  video_render_timeout: 900,
  image_generation_max_retries: 3,
  image_generation_retry_delay: 5,
  continue_on_partial_image_failure: true,
  playwright_browser: "chromium",
  geminiweb_model: "3.8 Flash",
  geminiweb_thinking: "Low",
  geminiweb_timeout: 300,
  geminiweb_chat_lock_timeout: 600,
  flowweb_url: "https://flow.google.com/",
  flowweb_timeout: 300,
  flow_image_model: DEFAULT_FLOW_MODEL,
  flow_image_outputs: DEFAULT_FLOW_OUTPUTS,
  watermark_removal_method: "builtin",
  output_dir: "output",
  asset_library_dirs: "output/Assets",
  web_ui_enabled: true,
  backend_host: "127.0.0.1",
  backend_port: 8000,
  backend_bind_host: "0.0.0.0",
  frontend_host: "127.0.0.1",
  frontend_port: 3000,
  frontend_bind_host: "0.0.0.0",
  web_ui_cors_origins: "",
};

const ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"];
const IMAGE_RESOLUTIONS = ["512", "1024", "1280", "2048"];
const VIDEO_RESOLUTIONS = ["512", "720", "1024", "1080", "1280", "2048"];
const TTS_METHODS = [
  { value: "local", label: "Edge-TTS (Local, Free)" },
  { value: "elevenlabs", label: "ElevenLabs (Cloud)" },
  { value: "comfyui", label: "ComfyUI Workflow" },
];
const ELEVENLABS_MODELS = [
  { value: "eleven_multilingual_v2", label: "Multilingual v2" },
  { value: "eleven_turbo_v2", label: "Turbo v2" },
  { value: "eleven_monolingual_v1", label: "Monolingual v1" },
];

type FormValue = string | number | boolean;
type FormData = Record<string, FormValue>;

// ---------------------------------------------------------------------------
// Field components (module-level so inputs keep focus across renders)
// ---------------------------------------------------------------------------

interface FieldShellProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
  disabled?: boolean;
}

function FieldShell({ label, hint, children, disabled }: FieldShellProps) {
  return (
    <div className={disabled ? "opacity-60" : undefined}>
      <label className="block text-sm font-medium mb-1">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground mt-1">{hint}</p>}
    </div>
  );
}

interface TextInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  disabled?: boolean;
  type?: string;
}

function TextInput({ label, value, onChange, placeholder, hint, disabled, type = "text" }: TextInputProps) {
  return (
    <FieldShell label={label} hint={hint} disabled={disabled}>
      <Input
        type={type}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </FieldShell>
  );
}

interface NumberInputProps {
  label: string;
  value: number | string;
  onChange: (value: number | "") => void;
  hint?: string;
  step?: number;
  min?: number;
  max?: number;
}

function NumberInput({ label, value, onChange, hint, step, min, max }: NumberInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <Input
        type="number"
        value={value ?? ""}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
      />
    </FieldShell>
  );
}

interface SelectInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  hint?: string;
  placeholder?: string;
  disabled?: boolean;
}

function SelectInput({ label, value, onChange, options, hint, placeholder, disabled }: SelectInputProps) {
  return (
    <FieldShell label={label} hint={hint} disabled={disabled}>
      <Select
        value={value || undefined}
        onValueChange={(v) => {
          // Radix's hidden native select can emit a spurious "" when the
          // controlled value changes; no real option has an empty value
          if (v !== "") onChange(v);
        }}
        disabled={disabled}
      >
        <SelectTrigger>
          <SelectValue placeholder={placeholder || "Select..."} />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldShell>
  );
}

interface SwitchInputProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
}

function SwitchInput({ label, checked, onChange, hint }: SwitchInputProps) {
  return (
    <div>
      <div className="flex items-center gap-3">
        <Switch checked={!!checked} onCheckedChange={onChange} />
        <label className="text-sm font-medium">{label}</label>
      </div>
      {hint && <p className="text-[10px] text-muted-foreground mt-1">{hint}</p>}
    </div>
  );
}

interface SecretInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  isSet?: boolean;
  hint?: string;
}

function SecretInput({ label, value, onChange, isSet, hint }: SecretInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <div className="relative">
        <Input
          type="password"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Paste new key to update..."
        />
        {isSet && !value && (
          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-green-600 dark:text-green-400 flex items-center gap-1">
            <KeyRound className="w-3 h-3" />
            Configured
          </span>
        )}
      </div>
    </FieldShell>
  );
}

function SubHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground border-t border-border/30 pt-4 first:border-t-0 first:pt-0">
      {children}
    </h3>
  );
}

function titleCase(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const SECTION_IDS = [
  "llm", "engines", "media", "comfyui", "audio",
  "performance", "browser", "watermark", "paths", "server",
];

export default function ConfigPage() {
  const router = useRouter();
  const { data: config, isLoading, error } = useConfig();
  const updateConfigMutation = useUpdateConfig();
  const [isLaunchingBrowser, setIsLaunchingBrowser] = useState(false);
  const [openSections, setOpenSections] = useState<Set<string>>(
    () => new Set(["llm", "engines"])
  );
  // Only user modifications are tracked; the rendered form is derived from
  // the server data so the inputs never see a value transition after mount
  const [edits, setEdits] = useState<FormData>({});

  const serverData = useMemo<FormData | null>(() => {
    if (!config) return null;
    const next: FormData = {};
    for (const key of EDITABLE_KEYS) {
      const incoming = (config as unknown as Record<string, FormValue | undefined>)[key];
      next[key] = incoming ?? DEFAULTS[key] ?? "";
    }
    return next;
  }, [config]);

  const cfg: FormData = serverData ? { ...serverData, ...edits } : {};

  const set = (key: string, value: FormValue) => {
    setEdits((prev) => {
      // Clearing a secret or numeric field reverts to the server value
      if (value === "" && (SECRET_KEYS.has(key) || NUMERIC_KEYS.has(key))) {
        const { [key]: _dropped, ...rest } = prev;
        return rest;
      }
      return { ...prev, [key]: value };
    });
  };

  const toggleSection = (id: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const allOpen = openSections.size === SECTION_IDS.length;

  const dirty =
    !!serverData &&
    Object.entries(edits).some(
      ([key, value]) => String(value) !== String((serverData as FormData)[key] ?? "")
    );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Only send fields that actually differ from the server values;
      // blank numeric inputs and cleared secrets are dropped
      const payload: Record<string, FormValue> = {};
      for (const [key, value] of Object.entries(edits)) {
        if (SECRET_KEYS.has(key) && String(value).trim() === "") continue;
        if (value === "" && NUMERIC_KEYS.has(key)) continue;
        if (serverData && String(value) === String((serverData as FormData)[key] ?? "")) continue;
        payload[key] = value;
      }
      if (Object.keys(payload).length === 0) {
        toast.info("No changes to save.");
        return;
      }
      await updateConfigMutation.mutateAsync(payload);
      setEdits({});
      toast.success("Configuration updated successfully!");
    } catch (err) {
      console.error("Failed to update config:", err);
      toast.error("Failed to update configuration.");
    }
  };

  const handleLaunchBrowser = async () => {
    setIsLaunchingBrowser(true);
    try {
      const data = await api.launchBrowser();
      toast.success(data.message || "Browser launched successfully!");
    } catch (err: any) {
      console.error("Error launching browser:", err);
      const detail = err.response?.data?.detail || err.message;
      toast.error(`Error launching browser: ${detail}`);
    } finally {
      setIsLaunchingBrowser(false);
    }
  };

  const [llmTest, setLlmTest] = useState<{
    running: boolean;
    status?: string;
    model?: string;
    reply?: string;
    error?: string;
    elapsed_ms?: number;
  }>({ running: false });

  const handleTestLlm = async () => {
    setLlmTest({ running: true });
    try {
      // Field names are uniform: {provider}_model / _api_key / _base_url.
      // Blank values fall back to the saved config server-side.
      const data = await api.testLlmConfig({
        provider: selectedProvider,
        model: String(cfg[`${selectedProvider}_model`] ?? ""),
        api_key: String(cfg[`${selectedProvider}_api_key`] ?? ""),
        base_url: String(cfg[`${selectedProvider}_base_url`] ?? ""),
      });
      setLlmTest({ running: false, ...data });
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message;
      setLlmTest({ running: false, status: "error", error: detail });
    }
  };

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 text-red-500">
        Error loading configuration.
      </div>
    );
  }

  // Don't mount the form until server values are ready — mounting selects
  // with fallback values and swapping them later triggers spurious Radix
  // Select change events
  if (!serverData || isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        Loading configuration...
      </div>
    );
  }

  // The model selector beside the provider dropdown is provider-specific, as
  // are the API key / base URL fields below it (local providers have no key)
  const selectedProvider = String(cfg.llm_provider || "gemini");
  const selectedProviderUsesApiKey = !["ollama", "lmstudio"].includes(selectedProvider);

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="max-w-5xl mx-auto mb-6 flex items-center gap-3">
        <Button variant="outline" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Global Configuration</h1>
          <p className="text-muted-foreground text-sm">
            Environment settings from <code>.env</code> — grouped and collapsible. Changes apply live and persist across restarts.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() =>
            setOpenSections(allOpen ? new Set() : new Set(SECTION_IDS))
          }
        >
          <ChevronsUpDown className="w-4 h-4 mr-1" />
          {allOpen ? "Collapse all" : "Expand all"}
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="max-w-5xl mx-auto space-y-4 pb-28">
        {/* ------------------------------------------------ LLM Providers */}
        <Collapsible
          title="LLM Providers"
          icon={<Brain className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-primary"
          summary={`Provider: ${String(cfg.llm_provider || "gemini")}`}
          open={openSections.has("llm")}
          onOpenChange={() => toggleSection("llm")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectInput
              label="LLM Provider"
              value={selectedProvider}
              onChange={(v) => set("llm_provider", v)}
              options={[
                { value: "gemini", label: "Google Gemini" },
                { value: "openai", label: "OpenAI (ChatGPT)" },
                { value: "zhipu", label: "Zhipu AI" },
                { value: "deepseek", label: "DeepSeek" },
                { value: "qwen", label: "Qwen (Alibaba Cloud)" },
                { value: "kimi", label: "Kimi (Moonshot)" },
                { value: "ollama", label: "Ollama (Local)" },
                { value: "lmstudio", label: "LM Studio (Local)" },
              ]}
              hint="Provider used for story and shot generation."
            />
            {selectedProvider === "gemini" && (
              <SelectInput
                label="Gemini Text Model"
                value={String(cfg.gemini_model || "gemini-3.5-flash-lite")}
                onChange={(v) => set("gemini_model", v)}
                options={[
                  { value: "gemini-3.5-flash-lite", label: "gemini-3.5-flash-lite (fast)" },
                  { value: "gemini-3-pro-preview", label: "gemini-3-pro-preview (quality)" },
                ]}
                hint="gemini-3.5-flash-lite for speed, gemini-3-pro-preview for quality."
              />
            )}
            {selectedProvider === "zhipu" && (
              <SelectInput
                label="Zhipu Model"
                value={String(cfg.zhipu_model || "glm-5.3")}
                onChange={(v) => set("zhipu_model", v)}
                options={[
                  { value: "glm-5.3", label: "GLM-5.3 (quality)" },
                  { value: "glm-5.3-flash", label: "GLM-5.3-Flash (fast)" },
                ]}
                hint="GLM-5.3 for quality, GLM-5.3-Flash for speed."
              />
            )}
            {selectedProvider === "openai" && (
              <TextInput
                label="OpenAI Model"
                value={String(cfg.openai_model || "gpt-4o")}
                onChange={(v) => set("openai_model", v)}
                placeholder="gpt-4o"
              />
            )}
            {selectedProvider === "deepseek" && (
              <TextInput
                label="DeepSeek Model"
                value={String(cfg.deepseek_model || "deepseek-chat")}
                onChange={(v) => set("deepseek_model", v)}
                placeholder="deepseek-chat"
                hint="deepseek-chat (V3) or deepseek-reasoner (R1)."
              />
            )}
            {selectedProvider === "qwen" && (
              <TextInput
                label="Qwen Model"
                value={String(cfg.qwen_model || "qwen-max")}
                onChange={(v) => set("qwen_model", v)}
                placeholder="qwen-max"
              />
            )}
            {selectedProvider === "kimi" && (
              <TextInput
                label="Kimi Model"
                value={String(cfg.kimi_model || "kimi-labs")}
                onChange={(v) => set("kimi_model", v)}
                placeholder="kimi-labs"
              />
            )}
            {selectedProvider === "ollama" && (
              <TextInput
                label="Ollama Model"
                value={String(cfg.ollama_model || "llama2")}
                onChange={(v) => set("ollama_model", v)}
                placeholder="llama2"
              />
            )}
            {selectedProvider === "lmstudio" && (
              <TextInput
                label="LM Studio Model"
                value={String(cfg.lmstudio_model || "lmstudio-community/qwen2")}
                onChange={(v) => set("lmstudio_model", v)}
                placeholder="lmstudio-community/qwen2"
              />
            )}
          </div>

          {selectedProviderUsesApiKey && (
            <p className="text-xs text-muted-foreground italic">
              Keys are saved to the <code>.env</code> file. Leave blank to keep existing values.
            </p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {selectedProvider === "gemini" && (
              <>
                <TextInput
                  label="Gemini Base URL"
                  value={String(cfg.gemini_base_url || "")}
                  onChange={(v) => set("gemini_base_url", v)}
                  placeholder="https://generativelanguage.googleapis.com"
                />
                <SecretInput
                  label="Gemini API Key"
                  value={String(cfg.gemini_api_key || "")}
                  onChange={(v) => set("gemini_api_key", v)}
                  isSet={config?.gemini_api_key_set}
                />
              </>
            )}
            {selectedProvider === "openai" && (
              <>
                <TextInput
                  label="OpenAI Base URL"
                  value={String(cfg.openai_base_url || "")}
                  onChange={(v) => set("openai_base_url", v)}
                  placeholder="https://api.openai.com/v1"
                />
                <SecretInput
                  label="OpenAI API Key"
                  value={String(cfg.openai_api_key || "")}
                  onChange={(v) => set("openai_api_key", v)}
                  isSet={config?.openai_api_key_set}
                />
              </>
            )}
            {selectedProvider === "zhipu" && (
              <>
                <TextInput
                  label="Zhipu Base URL"
                  value={String(cfg.zhipu_base_url || "")}
                  onChange={(v) => set("zhipu_base_url", v)}
                  placeholder="https://api.z.ai/api/coding/paas/v4"
                />
                <SecretInput
                  label="Zhipu API Key"
                  value={String(cfg.zhipu_api_key || "")}
                  onChange={(v) => set("zhipu_api_key", v)}
                  isSet={config?.zhipu_api_key_set}
                />
              </>
            )}
            {selectedProvider === "qwen" && (
              <>
                <TextInput
                  label="Qwen Base URL"
                  value={String(cfg.qwen_base_url || "")}
                  onChange={(v) => set("qwen_base_url", v)}
                  placeholder="https://dashscope.aliyuncs.com/api/v1"
                />
                <SecretInput
                  label="Qwen API Key"
                  value={String(cfg.qwen_api_key || "")}
                  onChange={(v) => set("qwen_api_key", v)}
                  isSet={config?.qwen_api_key_set}
                />
              </>
            )}
            {selectedProvider === "kimi" && (
              <>
                <TextInput
                  label="Kimi Base URL"
                  value={String(cfg.kimi_base_url || "")}
                  onChange={(v) => set("kimi_base_url", v)}
                  placeholder="https://api.moonshot.cn/v1"
                />
                <SecretInput
                  label="Kimi API Key"
                  value={String(cfg.kimi_api_key || "")}
                  onChange={(v) => set("kimi_api_key", v)}
                  isSet={config?.kimi_api_key_set}
                />
              </>
            )}
            {selectedProvider === "deepseek" && (
              <>
                <TextInput
                  label="DeepSeek Base URL"
                  value={String(cfg.deepseek_base_url || "https://api.deepseek.com")}
                  onChange={(v) => set("deepseek_base_url", v)}
                  placeholder="https://api.deepseek.com"
                />
                <SecretInput
                  label="DeepSeek API Key"
                  value={String(cfg.deepseek_api_key || "")}
                  onChange={(v) => set("deepseek_api_key", v)}
                  isSet={config?.deepseek_api_key_set}
                />
              </>
            )}
            {selectedProvider === "ollama" && (
              <TextInput
                label="Ollama Base URL"
                value={String(cfg.ollama_base_url || "http://localhost:11434")}
                onChange={(v) => set("ollama_base_url", v)}
                placeholder="http://localhost:11434"
              />
            )}
            {selectedProvider === "lmstudio" && (
              <TextInput
                label="LM Studio Base URL"
                value={String(cfg.lmstudio_base_url || "http://localhost:1234")}
                onChange={(v) => set("lmstudio_base_url", v)}
                placeholder="http://localhost:1234"
              />
            )}
          </div>

          {/* Selected provider's generation tuning — blank = global default */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <NumberInput
              label="LLM Max Tokens"
              value={cfg[`${selectedProvider}_max_tokens`] as number}
              onChange={(v) => set(`${selectedProvider}_max_tokens`, v === "" ? "" : String(v))}
              step={1024}
              min={1024}
              hint="Blank = global default. Raise for large JSON outputs / many shots."
            />
            <NumberInput
              label="Shot Batch Size"
              value={cfg[`${selectedProvider}_shot_batch_size`] as number}
              onChange={(v) => set(`${selectedProvider}_shot_batch_size`, v === "" ? "" : String(v))}
              min={1}
              hint="Blank = global default. Scenes per LLM call."
            />
            <NumberInput
              label="Parallel Batch Threads"
              value={cfg[`${selectedProvider}_parallel_batch_threads`] as number}
              onChange={(v) => set(`${selectedProvider}_parallel_batch_threads`, v === "" ? "" : String(v))}
              min={1}
              hint="Blank = global default. Cloud providers only."
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleTestLlm}
              disabled={llmTest.running}
            >
              {llmTest.running ? "Testing…" : "Test Connection"}
            </Button>
            {llmTest.status === "success" && (
              <span className="text-xs text-green-600 dark:text-green-400">
                ✓ {llmTest.model} replied &quot;{llmTest.reply}&quot; in {llmTest.elapsed_ms}ms
              </span>
            )}
            {llmTest.status === "unexpected_reply" && (
              <span className="text-xs text-amber-600 dark:text-amber-400">
                ⚠ Connected, but unexpected reply: &quot;{llmTest.reply}&quot;
              </span>
            )}
            {llmTest.status === "error" && (
              <span className="text-xs text-red-500">✗ {llmTest.error}</span>
            )}
          </div>

          <SubHeading>Generation Tuning (Global Defaults)</SubHeading>
          <p className="text-xs text-muted-foreground italic -mt-2">
            Used by providers without a per-provider override above.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <NumberInput
              label="LLM Max Tokens"
              value={cfg.llm_max_tokens as number}
              onChange={(v) => set("llm_max_tokens", v)}
              step={1024}
              min={1024}
              hint="Raise for large JSON outputs / many shots."
            />
            <NumberInput
              label="Shot Batch Size"
              value={cfg.shot_generation_batch_size as number}
              onChange={(v) => set("shot_generation_batch_size", v)}
              min={1}
              hint="Scenes processed per LLM call."
            />
            <NumberInput
              label="Parallel Batch Threads"
              value={cfg.max_parallel_batch_threads as number}
              onChange={(v) => set("max_parallel_batch_threads", v)}
              min={1}
              hint="Cloud providers only; 3-5 recommended, 1-2 for free tiers."
            />
          </div>
        </Collapsible>

        {/* --------------------------------------------- Generation Engines */}
        <Collapsible
          title="Generation Engines"
          icon={<Clapperboard className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-blue-500"
          summary={`${titleCase(String(cfg.image_generation_mode || "comfyui"))} images · ${titleCase(String(cfg.video_generation_mode || "comfyui"))} video`}
          open={openSections.has("engines")}
          onOpenChange={() => toggleSection("engines")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectInput
              label="Image Mode"
              value={String(cfg.image_generation_mode || "comfyui")}
              onChange={(v) => set("image_generation_mode", v)}
              options={[
                { value: "comfyui", label: "ComfyUI (Local)" },
                { value: "gemini", label: "Gemini (Cloud)" },
                { value: "geminiweb", label: "GeminiWeb - Gemini Web (Browser)" },
                { value: "flow", label: "Flow - Google Flow (Browser)" },
              ]}
            />
            <SelectInput
              label="Image Workflow (ComfyUI)"
              value={String(cfg.image_workflow || "krea2_reference")}
              onChange={(v) => set("image_workflow", v)}
              options={(config?.available_image_workflows || []).map((wf: string) => ({
                value: wf,
                label: titleCase(wf),
              }))}
            />
            <SelectInput
              label="Video Mode"
              value={String(cfg.video_generation_mode || "comfyui")}
              onChange={(v) => set("video_generation_mode", v)}
              options={[
                { value: "comfyui", label: "ComfyUI (Local)" },
                { value: "geminiweb", label: "GeminiWeb (Browser)" },
                { value: "flowweb", label: "FlowWeb (Browser)" },
              ]}
            />
            <SelectInput
              label="Video Workflow"
              value={String(cfg.video_workflow || "wan22_workflow")}
              onChange={(v) => set("video_workflow", v)}
              options={(config?.available_video_workflows || []).map((wf: string) => ({
                value: wf,
                label: titleCase(wf),
              }))}
            />
            <SelectInput
              label="Sound FX Workflow"
              value={String(cfg.soundfx_workflow || "mmaudio")}
              onChange={(v) => set("soundfx_workflow", v)}
              options={(config?.available_soundfx_workflows || []).map((wf: string) => ({
                value: wf,
                label: titleCase(wf),
              }))}
            />
            <SelectInput
              label="Video Prompt Mode"
              value={String(cfg.prompt_mode || "video")}
              onChange={(v) => set("prompt_mode", v)}
              options={[
                { value: "video", label: "Video — timestamped video_prompt (MiniMax H3)" },
                { value: "motion", label: "Motion — classic short motion_prompt (Wan 2.2)" },
              ]}
              hint="Default prompt style for shots without an explicit one."
            />
          </div>
        </Collapsible>

        {/* ------------------------------------------ Image & Video Defaults */}
        <Collapsible
          title="Image & Video Defaults"
          icon={<Crop className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-purple-500"
          summary={`${cfg.image_aspect_ratio || "16:9"} · ${cfg.video_resolution || "1280"}p`}
          open={openSections.has("media")}
          onOpenChange={() => toggleSection("media")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectInput
              label="Image Aspect Ratio"
              value={String(cfg.image_aspect_ratio || "16:9")}
              onChange={(v) => set("image_aspect_ratio", v)}
              options={ASPECT_RATIOS.map((r) => ({ value: r, label: r }))}
            />
            <SelectInput
              label="Image Resolution"
              value={String(cfg.image_resolution || "2048")}
              onChange={(v) => set("image_resolution", v)}
              options={IMAGE_RESOLUTIONS.map((r) => ({ value: r, label: r }))}
            />
            <SelectInput
              label="Video Aspect Ratio"
              value={String(cfg.video_aspect_ratio || "16:9")}
              onChange={(v) => set("video_aspect_ratio", v)}
              options={ASPECT_RATIOS.map((r) => ({ value: r, label: r }))}
            />
            <SelectInput
              label="Video Resolution"
              value={String(cfg.video_resolution || "1280")}
              onChange={(v) => set("video_resolution", v)}
              options={VIDEO_RESOLUTIONS.map((r) => ({ value: r, label: r }))}
              hint="1280 = 720p for 16:9."
            />
            <NumberInput
              label="Default Target Video Length (seconds)"
              value={cfg.target_video_length as number}
              onChange={(v) => set("target_video_length", v)}
              min={0}
              hint="0 = story-driven length. Max shots = length / shot length."
            />
            <NumberInput
              label="Default Shot Length (seconds)"
              value={cfg.default_shot_length as number}
              onChange={(v) => set("default_shot_length", v)}
              step={0.5}
              min={1}
            />
          </div>
        </Collapsible>

        {/* ------------------------------------------------------- ComfyUI */}
        <Collapsible
          title="ComfyUI"
          icon={<Server className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-green-500"
          summary={String(cfg.comfy_url || "http://127.0.0.1:8188")}
          open={openSections.has("comfyui")}
          onOpenChange={() => toggleSection("comfyui")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TextInput
              label="ComfyUI URL"
              value={String(cfg.comfy_url || "http://127.0.0.1:8188")}
              onChange={(v) => set("comfy_url", v)}
              placeholder="http://127.0.0.1:8188"
            />
            <TextInput
              label="Output Directory"
              value={String(cfg.comfy_output_dir ?? "")}
              onChange={(v) => set("comfy_output_dir", v)}
              placeholder="E:/ComfyUI/Output"
              hint="Where ComfyUI saves renders. Empty = auto-detect."
            />
            <TextInput
              label="Input Directory"
              value={String(cfg.comfy_input_dir ?? "")}
              onChange={(v) => set("comfy_input_dir", v)}
              placeholder="C:/ComfyUI/input"
              hint="Where ComfyUI loads input images. Empty = auto-detect."
            />
          </div>
        </Collapsible>

        {/* ------------------------------------------------ Narration & Audio */}
        <Collapsible
          title="Narration & Audio"
          icon={<Mic className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-accent"
          summary={`${titleCase(String(cfg.tts_method || "local"))} TTS`}
          open={openSections.has("audio")}
          onOpenChange={() => toggleSection("audio")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SwitchInput
              label="Generate Narration by Default"
              checked={!!cfg.generate_narration}
              onChange={(v) => set("generate_narration", v)}
              hint="New projects enable narration automatically."
            />
            <SelectInput
              label="TTS Method"
              value={String(cfg.tts_method || "local")}
              onChange={(v) => set("tts_method", v)}
              options={TTS_METHODS}
            />
            <TextInput
              label="TTS Voice"
              value={String(cfg.tts_voice || "en-US-AriaNeural")}
              onChange={(v) => set("tts_voice", v)}
              hint='Edge-TTS voice (e.g. "en-GB-SoniaNeural") or ElevenLabs voice id.'
            />
            <SecretInput
              label="ElevenLabs API Key"
              value={String(cfg.elevenlabs_api_key || "")}
              onChange={(v) => set("elevenlabs_api_key", v)}
              isSet={config?.elevenlabs_api_key_set}
            />
            <SelectInput
              label="ElevenLabs Model"
              value={String(cfg.elevenlabs_model || "eleven_multilingual_v2")}
              onChange={(v) => set("elevenlabs_model", v)}
              options={ELEVENLABS_MODELS}
            />
            <NumberInput
              label="ElevenLabs Stability"
              value={cfg.elevenlabs_stability as number}
              onChange={(v) => set("elevenlabs_stability", v)}
              step={0.05}
              min={0}
              max={1}
              hint="0.0 - 1.0 (higher = more stable)."
            />
            <NumberInput
              label="ElevenLabs Similarity"
              value={cfg.elevenlabs_similarity as number}
              onChange={(v) => set("elevenlabs_similarity", v)}
              step={0.05}
              min={0}
              max={1}
              hint="0.0 - 1.0 (higher = closer to original voice)."
            />
          </div>
        </Collapsible>

        {/* --------------------------------------- Performance & Reliability */}
        <Collapsible
          title="Performance & Reliability"
          icon={<Gauge className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-orange-500"
          summary={`${cfg.concurrent_comfyui_limit ?? 1}× ComfyUI · ${cfg.concurrent_geminiweb_limit ?? 1}× browser`}
          open={openSections.has("performance")}
          onOpenChange={() => toggleSection("performance")}
        >
          <SubHeading>Concurrency Limits (per engine)</SubHeading>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <NumberInput
              label="ComfyUI"
              value={cfg.concurrent_comfyui_limit as number}
              onChange={(v) => set("concurrent_comfyui_limit", v)}
              min={1}
              hint="VRAM heavy — keep at 1."
            />
            <NumberInput
              label="Gemini API"
              value={cfg.concurrent_gemini_limit as number}
              onChange={(v) => set("concurrent_gemini_limit", v)}
              min={1}
            />
            <NumberInput
              label="GeminiWeb / Flow (Browser)"
              value={cfg.concurrent_geminiweb_limit as number}
              onChange={(v) => set("concurrent_geminiweb_limit", v)}
              min={1}
              hint="Shared by GeminiWeb and Flow image generation."
            />
            <NumberInput
              label="Other Engines (fallback)"
              value={cfg.concurrent_default_limit as number}
              onChange={(v) => set("concurrent_default_limit", v)}
              min={1}
            />
            <NumberInput
              label="Flow Per-Project Concurrency"
              value={cfg.flow_project_concurrency as number}
              onChange={(v) => set("flow_project_concurrency", v)}
              min={1}
              hint="Parallel generations inside one Flow project."
            />
            <NumberInput
              label="Legacy Global Limit"
              value={cfg.concurrent_generation_limit as number}
              onChange={(v) => set("concurrent_generation_limit", v)}
              min={1}
              hint="Fallback when an engine has no specific limit."
            />
          </div>

          <SubHeading>Retries & Timeouts</SubHeading>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <NumberInput
              label="Video Render Timeout (s)"
              value={cfg.video_render_timeout as number}
              onChange={(v) => set("video_render_timeout", v)}
              min={60}
            />
            <NumberInput
              label="Image Generation Max Retries"
              value={cfg.image_generation_max_retries as number}
              onChange={(v) => set("image_generation_max_retries", v)}
              min={0}
            />
            <NumberInput
              label="Image Retry Delay (s)"
              value={cfg.image_generation_retry_delay as number}
              onChange={(v) => set("image_generation_retry_delay", v)}
              min={0}
            />
          </div>
          <SwitchInput
            label="Continue on Partial Image Failure"
            checked={!!cfg.continue_on_partial_image_failure}
            onChange={(v) => set("continue_on_partial_image_failure", v)}
            hint="Keep generating videos even when some shot images fail."
          />
        </Collapsible>

        {/* ------------------------------------------ Browser Automation */}
        <Collapsible
          title="Browser Automation (GeminiWeb & Flow)"
          icon={<Globe className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-sky-500"
          summary={titleCase(String(cfg.playwright_browser || "chromium"))}
          open={openSections.has("browser")}
          onOpenChange={() => toggleSection("browser")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectInput
              label="Playwright Browser"
              value={String(cfg.playwright_browser || "chromium")}
              onChange={(v) => set("playwright_browser", v)}
              options={[
                { value: "chromium", label: "Chromium (Default)" },
                { value: "chrome", label: "Google Chrome" },
                { value: "msedge", label: "Microsoft Edge" },
                { value: "firefox", label: "Firefox" },
                { value: "webkit", label: "WebKit (Safari)" },
              ]}
              hint="Browser engine for GeminiWeb and FlowWeb generation."
            />
            <SelectInput
              label="Gemini Web Model"
              value={String(cfg.geminiweb_model || "3.8 Flash")}
              onChange={(v) => set("geminiweb_model", v)}
              options={GEMINI_MODELS.map((m) => ({ value: m.value, label: m.label }))}
              hint="Default model for GeminiWeb image and video generation."
            />
            <SelectInput
              label="Gemini Web Thinking"
              value={String(cfg.geminiweb_thinking || "Low")}
              onChange={(v) => set("geminiweb_thinking", v)}
              options={GEMINI_THINKING.map((t) => ({ value: t.value, label: t.label }))}
              hint="Low = extended thinking off."
            />
            <SelectInput
              label="Flow Image Model"
              value={String(cfg.flow_image_model || DEFAULT_FLOW_MODEL)}
              onChange={(v) => set("flow_image_model", v)}
              options={FLOW_MODELS.map((m) => ({ value: m.value, label: m.label }))}
              hint="Director mode is always off; aspect ratio follows the project."
            />
            <SelectInput
              label="Flow Outputs per Prompt"
              value={String(cfg.flow_image_outputs || DEFAULT_FLOW_OUTPUTS)}
              onChange={(v) => set("flow_image_outputs", v)}
              options={FLOW_OUTPUTS.map((o) => ({ value: o.value, label: o.label }))}
            />
            <TextInput
              label="Flow URL"
              value={String(cfg.flowweb_url || "https://flow.google.com/")}
              onChange={(v) => set("flowweb_url", v)}
            />
          </div>

          <SubHeading>Timeouts & Profile</SubHeading>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <NumberInput
              label="GeminiWeb Timeout (s)"
              value={cfg.geminiweb_timeout as number}
              onChange={(v) => set("geminiweb_timeout", v)}
              min={30}
            />
            <NumberInput
              label="FlowWeb Timeout (s)"
              value={cfg.flowweb_timeout as number}
              onChange={(v) => set("flowweb_timeout", v)}
              min={30}
            />
            <NumberInput
              label="Chat Lock Timeout (s)"
              value={cfg.geminiweb_chat_lock_timeout as number}
              onChange={(v) => set("geminiweb_chat_lock_timeout", v)}
              min={0}
              hint="Per-project generation lock wait before proceeding unlocked."
            />
            <TextInput
              label="Browser Profile Path"
              value={String(cfg.geminiweb_chrome_profile ?? "")}
              onChange={(v) => set("geminiweb_chrome_profile", v)}
              placeholder="Auto (output/chrome_profile)"
              hint="Persistent login profile directory. Empty = default."
            />
          </div>

          <div className="border-t border-border/30 pt-4">
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs text-muted-foreground leading-relaxed max-w-md">
                If automated logins are blocked, launch a browser with persistent
                context and stealth settings. Once you log in there, automated
                runs will recognize your session.
              </p>
              <Button
                type="button"
                variant="outline"
                onClick={handleLaunchBrowser}
                disabled={isLaunchingBrowser}
                className="shrink-0 flex items-center gap-2 h-10 border-blue-500/30 hover:bg-blue-500/10 hover:border-blue-500/50 transition-all"
              >
                {isLaunchingBrowser ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
                    Launching...
                  </>
                ) : (
                  <>
                    <Globe className="w-4 h-4 text-blue-500" />
                    Launch Browser for Session Login
                  </>
                )}
              </Button>
            </div>
          </div>
        </Collapsible>

        {/* --------------------------------------------------- Watermark */}
        <Collapsible
          title="Watermark Removal"
          icon={<Droplets className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-rose-500"
          summary={titleCase(String(cfg.watermark_removal_method || "builtin"))}
          open={openSections.has("watermark")}
          onOpenChange={() => toggleSection("watermark")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectInput
              label="Removal Method"
              value={String(cfg.watermark_removal_method || "builtin")}
              onChange={(v) => set("watermark_removal_method", v)}
              options={[
                { value: "builtin", label: "Built-in Restoration (images)" },
                { value: "external", label: "External Tool" },
              ]}
            />
            <div />
            <TextInput
              label="External Tool (Images)"
              value={String(cfg.gemini_watermark_tool_image ?? "")}
              onChange={(v) => set("gemini_watermark_tool_image", v)}
              placeholder="Full path to image watermark removal tool"
              disabled={cfg.watermark_removal_method !== "external"}
            />
            <TextInput
              label="External Tool (Videos)"
              value={String(cfg.gemini_watermark_tool_video ?? "")}
              onChange={(v) => set("gemini_watermark_tool_video", v)}
              placeholder="Full path to video watermark removal tool"
              disabled={cfg.watermark_removal_method !== "external"}
              hint="Built-in restoration only supports images; video always needs an external tool."
            />
          </div>
        </Collapsible>

        {/* ------------------------------------------------ Paths & Storage */}
        <Collapsible
          title="Paths & Storage"
          icon={<FolderOpen className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-yellow-500"
          summary={String(cfg.output_dir || "output")}
          open={openSections.has("paths")}
          onOpenChange={() => toggleSection("paths")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TextInput
              label="Output Directory"
              value={String(cfg.output_dir || "output")}
              onChange={(v) => set("output_dir", v)}
              hint="Root for projects, logs and generated media. Restart required."
            />
            <TextInput
              label="Asset Library Dirs"
              value={String(cfg.asset_library_dirs || "output/Assets")}
              onChange={(v) => set("asset_library_dirs", v)}
              hint="Semicolon-separated list of asset library roots."
            />
          </div>
        </Collapsible>

        {/* ------------------------------------------------- Web UI Server */}
        <Collapsible
          title="Web UI Server"
          icon={<Network className="w-5 h-5 text-muted-foreground" />}
          accentClassName="bg-teal-500"
          summary={`backend :${cfg.backend_port || 8000} · frontend :${cfg.frontend_port || 3000}`}
          open={openSections.has("server")}
          onOpenChange={() => toggleSection("server")}
        >
          <SwitchInput
            label="Enable Web UI"
            checked={!!cfg.web_ui_enabled}
            onChange={(v) => set("web_ui_enabled", v)}
            hint="Takes effect on next start."
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TextInput
              label="Backend Host"
              value={String(cfg.backend_host || "127.0.0.1")}
              onChange={(v) => set("backend_host", v)}
              hint="External hostname used in URLs."
            />
            <NumberInput
              label="Backend Port"
              value={cfg.backend_port as number}
              onChange={(v) => set("backend_port", v)}
              min={1}
            />
            <TextInput
              label="Backend Bind Address"
              value={String(cfg.backend_bind_host || "0.0.0.0")}
              onChange={(v) => set("backend_bind_host", v)}
              hint="0.0.0.0 for LAN access."
            />
            <TextInput
              label="Frontend Host"
              value={String(cfg.frontend_host || "127.0.0.1")}
              onChange={(v) => set("frontend_host", v)}
            />
            <NumberInput
              label="Frontend Port"
              value={cfg.frontend_port as number}
              onChange={(v) => set("frontend_port", v)}
              min={1}
            />
            <TextInput
              label="Frontend Bind Address"
              value={String(cfg.frontend_bind_host || "0.0.0.0")}
              onChange={(v) => set("frontend_bind_host", v)}
            />
          </div>
          <TextInput
            label="CORS Origins"
            value={String(cfg.web_ui_cors_origins ?? "")}
            onChange={(v) => set("web_ui_cors_origins", v)}
            placeholder="http://localhost:3000,http://192.168.1.10:3000"
            hint="Comma-separated extra allowed origins. Defaults cover localhost and the configured frontend host."
          />
        </Collapsible>

        {/* ---------------------------------------------------- Save bar */}
        <div className="sticky bottom-4 z-20">
          <div className="bg-card/95 border border-border/50 rounded-xl p-4 shadow-lg backdrop-blur-md flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {dirty ? "You have unsaved changes" : "All changes saved"}
            </span>
            <Button
              type="submit"
              disabled={updateConfigMutation.isPending}
              className="flex items-center gap-2"
            >
              {updateConfigMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Configuration
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
