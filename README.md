# AI Video Factory

**Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration.**
<br><br>
![Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration](https://repository-images.githubusercontent.com/1152487184/341c4b55-bcdb-4d80-a0e7-9838ed32571f)

## Features

- 🎬 **End-to-End Pipeline**: From idea to final video in 7 automated steps
- 🎨 **Dual Image Generation**: Gemini API or ComfyUI (Flux/SDXL) support
- 🎥 **Advanced Video Generation**: Wan 2.2 model with ComfyUI integration
- 🚁 **Multi-Camera LoRA System**: Combine multiple camera movements (drone, orbit, dolly, zoom, etc.)
- 🎤 **Narration Support**: Optional TTS with multiple voice options
- 💾 **Project Management**: Crash recovery and selective regeneration
- 🔧 **Highly Configurable**: Customize every aspect of generation
- 🌐 **Web UI**: Modern Next.js frontend and FastAPI backend for visual story editing
- 📚 **Comprehensive Documentation**: Extensive guides and API references in `docs/`
- 🔄 **Batch Processing**: Automatically generate multiple videos from a list of prompts

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set your Gemini API key

```bash
export GEMINI_API_KEY="your_api_key_here"
```

**Start ComfyUI with Wan 2.2 workflow**
**(ComfyUI must be running on http://127.0.0.1:8188)**

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
├── core/              # Core pipeline orchestration and generators
├── web_ui/            # Visual interface
│   ├── backend/       # FastAPI backend for project and story APIs
│   └── frontend/      # Next.js frontend for visual story editing
├── agents/            # Prompts for LLM agents (story, narration, image, etc.)
├── workflow/          # ComfyUI JSON workflows (images, videos, TTS)
├── docs/              # Comprehensive documentation and guides
├── tests/             # Automated test suite
├── output/            # Generated projects, images, videos, and metadata
├── config.py          # Centralized configuration settings
├── core/main.py       # Main CLI entry point
├── projects.py        # CLI for project management
├── regenerate.py      # CLI for regenerating specific shots
└── batch_videos.py    # Batch video generation utility
```

### AI Agents Folder

This folder contains system prompts for LLM agents used in different stages of video generation.

#### Agent Types

```bash

agents/
├── story/         - Story generation agents
├── narration/     - Narration script agents
├── image/         - Image prompt engineering agents
└── video/         - Video motion/camera agents
```

#### How to Create a Custom Agent

1. **Navigate to the appropriate folder** (e.g., `agents/story/`)

2. **Create a new `.md` file** with your agent name (e.g., `my_custom_agent.md`)

3. **Write the system prompt** following this template:

   ```bash
   You are a [role description]. Your task is to [task description].

   ## Guidelines

   1. [Guideline 1]
   2. [Guideline 2]
   ...

   ## Output Format

   [Specify the expected output format]

   {USER_INPUT}
   ```

4. **Use the agent** by specifying its name:
   ```bash
   python core/main.py --story-agent my_custom_agent
   ```

## Available Agents

### Story Agents (`agents/story/`)

- `default.md` - Cinematic documentary style
- `dramatic.md` - Emotional, character-driven narratives
- `documentary.md` - Factual, educational content
- `time_traveler.md` ⭐ - First-person narratives from a time traveler's perspective using historical facts

### Shots Agents (`agents/shots/`)

- `default.md` - Standard shot prompt engineering
- `artistic.md` - Artistic, aesthetic-focused prompts
- `time_traveler.md` ⭐ - Photorealistic historical images from first-person time traveler perspective with DSLR photography

## Agent Prompt Guidelines

1. **Be Specific**: Clearly define the agent's role and task
2. **Include Examples**: Show examples of good inputs/outputs
3. **Define Format**: Specify the exact output format expected
4. **Use Placeholders**: Include `{USER_INPUT}` where user input should be inserted
5. **Keep it Focused**: Each agent should have a clear, single purpose

## Testing Your Agent

To test a new agent:

```bash
# List all agents
python core/main.py --list-agents

# Test with a simple idea
python core/main.py --idea "Test idea" --story-agent my_custom_agent --step 2
```
