# Critical Fix: Missing {USER_INPUT} Placeholder

## Issue

Only 28 shots generated instead of 120 shots, despite clear batch instructions.

**Configuration**:
- Target: 120 shots (24 shots/scene × 5 scenes)
- Actual: 28 shots (5-7 shots per batch)

**Log Evidence**:
```
[INFO] Shot distribution: 120 shots across 5 scenes (~24 shots/scene)
[INFO] Batch 4/5 complete (1/5)  # Only 5 shots
[INFO] Batch 2/5 complete (2/5)  # Only 5 shots
[INFO] Batch 5/5 complete (3/5)  # Only 5 shots
[INFO] Batch 3/5 complete (4/5)  # Only 6 shots
[INFO] Batch 1/5 complete (5/5)  # Only 7 shots
[INFO] Final shot count: 28 shots = ~140s video  # Should be 600s!
```

## Root Cause

The `prehistoric_pov.md` image agent was **missing the `{USER_INPUT}` placeholder** at the end of the prompt file.

### How the Flow Works

1. **Batch instruction created** in `shot_planner.py`:
```python
batch_instruction = f"""
BATCH PROCESSING: This is batch 1 of 5

CRITICAL SHOT REQUIREMENTS:
- You MUST generate exactly 24 shots for this batch
- This batch contains 1 scene(s)
- For EACH scene in this batch, generate 24-26 unique shots with different camera angles
- Each scene MUST have at least 3 shots (different angles: wide shot, close-up, detail, etc.)

IMPORTANT: Generate ONLY shots for these 1 scenes in this batch.
"""
```

2. **User input assembled**:
```python
user_input = f"{batch_graph}{batch_instruction}"
# batch_graph = JSON of scenes
# batch_instruction = Shot count requirements
```

3. **Agent prompt loaded**:
```python
image_prompt = load_agent_prompt("image", user_input, "prehistoric_pov")
# This loads the agent file and replaces {USER_INPUT} with user_input
```

4. **Prompt sent to LLM**: The agent prompt + user_input (with shot requirements)

### The Problem

The `prehistoric_pov.md` image agent file ended with:
```
## Remember
- First-Person POV
- Hands Visible
- Diegetic Camera
...
You are creating the most immersive, visceral prehistoric POV images ever generated...
```

**There was NO `{USER_INPUT}` placeholder!**

This meant:
- The batch instruction with shot requirements was **never inserted into the prompt**
- The LLM never received the instruction to generate 24 shots
- The LLM defaulted to generating 5-7 shots (its default behavior)

## Fix Applied

### 1. Added Shot Distribution Rules

Added clear shot distribution rules to `prehistoric_pov.md`:

```markdown
## Shot Distribution Rules

**CRITICAL**: Follow the shot count requirements specified in the user input EXACTLY.

- **Minimum**: 3 shots per scene (no exceptions)
- **Target**: As specified in user request (typically 20-30 shots per scene for full documentaries)
- **Variety**: Each scene's shots must use different camera angles and perspectives

**For POV shots, vary the perspective**:
- **Establishing**: Hands holding camera up to see landscape
- **Through-hands**: Looking through hands/foliage
- **Viewfinder**: Looking through camera LCD/eyepiece
- **Close-up**: Hands, equipment, or dinosaur details
- **Reaction**: Hands raised, trembling, reaching
- **Movement**: Walking/running with camera shake
- **Intimate**: Hands touching or offering to dinosaurs

**Camera Movement Types** (use variety):
- **handheld**: Natural breathing movement (subtle shake)
- **slow pan**: Hands turning camera slowly
- **tracking**: Character walking/running while filming
- **static**: Character standing still, recording steady
- **panic shake**: Fear-induced camera movement (intense scenes)
```

### 2. Added {USER_INPUT} Placeholder

Added at the very end of `prehistoric_pov.md`:

```markdown
## Input

You will receive scene descriptions with specific shot count requirements. Create image prompts that capture the essence of each scene visually.

**IMPORTANT**: Each scene includes a "narration" field. You must include this narration text in the shot output under the "narration" key. This narration will be used as voice-over for the video.

**CRITICAL**: The user input will specify EXACTLY how many shots to generate for each scene. You MUST follow this requirement precisely.

{USER_INPUT}
```

### 3. Updated Other Image Agents (for consistency)

- **default.md**: Updated shot distribution rules to emphasize "EXACTLY" following user input
- **prehistoric_dinosaur.md**: Updated shot distribution rules for consistency

## Verification

### Before Fix

