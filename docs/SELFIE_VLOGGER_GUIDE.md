# Selfie Vlogger Agents

## Overview

The Selfie Vlogger agents create authentic, first-person vlog-style content with GoPro camera aesthetics. Perfect for YouTube, TikTok, and Instagram content creators.

## Agents

### Story Agent: `selfie_vlogger`
- **Location**: `agents/story/selfie_vlogger.md`
- **Purpose**: Generates conversational, first-person vlog narratives
- **Style**: Spontaneous, enthusiastic, authentic vlogger personality

### Image Agent: `selfie_vlogger`
- **Location**: `agents/image/selfie_vlogger.md`
- **Purpose**: Creates GoPro selfie shot descriptions with ultra wide-angle aesthetics
- **Style**: Action camera, handheld POV, fisheye distortion

## Usage

### Option 1: Set as Default in config.py

Edit `config.py`:
```python
# Line ~531
STORY_AGENT = "selfie_vlogger"

# Line ~534
IMAGE_AGENT = "selfie_vlogger"
```

### Option 2: Use On-Demand

When prompted for agent selection, specify:
- Story agent: `selfie_vlogger`
- Image agent: `selfie_vlogger`

## Camera Type

The new `selfie` camera type has been added to `CAMERA_LORA_MAPPING`:
- Uses handheld motion LoRA for authentic vlog movement
- Trigger keyword: "handheld POV movement"
- Compatible with existing video generation pipeline

## Vlog Topics

The selfie vlogger works great for:

- **Food Reviews**: Restaurant visits, cooking, taste tests
- **Travel Vlogs**: Exploring new places, tourist attractions
- **Tech Reviews**: Unboxing, product demos, reviews
- **Daily Vlogs**: Day in the life, routines, behind the scenes
- **Event Coverage**: Concerts, festivals, conferences
- **Tutorials**: How-to guides from first-person perspective

## Example Prompts

Try these ideas with the selfie vlogger:

1. "Vlog about visiting a new coffee shop in downtown"
2. "Unboxing and reviewing the latest smartphone"
3. "Travel vlog exploring a historic city center"
4. "Food tour of a local night market"
5. "Behind the scenes at my workspace"
6. "Trying an extreme sport for the first time"
7. "Morning routine vlog"
8. "Attending a music festival"

## Output Characteristics

### Story Output
- First-person POV ("I", "me", "my")
- Conversational, spontaneous narration
- Direct audience engagement ("you guys", "check this out")
- Natural vlog structure: Hook → Intro → Exploration → Reaction → Closing
- Authentic, enthusiastic tone

### Image Output
- GoPro ultra wide-angle shots (16mm equivalent)
- Fisheye lens distortion
- Handheld POV camera movement
- Natural available lighting
- Vlogger visible in frame (selfie style)
- Varied shot types: classic selfie, walk-and-talk, close-up details, establishing shots

## Shot Types

Each scene includes varied shot types:

1. **Classic Selfie**: Arm's length, vlogger centered
2. **Walk-and-Talk**: Chest mount POV, moving through space
3. **Point-of-Interest**: Vlogger turns to show something
4. **Close-Up Detail**: Extreme close-up of objects/food
5. **Establishing Shot**: Wide angle showing full location
6. **Reaction Shot**: Vlogger's genuine emotional response

## Technical Specs

All image prompts include:
- "Shot on GoPro HERO11/12/13 Black"
- "Ultra wide-angle 16mm equivalent"
- "Slight fisheye distortion"
- "Handheld POV"
- "Natural available light"
- "Action camera aesthetic"

## Customization

You can modify the agent behavior by editing:
- `agents/story/selfie_vlogger.md` - Adjust vlogger personality and narration style
- `agents/image/selfie_vlogger.md` - Modify shot types and camera specifications
- `config.py` - Change camera LoRA settings for selfie movement

## Tips for Best Results

1. **Provide specific topics**: Instead of "coffee shop vlog", try "vlog about trying an exotic coffee drink at a new cafe"
2. **Include personal reactions**: The agent will include genuine reactions and commentary
3. **Let it be spontaneous**: Don't over-script - the agent works best with simple prompts
4. **Trust the vlog structure**: The agent knows how to structure engaging vlogs automatically
5. **Experiment with topics**: Try different niches to see what works best

## Sample Workflow

```bash
# 1. Set agents in config.py (or use on-demand)
# 2. Run story generation
python generate_story.py "Vlog about visiting a cat cafe for the first time"

# 3. Generate shots with selfie vlogger image agent
python shot_planner.py

# 4. Generate images with GoPro aesthetic
python generate_images.py

# 5. Render videos with handheld movement
python render_videos.py
```

## Troubleshooting

**Issue**: Generated shots don't look like selfies
- **Solution**: Verify `IMAGE_AGENT = "selfie_vlogger"` is set in config.py

**Issue**: Camera movement too static
- **Solution**: Ensure camera type is set to "selfie" in shots.json or use fpv/walk camera types

**Issue**: Narration sounds too formal
- **Solution**: Check that `STORY_AGENT = "selfie_vlogger"` is configured correctly

**Issue**: No fisheye distortion in images
- **Solution**: The selfie vlogger image agent automatically includes fisheye specs - check prompts are being used correctly

## Next Steps

1. Create your first vlog with a simple topic
2. Experiment with different camera types (selfie, fpv, walk)
3. Customize the agent personalities to match your style
4. Add your own catchphrases and signature style to the story agent
