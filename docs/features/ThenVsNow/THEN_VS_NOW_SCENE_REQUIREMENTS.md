# ThenVsNow Agent: Enhanced Scene Detail Requirements

**Date:** March 12, 2026
**Status:** Updated

---

## Overview

The ThenVsNow story agent has been enhanced with **7 mandatory scene detail requirements** to ensure ultra-realistic, production-accurate set recreations.

---

## The 7 Mandatory Scene Elements

### 1️⃣ Exact Movie Scene Reference

**Requirement:** Describe the precise iconic moment from the film.

**Why:** Ensures the scene is recognizable and authentic.

**Example:**
```
Titanic (1997) — Grand Staircase Scene as seen when Jack first meets Rose
The Godfather (1972) — Dark office study during the opening scene
```

---

### 2️⃣ Accurate Set Recreation

**Requirements:**
- ✅ Architecture exactly as seen in the movie
- ✅ Props faithful to the original
- ✅ Furniture matching the film
- ✅ Textures that match the original set
- ✅ Partial soundstage walls visible
- ✅ Removable panels visible
- ✅ Film equipment subtly visible

**Example:**
```
Ornate polished dark wood staircase with gilded railings,
red carpet runner, crystal chandelier above
```

---

### 3️⃣ Composition Lock (MANDATORY)

**CRITICAL:** This block MUST be included verbatim in every scene:

```
STRAIGHT-ON EYE-LEVEL CAMERA, PERFECTLY CENTERED SYMMETRICAL
FRAMING, TRIPOD-MOUNTED CAMERA PERSPECTIVE, NO TILT, NO DUTCH ANGLE,
NO SIDE ANGLE. MEDIUM-WIDE CENTERED COMPOSITION. BALANCED LEFT-TO-RIGHT
VISUAL WEIGHT.
```

**Why:**
- Ensures consistent, professional framing
- Maintains behind-the-scenes authenticity
- Tripod perspective mimics production footage
- Symmetrical framing creates balance
- No creative angles that would break immersion

---

### 4️⃣ Lighting & Atmosphere

**Requirements:**
- ✅ Time of day matching original scene
- ✅ Studio lighting rigs visible but natural
- ✅ Soft cinematic shadows
- ✅ Subtle haze if appropriate

**Example:**
```
Warm golden lighting, soft shadows, subtle studio haze
```

---

### 5️⃣ Production Crew (Natural)

**Requirements:**
- ✅ 2-5 crew members (not distracting)
- ✅ Camera operator near lens
- ✅ Gaffer adjusting light flags
- ✅ Grip near dolly track
- ✅ Moving naturally, not posing

**Why:** Creates authentic behind-the-scenes atmosphere without being distracting.

---

### 6️⃣ Character Presence Rule

**Requirements:**
- Scene may be empty OR
- If character is present, they must be **centered**

**Why:** Maintains composition balance and professional framing.

---

### 7️⃣ Rendering Style

**Keywords:**
```
Ultra-realistic
Hyper-detailed
Photorealistic textures
4K cinematic
Behind-the-scenes atmosphere
```

---

## Updated Scene Prompt Structure

### Format Template

```json
{
  "scene_id": 0,
  "location": "Set Name - Specific Scene Reference",
  "set_prompt": "EXACT MOVIE SCENE REFERENCE: [describe moment]. ACCURATE SET RECREATION: [architecture, props, textures]. Partial soundstage walls visible. Film equipment visible. COMPOSITION LOCK: [MANDATORY BLOCK]. LIGHTING: [time of day, rigs, shadows, haze]. PRODUCTION CREW: [2-5 crew members, positions]. RENDERING STYLE: [keywords].",
  "characters": "Actor Name (NOW) with younger self visible",
  "action": "[Meeting/Departure] [action description]. COMPOSITION LOCK: [MANDATORY BLOCK].",
  "emotion": "Emotion",
  "narration": "Narration text",
  "scene_duration": 20
}
```

---

## Complete Example

### Movie: Titanic (1997)

**Scene:** Grand Staircase Scene

