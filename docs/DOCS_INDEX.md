# 📚 AI Video Factory — Documentation

Welcome to the AI Video Factory documentation. Start with the entry point for your goal below, or browse the full index.

> **For AI coding agents:** the canonical instruction file is [`AGENTS.md`](../AGENTS.md) at the repository root.

---

## 🗂️ Documentation Map

```
docs/
├── getting-started/    # New here? Quick start, setup checklist, configuration reference
├── setup/              # Backend & provider installation (ComfyUI, Gemini, TTS, local LLMs)
├── guides/             # How-to guides: pipeline, camera LoRA, video length, regeneration…
├── features/           # Feature documentation: Asset Library, Then Vs Now, ASMR Glass Cutting
├── agents/             # Guides for the built-in LLM story/shots agents
├── reference/          # API reference & security guide
└── development/        # Historical: plans, fixes, testing notes, walkthroughs, archive
```

---

## 🎯 Quick Start for New Users

1. **[README.md](../README.md)** — Project overview and quick start
2. **[Quick Start](getting-started/QUICK_START.md)** — Get running in minutes
3. **[Setup Checklist](getting-started/SETUP_CHECKLIST.md)** — Step-by-step setup verification
4. **[Configuration Guide](getting-started/CONFIGURATION.md)** — Complete `config.py` reference
5. **[Example Ideas](getting-started/example_ideas.md)** — Sample video ideas to try

---

## 📖 Documentation by Category

### Getting Started (`getting-started/`)

| Document | Description |
|----------|-------------|
| [Quick Start](getting-started/QUICK_START.md) | Fastest path to your first video |
| [Netflix Quick Start](getting-started/QUICK_START_NETFLIX.md) | Netflix-style documentary walkthrough |
| [Setup Checklist](getting-started/SETUP_CHECKLIST.md) | Complete setup guide with checkboxes |
| [Configuration Guide](getting-started/CONFIGURATION.md) ⭐ | Complete `config.py` reference |
| [Example Ideas](getting-started/example_ideas.md) | Sample ideas for your first runs |

### Setup (`setup/`)

| Document | Description |
|----------|-------------|
| [ComfyUI Setup](setup/COMFYUI_SETUP_CHECKLIST.md) | ComfyUI installation and configuration |
| [Gemini Setup](setup/README_GEMINI_SETUP.md) | Gemini API configuration |
| [ElevenLabs Setup](setup/ELEVENLABS_SETUP.md) | ElevenLabs TTS configuration |
| [Ollama Setup](setup/OLLAMA_SETUP.md) | Local LLM via Ollama |
| [LM Studio Setup](setup/LMSTUDIO_SETUP.md) / [Guide](setup/LMSTUDIO_SETUP_GUIDE.md) | Local LLM via LM Studio |

### How-To Guides (`guides/`)

| Document | Description |
|----------|-------------|
| [Workflow Guide](guides/WORKFLOW_GUIDE.md) ⭐ | Complete 7-step pipeline overview |
| [Workflow Diagram](guides/WORKFLOW_DIAGRAM.md) | Visual system architecture |
| [Camera LoRA Guide](guides/CAMERA_LORA_GUIDE.md) ⭐ | Multi-camera LoRA system |
| [ComfyUI Image Guide](guides/COMFYUI_IMAGE_GUIDE.md) / [QuickRef](guides/COMFYUI_IMAGE_QUICKREF.md) | Image generation setup |
| [Video Length Guide](guides/VIDEO_LENGTH_GUIDE.md) / [QuickRef](guides/VIDEO_LENGTH_QUICKREF.md) / [Diagram](guides/VIDEO_LENGTH_DIAGRAM.md) | Video length configuration |
| [Auto Video Length](guides/AUTO_VIDEO_LENGTH_QUICK_GUIDE.md) | Automatic total-length targeting |
| [Video Regeneration Guide](guides/VIDEO_REGENERATION_GUIDE.md) / [QuickRef](guides/VIDEO_REGEN_QUICKREF.md) | Regenerate failed shots |
| [Project Guide](guides/SESSION_GUIDE.md) / [Visual Guide](guides/SESSION_VISUAL_GUIDE.md) | Project management |
| [Project Overview](guides/PROJECT_OVERVIEW.md) | Project structure and implementation |
| [Batch Videos](guides/BATCH_VIDEOS_README.md) / [Idea Files](guides/IDEA_FILE_README.md) | Batch processing |
| [Multi-LLM Summary](guides/MULTI_LLM_SUMMARY.md) | Supported LLM providers |
| [Gemini API](guides/GEMINI_API_SUMMARY.md) / [Gemini Web](guides/GEMINI_WEB_SUMMARY.md) | Generation backends |
| [Logging](guides/LOGGING_README.md) / [Usage](guides/LOGGING_USAGE_SUMMARY.md) | Logging system |
| **MiniMax H3 Prompt Guides** ([base](guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_base_en.md), [ref](guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_ref_en.md)) | Prompt-writing rules for MiniMax H3 video |

### Features (`features/`)

| Document | Description |
|----------|-------------|
| [Asset Library](features/ASSET_LIBRARY.md) 🆕 | Nested-category asset library and per-shot references |
| **Then Vs Now** ([Quick Start](features/ThenVsNow/THEN_VS_NOW_QUICKSTART.md)) | FLFI2V reunion videos — scene requirements, departure videos, motion prompts, thumbnails, implementation |
| **ASMR Glass Cutting** ([User Guide](features/asmr_glass_cutting/ASMR%20Glass%20Cutting%20-%20User%20Guide.md)) | ASMR project type — usage and implementation |

