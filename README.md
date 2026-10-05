# AI Video Factory

**Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration.**
<br><br>
![Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration](https://repository-images.githubusercontent.com/1152487184/341c4b55-bcdb-4d80-a0e7-9838ed32571f)

## Features

- 🎬 **End-to-End Pipeline**: From idea to final video in 7 automated steps
- 🧠 **Multi-LLM Support**: Gemini, OpenAI, Zhipu, DeepSeek, Qwen, Kimi, Ollama, and LM Studio
- 🎨 **Multiple Image Engines**: Gemini API, ComfyUI (Flux 2, Krea 2 reference, HiDream, Z-Image Turbo), or GeminiWeb browser automation — up to 2K resolution
- 🎥 **Multiple Video Models**: Wan 2.2 (t2v/i2v/FLFI2V with VFI + super-resolution), MiniMax H3, and LTX-2 via ComfyUI, with HD options (720p/1080p)
- 🚁 **Multi-Camera LoRA System**: Combine multiple camera movements (drone, orbit, dolly, zoom, etc.)
- 🔊 **Sound FX Generation**: Per-shot sound effects via MMAudio workflows
- 🖼️ **Asset Library**: Nested-category asset library (images/videos/audio/music) with per-shot reference injection
- 👤 **Unified Character References**: Single `image_prompt` schema with 8-view character reference sheets (full-body + face close-ups)
- 🎤 **Narration Support**: Optional TTS with ElevenLabs, Edge-TTS, or ComfyUI voices
- 💾 **Project Management**: Crash recovery, thumbnail management (upload/regenerate), and selective regeneration
- 🌐 **Modern Web UI**: FastAPI backend with a responsive React frontend for visual story editing and generation queue management
- ⏳ **Batch Queue**: Efficiently manage multiple generations with group selection and status tracking

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root with your API keys:

```bash
GEMINI_API_KEY="your_api_key_here"
# Optional:
OPENAI_API_KEY="your_openai_key"
ELEVENLABS_API_KEY="your_elevenlabs_key"
```

**Start ComfyUI** (must be running on `http://127.0.0.1:8188`)

### Generate a Video (CLI)

```bash
python core/main.py --idea "A beautiful sunset over the ocean"
```

### Start the Web UI

```bash
python web_ui/start.py
```

Open your browser to `http://localhost:3000` to access the visual story editor, asset library, and project manager. The backend API runs on `http://127.0.0.1:8000`.

## Project Structure

```bash
ai_video_factory/
├── core/              # Core pipeline logic (story engine, shot planner, comfy client)
├── web_ui/            # Web application
│   ├── backend/       # FastAPI backend (api/, services/, models/) and WebSocket progress
│   └── frontend/      # React/Next.js frontend
├── agents/            # Multi-category LLM agent prompts (story/, shots/)
├── workflow/          # ComfyUI JSON templates (image/, video/, soundfx/, voice/)
├── docs/              # Comprehensive guides, setup checklists, and API reference
├── tests/             # Automated test suite (unit + integration)
├── output/            # Generated projects, media, and the asset library
├── config.py          # Centralized configuration and path management
└── AGENTS.md          # Canonical instructions for AI coding agents
```

### AI Agents Folder

This folder contains system prompts for LLM agents used in different stages of video generation. The system uses a modular approach, combining base rules, context-specific data, and stylistic guidelines.

#### Agent Categories

```bash
agents/
├── story/             # Narrative generation
│   ├── asmr/          # ASMR glass cutting project type
│   ├── documentary/   # Realistic, historical, and educational (with _base/_contexts/_styles)
│   ├── movie/         # Cinematic fiction and genres (with _base/_contexts/_styles)
│   ├── system/        # Master script guidelines
│   └── then_vs_now/   # Comparative storytelling (FLFI2V)
└── shots/             # Visual prompt engineering
    ├── base/          # Standard shot rules
    ├── cameras/       # Specialized camera configurations
    ├── contexts/      # Subject-specific visual data
    ├── soundfx/       # Sound FX prompt rules
    ├── styles/        # Artistic and atmospheric styles
    └── videoprompt/   # Video-model-specific prompt rules (e.g. MiniMax H3)
```

#### Available Story Agents

- **Documentary**: `default`, `documentary`, `netflix_documentary`, `youtube_documentary`, `youtube_news`, `time_traveler`, plus historical packs (`greek_*`, `roman_kingdom`, `indus_valley`, `plague_of_athens`, `persian_empire`, `prehistoric_*`).
- **Movie**: `action`, `horror`, `comedy`, `cyberpunk`, `drama`, `fantasy`, `mystery`, `romance`, `scifi`, `thriller`, `western`.
- **Specialized**: `asmr/asmr_glass_cutting`, `then_vs_now` ⭐, `selfie_vlogger`.

#### How to Create a Custom Agent

1. **Select a category** (e.g., `agents/story/documentary/`)
2. **Create a new `.md` file** (e.g., `my_special_agent.md`)
3. **Write the system prompt** using the `{USER_INPUT}` placeholder for the dynamic prompt.
4. **Leverage Modularity**: You can include base files and contexts using the `#include` directive (handled by `AgentLoader`).

```bash
python core/main.py --story-agent my_special_agent
```

## Advanced Usage

### Resolution Selection
Customize output quality via `config.py` or the Web UI:
- **Images**: Up to 2048x2048 (Flux 2 / Krea 2 / Gemini)
- **Videos**: 720p or 1080p (Wan 2.2, MiniMax H3, LTX-2)

### Workflow Overrides
Pick the generation workflow per run without touching `config.py`:

```bash
python core/main.py --idea "..." --video-workflow minimax_h3_i2v_8s --image-workflow krea2_reference
```

### Departure Overrides
For shots requiring specific motion transitions, use the **Departure Prompt** field in the Web UI to manually guide the AI's motion prediction.

### Batch Processing
Run multiple ideas from a text file:
```bash
python batch_videos.py --file ideas.txt
```

---

## Documentation & Support

For deep dives into specific subsystems, refer to the following guides:

- 🤖 **[AGENTS.md](AGENTS.md)**: Canonical guidance for AI coding agents working on this repo.
- 🎮 **[ComfyUI Setup](docs/setup/COMFYUI_SETUP_CHECKLIST.md)**: Hardware requirements and workflow installation.
- 📸 **[Camera & LoRA Guide](docs/guides/CAMERA_LORA_GUIDE.md)**: Master the multi-camera motion system.
- 🖼️ **[Asset Library](docs/features/ASSET_LIBRARY.md)**: Asset library design and shot references.
- 🛠️ **[API Reference](docs/reference/API_REFERENCE.md)**: Complete backend documentation.
- 📚 **[Full Index](docs/DOCS_INDEX.md)**: Browse all available documentation.
