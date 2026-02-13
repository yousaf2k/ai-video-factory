# 📚 AI Video Factory - Documentation Index

Complete guide to all documentation for the AI Video Factory system.

---

## 🎯 Quick Start for New Users

### Start Here:

1. **[README.md](../README.md)** - Project overview and quick start
2. **[Quick Start](QUICK_START.md)** - Get running in 5 minutes
3. **[Setup Checklist](SETUP_CHECKLIST.md)** - Step-by-step setup verification

---

## 📖 Documentation by Category

### Getting Started

| Document | Description |
|----------|-------------|
| [Quick Start](QUICK_START.md) | Fastest path to first video |
| [Setup Checklist](SETUP_CHECKLIST.md) | Complete setup guide with checkboxes |
| [ComfyUI Setup](COMFYUI_SETUP_CHECKLIST.md) | ComfyUI installation and configuration |
| [Gemini Setup](README_GEMINI_SETUP.md) | Gemini API configuration |

### Configuration

| Document | Description |
|----------|-------------|
| **[Configuration Guide](CONFIGURATION.md)** ⭐ | Complete config.py reference |
| **[Camera LoRA Guide](CAMERA_LORA_GUIDE.md)** ⭐ | Multi-camera LoRA system |
| [ComfyUI Image Guide](COMFYUI_IMAGE_GUIDE.md) | ComfyUI image generation setup |
| [ElevenLabs Setup](ELEVENLABS_SETUP.md) | ElevenLabs TTS configuration |

### Workflow & Pipeline

| Document | Description |
|----------|-------------|
| **[Workflow Guide](WORKFLOW_GUIDE.md)** ⭐ | Complete pipeline overview |
| [Session Guide](SESSION_GUIDE.md) | Session management |
| [Video Regeneration Guide](VIDEO_REGENERATION_GUIDE.md) | Regenerate failed shots |
| [Workflow Diagram](WORKFLOW_DIAGRAM.md) | Visual system architecture |

### Reference

| Document | Description |
|----------|-------------|
| **[API Reference](API_REFERENCE.md)** ⭐ | Complete API documentation |
| [Features Overview](COMPLETE_FEATURE_OVERVIEW.md) | All features explained |
| [Project Overview](PROJECT_OVERVIEW.md) | Project structure and implementation |
| [Implementation Summary](IMPLEMENTATION_SUMMARY.md) | Technical implementation details |

### Quick Reference

| Document | Description |
|----------|-------------|
| [ComfyUI Image QuickRef](COMFYUI_IMAGE_QUICKREF.md) | Image generation cheat sheet |
| [Video Length Guide](VIDEO_LENGTH_GUIDE.md) | Video length configuration |
| [Video Length QuickRef](VIDEO_LENGTH_QUICKREF.md) | Video length cheat sheet |
| [Video Regeneration QuickRef](VIDEO_REGEN_QUICKREF.md) | Regeneration quick reference |
| [Session Visual Guide](SESSION_VISUAL_GUIDE.md) | Visual session guide |
| [Features Summary](FEATURES_SUMMARY.md) | Feature summary |
| [New Features Summary](NEW_FEATURES_SUMMARY.md) | New features overview |
| [Final Feature Summary](FINAL_FEATURE_SUMMARY.md) | Final feature list |

### Testing

| Document | Description |
|----------|-------------|
| [Test Results](TEST_RESULTS.md) | System test results |

---

## 🎓 Learning Path

### Beginner (New to AI Video Factory)

1. **[README.md](../README.md)** - Understand what the system does
2. **[Quick Start](QUICK_START.md)** - Get your first video running
3. **[Setup Checklist](SETUP_CHECKLIST.md)** - Verify your setup
4. Create your first video!

### Intermediate (Understanding the System)

1. **[Workflow Guide](WORKFLOW_GUIDE.md)** - Understand the 7-step pipeline
2. **[Configuration Guide](CONFIGURATION.md)** - Learn all configuration options
3. **[Camera LoRA Guide](CAMERA_LORA_GUIDE.md)** - Master the multi-camera system
4. **[API Reference](API_REFERENCE.md)** - Understand the code structure

