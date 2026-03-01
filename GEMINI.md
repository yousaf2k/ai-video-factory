# Gemini CLI Context: AI Video Factory

This document provides essential context for interacting with the AI Video Factory project using the Gemini CLI.

## Project Overview

**AI Video Factory** is a comprehensive automated pipeline for generating cinematic videos from simple text ideas. It orchestrates a multi-step process involving story generation, shot planning, image generation, video rendering, and narration.

### Key Technologies
- **Python**: Core application logic.
- **LLMs**: Primarily **Google Gemini**, but also supports OpenAI, Zhipu, Qwen, Kimi, Ollama, and LM Studio.
- **Image/Video Generation**: **ComfyUI** (supporting Flux, SDXL, and Wan 2.2 models).
- **Narration**: **ElevenLabs**, **Edge-TTS** (local), or ComfyUI-based TTS.
- **Web UI**: **FastAPI** backend with a modern frontend.

### Architecture
- `core/`: The engine of the application, including:
    - `main.py`: Entry point for the CLI pipeline.
    - `story_engine.py`: Handles initial story and narration text generation.
    - `shot_planner.py`: Breaks scenes into specific shots with visual/motion prompts.
    - `comfy_client.py`: Interfaces with the ComfyUI API.
    - `session_manager.py`: Manages session state, enabling crash recovery and resumption.
- `agents/`: System prompts (Markdown) that define the "personality" and rules for different pipeline stages.
- `workflow/`: JSON workflow templates for ComfyUI (images, video, voice).
- `web_ui/`: Backend and frontend code for the web interface.

## Building and Running

### Prerequisites
1.  Python 3.10+
2.  ComfyUI running locally (typically on `http://127.0.0.1:8188`).
3.  API Keys (Gemini, ElevenLabs, etc.) configured in a `.env` file.

### Installation
```bash
pip install -r requirements.txt
```

### Key Commands
- **Run Pipeline (CLI):**
  ```bash
  python core/main.py --idea "A futuristic city in the clouds"
  ```
- **Run Web UI:**
  ```bash
  python web_ui/start.py
  ```
- **Run Tests:**
  ```bash
  python run_tests.py
  # OR
  pytest
  ```
- **List Available Agents:**
  ```bash
  python core/main.py --list-agents
  ```

## Development Conventions

### Agent-Based Customization
The system uses "Agents" defined in Markdown files within the `agents/` directory. Each file contains a system prompt and guidelines for the LLM.
- **To create a new agent:** Add a `.md` file to `agents/{type}/` following the existing templates.
- **To use a custom agent:** Use flags like `--story-agent agent_name`.

### Session Management
All generation data is stored in `output/sessions/{session_id}/`.
- `meta.json`: High-level session progress.
- `story.json`: The generated story/script.
- `shots.json`: Detailed shot plans.
- `images/`: Generated reference images.
- `videos/`: Final rendered video clips.

### Configuration
Configuration is managed in `config.py` and can be overridden by environment variables in `.env`. Key settings include:
- `LLM_PROVIDER`: Choose your primary LLM.
- `IMAGE_GENERATION_MODE`: `gemini` or `comfyui`.
- `IMAGE_WORKFLOW`: Which ComfyUI workflow to use (e.g., `flux2`).

### Logging
Logs are stored in the `logs/` directory. The logging level can be configured in `config.py`.

## Documentation
Refer to the `docs/` directory for detailed guides on specific features:
- `COMFYUI_SETUP_CHECKLIST.md`: Setting up the generation backend.
- `CAMERA_LORA_GUIDE.md`: Using LoRAs for advanced camera movements.
- `SESSION_GUIDE.md`: Deep dive into how sessions work.
- `DOCS_INDEX.md`: A complete index of all documentation.