```json
{
  "scene_id": 0,
  "location": "Titanic (1997) — Grand Staircase Scene when Jack meets Rose",
  "set_prompt": "EXACT MOVIE SCENE REFERENCE: Grand staircase from Titanic (1997) as seen when Jack first meets Rose at the top of the stairs. ACCURATE SET RECREATION: Ornate polished dark wood staircase with intricate gilded railings featuring Art Nouveau patterns, deep red carpet runner cascading down center, massive crystal chandelier with thousands of crystals suspended above, tall arched windows with stained glass accents. Partial soundstage walls visible at edges, removable panels showing construction. Film equipment subtly positioned: large cinema cameras on dolly tracks at base of stairs, heavy crane arm extending overhead with counterweights visible, C-stands with diffusion flags near windows. COMPOSITION LOCK: STRAIGHT-ON EYE-LEVEL CAMERA, PERFECTLY CENTERED SYMMETRICAL FRAMING, TRIPOD-MOUNTED CAMERA PERSPECTIVE, NO TILT, NO DUTCH ANGLE, NO SIDE ANGLE. MEDIUM-WIDE CENTERED COMPOSITION. BALANCED LEFT-TO-RIGHT VISUAL WEIGHT. LIGHTING: Late afternoon golden hour sunlight streaming through tall windows creating long shadows, studio HMI lights on stands fill in shadows, soft diffused glow through chandelier, subtle atmospheric haze. PRODUCTION CREW: Camera operator at primary lens below, focus puller checking marks on tape measure, gaffer adjusting large silk diffusion flag to right of frame, grip marking dolly track position, script supervisor taking notes in background. All crew moving naturally, not posing. RENDERING STYLE: Ultra-realistic, hyper-detailed, photorealistic wood grain textures, crystal refraction, fabric folds in clothing, 4K cinematic resolution, behind-the-scenes documentary atmosphere, film production authenticity.",
  "characters": "Leonardo DiCaprio (NOW) with younger self visible",
  "action": "[Meeting] Leo walks onto the grand staircase set holding iPhone 15 Pro Max, younger Leo beside him, both pause to admire the ornate staircase. STRAIGHT-ON EYE-LEVEL CAMERA, PERFECTLY CENTERED SYMMETRICAL FRAMING. Camera operator follows movement with smooth dolly push. Gaffer adjusts overhead light.",
  "emotion": "Deep nostalgia, wonder",
  "narration": "Standing here where it all began, meeting Rose for the first time...",
  "scene_duration": 30
}
```

---

## Set Prompt Elements Breakdown

### Detailed Breakdown

```
set_prompt: "EXACT MOVIE SCENE REFERENCE: ...

ACCURATE SET RECREATION:
- Architecture (style, era, materials)
- Props (furniture, decorations)
- Textures (wood, fabric, metal)
- Soundstage evidence (partial walls, panels)
- Film equipment (cameras, lights, rigging)

COMPOSITION LOCK (MANDATORY):
STRAIGHT-ON EYE-LEVEL CAMERA, PERFECTLY CENTERED SYMMETRICAL
FRAMING, TRIPOD-MOUNTED CAMERA PERSPECTIVE, NO TILT, NO DUTCH
ANGLE, NO SIDE ANGLE. MEDIUM-WIDE CENTERED COMPOSITION.
BALANCED LEFT-TO-RIGHT VISUAL WEIGHT.

LIGHTING:
- Time of day (morning, afternoon, evening)
- Studio lighting rigs (visible but natural)
- Shadow quality (soft, cinematic)
- Atmosphere (haze, dust particles if applicable)

PRODUCTION CREW:
- 2-5 crew members
- Camera operator (near lens)
- Gaffer (adjusting lights)
- Grip (near dolly/tracks)
- Movement (natural, not posing)

RENDERING STYLE:
Ultra-realistic, hyper-detailed, photorealistic textures,
4K cinematic, behind-the-scenes atmosphere"
```

---

## Why These Requirements Matter

### 1. Authenticity
- Viewers recognize exact movie moments
- Sets feel genuine and lived-in
- Film equipment creates production credibility

### 2. Consistency
- All scenes follow same composition rules
- Tripod perspective maintains professional feel
- Balanced framing creates visual harmony

### 3. Immersion
- Behind-the-scenes atmosphere feels real
- Production crew adds life
- Natural crew movement breaks sterility

### 4. Quality
- Ultra-realistic rendering matches modern expectations
- 4K cinematic quality meets production standards
- Hyper-detailed textures reward close inspection

---

## Quality Checklist

When generating scene descriptions, verify:

