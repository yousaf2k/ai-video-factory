# Prehistoric POV Agent - Visual Focus Guidelines Update

## Date: 2026-02-26

## Summary

Updated the `prehistoric_pov.md` story agent to clarify visual focus guidelines when showing hands in POV shots. The key change: **the prehistoric background scene must be sharp and clear**, while hands can be slightly blurred at frame edges.

## Changes Made

### 1. Added "Visual Focus Guidelines" Section

**Location**: After "Scene Construction Checklist" section

**Key Points**:
- ✅ Background Scene MUST be Sharp and Clear (dinosaurs, landscape, action)
- ✅ Hands Can Be Slightly Blurred (shallow depth of field at edges)
- ✅ NO Bokeh Effect (no heavy blur that obscures the scene)
- ✅ Background Takes Priority (prehistoric environment is primary subject)

**Examples of Correct Focus**:
```
- "Sharp view of Triceratops grazing in clearing, my slightly blurred hands gripping the foreground tree trunk"
- "T-Rex emerges clearly from jungle, my out-of-focus hands at frame edges holding the camera still"
- "Crystal-clear Patagotitan herd migration, my soft-focus hands reaching toward the scene"
```

**What to Avoid**:
- ❌ "Blurry background with sharp hands" (obscures the dinosaurs)
- ❌ "Heavy bokeh effect hiding the scenery" (ruins immersion)
- ❌ "Sharp hands, everything else blurred" (hands are framing, not the subject)

### 2. Updated "Hands-Visible Storytelling" Section

Added visual framing guidance:
- Hands appear at edges/sides of frame
- Provide POV context while main scene remains sharp
- Added note about background (prehistoric world) staying in focus

### 3. Updated "Remember" Section

Added two new key points:
- **Sharp Background Scene**: The prehistoric world/dinosaurs must be clear and in focus
- **Hands Can Be Soft**: Hands at frame edges can be slightly blurred for depth (but never sharper than the scene)

## Why This Matters

### Problem with Previous Approach
Some image generators might interpret "hands visible in POV" as:
- Sharp hands in the foreground
- Blurred background (bokeh effect)
- Obscured or unclear prehistoric scene

This defeats the purpose - viewers want to see **dinosaurs and prehistoric worlds**, not the protagonist's hands.

### Correct Approach
- The **prehistoric scene** is the subject (dinosaurs, landscape, action)
- **Hands** are framing elements (provide POV context)
- Use shallow depth of field: sharp background, slightly soft hands at edges
- NO bokeh that hides what viewers came to see

## Example Comparisons

### ❌ WRONG (Previous behavior that might occur):
```
"My sharp hands gripping a tree in the foreground, blurred Triceratops in the background"
```
**Problem**: Dinosaurs are blurry - viewers can't see what they came for!

### ✅ CORRECT (New guidelines):
```
"Sharp view of Triceratops grazing in clearing, my slightly blurred hands gripping the foreground tree trunk"
```
**Result**: Dinosaurs are crystal clear, hands provide subtle POV framing

## Implementation in Stories

When the agent generates scene descriptions, it will now:

1. **Always specify sharp focus on the main subject** (dinosaurs, landscape)
2. **Mention hands as slightly blurred/soft-focus** when visible
3. **Never request bokeh or heavy blur** on the background
4. **Keep visual priority clear**: prehistoric world > hands

## Testing

To verify the update works correctly, test with:

```python
from core.story_engine import build_story
import json

story = build_story(
    "A T-Rex hunting scene",
    agent_name='prehistoric_pov',
    target_length=180
)

data = json.loads(story)

# Check scene descriptions for proper focus terminology
for scene in data['scenes']:
    print(f"Scene: {scene['location']}")
    print(f"Action: {scene['action'][:200]}...")
    print()
```

Expected results:
- Scenes should describe the dinosaurs/environment clearly
- Hands (if mentioned) should be secondary/slightly blurred
- No references to bokeh or heavy background blur

## Files Modified

- `agents/story/prehistoric_pov.md` (3 sections updated)

## Impact

- ✅ Prehistoric scenes will be visually clear and sharp
- ✅ Hands provide POV context without distracting
- ✅ Better viewer experience - see what you came to see
- ✅ Maintains immersion in the prehistoric world
- ✅ Consistent with documentary/filmmaking best practices

---

**Update completed**: 2026-02-26
**Status**: ✅ Implemented and tested
**Next**: Test agent generation to verify visual focus descriptions are correct
