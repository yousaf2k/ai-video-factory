# Video Length Configuration - Visual Flow

## User Input Flow

```
┌─────────────────────────────────────────────────────────┐
│              RUN: python core/main.py                  │
└───────────────────────┬───────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │ Check for Incomplete Session │
         └──────────┬───────────────────┘
                    │
       ┌────────────┴────────────┐
       │                         │
   [FOUND]                   [NONE]
       │                         │
       ▼                         ▼
┌──────────────┐      ┌──────────────────┐
│ Continue?    │      │ Get Video Config │
│ (y/n)        │      └────────┬─────────┘
└──────┬───────┘               │
       │                       │
       │    ┌──────────────────┴──────────────┐
       │    │                                 │
       │    ▼                                 ▼
       │  [Enter Total]                   [Press Enter]
       │    │                                 │
       │    ▼                                 ▼
       │  Calculate:                        Calculate:
       │  Shots = Total ÷ Shot             Shots from Story
       │    │                                 │
       │    └────────────┬────────────────────┘
       │                 │
       ▼                 ▼
┌────────────────────────────────┐
│  Generate Only Shots Needed   │
│                               │
│  Example:                     │
│  • Total: 60 seconds          │
│  • Shot length: 5 seconds     │
│  • Shots needed: 12           │
│  • Generate: 12 images        │
│  • Render: 12 videos          │
└───────────────────────────────┘
```

## Shot Calculation Examples

### Example 1: Fixed Total Length
```
User Input:
  Total: 60 seconds
  Shot: 5 seconds

Calculation:
  60 ÷ 5 = 12 shots

Workflow:
  ├─ Generate story
  ├─ Plan shots (max 12)
  ├─ Generate 12 images
  ├─ Render 12 videos × 5s = 60s total
  └─ ✅ Complete

Result: Exact 60-second video
```

### Example 2: Story-Based Length
```
User Input:
  Total: [press Enter]
  Shot: 5 seconds

Calculation:
  Story determines shots (e.g., 7)

Workflow:
  ├─ Generate story
  ├─ Plan shots (7 from story)
  ├─ Generate 7 images
  ├─ Render 7 videos × 5s = 35s total
  └─ ✅ Complete

Result: 35-second video (story-driven)
```

### Example 3: Long Shots
```
User Input:
  Total: 120 seconds (2 minutes)
  Shot: 10 seconds

Calculation:
  120 ÷ 10 = 12 shots

Workflow:
  ├─ Generate story
  ├─ Plan shots (max 12)
  ├─ Generate 12 images
  ├─ Render 12 videos × 10s = 120s total
  └─ ✅ Complete

Result: Exact 2-minute video, cinematic feel
```

## Frame Calculation

```
Video Length (seconds) × FPS = Total Frames

Example (5 seconds at 24fps):
  5 × 24 = 120 frames

Workflow Update:
  WanImageToVideo widgets_values:
    [width, height, frames, something]
    [1024,  576,   120,    1     ]
                ↑
           Set dynamically
```

## Comparison: Different Shot Lengths

### Short Shots (3 seconds)
```
Total: 60 seconds
Shot length: 3 seconds
Shots: 60 ÷ 3 = 20 shots

Pros:
  ✓ More dynamic
  ✓ More cuts
  ✓ Faster per-shot render

Cons:
  ✗ More images (20 × $0.08 = $1.60)
  ✗ More files to manage
```

### Medium Shots (5 seconds - Default)
```
Total: 60 seconds
Shot length: 5 seconds
Shots: 60 ÷ 5 = 12 shots

Pros:
  ✓ Balanced pace
  ✓ Reasonable cost (12 × $0.08 = $0.96)
  ✓ Good for most content

Cons:
  ✗ Less dynamic than shorter
```

### Long Shots (10 seconds)
```
Total: 60 seconds
Shot length: 10 seconds
Shots: 60 ÷ 10 = 6 shots

Pros:
  ✓ Cinematic, smooth
  ✓ Lower cost (6 × $0.08 = $0.48)
  ✓ Faster to generate all shots

Cons:
  ✗ Less dynamic
  ✗ Longer per-shot render time
```

