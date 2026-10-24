// Gemini Web mode picker options — these mirror gemini.google.com's mode
// picker exactly: three models and three thinking levels. The backend
// transports a selection as "<model>|<thinking>" in the gemini_mode field.
export const GEMINI_MODELS = [
  { value: "3.5 Flash-Lite", label: "3.5 Flash-Lite" },
  { value: "3.8 Flash", label: "3.8 Flash" },
  { value: "3.1 Pro", label: "3.1 Pro" },
] as const;

export const GEMINI_THINKING = [
  { value: "Low", label: "Low (Quick and efficient)" },
  { value: "Medium", label: "Medium (Balanced depth)" },
  { value: "High", label: "High (Extra thorough)" },
] as const;

export const DEFAULT_GEMINI_MODEL = "3.8 Flash";
export const DEFAULT_GEMINI_THINKING = "Low";

// Legacy combined six-mode names (Fast/Medium/Pro ± Thinking) that older
// configs and localStorage entries may still hold.
const LEGACY_MODE_MAP: Record<string, { model: string; thinking: string }> = {
  "Fast": { model: "3.5 Flash-Lite", thinking: "Low" },
  "Medium": { model: "3.8 Flash", thinking: "Low" },
  "Pro": { model: "3.1 Pro", thinking: "Low" },
  "Fast Thinking": { model: "3.5 Flash-Lite", thinking: "High" },
  "Medium Thinking": { model: "3.8 Flash", thinking: "High" },
  "Pro Thinking": { model: "3.1 Pro", thinking: "High" },
};

export function decodeLegacyGeminiMode(mode?: string | null): {
  model?: string;
  thinking?: string;
} {
  if (!mode) return {};
  const legacy = LEGACY_MODE_MAP[mode];
  if (legacy) return legacy;
  const [model, thinking] = mode.split("|");
  return { model: model || undefined, thinking: thinking || undefined };
}
