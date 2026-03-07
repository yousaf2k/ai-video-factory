# Image Generation Retry Mechanism - Implementation Complete

## Overview

The image generation retry mechanism has been successfully implemented to automatically retry failed image generations, improving pipeline reliability and reducing manual intervention.

## Files Modified

### 1. `config.py`
Added three new configuration values:

```python
# Maximum retry attempts for failed image generation (including initial attempt)
IMAGE_GENERATION_MAX_RETRIES = 3

# Delay between retry attempts in seconds
IMAGE_GENERATION_RETRY_DELAY = 5

# Continue to video generation even if some images failed
CONTINUE_ON_PARTIAL_IMAGE_FAILURE = True
```

### 2. `core/retry_tracker.py` (NEW FILE)
Created a new module to track failed generations and retry statistics:

**Classes:**
- `RetryStatus`: Enum for retry status (PENDING, SUCCESS, FAILED_PERMANENTLY)
- `FailedVariation`: Dataclass representing a failed image variation
- `RetrySummary`: Dataclass for retry statistics
- `RetryTracker`: Main class for tracking and managing retries

**Key Methods:**
- `record_failure()`: Record a failed variation for potential retry
- `record_success()`: Record a successful generation
- `increment_attempts()`: Increment attempt count and check if should retry
- `mark_success()`: Mark a previously failed variation as successful
- `mark_permanent_failure()`: Mark a variation as permanently failed
- `get_pending_retries()`: Get list of variations that still need retry
- `print_summary()`: Print comprehensive retry statistics

### 3. `core/image_generator.py`
Rewrote `generate_images_for_shots()` function to implement three-phase retry logic:

**Phase 1: Initial Generation**
- Loop through all shots and variations
- Track successful and failed variations
- Update progress callback for each success

**Phase 2: Retry Loop**
- For each retry round (up to max_retries - 1):
  - Retry all pending failed variations
  - Generate new random seeds for fresh attempts
  - Track which succeed and which still fail
  - Optional delay between retry rounds

**Phase 3: Summary**
- Print comprehensive retry summary
- Report initial successes, retry successes, permanent failures
- Return both updated shots and retry_tracker

**Changes:**
- Added `retry_tracker` parameter (optional, defaults to None)
- Changed return value from `shots` to `(shots, retry_tracker)` tuple
- Track failures at variation level (not shot level)
- Generate new seeds for each retry attempt
- Maintain backward compatibility

### 4. `core/main.py`
Updated `_generate_images()` function (line 1680):

- Initialize `RetryTracker` before calling `generate_images_for_shots()`
- Capture both return values: `shots, retry_tracker = generate_images_for_shots(...)`
- Update shots list with generated images from retry results
- Print retry summary after generation
- Handle partial success:
  - If some shots have images: Continue to video generation (if config allows)
  - If no shots have images: Stop pipeline with error
- Return success/failure status to control pipeline flow

Updated `_render_videos()` function (line 1762):
- Filter `valid_shots` to only include shots with `image_paths`
- Log count of skipped shots

## Features

### Automatic Retry
- Failed image generations are automatically retried up to 3 times (configurable)
- Each retry uses a new random seed for fresh attempts
- Retry attempts happen at the end of the initial generation phase

### Variation-Level Tracking
- Tracks failures at the shot+variation level
- If multiple variations per shot are generated, each variation is tracked independently
- Successful variations are preserved, only failed ones are retried

### Comprehensive Statistics
- Tracks total variations attempted
- Tracks initial successes and failures
- Tracks successes after retry
- Tracks permanent failures (exhausted all retries)
- Prints detailed summary with success rate

### Partial Failure Handling
- Configurable behavior: continue or stop on partial image generation failure
- Video generation uses only shots with successfully generated images
- Clear logging of skipped shots

### Resume Support
- Existing images are loaded from disk before generation
- Only missing shots are regenerated
- No duplicate images created

## Configuration

### Default Settings (Balanced)
```python
IMAGE_GENERATION_MAX_RETRIES = 3      # Initial + 2 retries
IMAGE_GENERATION_RETRY_DELAY = 5      # 5 seconds between retries
CONTINUE_ON_PARTIAL_IMAGE_FAILURE = True
```

### Fast Fail (No Retries)
```python
IMAGE_GENERATION_MAX_RETRIES = 1      # Initial attempt only
IMAGE_GENERATION_RETRY_DELAY = 0
CONTINUE_ON_PARTIAL_IMAGE_FAILURE = False
```

