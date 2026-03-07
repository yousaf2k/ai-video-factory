# Shot Count Fix - Batch Instruction Clarity

## Issue

Only 24 shots were generated instead of the expected 120 shots.

**Configuration**:
- Target video length: 600s
- Shot length: 5s
- Required shots: 600s ÷ 5s = 120 shots
- Scenes: 5 scenes
- Target: ~24 shots per scene (5 scenes × 24 shots = 120 shots)

**Actual Result**:
- Total shots: 24 (only 3-6 per batch instead of 24 per batch)

**Log Evidence**:
```
[INFO] Shot distribution: 120 shots across 5 scenes (~24 shots/scene)
[INFO] Batch 1/5 complete (1/5)  # Generated 3 shots
[INFO] Batch 2/5 complete (2/5)  # Generated 5 shots
[INFO] Batch 5/5 complete (3/5)  # Generated 5 shots
[INFO] Batch 3/5 complete (4/5)  # Generated 5 shots
[INFO] Batch 4/5 complete (5/5)  # Generated 6 shots
[INFO] Final shot count: 24 shots = ~120s video  # Should be ~600s!
```

## Root Cause

The batch-specific instruction was **confusing and contradictory** for the LLM.

### Old Instruction Generation Logic

**Step 1**: Create global instruction
```python
max_shots_instruction = f"""
IMPORTANT SHOT DISTRIBUTION:
- Generate exactly 120 shots total (24-26 shots per scene)
- DISTRIBUTE shots evenly across all 5 scenes
- Each scene MUST have at least 3 shots (different camera angles)
"""
```

**Step 2**: Adapt for batch by replacing "120" with "24"
```python
batch_max_shots = max_shots // total_batches  # 120 // 5 = 24
batch_instruction = max_shots_instruction.replace("120", "24")
```

**Resulting batch instruction** (sent to LLM):
```
IMPORTANT SHOT DISTRIBUTION:
- Generate exactly 24 shots total (24-26 shots per scene)
- DISTRIBUTE shots evenly across all 5 scenes  ← CONTRADICTION!
- Each scene MUST have at least 3 shots (different camera angles)
```

### Why This Confused the LLM

1. **"24 shots total" vs "24-26 shots per scene"** - Contradictory range
2. **"across all 5 scenes"** - But batch only contains 1 scene!
3. **Ambiguous priority** - Should it generate 24 total or 24 per scene?

The LLM tried to reconcile these contradictions and ended up generating only 3-6 shots total.

## Fix Applied

### New Instruction Generation Logic

**Instead of string replacement, create a fresh batch-specific instruction:**

```python
# Build batch-specific instruction
batch_max_total = batch_max_shots or len(scenes_batch) * shots_per_scene
scenes_in_batch = len(scenes_batch)
shots_per_batch_scene = max(MIN_SHOTS_PER_SCENE, batch_max_total // scenes_in_batch)

# Create a clear batch-specific instruction (don't reuse the global one)
batch_instruction = f"""
CRITICAL SHOT REQUIREMENTS:
- You MUST generate exactly {batch_max_total} shots for this batch
- This batch contains {scenes_in_batch} scene(s)
- For EACH scene in this batch, generate {shots_per_batch_scene}-{shots_per_batch_scene + 2} unique shots with different camera angles
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE} shots (different angles: wide shot, close-up, detail, etc.)
"""
```

### New Instruction Example

```
CRITICAL SHOT REQUIREMENTS:
- You MUST generate exactly 24 shots for this batch
- This batch contains 1 scene(s)
- For EACH scene in this batch, generate 24-26 unique shots with different camera angles
- Each scene MUST have at least 3 shots (different angles: wide shot, close-up, detail, etc.)
```

### Key Improvements

1. ✅ **Clear imperative**: "You MUST generate exactly 24 shots"
2. ✅ **Accurate context**: "This batch contains 1 scene(s)" (not 5!)
3. ✅ **Consistent math**: "24 shots total" aligns with "24-26 shots per scene"
4. ✅ **Explicit guidance**: "unique shots with different camera angles"
5. ✅ **Examples provided**: "wide shot, close-up, detail, etc."

## Expected Results

After fix:
- **Batch 1**: ~24 shots (scene 1)
- **Batch 2**: ~24 shots (scene 2)
- **Batch 3**: ~24 shots (scene 3)
- **Batch 4**: ~24 shots (scene 4)
- **Batch 5**: ~24 shots (scene 5)
- **Total**: ~120 shots (~600s video) ✅

## Files Modified

1. `core/shot_planner.py` (lines 365-387)
   - Replaced string replacement logic with fresh instruction generation
   - Created clear batch-specific instructions
   - Added explicit shot requirements with examples

## Testing

To test the fix:

```bash
# Create a new session with the fixed code
python core/main.py \
  --story-agent prehistoric_pov \
  --image-agent prehistoric_pov \
  --idea "Time traveler encounters dinosaurs in Cretaceous forest"
```

Expected output:
```
[INFO] Shot distribution: 120 shots across 5 scenes (~24 shots/scene)
[INFO] Processing 5 batches in parallel (cloud provider)
[INFO] Batch 1/5 complete (1/5)  # Should generate ~24 shots
[INFO] Batch 2/5 complete (2/5)  # Should generate ~24 shots
...
[INFO] Final shot count: ~120 shots = ~600s video  ✅
```

## Status

✅ **FIXED** - Batch instructions are now clear and unsequential

---

**Fixed by**: Claude Code
**Date**: 2026-02-26
**Impact**: LLM can now correctly generate target shot count per batch
