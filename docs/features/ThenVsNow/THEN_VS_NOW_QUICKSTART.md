# Then Vs Now Feature - Quick Start Guide

## What is "Then Vs Now"?

The "Then Vs Now" feature creates cinematic reunion videos where original cast members return to iconic movie sets. Each character appears in two forms:
- **THEN**: Their original appearance from the movie
- **NOW**: Their current appearance today

Each character gets two video segments:
- **Meeting**: Arrival at the set, rediscovering the location
- **Departure**: Leaving the set, reflective moments

---

## How to Use

### Step 1: Create a New Project

1. Go to the Web UI
2. Click "Create New Project"
3. **Story Agent**: Select "then_vs_now"
4. **Idea**: Enter a movie name (e.g., "The Godfather", "Back to the Future")
5. **Duration** (optional): Set target video length in seconds
6. Click "Create Project"

### Step 2: Review Generated Content

The system automatically generates:
- **Story**: Movie details, cast list, director, genre
- **Characters**: 8-25 cast members with THEN/NOW prompts
- **Scenes**: Iconic movie set locations
- **Shots**: 2 shots per character (Meeting + Departure)
- **YouTube Metadata**: SEO titles, keywords, chapters

### Step 3: Generate Images

For each shot, you'll generate **two images**:

1. Click "Generate Images" or regenerate individual shots
2. The system creates:
   - **THEN image**: Character in original movie attire
   - **NOW image**: Character today in expensive modern attire
3. Images are named: `shot_001_then_001.png`, `shot_001_now_001.png`

**Toggle Between Images:**
- Use the THEN/NOW buttons on each shot card
- Purple = THEN, Pink = NOW

### Step 4: Generate Videos

For each shot, you'll generate **two videos**:

1. Click "Generate Videos" or regenerate individual shots
2. Select workflow: `wan22_flfi2v` (FLFI2V workflow)
3. The system creates:
   - **Meeting video**: Character arrives at set
   - **Departure video**: Character leaves set
4. Videos are named: `shot_001_meeting_001.mp4`, `shot_001_departure_001.mp4`

**Toggle Between Videos:**
- Use the Meeting/Departure buttons on each shot card
- Purple = Meeting, Pink = Departure

### Step 5: Export and Share

Once generation is complete:
1. Preview shots using the toggle buttons
2. Download individual videos or use batch export
3. Use the generated YouTube metadata for publishing

---

## UI Features

### FLFI2V Badge

Shots with the **FLFI2V** badge (purple-to-pink gradient) indicate:
- This shot uses dual-image mode
- Two images will be generated (THEN + NOW)
- Two videos will be generated (Meeting + Departure)

### THEN/NOW Toggle

```
┌─────────────────────────────┐
│  [THEN]  [NOW]              │
│  Purple   Pink              │
└─────────────────────────────┘
```

- Click **THEN** to see the character in original appearance
- Click **NOW** to see the character today

### Meeting/Departure Toggle

```
┌────────────────────────────────┐
│  [Meeting]  [Departure]        │
│  Purple      Pink              │
└────────────────────────────────┘
```

- Click **Meeting** to see arrival video
- Click **Departure** to see departure video

---

## Example: Creating a "The Godfather" Reunion

### Input
```
Story Agent: then_vs_now
Idea: The Godfather
Duration: 300 seconds (5 minutes)
```

### Generated Content

**Story:**
- Title: "The Godfather: The Reunion"
- Year: 1972
- Cast: Marlon Brando, Al Pacino, James Caan, etc.
- Director: Francis Ford Coppola
- Genre: Crime Drama

**Characters (example):**
- Marlon Brando as Don Vito Corleone
- Al Pacino as Michael Corleone
- James Caan as Sonny Corleone
- Robert Duvall as Tom Hagen

**Shots per character:**
1. Meeting shot (arrival at iconic set)
2. Departure shot (leaving the set)

Total shots: 8 characters × 2 = 16 shots

---

## Tips for Best Results

### 1. Choose Popular Movies
- Well-known movies with iconic sets work best
- The system generates better content for familiar locations

### 2. Adjust Duration
- Longer movies: Use 300-600 seconds (5-10 minutes)
- Shorter movies: Use 120-300 seconds (2-5 minutes)
- Each character needs ~30-60 seconds total

### 3. Review Generated Prompts
- Check the THEN and NOW image prompts
- Verify the Meeting and Departure video prompts
- Edit if needed before generation

