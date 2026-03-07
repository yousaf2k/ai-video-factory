# Prehistoric POV Agents - Quick Start Guide

## What Are POV Agents?

The `prehistoric_pov` agents create immersive **first-person dinosaur documentaries** where viewers experience the prehistoric world through a survivor's eyes. Every shot includes **visible human hands** holding cameras, creating visceral "you are there" content.

## Quick Start

### Generate a POV Dinosaur Documentary

```bash
# 1. Generate story with POV agent
python core/main.py --story-agent prehistoric_pov --idea "Time traveler encounters T-Rex in Cretaceous forest"

# 2. Generate POV images (hands visible in every shot)
python core/main.py --image-agent prehistoric_pov --resume [session_id]

# 3. Render video
python core/main.py --resume [session_id] --render
```

## Key Features

- ✅ **First-Person POV**: "I see...", "My hands tremble..."
- ✅ **Hands Visible**: Every shot shows human hands holding cameras
- ✅ **Diegetic Camera**: Character actively filming with Sony Venice 2
- ✅ **Survival Stakes**: Danger, terror, wonder mixed with discovery
- ✅ **Cinematic Quality**: Sony Venice 2 + Arri Signature Prime + 8K

## POV vs. Traditional

| Traditional | POV |
|-------------|-----|
| Third-person observer | First-person participant |
| Invisible camera | Visible camera/hands |
| "These creatures lived..." | "I see... My hands shake..." |
| Scientific wonder | Survival terror + wonder |

## When to Use POV

✅ **Use POV** when you want:
- Immersive "you are there" experience
- Character-driven survival narrative
- Modern vlogging/selfie style
- High YouTube engagement (POV performs well)

✅ **Use Traditional** (`prehistoric_dinosaur`) when you want:
- Pure educational documentary
- Epic cinematic shots without humans
- Objective scientific narration
- Traditional nature documentary style

## Example Output

### Story Narration (POV)
> "My hands tremble as I raise the camera. Through the lens, 40 feet of apex predator stands in a sunlit clearing. I hold my breath. One wrong move and I'm the first human to be eaten by a T-Rex in 66 million years."

### Image Prompt (POV)
> "First person POV shot with hands visible gripping Sony Venice 2 camera body, massive Tyrannosaurus Rex standing 40 feet away in Late Cretaceous forest clearing, human hands with fingers on focus ring visible at bottom of frame. Shot on Sony Venice 2 with Arri Signature Prime 21mm wide lens, 8K resolution, 16:9 widescreen. Photorealistic, Netflix quality, hands visible, POV immersion."

## Technical Specs

Every POV prompt includes:
- **First person POV**
- **Hands visible in frame**
- **Sony Venice 2** (diegetic camera)
- **Arri Signature Prime** lenses (16mm-85mm)
- **8K resolution**
- **16:9 widescreen**
- **Netflix quality**
- **Photorealistic**

## POV Shot Types

1. **Establishing Shots**: Hands holding camera up to see landscape
2. **Through-the-Hands**: Looking through hands/foliage at dinosaurs
3. **Viewfinder Shots**: Looking through camera LCD/eyepiece
4. **Reaction Shots**: Hands raised in defense/surrender
5. **Running POV**: Camera shake, hands clutching gear while fleeing
6. **Intimate Encounters**: Hands reaching out to dinosaurs
7. **Scientific Equipment**: Hands operating research tools
8. **Selfie/Vlogger**: Arm extended, self-recording

## Full Documentation

See `docs/PREHISTORIC_POV_GUIDE.md` for complete guide with examples, best practices, and troubleshooting.

## Files Created

- ✅ `agents/story/prehistoric_pov.md` (~301 lines)
- ✅ `agents/image/prehistoric_pov.md` (~276 lines)
- ✅ `docs/PREHISTORIC_POV_GUIDE.md` (~617 lines)
- ✅ `config.py` updated (added prehistoric_pov options)

---

**Ready to create immersive POV dinosaur documentaries!** 🦖

Use `--story-agent prehistoric_pov --image-agent prehistoric_pov` to activate.