### Advanced (Customization & Development)

1. **[API Reference](API_REFERENCE.md)** - Complete API documentation
2. **[Camera LoRA Guide](CAMERA_LORA_GUIDE.md)** - Add custom cameras and LoRAs
3. **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Technical details
4. Study source code in `core/` directory

---

## 📋 Common Tasks

### "I want to set up the system"

1. Read [Quick Start](QUICK_START.md) (5 minutes)
2. Follow [Setup Checklist](SETUP_CHECKLIST.md) (step-by-step)
3. Configure ComfyUI: [ComfyUI Setup](COMFYUI_SETUP_CHECKLIST.md)

### "I need to understand how it works"

1. Read [Workflow Guide](WORKFLOW_GUIDE.md) (complete pipeline)
2. Study [Configuration Guide](CONFIGURATION.md) (all settings)
3. Review [Camera LoRA Guide](CAMERA_LORA_GUIDE.md) (multi-camera system)

### "Something isn't working"

1. Check [Setup Checklist](SETUP_CHECKLIST.md) (troubleshooting section)
2. Review [Gemini Setup](README_GEMINI_SETUP.md) (detailed troubleshooting)
3. Check [Test Results](TEST_RESULTS.md) (common issues)

### "I want to customize the system"

1. Read [Configuration Guide](CONFIGURATION.md) (all settings)
2. Study [Camera LoRA Guide](CAMERA_LORA_GUIDE.md) (add cameras)
3. Review [API Reference](API_REFERENCE.md) (code structure)

### "I want to use multiple cameras"

1. Read [Camera LoRA Guide](CAMERA_LORA_GUIDE.md) (complete guide)
2. Check [Configuration Guide](CONFIGURATION.md) (LORA_NODES setup)
3. See examples in the guide

---

## 🔍 Key Features Documentation

### Multi-Camera LoRA System

The AI Video Factory supports combining multiple camera movements in a single shot:

```python
# Single camera
"camera": "drone"

# Multiple cameras
"camera": "drone, orbit"
"camera": ["dolly", "zoom"]
```

**See:** [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)

### Dual Image Generation

Choose between Gemini API or ComfyUI for image generation:

```python
# In config.py
IMAGE_GENERATION_MODE = "gemini"  # or "comfyui"
```

**See:** [Configuration Guide](CONFIGURATION.md), [ComfyUI Image Guide](COMFYUI_IMAGE_GUIDE.md)

### Session Management & Crash Recovery

Full session tracking with automatic resume:

```bash
# List sessions
python sessions.py --list

# Resume session
python main.py --session session_20260210_174844

# Regenerate failed shots
python regenerate.py --session session_20260210_174844 --videos --failed-only
```

**See:** [Session Guide](SESSION_GUIDE.md), [Video Regeneration Guide](VIDEO_REGENERATION_GUIDE.md)

---

## 🚀 Quick Commands

```bash
# Generate a video
python main.py --idea "Your video idea"

# With custom settings
python main.py --idea "Your idea" --max-shots 5 --shot-length 8

# Enable narration
python main.py --idea "Your idea" --generate-narration --tts-voice en-US-AriaNeural

# Resume from session
python main.py --session session_20260210_174844

# Regenerate specific shots
python regenerate.py --session session_20260210_174844 --shots 1,3,5

# Test setup
python test_setup.py
```

---

## 📁 Project Structure

