# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Video Factory is an end-to-end pipeline that transforms text ideas into cinematic videos using AI. The system combines multiple LLM providers (Gemini, OpenAI, Zhipu, etc.) for story/prompt generation with ComfyUI for video rendering, wrapped in a modern React web UI.

## Development Commands

### Core Pipeline
```bash
# Generate a video from CLI
python core/main.py --idea "A beautiful sunset over the ocean"

# Run with specific story agent
python core/main.py --idea "Historical documentary" --story-agent netflix_documentary

# Batch process multiple ideas
python batch_videos.py --file ideas.txt
```

### Web UI
```bash
# Start both backend and frontend
python web_ui/start.py

# Start only backend (FastAPI on port 8000)
python web_ui/start.py --backend-only

# Start only frontend (Next.js on port 3000)
python web_ui/start.py --frontend-only

# Backend only (direct)
cd web_ui/backend && python main.py
```

### Frontend Development
```bash
cd web_ui/frontend
npm install           # Install dependencies
npm run dev          # Start development server
npm run build        # Build for production
npm run lint         # Run linter
```

### Testing
```bash
# Run all tests
python run_tests.py

# Run specific test file
pytest tests/test_api_endpoints.py -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html
```

## Architecture Overview

### Pipeline Flow
```
Idea → Story → Scene Graph → Shots → Images → Videos → Narration
        ↓        ↓            ↓       ↓        ↓         ↓
     LLM     Scene       Shot      Image    ComfyUI   TTS
   Engine    Graph      Planner   Generator           Engine
```

### Core Components

**LLM Layer** (`core/llm_engine.py`, `core/gemini_engine.py`)
- Abstract provider interface supporting Gemini, OpenAI, Zhipu, Qwen, Kimi, Ollama, LM Studio
- Configurable via `LLM_PROVIDER` environment variable
- Handles both text generation and JSON-structured outputs

**Agent System** (`core/agent_loader.py`)
- Modular prompt templates in `agents/{category}/{name}.md`
- Supports `#include` directives for composition
- Categories: `story/`, `shots/`, with subdirectories for documentary, movie, then_vs_now
- Special agents like `then_vs_now` use multiple camera/reference workflows

**Story Pipeline** (`core/story_engine.py`, `core/scene_graph.py`, `core/shot_planner.py`)
- `build_story()`: Generates narrative structure with scenes, characters, settings
- `build_scene_graph()`: Creates visual scene breakdowns
- `plan_shots()`: Plans detailed shots with camera movements, prompts, durations
- Supports intelligent scene duration validation and auto-correction

**Generation Layer** (`core/image_generator.py`, `core/comfy_client.py`)
- Multiple image modes: Gemini API, ComfyUI (Flux/SDXL), or GeminiWeb (browser automation)
- Video generation via ComfyUI with Wan 2.2 model
- Multi-camera LoRA system for motion effects (drone, orbit, dolly, zoom, etc.)

**Workflow Compiler** (`core/prompt_compiler.py`)
- Auto-discovers workflows from `workflow/video/` and `workflow/image/` directories
- Supports both API JSON and Workflow JSON formats
- Node ID detection via title tags (`[prompt]`, `[image_in]`, `[video_out]`) or heuristics

**Project Management** (`core/project_manager.py`)
- Atomic file-locking for concurrent access safety
- Crash recovery and state persistence
- Thumbnail management and selective regeneration

### Web UI Architecture

**Backend** (`web_ui/backend/`)
- FastAPI with WebSocket for real-time progress updates
- Pydantic models in `models/` for type safety
- Service layer in `services/` for business logic
- API routers in `api/` for REST endpoints

**Frontend** (`web_ui/frontend/`)
- Next.js 14 with App Router
- React Query for data fetching and caching
- Radix UI components with Tailwind CSS
- Zustand for state management
- DnD Kit for drag-and-drop (shot reordering)

**Key Frontend Patterns**
- Server components for data fetching
- Client components for interactivity
- API service layer in `src/services/api.ts`
- Component structure: `components/{feature}/{Component}.tsx`

## Configuration System

**`config.py`** is the central configuration hub with:
- LLM provider selection and API keys
- Image/video dimensions calculation
- Workflow auto-discovery
- Camera-to-LoRA mappings
- Concurrent generation limits per engine type

**Environment Variables** (`.env` file)
```bash
GEMINI_API_KEY="sk-..."          # Required for Gemini
OPENAI_API_KEY="sk-..."          # Optional OpenAI
LLM_PROVIDER="gemini"            # Primary LLM
IMAGE_GENERATION_MODE="comfyui"  # comfyui, gemini, geminiweb
VIDEO_GENERATION_MODE="comfyui"  # comfyui, geminiweb
COMFY_OUTPUT_DIR="E:/ComfyUI/Output"  # ComfyUI output path
```

**Dynamic Configuration**
- Workflows are auto-discovered from `workflow/` directory on startup
- Node IDs detected via title tags or connection tracing
- Supports multiple resolutions (512, 720, 1024, 1080, 1280, 2048)
- Aspect ratios: 1:1, 16:9, 9:16, 4:3, 3:4

