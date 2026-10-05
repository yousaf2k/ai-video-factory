# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository. This is the canonical instruction file for the project — tool-specific entry points (`CLAUDE.md`, `GEMINI.md`) import it.

## Project Overview

AI Video Factory is an end-to-end pipeline that transforms text ideas into cinematic videos using AI. It combines multiple LLM providers (Gemini, OpenAI, Zhipu, DeepSeek, Qwen, Kimi, Ollama, LM Studio) for story/prompt generation with ComfyUI (and Gemini Flow web automation) for image/video rendering, wrapped in a FastAPI + React web UI.

## Development Commands

### Core Pipeline

```bash
# Generate a video from CLI
python core/main.py --idea "A beautiful sunset over the ocean"

# Run with specific story / shots agents
python core/main.py --idea "Historical documentary" --story-agent netflix_documentary

# Override workflows for a single run
python core/main.py --idea "..." --video-workflow minimax_h3_i2v_8s --image-workflow krea2_reference

# List available agents / projects / TTS voices
python core/main.py --list-agents
python core/main.py --list-projects
python core/main.py --list-voices

# Batch process multiple ideas
python batch_videos.py --file ideas.txt

# Project management CLI
python projects.py --list
python regenerate.py --project project_XXXXXXXX --videos --failed-only
```

### ASMR Glass Cutting

```bash
# Generate ASMR glass cutting videos from natural language
python core/main.py --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting --shot-length 5

# Category input (agent expands to 5-10 objects); custom shot duration
python core/main.py --idea "tropical fruits" --story-agent asmr/asmr_glass_cutting --shot-length 8
```

### Web UI

```bash
# Start both backend (FastAPI :8000) and frontend (Next.js :3000)
python web_ui/start.py

python web_ui/start.py --backend-only
python web_ui/start.py --frontend-only

# Backend only (direct)
cd web_ui/backend && python main.py
```

### Frontend Development

```bash
cd web_ui/frontend
npm install       # Install dependencies
npm run dev       # Start development server
npm run build     # Build for production
npm run lint      # Run linter
```

### Testing

```bash
python run_tests.py                      # Run all tests
pytest tests/test_assets_api.py -v       # Specific test file
pytest tests/integration/ -v             # Integration tests only
pytest tests/ --cov=core --cov-report=html
```

Mock external services (ComfyUI, LLM providers) in tests; shared fixtures live in `tests/conftest.py`.

## Architecture Overview

### Pipeline Flow

```
Idea → Story → Scene Graph → Shots → Images → Videos → Narration
        ↓        ↓            ↓       ↓        ↓         ↓
     LLM     Scene       Shot      Image    ComfyUI   TTS
    Engine    Graph      Planner  Generator  /Flow    Engine
```

### Core Components (`core/`)

- **LLM layer** (`llm_engine.py`, `gemini_engine.py`): provider abstraction, text + JSON-structured outputs, selected via `LLM_PROVIDER`.
- **Agent system** (`agent_loader.py`): modular prompt templates in `agents/` with `#include` composition and `{USER_INPUT}` placeholder.
- **Story pipeline** (`story_engine.py`, `scene_graph.py`, `shot_planner.py`): story → visual scenes → shots with camera movements, prompts, durations; scene duration validation and auto-correction.
- **Generation layer** (`image_generator.py`, `comfyui_image_generator.py`, `geminiweb_image_generator.py`, `comfy_client.py`, `flowweb_video_generator.py`): Gemini API / ComfyUI (Flux, Krea2, HiDream, Z-Image) / GeminiWeb browser automation for images; Wan 2.2, MiniMax H3, LTX-2 via ComfyUI for video.
- **Workflow compiler** (`prompt_compiler.py`, `workflow_loader.py`): auto-discovers workflows from `workflow/`, supports API JSON and Workflow JSON, detects node IDs via title tags (`[prompt]`, `[image_in]`, `[video_out]`, …) or heuristics.
- **Project management** (`project_manager.py`): atomic file-locking, crash recovery, thumbnails, selective regeneration; `video_regenerator.py` and `render_monitor.py` handle re-renders.
- **Narration** (`narration_generator.py`): ElevenLabs, Edge-TTS, or ComfyUI voice workflows.
- **Security** (`secrets.py`): optional encryption of API keys stored in `.env`.