- [ ] **Scene Reference**: Names specific movie moment
- [ ] **Architecture**: Describes building/materials accurately
- [ ] **Props**: Lists key furniture/decorations
- [ ] **Textures**: Mentions materials (wood, metal, fabric)
- [ ] **Soundstage**: Partial walls/panels visible
- [ ] **Film Equipment**: Cameras, lights, rigging present
- [ ] **Composition Lock**: Mandatory block included verbatim
- [ ] **Lighting**: Time of day + studio setup described
- [ ] **Shadows**: Soft cinematic shadows mentioned
- [ ] **Crew**: 2-5 members with roles
- [ ] **Positions**: Natural placement, not forced
- [ ] **Style**: Ultra-realistic, 4K cinematic keywords

---

## Before vs After Comparison

### BEFORE (Basic Description)
```
A grand staircase with wood railings and a carpet.
Actor walks onto the set and looks around.
```

### AFTER (With All 7 Elements)
```
Titanic (1997) — Grand Staircase Scene when Jack meets Rose

Ornate polished dark wood staircase with gilded railings,
red carpet runner, crystal chandelier above.

STRAIGHT-ON EYE-LEVEL CAMERA, PERFECTLY CENTERED SYMMETRICAL
FRAMING, TRIPOD-MOUNTED CAMERA PERSPECTIVE, NO TILT.

Film cameras on dolly positioned behind main lens. Gaffer adjusting
light flag to the right, camera assistant checking monitor to the left.

Warm golden lighting, soft shadows, subtle studio haze.
Hyper-realistic, 4K cinematic, behind-the-scenes realism.
```

---

## Implementation

### File Modified

**File:** `agents/story/then_vs_now.md`

**Changes:**
- Lines 97-149: Added 7 mandatory scene detail requirements
- Lines 53-60: Updated prompt structure with all requirements
- Lines 62-84: Updated scene template with proper formatting

### Impact

- ✅ **Scene prompts** are now much more detailed
- ✅ **Set recreation** is more accurate to source material
- ✅ **Composition** is consistent and professional
- ✅ **Atmosphere** feels authentic and lived-in
- ✅ **Crew presence** adds production realism
- ✅ **Rendering** meets 4K cinematic standards

---

## Testing

### Generate New Project

1. Create new ThenVsNow project
2. Enter movie name (e.g., "The Godfather")
3. Generate story
4. Check scenes in story.json
5. Verify all 7 elements are present

### Verification

```bash
# Check scene prompts
cat output/projects/{project_id}/story.json | jq '.scenes[0].set_prompt'
```

Should see:
- "EXACT MOVIE SCENE REFERENCE"
- "ACCURATE SET RECREATION"
- "COMPOSITION LOCK:" (with mandatory block)
- "LIGHTING:"
- "PRODUCTION CREW:"
- "RENDERING STYLE:"

---

## Examples by Genre

### Drama
```
The Godfather (1972) — Dark office study during opening scene
COMPOSITION LOCK: STRAIGHT-ON EYE-LEVEL CAMERA...
Deep mahogany paneling, red velvet drapes, desk lamp with warm glow
```

### Sci-Fi
```
Blade Runner (1982) — Tyrell Corporation pyramid office
COMPOSITION LOCK: STRAIGHT-ON EYE-LEVEL CAMERA...
Brushed metal surfaces, holographic displays, rain on windows
```

### Fantasy
```
The Lord of the Rings (2001) — The Shire
COMPOSITION LOCK: STRAIGHT-ON EYE-LEVEL CAMERA...
Hobbit holes with round doors, lush green gardens, warm sunlight
```

---

## Tips for Best Results

1. **Know the Movie:** Reference specific iconic scenes
2. **Be Specific:** Don't say "a room" - say "dark wood-paneled study with red velvet drapes"
3. **Include the Lock:** Always include the composition lock verbatim
4. **Add Crew:** Always mention 2-5 crew members with natural actions
5. **Describe Lighting:** Time of day + studio setup + shadows + haze
6. **Use Keywords:** "ultra-realistic", "4K cinematic", "behind-the-scenes"

---

**Status:** ✅ Updated and ready for use

**Next Steps:**
1. Create new ThenVsNow project to see enhanced scene prompts
2. Verify all 7 requirements are in generated scenes
3. Check that set prompts are much more detailed than before
4. Enjoy ultra-realistic set recreations!
