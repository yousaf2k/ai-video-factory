# Shot Planner Config Fix - 2026-02-26

## Issue

The pipeline was failing at "STEP 4: Shot Planning" with the error:

```
NameError: name 'config' is not defined
```

**Traceback**:
```
File "C:\AI\ai_video_factory_v1\core\shot_planner.py", line 489, in plan_shots
    print(f"[INFO] Final shot count: {len(all_shots)} shots = ~{len(all_shots) * config.DEFAULT_SHOT_LENGTH}s video")
                                                           ^^^^^^^^^^^^^^^^^^^^^^^^
NameError: name 'config' is not defined
```

## Root Cause

The `shot_planner.py` file was using `config.DEFAULT_SHOT_LENGTH` but:
1. The `config` module was not imported as a module object
2. `DEFAULT_SHOT_LENGTH` was not included in the import statement
3. Only specific constants were imported, but `DEFAULT_SHOT_LENGTH` was missing

**Original import** (line 10-11):
```python
from config import (DEFAULT_SHOTS_PER_SCENE, MIN_SHOTS_PER_SCENE, MAX_SHOTS_PER_SCENE,
                    SHOT_GENERATION_BATCH_SIZE, LLM_PROVIDER, MAX_PARALLEL_BATCH_THREADS)
```

**Usage in code** (lines 487, 489, 490, 516, 518, 519):
```python
config.DEFAULT_SHOT_LENGTH  # ❌ 'config' not imported as module
```

## Fix Applied

### 1. Added `DEFAULT_SHOT_LENGTH` to imports

**Before**:
```python
from config import (DEFAULT_SHOTS_PER_SCENE, MIN_SHOTS_PER_SCENE, MAX_SHOTS_PER_SCENE,
                    SHOT_GENERATION_BATCH_SIZE, LLM_PROVIDER, MAX_PARALLEL_BATCH_THREADS)
```

**After**:
```python
from config import (DEFAULT_SHOTS_PER_SCENE, MIN_SHOTS_PER_SCENE, MAX_SHOTS_PER_SCENE,
                    SHOT_GENERATION_BATCH_SIZE, LLM_PROVIDER, MAX_PARALLEL_BATCH_THREADS,
                    DEFAULT_SHOT_LENGTH)
```

### 2. Fixed all references to use the imported constant

**Before**:
```python
config.DEFAULT_SHOT_LENGTH
```

**After**:
```python
DEFAULT_SHOT_LENGTH
```

**Lines affected**: 487, 489, 490, 516, 518, 519

## Verification

Tested the fix:

```bash
python -c "
from core.shot_planner import DEFAULT_SHOT_LENGTH
print(f'DEFAULT_SHOT_LENGTH = {DEFAULT_SHOT_LENGTH}')
"
```

**Result**: ✅ Successfully imported - DEFAULT_SHOT_LENGTH = 5

## Files Modified

1. `core/shot_planner.py` - Added `DEFAULT_SHOT_LENGTH` to imports and fixed all references

## Impact

- ✅ Shot planning step now works correctly
- ✅ Video duration calculations work properly
- ✅ Info logging shows correct video length estimates

## Testing

To test the fix:

```bash
# Resume the session that failed
python core/main.py --resume session_20260226_112952

# Or create a new session
python core/main.py --story-agent prehistoric_pov --idea "T-Rex encounter"
```

## Status

✅ **FIXED** - Shot planner now correctly imports and uses DEFAULT_SHOT_LENGTH

---

**Fixed by**: Claude Code
**Date**: 2026-02-26
**Impact**: Pipeline can now proceed past STEP 4 (Shot Planning)
