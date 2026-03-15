# Error Handling Fix - Loader Not Stopping on Gemini Web Failures

**Date:** March 12, 2026
**Status:** Fixed

---

## Problem

When Gemini Web video generation failed, the initialization/generation loader continued running indefinitely instead of stopping and showing an error. This left the UI in a stuck loading state with no way for the user to recover except by refreshing the page.

---

## Root Cause

When video or image generation failed (e.g., Gemini Web API error), the exception was:
1. Logged to the console
2. Re-raised to the API endpoint
3. Returned as an HTTP 500 error to the client

**However**, no WebSocket "cancelled" event was broadcast to the frontend to clear the loading state. The frontend's `useProgress` hook relies on receiving "progress", "completed", or "cancelled" events to manage the loading spinner.

---

## Solution

Added "cancelled" event broadcasts in all exception handlers for generation functions.

### Files Modified

**`web_ui/backend/services/generation_service.py`**

#### 1. Fixed `regenerate_shot_image()` (lines 371-380)

**Before:**
```python
except Exception as e:
    logger.error(f"Error regenerating shot {shot_index} image: {e}")
    raise
```

**After:**
```python
except Exception as e:
    logger.error(f"Error regenerating shot {shot_index} image: {e}")
    # Broadcast cancelled event to clear loading state in UI
    manager.broadcast_sync(project_id, {
        "type": "cancelled",
        "project_id": project_id,
        "shot_index": shot_index,
        "shot_id": shot.get('id')
    })
    raise
```

#### 2. Fixed `regenerate_shot_video()` (lines 612-621)

**Before:**
```python
except Exception as e:
    logger.error(f"Error regenerating shot {shot_index} video: {e}")
    raise
```

**After:**
```python
except Exception as e:
    logger.error(f"Error regenerating shot {shot_index} video: {e}")
    # Broadcast cancelled event to clear loading state in UI
    manager.broadcast_sync(project_id, {
        "type": "cancelled",
        "project_id": project_id,
        "shot_index": shot_index,
        "shot_id": shot.get('id')
    })
    raise
```

#### 3. Enhanced Batch Generation Error Handling (lines 196-204)

**Before:**
```python
except Exception as e:
    logger.error(f"Batch error on shot {shot_index}: {str(e)}")
    # Broadcast error/cancel so UI spinner doesn't run forever
    manager.broadcast_sync(project_id, {
        "type": "cancelled",
        "project_id": project_id,
        "shot_index": shot_index
    })
```

**After:**
```python
except Exception as e:
    logger.error(f"Batch error on shot {shot_index}: {str(e)}")
    # Broadcast error/cancel so UI spinner doesn't run forever
    manager.broadcast_sync(project_id, {
        "type": "cancelled",
        "project_id": project_id,
        "shot_index": shot_index,
        "shot_id": shot_data.get('id') if shot_data else None
    })
```

Added `shot_id` field for consistency with other broadcasts.

---

## How It Works

### Event Flow (Success)
```
1. User clicks "Regenerate"
2. Frontend shows loading spinner
3. Backend broadcasts "progress" events (0%, 50%, 100%)
4. Backend broadcasts "completed" event
5. Frontend hides loading spinner
```

### Event Flow (Failure - Before Fix)
```
1. User clicks "Regenerate"
2. Frontend shows loading spinner
3. Backend broadcasts "progress" event (0%)
4. Generation fails with exception
5. ❌ No "cancelled" event broadcast
6. ❌ Frontend spinner keeps running forever
```

### Event Flow (Failure - After Fix)
```
1. User clicks "Regenerate"
2. Frontend shows loading spinner
3. Backend broadcasts "progress" event (0%)
4. Generation fails with exception
5. ✅ Backend broadcasts "cancelled" event
6. ✅ Frontend clears progress state
7. ✅ Frontend hides loading spinner
8. ✅ User sees error message from API response
```

---

## Frontend Handling

The frontend's `useProgress` hook (`web_ui/frontend/src/hooks/useProgress.ts`) already properly handles "cancelled" events:

```typescript
else if (data.type === 'cancelled') {
    if (shotKey) {
        setShotProgress((prev) => {
            const next = { ...prev };
            delete next[shotKey];  // Remove from progress state
            return next;
        });
    }
}
```

When a shot is removed from the progress state, the loading spinner automatically disappears.

---

## Affected Generation Methods

This fix applies to all generation methods:

✅ **Image Generation**
- Standard image generation (ComfyUI/Gemini)
- FLFI2V THEN image generation
- FLFI2V NOW image generation

✅ **Video Generation**
- Standard video generation (ComfyUI)
- Gemini Web video generation
- FLFI2V Meeting video generation
- FLFI2V Departure video generation

✅ **Batch Generation**
- Batch image regeneration
- Batch video regeneration

---

## Testing Checklist

To verify the fix works correctly:

- [ ] **Gemini Web Video Failure**: Start a video generation with Gemini Web, force a failure (e.g., invalid image), verify spinner stops
- [ ] **ComfyUI Video Failure**: Start a ComfyUI video generation with ComfyUI disconnected, verify spinner stops
- [ ] **Image Generation Failure**: Start image generation with invalid configuration, verify spinner stops
- [ ] **Batch Generation Failure**: Start batch generation, verify individual shot failures don't block other shots
- [ ] **Error Message Visible**: Verify user can see the error message from the API response
- [ ] **Can Retry**: Verify user can click regenerate again after a failure

---

## Related Code

### WebSocket Message Format

**Cancelled Event:**
```json
{
  "type": "cancelled",
  "project_id": "project_abc123",
  "shot_index": 1,
  "shot_id": "def456"
}
```

### Error Response Format

**API Response (HTTP 500):**
```json
{
  "detail": "Failed to regenerate video: Gemini Web API error: Invalid image format"
}
```

---

## Additional Notes

### Why Re-raise After Broadcasting?

The exception is re-raised after broadcasting the "cancelled" event because:
1. The API endpoint still needs to return an error response to the client
2. The error needs to be logged for debugging
3. The HTTP 500 status code informs the frontend that the operation failed

### Propagation Chain

```
_generate_single_video() raises RuntimeError
    ↓
regenerate_shot_video() catches and broadcasts "cancelled"
    ↓
regenerate_shot_video() re-raises
    ↓
API endpoint catches and returns HTTP 500
    ↓
Frontend receives error response
```

Both the WebSocket event (for real-time UI updates) and the HTTP response (for final error message) are important for a good user experience.

---

**Status:** ✅ Fixed and deployed
