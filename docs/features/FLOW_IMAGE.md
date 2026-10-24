# Google Flow Image Generation (FlowWeb)

Browser-based image generation via [Google Flow](https://flow.google.com/) — the `flow` image
generation mode. Like the GeminiWeb mode, it drives a real Chrome window with Playwright using
the persisted Google login, so there is **no API key** and no extra setup beyond a one-time
Google sign-in.

## Quick Start

1. Log in once: Web UI → **Global Configuration → Browser Management → Launch Browser for
   Session Login** (same profile as GeminiWeb; already done if GeminiWeb works).
2. Global Configuration → **Image Mode** → `Flow - Google Flow (Browser)`, and set the
   **Flow Image Model / Outputs per Prompt** defaults (see below).
3. Generate images as usual — per-shot dialog, batch grid, character references, thumbnails and
   scene backgrounds all honor the `flow` mode.

CLI: `IMAGE_GENERATION_MODE="flow"` in `.env` (or `IMAGE_GENERATION_MODE` in `config.py`).

## Settings

Flow exposes its generation settings in the prompt-bar settings popover. They are mapped in the
Web UI and applied in Flow before every generation:

| Setting | Where in our UI | Default | Behavior in Flow |
|---------|-----------------|---------|------------------|
| Media type (Image/Video) | fixed to Image for image generations | Image | switched only if Video is active |
| Aspect ratio | follows each project's aspect ratio | `16:9` | `16:9`, `4:3`, `1:1`, `3:4`, `9:16` supported; only clicked when it differs |
| Model | Global Config → *Flow Image Model* | **Nano Banana 2.1** | `Nano Banana Pro`, `Nano Banana 2 Lite`, `Nano Banana 2.1`; only changed when the picker shows a different model |
| Outputs per prompt | Global Config → *Flow Outputs* | **x1** | `x1`–`x4`; only clicked when it differs |
| Director mode | shown as fixed "Off (default)" | **Off** | **never toggled** by the automation |

Time-saving rule: every setting is read first — if Flow already shows the requested value, the
automation skips the click ("already selected → don't change").

## Project Reuse (same as Gemini chat)

Each pipeline project maps to one Flow project workspace, tracked in
`output/flow_project_registry.json` (project title → project URL). Shots,
characters, props, backgrounds and thumbnails all build the same title
(`<story title> - <project id>`), so they share the project's single
workspace. Newly created Flow projects are **renamed to that title** (Flow
defaults to timestamp names like 'Oct 16 - 12:57'); already-named projects are
left untouched, and workspaces still carrying an auto-generated timestamp name
are renamed on the next run — so the project is identifiable by name in
Flow's project grid and the title-based card search works as a fallback:

1. **First generation for a project**: opens `https://flow.google.com/`, searches the project
   grid for a card with the project's title, and clicks it if found; otherwise creates a new
   one via **New project**. The resulting URL is registered for future runs.
2. **Subsequent generations**: navigate straight to the registered project URL (falls back to
   card-clicking if the registered project is gone).
3. **No-title generations** (callers that don't pass a project title) share one self-healing
   default workspace registered under `__flow_default_workspace__`.
3. Concurrency inside one project is controlled by `FLOW_PROJECT_CONCURRENCY` (default **2**):
   - **Generation slots** (`output/flow_project_lock_<title>_slotN.lock`) allow up to N
     parallel generations per project — Flow's grid handles concurrent generations natively
     (that is what its x2–x4 outputs option does). Extra workers wait for a free slot.
   - **Settings lock** (`output/flow_settings_lock_<title>.lock`, single slot) serializes the
     phase that must not race between parallel workers: project lookup/creation, the settings
     popover, and prompt submit (Flow applies settings to future outputs, so a concurrent
     change could land in the other worker's generation). Generation + download then run in
     parallel.
   - **Result attribution**: each worker matches new tiles against its own prompt (Flow derives
     the tile label from the prompt) so side-by-side generations never download each other's
     image. Keep parallel prompts distinct — identical prompts in one project cannot be told
     apart. The chosen tile's match score is logged (`prompt-match 0.80, label='…'`).
     Tile labels are English, so a prompt written in a non-Latin script (e.g. an Urdu scene
     location inside a background-sheet prompt) can never word-match its own label; such
     prompts are first rendered into English label keywords via one LLM call
     (`_label_hints_for_prompt`, logged as `label hints for tile matching`) and the tile is
     matched against those (`hint-match 0.60`). ASCII-only prompts skip the LLM entirely.

## How a Generation Runs

`core/flowweb_image_generator.py` checks out a cloned worker browser profile
(`output/chrome_profile_worker_N`, shared with GeminiWeb) and launches
`core/flowweb_image_subprocess.py` (Playwright must run outside the FastAPI process):

1. Open/reuse the Flow project (registry → card click → New project).
2. Align the settings popover (Image tab, aspect ratio, model, outputs) — skipping anything
   already selected.
3. Attach reference images as **ingredients** via the prompt-bar **+** add-media panel:
   - Uploaded assets are looked up by file name (list scan, then the **Search assets** box —
     file names are unique per project and uploads keep their original name)
   - Assets **generated in Flow** (backgrounds, character sheets) are listed under Flow's
     prompt-derived titles instead, so each generation registers `{label, src}` in
     `output/flow_asset_registry.json` (earlier generations are back-filled from the
     subprocess log) and the attach finds them by label search + exact tile-src match
   - The asset is selected and confirmed with **Add to prompt**; only genuinely unknown
     files go through the panel's **Upload media** file chooser (which registers the file
     name for future attaches)
   - Flow's **Uploading image…** modal is awaited (dismissed + retried when stuck) because
     its backdrop blocks every other control.
4. Type the prompt into the editor and click the arrow (Start generation) button.
5. Wait for the new tile to finish rendering (percentage indicator gone, image loaded).
6. Download: native download action if available, else an authenticated fetch of the tile's
   same-origin URL (`https://flow.google.com/asb/...`), converted to PNG. An element screenshot
   is the last-resort fallback.

Failures save diagnostic screenshots next to the target image path
(`*_diagnostic.png`, `*_download_diagnostic.png`, `*_project_diagnostic.png`,
`*_upload_diagnostic.png`).

## Configuration

```bash
FLOWWEB_URL=https://flow.google.com/
FLOW_IMAGE_MODEL=Nano Banana 2.1   # Nano Banana Pro | Nano Banana 2 Lite | Nano Banana 2.1
FLOW_IMAGE_OUTPUTS=x1              # x1 | x2 | x3 | x4
FLOW_AGENT_MODE=false              # stays off; automation never toggles Director
FLOWWEB_TIMEOUT=300                # seconds to wait for a generation
FLOW_PROJECT_CONCURRENCY=2         # parallel generations inside ONE Flow project
```

Browser settings are shared with GeminiWeb (`PLAYWRIGHT_BROWSER`, `PLAYWRIGHT_CHANNEL`,
`GEMINIWEB_CHROME_PROFILE`).

## Files

- `core/flowweb_image_generator.py` — worker-profile checkout + subprocess wrapper
- `core/flowweb_image_subprocess.py` — Playwright automation (registry, locks, settings, download)
- `web_ui/backend/api/config_api.py` — `flow_image_model` / `flow_image_outputs` config endpoints
- `web_ui/frontend/src/lib/flowModes.ts` — model/output choices for the UI
- `tests/unit/test_flowweb_image.py` — offline unit tests

## Troubleshooting

- **Login prompt appears / empty generations**: launch *Browser for Session Login* and sign in
  to Google once; the worker profiles clone the master profile.
- **Settings popover not applied**: check `output/logs/flowweb_image_subprocess.log` — the
  automation logs each setting with "already …; skipping" or the value it set.
- **Google account changes**: delete the `chrome_profile_worker_*` folders to re-clone the
  master profile after re-login.