```
ai_video_factory/
├── README.md                    # Main project README
├── config.py                    # All configuration
├── main.py                      # Pipeline entry point
├── regenerate.py                # Regeneration utility
├── sessions.py                  # Session management CLI
│
├── docs/                        # 📚 Documentation (this folder)
│   ├── DOCS_INDEX.md           # ← You are here
│   ├── CONFIGURATION.md        # Configuration reference
│   ├── CAMERA_LORA_GUIDE.md    # Multi-camera system
│   ├── WORKFLOW_GUIDE.md       # Pipeline overview
│   ├── API_REFERENCE.md        # Complete API docs
│   ├── QUICK_START.md          # Get started fast
│   └── ... (see full list above)
│
├── core/                        # Core modules
│   ├── main.py                 # Pipeline orchestration
│   ├── story_engine.py         # Story generation
│   ├── scene_graph.py          # Scene breakdown
│   ├── shot_planner.py         # Shot planning
│   ├── image_generator.py      # Image generation
│   ├── prompt_compiler.py      # Workflow compilation
│   ├── comfy_client.py         # ComfyUI interface
│   └── session_manager.py      # Session management
│
├── agents/                      # Prompt templates
│   ├── story/                  # Story generation agents
│   ├── image_prompt/           # Image prompt agents
│   ├── video_motion/           # Video motion agents
│   └── narration/              # Narration agents
│
├── workflow/                    # ComfyUI workflows
│   ├── video/                  # Video generation
│   ├── image/                  # Image generation
│   └── voice/                  # TTS workflows
│
├── input/                       # Input files
│   └── story.txt               # Default idea input
│
└── output/                      # Output files
    └── sessions/               # Session folders
```

---

## 🎯 Decision Tree

```
Do you want to...
│
├─ Start using the system immediately?
│  └─→ Read [Quick Start](QUICK_START.md)
│
├─ Understand how the pipeline works?
│  └─→ Read [Workflow Guide](WORKFLOW_GUIDE.md)
│
├─ Configure the system?
│  └─→ Read [Configuration Guide](CONFIGURATION.md)
│
├─ Use multiple camera movements?
│  └─→ Read [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)
│
├─ Set up the system step-by-step?
│  └─→ Read [Setup Checklist](SETUP_CHECKLIST.md)
│
├─ Troubleshoot issues?
│  └─→ Read [Setup Checklist](SETUP_CHECKLIST.md) (troubleshooting section)
│
├─ Customize or extend the system?
│  └─→ Read [API Reference](API_REFERENCE.md)
│
├─ Regenerate failed videos?
│  └─→ Read [Video Regeneration Guide](VIDEO_REGENERATION_GUIDE.md)
│
└─ Find specific documentation?
   └─→ Use this index (DOCS_INDEX.md)
```

---

## 💡 Tips

1. **First time?** Start with [README.md](../README.md), then [Quick Start](QUICK_START.md)
2. **Configuration?** See [Configuration Guide](CONFIGURATION.md) for all settings
3. **Multi-camera?** Read [Camera LoRA Guide](CAMERA_LORA_GUIDE.md) completely
4. **Having trouble?** Check [Setup Checklist](SETUP_CHECKLIST.md) troubleshooting section
5. **Development?** Use [API Reference](API_REFERENCE.md) as your guide
6. **Visual learner?** [Workflow Diagram](WORKFLOW_DIAGRAM.md) has architecture diagrams

---

## 📞 Quick Links

### Setup
- [Quick Start](QUICK_START.md)
- [Setup Checklist](SETUP_CHECKLIST.md)
- [ComfyUI Setup](COMFYUI_SETUP_CHECKLIST.md)
- [Gemini Setup](README_GEMINI_SETUP.md)

### Configuration
- [Configuration Guide](CONFIGURATION.md)
- [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)
- [ElevenLabs Setup](ELEVENLABS_SETUP.md)

### Workflow
- [Workflow Guide](WORKFLOW_GUIDE.md)
- [Session Guide](SESSION_GUIDE.md)
- [Video Regeneration Guide](VIDEO_REGENERATION_GUIDE.md)

### Reference
- [API Reference](API_REFERENCE.md)
- [Features Overview](COMPLETE_FEATURE_OVERVIEW.md)
- [Project Overview](PROJECT_OVERVIEW.md)

---

## 🔄 Documentation Updates

**New in This Version:**

- ⭐ **[Configuration Guide](CONFIGURATION.md)** - Complete config.py reference
- ⭐ **[Camera LoRA Guide](CAMERA_LORA_GUIDE.md)** - Multi-camera LoRA system documentation
- ⭐ **[Workflow Guide](WORKFLOW_GUIDE.md)** - Complete pipeline overview
- ⭐ **[API Reference](API_REFERENCE.md)** - Full API documentation

**Last Updated:** February 11, 2026
**Version:** 3.0 (Multi-Camera LoRA System)

---

**Happy Video Creating! 🎬**