## Agent Development

**Creating New Agents**
1. Create `.md` file in appropriate category: `agents/{category}/{name}.md`
2. Use `{USER_INPUT}` placeholder for dynamic content
3. Use `#include path/to/file.md` for composition
4. Reference via `--story-agent {name}` or `--shots-agent {name}`

**Agent Types**
- `story/`: Narrative generation (documentary, movie, then_vs_now)
- `shots/`: Visual prompt engineering with camera/context/style includes
- Special agents like `then_vs_now` require departure prompts and reference images

## Workflow Development

**Video Workflows** (`workflow/video/*.json`)
- Must be ComfyUI API or Workflow JSON format
- Use title tags for node discovery: `[prompt]`, `[image_in]`, `[video_out]`, `[seed]`
- FLFI2V workflows use `[image_in_first]` and `[image_in_last]` tags

**Image Workflows** (`workflow/image/*.json`)
- Tags: `[positive]`, `[negative]`, `[ksampler]`, `[vae]`, `[save]`
- IPAdapter workflows use `[reference]` and `[ipadapter]` tags

**Camera LoRA System**
- Up to 4 simultaneous camera types via `LORA_NODES` array
- Each camera has high/low noise LoRA with trigger keywords
- Configured in `CAMERA_LORA_MAPPING` dictionary

## Important Patterns

**Error Handling**
- Image generation includes retry mechanism (`IMAGE_GENERATION_MAX_RETRIES`)
- Graceful degradation with `CONTINUE_ON_PARTIAL_IMAGE_FAILURE`
- Render timeout via `VIDEO_RENDER_TIMEOUT`

**Concurrency**
- Per-engine concurrent limits in `CONCURRENT_GENERATION_LIMITS`
- Queue-based processing with WebSocket progress updates
- Atomic file locking for project metadata

**Path Resolution**
- Use `config.resolve_path()` for cross-drive compatibility
- Supports both relative and absolute paths
- Handles `output/` prefix specially for different drives

**Testing Patterns**
- Integration tests in `tests/integration/`
- Unit tests for specific modules
- Use `pytest` with fixtures from `tests/conftest.py`
- Mock external services (ComfyUI, LLM providers) in tests

## Common Issues

**ComfyUI Connection**
- Must be running on `http://127.0.0.1:8188`
- Check `COMFY_OUTPUT_DIR` points to correct ComfyUI installation
- Workflow JSON must match ComfyUI API format

**Workflow Detection**
- If workflow not detected, add title tags to nodes
- Check workflow is valid JSON (no trailing commas)
- Verify node IDs are strings, not integers

**Web UI CORS**
- Backend uses `WEB_UI_CORS_ORIGINS` from config
- Includes Private Network Access header for local development
- Configure `BACKEND_HOST` and `FRONTEND_HOST` for network access

**Path Issues**
- Use forward slashes in config (`"output/projects"`)
- Use `config.resolve_path()` when combining paths
- Check `ABS_OUTPUT_DIR` and `ABS_PROJECTS_DIR` for resolved paths

## File Organization

```
core/               # Core pipeline logic
├── main.py        # CLI entry point and pipeline orchestrator
├── llm_engine.py  # LLM provider abstraction
├── agent_loader.py # Agent prompt management
├── story_engine.py # Story generation
├── shot_planner.py # Shot planning with camera/prompts
├── image_generator.py # Image generation (Gemini/ComfyUI)
├── comfy_client.py # ComfyUI API client
├── prompt_compiler.py # Workflow compilation
└── project_manager.py # Project persistence and crash recovery

web_ui/
├── backend/       # FastAPI backend
│   ├── main.py    # FastAPI app and WebSocket
│   ├── api/       # API route handlers
│   ├── models/    # Pydantic models
│   └── services/  # Business logic
└── frontend/      # Next.js frontend
    └── src/
        ├── app/   # Next.js App Router pages
        ├── components/ # React components
        └── services/   # API client

agents/            # LLM agent prompts
workflow/          # ComfyUI workflow templates
docs/              # Comprehensive guides
tests/             # Test suite
output/            # Generated projects and media
```

## Development Workflow

**Adding New Features**
1. Start with CLI implementation in `core/`
2. Add API endpoints in `web_ui/backend/api/`
3. Create frontend components in `web_ui/frontend/src/components/`
4. Add tests in `tests/`
5. Update documentation in `docs/`

**Debugging Tips**
- Check `startup_debug.txt` for web UI initialization issues
- Use `/health` endpoint to verify configuration
- WebSocket connections at `/api/ws/progress/{project_id}`
- Logs in `output/logs/` with rotation configured

**Performance Considerations**
- LLM calls use batching with `MAX_PARALLEL_BATCH_THREADS`
- Image/video generation respects `CONCURRENT_GENERATION_LIMITS`
- Large prompts may need `LLM_MAX_TOKENS` increased
- ComfyUI is VRAM-intensive - limit concurrent generations accordingly