### Web UI Architecture

**Backend** (`web_ui/backend/`) — FastAPI + WebSocket (`/api/ws/progress/{project_id}`):
- `api/`: routers — `projects.py`, `stories.py`, `editor.py`, `shots.py`, `queue.py`, `assets.py`, `config_api.py`
- `services/`: business logic — `project_service.py`, `generation_service.py`, `queue_service.py`, `asset_service.py`, `export_service.py`
- `models/`: Pydantic schemas per domain (project, story, shot, queue, asset)

**Frontend** (`web_ui/frontend/`) — Next.js 14 App Router, React Query, Radix UI + Tailwind CSS, Zustand, DnD Kit:
- Feature components in `src/components/{feature}/` (agents, assets, characters, editor, queue, scenes, shots, …)
- API client in `src/services/api.ts`

### Asset Library

Global asset library with nested categories (top-level category = asset type: `Images`/`Videos`/`Audio`/`Music`, aliased `i`/`v`/`a`/`m`). There is **no metadata JSON** — the filename is the metadata: `{id}-{Title}.{ext}` (8-char hex id). Assets attach to shots as references (`reference_asset_ids`), resolved either as library refs (`i/9f3ab21c`) or project-media refs (`p/{project_id}/{media_dir}/{filename}`). Library roots come from `ASSET_LIBRARY_DIRS` (default `output/Assets`). See `docs/ASSETS_FEATURE_PLAN.md`.

## Configuration System

**`config.py`** is the central hub: LLM provider selection, image/video dimensions and workflows, camera-to-LoRA mappings, concurrent generation limits, and path resolution (`config.resolve_path()` for cross-drive compatibility).

Key environment variables (`.env` at project root):

```bash
GEMINI_API_KEY="..."               # Primary LLM key
OPENAI_API_KEY="..."               # Optional
LLM_PROVIDER="gemini"              # gemini, openai, zhipu, deepseek, qwen, kimi, ollama, lmstudio
IMAGE_GENERATION_MODE="comfyui"    # comfyui, gemini, geminiweb
VIDEO_GENERATION_MODE="comfyui"    # comfyui, geminiweb
COMFY_URL="http://127.0.0.1:8188"
COMFY_OUTPUT_DIR="E:/ComfyUI/Output"
ASSET_LIBRARY_DIRS="output/Assets" # semicolon-separated extra library roots
```

Notable defaults: `IMAGE_WORKFLOW = "krea2_reference"`, `VIDEO_WORKFLOW = "wan22_workflow"`. Workflows are auto-discovered from `workflow/` on startup; supported image resolutions up to 2048, aspect ratios 1:1, 16:9, 9:16, 4:3, 3:4.

## Agent Development

1. Create a `.md` file in the right category: `agents/story/…` or `agents/shots/…`
2. Use `{USER_INPUT}` for dynamic content and `#include path/to/file.md` for composition
3. Reference via `--story-agent {name}` or `--shots-agent {name}` (subdirectory paths like `asmr/asmr_glass_cutting` work)

Agent layout:

```
agents/
├── story/
│   ├── asmr/            # ASMR glass cutting
│   ├── documentary/     # default, netflix/youtube documentary, historical, _base/_contexts/_styles
│   ├── movie/           # action, horror, comedy, drama, sci-fi, thriller, … + _base/_contexts/_styles
│   ├── system/          # master_script guidelines
│   └── then_vs_now/     # FLFI2V comparative storytelling
└── shots/
    ├── base/            # base_shots_standard
    ├── cameras/         # gopro, disney/ghibli/pixar animation, imax, horror, rockstar
    ├── contexts/        # visual context packs (greek, roman, indus, gta6, prehistoric, …)
    ├── soundfx/         # soundfx_default
    ├── styles/          # artistic, ghibli, horror, pixar, vlog, …
    └── videoprompt/     # videoprompt_minimax_h3 (MiniMax H3 prompt rules)
```