Key Then Vs Now docs: [Scene Requirements](features/ThenVsNow/THEN_VS_NOW_SCENE_REQUIREMENTS.md) · [How to Make Departure Videos](features/ThenVsNow/HOW_TO_MAKE_DEPARTURE_VIDEOS.md) · [FLFI2V Video Generation Logic](features/ThenVsNow/FLFI2V_VIDEO_GENERATION_LOGIC.md) · [Motion Prompt Guide](features/ThenVsNow/THEN_VS_NOW_MOTION_PROMPT_GUIDE.md) · [Thumbnail Guide](features/ThenVsNow/THEN_VS_NOW_THUMBNAIL_GUIDE.md) · [FLFI2V Implementation](features/ThenVsNow/THEN_VS_NOW_FLFI2V_IMPLEMENTATION.md)

### Agent Guides (`agents/`)

The prompt templates themselves live in the [`agents/`](../agents/) directory — see [`AGENTS.md`](../AGENTS.md) for layout and authoring rules.

| Document | Description |
|----------|-------------|
| [Netflix Documentary Agent](agents/NETFLIX_DOCUMENTARY_AGENT.md) / [Summary](agents/NETFLIX_AGENT_SUMMARY.md) | Netflix-style documentary agent |
| [YouTube Agent Quick Start](agents/YOUTUBE_AGENT_QUICK_START.md) / [Checklist](agents/YOUTUBE_AGENT_CHECKLIST.md) | YouTube documentary agent |
| [Prehistoric POV Quick Start](agents/PREHISTORIC_POV_QUICKSTART.md) / [Guide](agents/PREHISTORIC_POV_GUIDE.md) | Prehistoric POV agents |
| [Selfie Vlogger Guide](agents/SELFIE_VLOGGER_GUIDE.md) | Selfie vlog agent |

### Reference (`reference/`)

| Document | Description |
|----------|-------------|
| [API Reference](reference/API_REFERENCE.md) ⭐ | Core module API documentation |
| [Security Guide](reference/SECURITY_GUIDE.md) | API key encryption and secrets management |

### Development & History (`development/`)

Historical records — implementation plans, bug-fix notes, and test reports. Useful for archaeology, not required reading.

| Folder | Contents |
|--------|----------|
| [plans/](development/plans/) | Feature implementation plans and summaries |
| [fixes/](development/fixes/) | Bug fix summaries (scene graph, shot planner, socket exhaustion, …) |
| [testing/](development/testing/) | Test results and LLM provider verification ([Test Results](development/testing/TEST_RESULTS.md), [Provider Status](development/testing/LLM_PROVIDER_STATUS.md)) |
| [walkthroughs/](development/walkthroughs/) | Local LLM providers, scene grouping, Gemini Flow walkthroughs |
| [code_reviews/](development/code_reviews/) | Code review reports |
| [archive/](development/archive/) | Superseded feature summaries and design docs |

---

## 🚀 Quick Commands

```bash
# Generate a video
python core/main.py --idea "Your video idea"

# With custom settings
python core/main.py --idea "Your idea" --max-shots 5 --shot-length 8

# Override workflows for a run
python core/main.py --idea "Your idea" --video-workflow minimax_h3_i2v_8s --image-workflow krea2_reference

# List agents / projects
python core/main.py --list-agents
python core/main.py --list-projects

# Enable narration
python core/main.py --idea "Your idea" --tts-voice en-US-AriaNeural

# Regenerate specific shots
python regenerate.py --project project_XXXXXXXX --shots 1,3,5

# Start the Web UI
python web_ui/start.py

# Run tests
python run_tests.py
```

---

## 🔍 Key Features Documentation

### Asset Library 🆕
Nested-category asset library with per-shot references (library refs `i/{id}` and project-media refs `p/{project}/…`). Filename-as-metadata design.
**See:** [Asset Library](features/ASSET_LIBRARY.md)

### Multi-Camera LoRA System
Combine multiple camera movements in a single shot:
```python
"camera": "drone, orbit"   # or ["dolly", "zoom"]
```
**See:** [Camera LoRA Guide](guides/CAMERA_LORA_GUIDE.md)

### Multiple Video Models
Wan 2.2 (t2v / i2v / FLFI2V, VFI + super-resolution), MiniMax H3, and LTX-2 workflows in `workflow/video/`; select per run with `--video-workflow`.
**See:** [MiniMax H3 Prompt Guides](guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_base_en.md), [Then Vs Now Quick Start](features/ThenVsNow/THEN_VS_NOW_QUICKSTART.md)

### Dual Image Generation
Gemini API, ComfyUI (Flux 2, Krea 2 reference, HiDream, Z-Image Turbo), or GeminiWeb browser automation.
**See:** [Configuration Guide](getting-started/CONFIGURATION.md), [ComfyUI Image Guide](guides/COMFYUI_IMAGE_GUIDE.md)

---

## 🎓 Learning Path

- **Beginner:** [README](../README.md) → [Quick Start](getting-started/QUICK_START.md) → [Setup Checklist](getting-started/SETUP_CHECKLIST.md)
- **Intermediate:** [Workflow Guide](guides/WORKFLOW_GUIDE.md) → [Configuration Guide](getting-started/CONFIGURATION.md) → [Camera LoRA Guide](guides/CAMERA_LORA_GUIDE.md)
- **Advanced:** [API Reference](reference/API_REFERENCE.md) → [Asset Library](features/ASSET_LIBRARY.md) → [AGENTS.md](../AGENTS.md)

---

## 🔄 Documentation Updates

**Last Updated:** October 4, 2026
**Version:** 5.1 (documentation reorganization: getting-started / setup / guides / features / agents / reference / development)

---
**Happy Video Creating! 🎬**