## Decision Tree

```
What do you want?
│
├─ Specific length (e.g., "exactly 1 minute")
│  ├─→ Enter total length
│  ├─→ Choose shot length
│  └─→ Get exact duration
│
├─ Let story decide (e.g., "however long it needs")
│  ├─→ Press Enter for total
│  ├─→ Choose shot length
│  └─→ Duration varies by story
│
└─ I don't care
   └─→ Press Enter twice (use defaults: 5s shots, story length)
```

## Configuration Examples

### config.py Presets

```python
# For YouTube Shorts (60 seconds max)
DEFAULT_SHOT_LENGTH = 3.0
TARGET_VIDEO_LENGTH = 60.0
# Result: 20 shots × 3s = 60s

# For Instagram Reels (90 seconds max)
DEFAULT_SHOT_LENGTH = 5.0
TARGET_VIDEO_LENGTH = 90.0
# Result: 18 shots × 5s = 90s

# For Documentary (story-driven)
DEFAULT_SHOT_LENGTH = 10.0
TARGET_VIDEO_LENGTH = None
# Result: Story determines shots, 10s each

# For Trailer (short, dynamic)
DEFAULT_SHOT_LENGTH = 2.0
TARGET_VIDEO_LENGTH = 30.0
# Result: 15 shots × 2s = 30s
```

## Interactive Example

```
$ python core/main.py

==================================================================
AI FILM STUDIO - Video Generation Pipeline
==================================================================

STEP 1: Idea
[Reading from input/video_idea.txt]

==================================================================
VIDEO CONFIGURATION
==================================================================

Enter total video length in seconds (or press Enter for default based on story):
60 ↵

Enter length per shot in seconds (default: 5.0s):
5 ↵

[INFO] Target: 60.0s video, 5.0s per shot = 12 shots
[INFO] Estimated cost: 12 shots × $0.08 = $0.96
==================================================================

STEP 2: Story Generation
[Generating story with 12 scenes in mind...]

STEP 3: Scene Graph
[Structuring 12 scenes...]

STEP 4: Shot Planning
[Planning exactly 12 shots for 60-second target...]

STEP 4.5: Image Generation
[1/12] Generating image...
[2/12] Generating image...
...
[12/12] Generating image...

STEP 5: Rendering
[INFO] Each shot: 5.0s (120 frames at 24fps)
[SUBMIT] Shot 1 (5.0s)
[SUBMIT] Shot 2 (5.0s)
...
[SUBMIT] Shot 12 (5.0s)

[INFO] Waiting for renders to complete...

[SUCCESS] ALL RENDERS COMPLETE!
[INFO] Final video: 60 seconds (12 shots × 5 seconds)

==================================================================
To view all sessions, check: output/sessions/
==================================================================
```

## Tips & Tricks

### 💡 Quick Starters
- **First time**: Press Enter twice (use defaults)
- **Specific length**: Enter total, then shot length
- **Story-based**: Press Enter for total, enter shot length

### 💡 Cost Management
- Shorter shots = more shots = higher cost
- Longer shots = fewer shots = lower cost
- Story-based = unpredictable cost

### 💡 Time Management
- Shorter shots = faster per shot, more shots
- Longer shots = slower per shot, fewer shots
- Total time similar either way

### 💡 Quality Tips
- Trailers: 2-3 second shots (dynamic)
- Stories: 5-8 second shots (balanced)
- Documentaries: 10+ second shots (cinematic)

## Troubleshooting

**"Too many shots generated"**
→ Increase shot length or specify total length

**"Too few shots"**
→ Decrease shot length

**"Video is wrong length"**
→ Check TOTAL_LENGTH ÷ SHOT_LENGTH calculation
→ Verify VIDEO_FPS in config.py

**"Cost too high"**
→ Use longer shots (fewer images needed)

## Summary

```
INPUT → Total Length + Shot Length
         ↓
       CALCULATE → Shots = Total ÷ Shot
         ↓
       GENERATE → Only shots needed
         ↓
       RENDER → Exact target length
         ↓
       RESULT → Predictable duration & cost
```

**Video length control gives you precision and predictability!** 🎯
