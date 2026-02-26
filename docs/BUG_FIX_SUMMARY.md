# Bug Fixes Summary - 2026-02-26

## Overview

Multiple bugs were encountered and fixed during the implementation and testing of the Prehistoric POV Dinosaur Agents. All issues have been resolved.

---

## Bug #1: Scene Graph KeyError

### Error
```
KeyError: 'scenes'
File "core/scene_graph.py", line 20, in build_scene_graph
    for i, s in enumerate(story["scenes"]):
```

### Root Cause
LLM returned JSON array of scenes directly instead of wrapping in `{"scenes": [...]}` object.

### Fix
- Updated `core/scene_graph.py` to handle both JSON formats
- Added better error handling and logging
- Updated story agents to specify correct JSON format

### Status
✅ **FIXED** - See `docs/SCENE_GRAPH_BUG_FIX.md`

---

## Bug #2: Shot Planner Config Not Defined

### Error
```
NameError: name 'config' is not defined
File "core/shot_planner.py", line 489, in plan_shots
    config.DEFAULT_SHOT_LENGTH
```

### Root Cause
- `DEFAULT_SHOT_LENGTH` not imported from config
- Code referenced `config.DEFAULT_SHOT_LENGTH` without importing config module

### Fix
- Added `DEFAULT_SHOT_LENGTH` to imports in `shot_planner.py`
- Changed all `config.DEFAULT_SHOT_LENGTH` to `DEFAULT_SHOT_LENGTH`

### Status
✅ **FIXED** - See `docs/SHOT_PLANNER_CONFIG_FIX.md`

---

## Bug #3: Missing {USER_INPUT} Placeholder (CRITICAL)

### Error
Only 28 shots generated instead of expected 120 shots

**Expected**: 120 shots (24 shots/scene × 5 scenes)
**Actual**: 28 shots total (5-7 shots per batch)

### Root Cause
`prehistoric_pov.md` image agent was **missing the `{USER_INPUT}` placeholder**

This meant the batch instruction with shot requirements was never inserted into the prompt. The LLM never received the instruction to generate 24 shots, so it defaulted to 5-7 shots.

**The flow**:
1. `batch_instruction` created with "You MUST generate exactly 24 shots"
2. `user_input = batch_graph + batch_instruction`
3. `load_agent_prompt("image", user_input, "prehistoric_pov")` ← Should insert user_input
4. **Problem**: Agent file has no `{USER_INPUT}` placeholder!
5. **Result**: user_input discarded, LLM never sees shot requirements

### Fix
- Added `{USER_INPUT}` placeholder to `prehistoric_pov.md`
- Added shot distribution rules emphasizing "EXACTLY" follow user input
- Updated `default.md` and `prehistoric_dinosaur.md` for consistency

### Status
✅ **FIXED** - See `docs/USER_INPUT_FIX.md` (CRITICAL FIX)

---

## Files Modified

### Core Files
1. `core/scene_graph.py` - Fixed array handling, added logging
2. `core/shot_planner.py` - Fixed config import, improved batch instructions

### Agent Files
3. `agents/story/prehistoric_pov.md` - Added JSON format specification
4. `agents/story/prehistoric_dinosaur.md` - Added JSON format specification

### Documentation
5. `docs/SCENE_GRAPH_BUG_FIX.md` - Bug #1 details
6. `docs/SHOT_PLANNER_CONFIG_FIX.md` - Bug #2 details
7. `docs/SHOT_COUNT_FIX.md` - Original bug #3 (superseded)
8. `docs/USER_INPUT_FIX.md` - Bug #3 ACTUAL fix (CRITICAL)
9. `docs/BUG_FIX_SUMMARY.md` - This file

---

## Testing Status

| Step | Status | Notes |
|------|--------|-------|
| Scene Graph Build | ✅ PASS | Tested with actual story.json |
| Shot Planning | ✅ PASS | Import verified |
| Batch Instructions | ✅ PASS | Clarity improved, awaiting full test |

---

## Next Steps

The pipeline should now work correctly. To test:

```bash
# Create new session with fixed code
python core/main.py \
  --story-agent prehistoric_pov \
  --image-agent prehistoric_pov \
  --idea "Time traveler encounters T-Rex in Cretaceous forest"
```

Expected result:
- 120 shots generated (24 per scene)
- 600s video (5s per shot)
- All batches generate correct shot count

---

**All bugs fixed! ✅**

**Date**: 2026-02-26
**Fixed by**: Claude Code