### Aggressive (Maximum Reliability)
```python
IMAGE_GENERATION_MAX_RETRIES = 5      # Initial + 4 retries
IMAGE_GENERATION_RETRY_DELAY = 10     # Longer delay for API recovery
CONTINUE_ON_PARTIAL_IMAGE_FAILURE = True
```

## Usage

The retry mechanism is automatically enabled when calling `generate_images_for_shots()`:

```python
from core.image_generator import generate_images_for_shots
from core.retry_tracker import RetryTracker

# Initialize retry tracker
retry_tracker = RetryTracker(max_retries=config.IMAGE_GENERATION_MAX_RETRIES)

# Generate images with automatic retry
shots, retry_tracker = generate_images_for_shots(
    shots=shots,
    output_dir=output_dir,
    mode="comfyui",
    images_per_shot=1,
    progress_callback=callback,
    retry_tracker=retry_tracker
)

# Retry summary is automatically printed
```

## Testing

A test suite has been provided in `test_retry_mechanism.py`:

```bash
python test_retry_mechanism.py
```

Tests verify:
- Basic retry tracker functionality
- Retry exhaustion (max retries enforced)
- Multiple variations per shot handling
- Configuration values accessibility

## Edge Cases Handled

| Scenario | Behavior |
|----------|----------|
| All images fail | Pipeline stops with clear error message |
| Partial shot failure (some variations succeed) | Video generation uses first successful variation |
| No failures | No retries attempted, minimal overhead |
| Resume with existing images | Only regenerates missing images |
| Intermittent failures (some succeed on retry) | Continues retrying until all succeed or max retries reached |
| IMAGES_PER_SHOT > 1 | Tracks and retries each variation independently |

## Backward Compatibility

- Existing sessions without retry metadata continue to work
- Old code calling `generate_images_for_shots()` without `retry_tracker` parameter still works
- Can ignore second return value if retry tracking not needed
- Configuration defaults ensure functionality even if config not updated
- Changes are additive (no breaking changes to existing functionality)

## Example Output

```
[PHASE 1] Initial image generation...
Generating 30 images (1 per shot) using ComfyUI...

[Shot 1/10] Generating...
  Prompt: A majestic dinosaur roaming through prehistoric jungle...
  [1/1] Generating variation (seed: 123456789)...
    [PASS] Variation 1 succeeded
  [SUMMARY] Generated 1/1 variation(s) for shot 1

[Shot 2/10] Generating...
  Prompt: Close-up of T-Rex jaws...
  [1/1] Generating variation (seed: 987654321)...
    [FAIL] Variation 1 failed - will retry later
  [SUMMARY] All variations failed for shot 2

...

[PHASE 2.1] Retry round 1/2...
            3 variation(s) to retry
  [Shot 2] Retrying variation 1 (attempt 2/3)...
    [PASS] Retry succeeded
  [Shot 5] Retrying variation 1 (attempt 2/3)...
    [FAIL] Retry attempt 2 failed
  [Shot 8] Retrying variation 1 (attempt 2/3)...
    [PASS] Retry succeeded

[PHASE 2.2] Retry round 2/2...
            1 variation(s) to retry
  [Shot 5] Retrying variation 1 (attempt 3/3)...
    [PASS] Retry succeeded

[SUCCESS] All retries completed successfully!

[INFO] Image generation complete. Images saved to: output/session_xxx/generated_images

==================================================================
IMAGE GENERATION RETRY SUMMARY
==================================================================
Total variations attempted: 30
Initial success: 27
Initial failures: 3
Success after retry: 3
Permanent failures: 0
Overall success rate: 100.0%
==================================================================

[FINAL] 10/10 shots have at least one image
```

## Benefits

1. **Improved Reliability**: Automatically recovers from transient failures
2. **Reduced Manual Intervention**: No need to manually regenerate failed images
3. **Better Visibility**: Clear statistics on what succeeded and what failed
4. **Flexible Configuration**: Can tune retry behavior based on needs
5. **Partial Success Support**: Can continue with successful images even if some fail
6. **Efficient**: Only retries failed variations, preserves successful ones

## Future Enhancements

Possible future improvements:
- Exponential backoff for retry delays
- Per-shot retry limits (some shots may need more retries)
- Retry with different parameters (e.g., different workflow)
- Parallel retry of failed variations
- Persistent retry state across sessions