### 4. Use High-Quality Workflows
- Images: `flux2` or `flux` workflows recommended
- Videos: `wan22_flfi2v` (required for FLFI2V)

### 5. Generate in Batches
- Start with a few characters to test
- Adjust prompts based on results
- Then generate the full batch

---

## Troubleshooting

### "FLFI2V badge not showing"

**Cause**: Shot wasn't generated with FLFI2V mode

**Solution**:
1. Check that story agent was "then_vs_now"
2. Verify shots.json has `"is_flfi2v": true`
3. Try recreating the project

### "Only one image generated"

**Cause**: Image generation didn't complete both variants

**Solution**:
1. Check the generation logs
2. Manually regenerate with `image_variant: "both"`
3. Verify enough disk space

### "Video generation fails"

**Cause**: Missing workflow or incomplete images

**Solution**:
1. Ensure both THEN and NOW images exist
2. Check `wan22_flfi2v` workflow is in config
3. Verify ComfyUI is running

### "Toggle buttons don't work"

**Cause**: Images/videos not properly saved

**Solution**:
1. Refresh the browser page
2. Check shots.json has the paths
3. Regenerate the missing variant

---

## Advanced: Custom Prompts

### Edit Image Prompts

You can customize the THEN and NOW prompts:

1. Click "Edit" on a shot
2. Modify `then_image_prompt` and `now_image_prompt`
3. The set prompt is automatically appended

### Edit Video Prompts

Customize Meeting and Departure videos:

1. Click "Edit" on a shot
2. Modify `meeting_video_prompt` or `departure_video_prompt`
3. Each video uses different motion descriptions

### Set Prompts

The set_prompt is in the scene data:
- Provides detailed movie set background
- Automatically appended to image prompts
- Ensures consistent backgrounds across characters

---

## File Structure

Generated files are organized as:

```
output/projects/{project_id}/
├── images/
│   ├── shot_001_then_001.png
│   ├── shot_001_now_001.png
│   ├── shot_002_then_001.png
│   └── shot_002_now_001.png
├── videos/
│   ├── shot_001_meeting_001.mp4
│   ├── shot_001_departure_001.mp4
│   ├── shot_002_meeting_001.mp4
│   └── shot_002_departure_001.mp4
├── story.json
└── shots.json
```

---

## YouTube Publishing

The system generates YouTube metadata:

**Title Options:**
- SEO-optimized titles with click appeal
- Examples: "The Godfather Cast Reunion 50 Years Later | THEN VS NOW"

**Keywords:**
- Movie name, "then vs now", "cast reunion"
- "behind the scenes", "movie sets"

**Chapters:**
- Timestamped chapters for each segment
- Example: "0:00 - Introduction", "0:30 - Don Corleone Returns"

**Description Preview:**
- First 200 characters of video description
- Includes hook and main content summary

---

## Comparison: Documentary vs ThenVsNow

| Feature | Documentary | Then Vs Now |
|---------|-------------|-------------|
| Input | Story idea | Movie name |
| Images per shot | 1 | 2 (THEN + NOW) |
| Videos per shot | 1 | 2 (Meeting + Departure) |
| Shot planner | Required | Bypassed |
| Scenes | Custom | Movie sets |
| Characters | Generated | Cast members |
| YouTube metadata | Basic | Enhanced with SEO |

---

## Getting Help

If you encounter issues:

1. **Check Logs**: Look at the generation logs for errors
2. **Verify Files**: Ensure all workflow files exist
3. **Review Prompts**: Check that prompts are valid
4. **Test Workflow**: Try a simple movie first
5. **Report Issues**: Include movie name and error messages

---

## Examples to Try

### Classic Movies
- The Godfather (1972)
- Back to the Future (1985)
- Star Wars: A New Hope (1977)
- The Wizard of Oz (1939)
- Casablanca (1942)

### Modern Classics
- The Matrix (1999)
- Fight Club (1999)
- Pulp Fiction (1994)
- The Shawshank Redemption (1994)
- Forrest Gump (1994)

### Ensemble Casts
- The Avengers (2012)
- Ocean's Eleven (2001)
- The Expendables (2010)
- Love Actually (2003)

---

## Summary

The "Then Vs Now" feature creates immersive reunion videos with:

✅ Automatic movie set detection
✅ Dual-image generation (THEN + NOW)
✅ Dual-video generation (Meeting + Departure)
✅ SEO-optimized YouTube metadata
✅ Easy-to-use toggle controls
✅ Backward compatible with existing projects

Try it with your favorite movie today!
