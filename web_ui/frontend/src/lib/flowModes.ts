// Google Flow (flow.google.com) image settings — these mirror Flow's
// settings popover exactly: Image/Video tabs, aspect ratio chips, the model
// dropdown and outputs-per-prompt (x1–x4). Agent mode is never toggled by
// the automation and stays at its default (off).
export const FLOW_MODELS = [
  { value: "Nano Banana Pro", label: "🍌 Nano Banana Pro" },
  { value: "Nano Banana 2 Lite", label: "🍌 Nano Banana 2 Lite" },
  { value: "Nano Banana 2.1", label: "🍌 Nano Banana 2.1" },
] as const;

export const FLOW_OUTPUTS = [
  { value: "x1", label: "x1 (default)" },
  { value: "x2", label: "x2" },
  { value: "x3", label: "x3" },
  { value: "x4", label: "x4" },
] as const;

export const FLOW_ASPECT_RATIOS = ["16:9", "4:3", "1:1", "3:4", "9:16"] as const;

export const DEFAULT_FLOW_MODEL = "Nano Banana 2.1";
export const DEFAULT_FLOW_OUTPUTS = "x1";