Character references use a **unified schema**: a single `image_prompt` and `character_reference_image_path` per character; reference generation produces 8-view character sheets (4 full-body + 4 face close-ups). Shots agents may emit `soundfx_prompt`; blank soundfx falls back to generic sounds.

## Workflow Development

- **Video** (`workflow/video/`): Wan 2.2 (t2v/i2v/FLFI2V, VFI + super-resolution variants), MiniMax H3 (`minimax_h3_i2v*.json`), LTX-2. Title tags: `[prompt]`, `[image_in]`, `[video_out]`, `[seed]`; FLFI2V uses `[image_in_first]`/`[image_in_last]`.
- **Image** (`workflow/image/`): Flux, Flux 2, Krea 2 reference, HiDream, Z-Image Turbo, IPAdapter (then/now). Tags: `[positive]`, `[negative]`, `[ksampler]`, `[vae]`, `[save]`; IPAdapter uses `[reference]`/`[ipadapter]`.
- **Sound FX** (`workflow/soundfx/`): MMAudio and woosh workflows for shot SFX.
- **Voice** (`workflow/voice/`): TTS workflows.

Camera LoRA system: up to 4 simultaneous camera types via the `LORA_NODES` array and `CAMERA_LORA_MAPPING` (high/low noise LoRA pairs with trigger keywords).

## Important Patterns

- **Error handling**: image retry via `IMAGE_GENERATION_MAX_RETRIES`, graceful degradation with `CONTINUE_ON_PARTIAL_IMAGE_FAILURE`, render timeout `VIDEO_RENDER_TIMEOUT`.
- **Concurrency**: per-engine limits in `CONCURRENT_GENERATION_LIMITS`; queue-based processing with WebSocket progress; atomic file locking for project metadata.
- **Path resolution**: use `config.resolve_path()`; forward slashes in config values; `output/` prefix handled specially across drives.
- **LLM batching**: `SHOT_GENERATION_BATCH_SIZE` + `MAX_PARALLEL_BATCH_THREADS` (cloud only); raise `LLM_MAX_TOKENS` for many shots.

## Common Issues

- **ComfyUI connection**: must run on `http://127.0.0.1:8188`; verify `COMFY_OUTPUT_DIR`; workflow JSON must match the API format.
- **Workflow detection**: add title tags to nodes; validate JSON (no trailing commas; string node IDs).
- **Web UI CORS**: configured via `WEB_UI_CORS_ORIGINS`; set `BACKEND_HOST`/`FRONTEND_HOST` for LAN access; check `startup_debug.txt` and `output/logs/`.
- **Paths**: prefer `config.resolve_path()` over manual joins; check `ABS_OUTPUT_DIR`/`ABS_PROJECTS_DIR`.

## Development Workflow

1. Implement in `core/` (CLI first)
2. Add API endpoints in `web_ui/backend/api/` (+ Pydantic model in `models/`, service in `services/`)
3. Add frontend components in `web_ui/frontend/src/components/`
4. Add tests in `tests/`
5. Update documentation in `docs/` (keep `docs/DOCS_INDEX.md` accurate)

## Documentation Map

- `README.md` — project overview and quick start
- `docs/DOCS_INDEX.md` — full documentation index (start here)
- `docs/getting-started/` — quick start, setup checklist, configuration reference
- `docs/setup/` — ComfyUI, Gemini, ElevenLabs, and local-LLM (Ollama/LM Studio) setup
- `docs/guides/` — pipeline, camera LoRA, video length, regeneration, MiniMax H3 guides
- `docs/features/` — Asset Library, Then Vs Now, ASMR Glass Cutting documentation
- `docs/agents/` — guides for the built-in story/shots agents
- `docs/reference/` — API reference and security guide
- `docs/development/` — historical plans, fixes, test reports, walkthroughs, archive