**Prompt sent to LLM** (prehistoric_pov.md without {USER_INPUT}):
```
[Full agent prompt about POV shots, hands, camera specs...]
You are creating the most immersive, visceral prehistoric POV images ever generated...
[END OF PROMPT - NO INSTRUCTION ABOUT SHOT COUNT!]
```

**LLM Response**: Generated 5-7 shots (default behavior)

### After Fix

**Prompt sent to LLM** (prehistoric_pov.md with {USER_INPUT}):
```
[Full agent prompt about POV shots, hands, camera specs...]

## Shot Distribution Rules
**CRITICAL**: Follow the shot count requirements specified in the user input EXACTLY.
...

## Input
You will receive scene descriptions with specific shot count requirements.
**CRITICAL**: The user input will specify EXACTLY how many shots to generate for each scene.

{USER_INPUT} ← BATCH INSTRUCTION INSERTED HERE!
```

**Batch instruction inserted at {USER_INPUT}**:
```
BATCH PROCESSING: This is batch 1 of 5

CRITICAL SHOT REQUIREMENTS:
- You MUST generate exactly 24 shots for this batch
- This batch contains 1 scene(s)
- For EACH scene in this batch, generate 24-26 unique shots with different camera angles
- Each scene MUST have at least 3 shots (different angles: wide shot, close-up, detail, etc.)

IMPORTANT: Generate ONLY shots for these 1 scenes in this batch.
```

**Expected LLM Response**: Generate 24 shots as instructed

## Files Modified

1. `agents/image/prehistoric_pov.md` - Added {USER_INPUT} placeholder and shot distribution rules
2. `agents/image/default.md` - Updated shot distribution rules
3. `agents/image/prehistoric_dinosaur.md` - Updated shot distribution rules

## Expected Results After Fix

```
[INFO] Shot distribution: 120 shots across 5 scenes (~24 shots/scene)
[INFO] Processing 5 batches in parallel (cloud provider)
[INFO] Batch 1/5 complete (1/5)  # Should generate ~24 shots ✅
[INFO] Batch 2/5 complete (2/5)  # Should generate ~24 shots ✅
[INFO] Batch 3/5 complete (3/5)  # Should generate ~24 shots ✅
[INFO] Batch 4/5 complete (4/5)  # Should generate ~24 shots ✅
[INFO] Batch 5/5 complete (5/5)  # Should generate ~24 shots ✅
[INFO] Final shot count: ~120 shots = ~600s video  ✅
```

## Testing

To test the fix:

```bash
python core/main.py \
  --story-agent prehistoric_pov \
  --image-agent prehistoric_pov \
  --idea "Time traveler encounters T-Rex in Cretaceous forest"
```

**Expected result**:
- Each batch generates ~24 shots (not 5-7)
- Total shots: ~120 (not 28)
- Video length: ~600s (not 140s)

## Technical Details

### Agent Loader Flow

The `load_agent_prompt()` function in `agent_loader.py`:

```python
def load_agent_prompt(agent_type: str, user_input: str, agent_name: str = "default") -> str:
    loader = get_agent_loader()
    return loader.format_prompt(agent_type, user_input, agent_name)

def format_prompt(self, agent_type: str, user_input: str, agent_name: str = "default") -> str:
    prompt = self.load_prompt(agent_type, agent_name)
    return prompt.replace("{USER_INPUT}", user_input)  # ← Simple string replacement
```

This function:
1. Loads the agent prompt file (e.g., `prehistoric_pov.md`)
2. Replaces `{USER_INPUT}` with the provided user_input string
3. Returns the complete prompt

**If `{USER_INPUT}` is missing from the agent file**, the replacement does nothing, and the user_input (containing shot count requirements) is silently discarded!

### Why This Bug Wasn't Caught Earlier

1. Other image agents (default, time_traveler, artistic, etc.) had `{USER_INPUT}`
2. Only `prehistoric_pov.md` was missing it (newly created agent)
3. No validation to check if `{USER_INPUT}` exists in agent files
4. No error if replacement doesn't find the placeholder

### Prevention

For future agent files, ensure:
1. ✅ All agent files have `{USER_INPUT}` at the end
2. ✅ Shot distribution rules explicitly state to follow user input requirements
3. ✅ Use "CRITICAL" and "MUST" language for important requirements
4. ✅ Test new agents with shot count requirements

## Status

✅ **FIXED** - {USER_INPUT} placeholder added to prehistoric_pov.md
✅ **READY FOR TESTING** - Run new session to verify fix

---

**Fixed by**: Claude Code
**Date**: 2026-02-26
**Impact**: LLM now receives shot count instructions and should generate correct number of shots
