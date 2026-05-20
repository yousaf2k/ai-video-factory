# AI Video Factory

**Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration.**
<br><br>
![Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration](https://repository-images.githubusercontent.com/1152487184/341c4b55-bcdb-4d80-a0e7-9838ed32571f)

## Features

- 🎬 **End-to-End Pipeline**: From idea to final video in 7 automated steps
- 🎨 **Dual Image Generation**: Gemini API or ComfyUI (Flux/SDXL/Flux 2) support with up to 2K resolution
- 🎥 **Advanced Video Generation**: Wan 2.2 model with ComfyUI integration and HD resolution options (720p/1080p)
- 🚁 **Multi-Camera LoRA System**: Combine multiple camera movements (drone, orbit, dolly, zoom, etc.)
- 🔄 **Flexible Motion Control**: Override departure prompts for custom shot-to-shot transitions
- 🎤 **Narration Support**: Optional TTS with ElevenLabs, Edge-TTS, or ComfyUI voices
- 💾 **Project Management**: Crash recovery, thumbnail management (upload/regenerate), and selective regeneration
- 🌐 **Modern Web UI**: FastAPI backend with a responsive React frontend for visual story editing and generation queue management
- 📚 **Comprehensive Documentation**: Extensive guides and API references in `docs/`
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

Open your browser to `http://localhost:3000` to access the visual story editor and project manager. The backend API runs on `http://127.0.0.1:8000`.

## Project Structure

```bash
ai_video_factory/
├── core/              # Core pipeline logic (story engine, shot planner, comfy client)
├── web_ui/            # Web application
│   ├── backend/       # FastAPI backend and project services
│   └── frontend/      # React/Next.js frontend
├── agents/            # Multi-category LLM agents (Documentary, Movie, Then Vs Now)
├── workflow/          # ComfyUI JSON templates for images, videos, and TTS
├── docs/              # Comprehensive guides (LoRA, ComfyUI setup, API ref)
├── tests/             # Automated test suite
├── output/            # Generated projects, media, and metadata
├── config.py          # Centralized configuration and path management
└── core/main.py       # Main CLI entry point
```

### AI Agents Folder

This folder contains system prompts for LLM agents used in different stages of video generation. The system uses a modular approach, combining base rules, context-specific data, and stylistic guidelines.

#### Agent Categories

```bash
agents/
├── story/             # Narrative generation
│   ├── documentary/   # Realistic, historical, and educational
│   ├── movie/         # Cinematic fiction and genres
│   └── then_vs_now/   # Comparative storytelling
└── shots/             # Visual prompt engineering
    ├── cameras/       # Specialized camera configurations
    ├── contexts/      # Subject-specific visual data
    └── styles/        # Artistic and atmospheric styles
```

#### Available Story Agents

- **Documentary**: `default`, `netflix_documentary`, `youtube_documentary`, `time_traveler`.
- **Historical**: `greek_classical`, `roman_kingdom`, `indus_valley`, `plague_of_athens`.
- **Movie**: `action`, `horror`.
- **Specialized**: `then_vs_now` ⭐, `selfie_vlogger`.

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
- **Images**: Up to 2048x2048 (Flux/Gemini)
- **Videos**: 720p or 1080p (Wan 2.2)

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

- 🎮 **[ComfyUI Setup](docs/setup/COMFYUI_SETUP_CHECKLIST.md)**: Hardware requirements and workflow installation.
- 📸 **[Camera & LoRA Guide](docs/guides/CAMERA_LORA_GUIDE.md)**: Master the multi-camera motion system.
- 🛠️ **[API Reference](docs/API_REFERENCE.md)**: Complete backend documentation.
- 📚 **[Full Index](docs/DOCS_INDEX.md)**: Browse all available documentation.
