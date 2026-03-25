# Project Management - Visual Guide

## Pipeline Flow with Project Management

```
┌─────────────────────────────────────────────────────────────────┐
│                    RUN: python core/main.py                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Check for Incomplete │
              │      Projects         │
              └──────────┬───────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
        [FOUND]                   [NONE]
            │                         │
            ▼                         ▼
    ┌───────────────┐       ┌─────────────────┐
    │ Display       │       │ Create New      │
    │ Project Info  │       │ Project         │
    └───────┬───────┘       └────────┬────────┘
            │                        │
            ▼                        │
    ┌───────────────┐                │
    │ Ask: Continue?│                │
    └───┬───────┬───┘                │
        │       │                    │
      [Y]     [N]                    │
        │       │                    │
        │       └────────────────────┤
        │                            │
        ▼                            ▼
┌─────────────────┐         ┌─────────────────┐
│ Resume Project  │         │   New Project   │
│                 │         │                 │
│ • Load metadata │         │ • Create project│
│ • Check progress│         │ • Save idea     │
│ • Skip completed│         └────────┬────────┘
└────────┬────────┘                   │
         │                            │
         └────────────┬───────────────┘
                      ▼
         ┌────────────────────────┐
         │   STEP 2: Story        │
         │   Generate & Save      │
         │   → story.json         │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   STEP 3: Scene Graph  │
         │   Structure scenes     │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   STEP 4: Shot Planning│
         │   Generate & Save      │
         │   → shots.json         │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │ STEP 4.5: Images       │
         │ For each shot:         │
         │ • Check if exists      │
         │ • Generate if needed   │
         │ • Mark complete        │
         │ • Save image           │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   STEP 5: Rendering    │
         │ For each shot:         │
         │ • Check if rendered    │
         │ • Submit to ComfyUI    │
         │ • Mark complete        │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   Wait for ComfyUI     │
         │   to finish all        │
         └────────────┬───────────┘
                      ▼
         ┌────────────────────────┐
         │   Mark Project         │
         │   COMPLETE             │
         └────────────────────────┘
```

## Project Directory Structure

```
output/projects/
│
├── project_20250207_143000/              ← COMPLETED SESSION
│   ├── project_20250207_143000_meta.json
│   ├── story.json
│   ├── shots.json
│   └── images/
│       ├── shot_001.png
│       ├── shot_002.png
│       └── ... (all 7 shots)
│
├── project_20250208_002238/              ← INCOMPLETE SESSION
│   ├── project_20250208_002238_meta.json
│   ├── story.json
│   ├── shots.json
│   └── images/
│       ├── shot_001.png    ← DONE
│       ├── shot_002.png    ← DONE
│       ├── shot_003.png    ← DONE
│       ├── shot_004.png    ← FAILED
│       └── ... (remaining not generated)
│
└── project_20250208_031515/              ← FUTURE SESSION
    └── (will be created on next run)
```

## Crash Recovery Scenarios

### Scenario 1: Crash During Image Generation

```
Initial Run:
  Story   [✓ COMPLETE]
  Shots   [✓ COMPLETE]
  Images  [⏳ 3/7 done] ← CRASH
  Videos  [⬜ NOT STARTED]

After Re-run:
  "INCOMPLETE SESSION FOUND"
  Continue? [y]

  Resume:
    Images  [⏳ 3/7 done, 4 remaining]
    → Skip shots 1-3 (already have images)
    → Generate shots 4-7
    → Continue to videos
```

### Scenario 2: Crash During Video Rendering

```
Initial Run:
  Story   [✓ COMPLETE]
  Shots   [✓ COMPLETE]
  Images  [✓ 7/7 done]
  Videos  [⏳ 2/7 done] ← CRASH

After Re-run:
  "INCOMPLETE SESSION FOUND"
  Continue? [y]

  Resume:
    Videos  [⏳ 2/7 done, 5 remaining]
    → Skip shots 1-2 (already rendered)
    → Submit shots 3-7 to ComfyUI
```

### Scenario 3: User Chooses "No" (Start Fresh)

```
Initial Run:
  Incomplete project found
  Continue? [n]

  Result:
    → Create NEW project
    → New timestamp
    → Generate everything fresh
    → Old project preserved for reference
```

## Project States

```
┌─────────────────────────────────────────────────────────┐
│                   SESSION STATES                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  NEW        → Just created, no steps complete          │
│  IN_PROGRESS → Some steps complete, more to do         │
│  COMPLETE   → All steps done, all videos rendered      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                   STEP STATES                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  story         ✓  Story generated & saved              │
│  scene_graph  ✓  Scenes structured                     │
│  shots        ✓  Shot prompts created                  │
│  images       ✓  All images generated                  │
│  videos       ✓  All videos rendered                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Shot Status Indicators

```
[DONE]  - Image generated, video rendered
[IMG]   - Image generated, video NOT rendered
[TODO]  - Image NOT generated, video NOT rendered
[SKIP]  - Skipped (already exists)
```

## Commands Reference

```bash
# Main pipeline
python core/main.py                    # Run with auto-recovery

# Project management
python projects.py list                # List all projects
python projects.py view <id>           # View project details
python projects.py help                # Show help

# Direct file access
cat output/projects/project_X/story.json       # View story
cat output/projects/project_X/shots.json       # View prompts
ls output/projects/project_X/images/           # View images
```

## Progress Tracking Example

```
Project: project_20250208_002238
Status: IN PROGRESS

Progress Bar:
Story    [████████████████████] 100%  ✓
Shots    [████████████████████] 100%  ✓
Images   [████████████░░░░░░░░]  57%  ⏳ (4/7)
Videos   [░░░░░░░░░░░░░░░░░░░░]   0%  ⬜ (0/7)

Shot Breakdown:
  [DONE] Shot 1: Sweeping aerial view...
  [DONE] Shot 2: Animated map...
  [IMG]  Shot 3: Detailed CGI recreation...
  [IMG]  Shot 4: Close-ups of artifacts...
  [TODO] Shot 5: Trade routes graphics...
  [TODO] Shot 6: Climate change visuals...
  [TODO] Shot 7: Present-day footage...
```

## Benefits

✅ **Zero Data Loss** - Everything saved immediately
✅ **Smart Recovery** - Only do what's needed
✅ **Full History** - Track all generations
✅ **Easy Management** - Simple commands
✅ **Debugging** - Review all data
✅ **Reusable** - Export prompts from projects
