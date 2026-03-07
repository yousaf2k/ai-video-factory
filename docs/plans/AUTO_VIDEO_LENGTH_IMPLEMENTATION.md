# Automatic Video Length Calculation - Implementation Summary

## Overview

This implementation adds automatic video length calculation to the AI Video Factory system. The system now automatically calculates the number of shots needed to cover a target video length, using a clear priority chain.

## Changes Made

### 1. config.py (Lines 284-323)

**Added `calculate_max_shots_from_config()` helper function**

This function implements the priority chain for determining max_shots:

1. **Manual Override** (`DEFAULT_MAX_SHOTS > 0`): Returns exact shot count
2. **Automatic Calculation** (`TARGET_VIDEO_LENGTH > 0`): Returns `int(TARGET_VIDEO_LENGTH / DEFAULT_SHOT_LENGTH)`
3. **No Limit** (both are 0): Returns `None` for story-driven generation

**Example calculations:**
- `DEFAULT_MAX_SHOTS = 0, TARGET_VIDEO_LENGTH = 600` → 120 shots (600 ÷ 5)
- `DEFAULT_MAX_SHOTS = 50, TARGET_VIDEO_LENGTH = 600` → 50 shots (manual override)
- `DEFAULT_MAX_SHOTS = 0, TARGET_VIDEO_LENGTH = 0` → None (no limit)

### 2. core/main.py (Lines 1093-1140)

**Updated video configuration logic**

Replaced the existing priority chain with clearer logic:
- Priority 1: `--total-length N` (CLI) → Calculate shots from length
- Priority 2: `--max-shots N` (CLI) → Exact shot count (including 0 for no limit)
- Priority 3: Config automatic → Use `calculate_max_shots_from_config()`

**Enhanced logging:**
- Shows calculation: "Automatic calculation: 600s ÷ 5s/shot = 120 shots"
- Indicates source: "from --total-length", "from DEFAULT_MAX_SHOTS manual override", etc.

**Fixed resume session bug (Line 2613):**
- Before: `max_shots=args.max_shots or config.DEFAULT_MAX_SHOTS` (bug: `0` is falsy)
- After: `max_shots=args.max_shots if args.max_shots is not None else calculate_max_shots_from_config()`

**Updated config display (Lines 140-145):**
- Now shows calculated max_shots instead of raw config value
- Displays "No limit (story-driven)" when appropriate

### 3. core/shot_planner.py (Lines 333-347, 481-510)

**Added shot distribution planning logs:**
- Shows: `[INFO] Shot distribution: 120 shots across 10 scenes (~12 shots/scene)`

**Added results logging:**
- After enforcing max_shots limit
- Shows: `[INFO] Target achieved: 120 shots = ~600s video`
- Shows: `[INFO] Final shot count: 115 shots = ~575s video`

## Verification

### Test Script

Created `test_auto_calculation.py` to verify all calculation scenarios:

```bash
python test_auto_calculation.py
```

All tests pass:
- ✓ Automatic calculation from TARGET_VIDEO_LENGTH
- ✓ Manual override takes priority
- ✓ No limit when both are 0
- ✓ Different shot lengths
- ✓ Small video lengths

### Real Config Test

```bash
python -c "import config; print(config.calculate_max_shots_from_config())"
# Output: 120
```

## Usage Examples

### Example 1: Default Automatic Calculation
```bash
# config.py: TARGET_VIDEO_LENGTH = 600, DEFAULT_MAX_SHOTS = 0
python core/main.py --idea "My documentary"

# Output:
# [INFO] Target video length: 600s (from config)
# [INFO] Automatic calculation: 600s ÷ 5s/shot = 120 shots
# [INFO] Shot distribution: 120 shots across 10 scenes (~12 shots/scene)
# [INFO] Target achieved: 120 shots = ~600s video
```

### Example 2: CLI Override
```bash
python core/main.py --idea "Test" --total-length 120

# Output:
# [INFO] Target video length: 120s (from --total-length)
# [INFO] Automatic calculation: 120s ÷ 5s/shot = 24 shots
# [INFO] Target achieved: 24 shots = ~120s video
```

### Example 3: Manual Override in Config
```bash
# config.py: DEFAULT_MAX_SHOTS = 50, TARGET_VIDEO_LENGTH = 600
python core/main.py --idea "Test"

# Output:
# [INFO] Maximum shots: 50 (from DEFAULT_MAX_SHOTS manual override)
# [INFO] Target achieved: 50 shots = ~250s video
```

### Example 4: No Limit
```bash
python core/main.py --idea "Test" --max-shots 0

# Output:
# [INFO] No shot limit (--max-shots 0)
# [INFO] Final shot count: 200 shots = ~1000s video (story-driven)
```

## Backward Compatibility

✅ **Preserved:**
- `--max-shots N` continues to work (exact shot count)
- `--total-length N` continues to work (with better logging)
- Manual override (`DEFAULT_MAX_SHOTS > 0`) takes priority

✅ **Bug fix:**
- `--max-shots 0` now correctly means "no limit"

⚠️ **Behavior change (desired fix):**
- Config with `TARGET_VIDEO_LENGTH=600, DEFAULT_MAX_SHOTS=0` now generates 120 shots
- Previously: Generated unlimited shots (TARGET_VIDEO_LENGTH was ignored)
- Migration: Users who want unlimited shots should set `TARGET_VIDEO_LENGTH = 0`

## Configuration Guide

### For 10-minute videos (default):
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 600  # 10 minutes
DEFAULT_SHOT_LENGTH = 5
```
Result: 120 shots automatically

### For story-driven (no limit):
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 0
```
Result: As many shots as the story needs

### For testing (limit shots):
```python
DEFAULT_MAX_SHOTS = 10  # Manual override
TARGET_VIDEO_LENGTH = 600  # Ignored due to manual override
```
Result: Exactly 10 shots

## Files Modified

1. `config.py` - Added `calculate_max_shots_from_config()` helper
2. `core/main.py` - Updated priority chain logic and fixed resume bug
3. `core/shot_planner.py` - Enhanced logging for distribution and results
4. `test_auto_calculation.py` - New test script (created)
5. `docs/AUTO_VIDEO_LENGTH_IMPLEMENTATION.md` - This documentation (created)
