# Project Overview: AI Video Factory

The **AI Video Factory** is an automated pipeline for generating cinema-quality videos from text ideas. 

## 🏗️ Architecture & Core Components

- **`core/`**: The engine of the project.
  - `main.py`: CLI entry point.
  - `story_engine.py`: Handles initial story generation and narration text with LLMs.
  - `shot_planner.py`: Breaks a story into individual scenes and detailed shot plans.
  - `comfy_client.py`: Interfaces with the ComfyUI API for generation.
  - `prompt_compiler.py`: Compiles high-level shot plans into low-level ComfyUI JSON workflows.
  - `project_manager.py`: Orchestrates project state, ensuring recoverability and progress tracking.

- **`web_ui/`**: A modern visual story editor and project management dashboard.
  - **Backend (`fastapi`)**: Manages project inventory, story editing, and the generation queue.
  - **Frontend (`next.js`)**: Provides a visual interface with drag-and-drop shot management, real-time status updates, and interactive story refinement.

- **`agents/`**: System prompts (Markdown) for specialized LLM tasks (story generation, shot planning, narration script engineering, and video motion control).

- **`workflow/`**: JSON templates for ComfyUI. These are used as blueprints for image generation (Flux/SDXL), video rendering (Wan 2.2), and text-to-speech (ElevenLabs/Edge-TTS).

## 🔄 Data Flow
1. **Idea Generation**: The user provides a text idea.
2. **Story Development**: The `StoryEngine` uses an LLM to expand the idea into a multi-scene narrative.
3. **Shot Planning**: The story is broken into cinematic shots with detailed visual and motion descriptions.
4. **Project Setup**: A directory structure is created in `output/projects/{project_id}` including `meta.json`, `story.json`, and `shots.json`.
5. **Asset Generation**:
   - **Images**: Generated using ComfyUI (Flux/SDXL) or Gemini API.
   - **Videos**: Rendered from images using ComfyUI (Wan 2.2) and motion-controlled LoRAs.
   - **Narration**: Optional audio generation using TTS providers.
6. **Project Management**: Selective regeneration of shots or batch video creation for larger projects.

## 💾 Project Storage
All project data resides in `output/projects/{project_id}/`.
- `/images`: Generated reference images for each shot.
- `/videos`: Final rendered cinematic video clips.
- `meta.json`: Progress reporting and high-level project metadata.
