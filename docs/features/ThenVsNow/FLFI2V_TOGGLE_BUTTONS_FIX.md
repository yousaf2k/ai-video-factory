# FLFI2V Toggle Buttons Fix

**Date:** March 12, 2026
**Status:** Fixed

---

## Problem

- THEN image was visible, but NOW image was not
- No toggle buttons to switch between THEN and NOW images
- Status indicators showed "Image Not Generated" even though images existed

---

## Root Causes

### Issue 1: Toggle Buttons Hidden

**Old Code:**
```tsx
{shot.image_path && shot.video_path && (
  // Toggle buttons here
)}
```

**Problem:** Required both `image_path` AND `video_path` to exist, but FLFI2V generates images first, then videos later.

**Fix:**
```tsx
{(shot.image_path || shot.then_image_path || shot.now_image_path || ...) && (
  // Toggle buttons here
)}
```

### Issue 2: Image URL Logic

**Old Code:**
```tsx
const imageUrl = shot.is_flfi2v
  ? getMediaUrl(activeImageMode === 'then' ? shot.then_image_path : shot.now_image_path)
  : getMediaUrl(shot.image_path);
```

**Problem:** If the selected mode's image doesn't exist, shows nothing.

**Fix:**
```tsx
const imageUrl = shot.is_flfi2v
  ? getMediaUrl(
    activeImageMode === 'then'
      ? shot.then_image_path || shot.now_image_path || shot.image_path
      : shot.now_image_path || shot.then_image_path || shot.image_path
  )
  : getMediaUrl(shot.image_path);
```

### Issue 3: Status Indicator

**Old Code:**
```tsx
shot.image_generated ? "✓" : "○"
```

**Problem:** For FLFI2V shots, checks `image_generated` but actual flags are `then_image_generated` and `now_image_generated`.

**Fix:**
```tsx
(shot.then_image_generated || shot.now_image_generated || shot.image_generated)
  ? "✓" : "○"
```

---

## How to Use Toggle Buttons

1. **Generate Images** - Generate both THEN and NOW images
2. **Hover Over Shot** - Toggle buttons appear in top-right corner
3. **Click THEN** - Shows original appearance (purple button)
4. **Click NOW** - Shows current appearance (pink button)

**Button Colors:**
- 🟣 Purple = THEN (original appearance)
- 🩷 Pink = NOW (current appearance)

---

## Video Toggle Buttons

Same pattern applies to videos:
- Meeting (purple) - Arrival at set
- Departure (pink) - Leaving set

---

## File Modified

`web_ui/frontend/src/components/shots/ShotCard.tsx`

**Changes:**
- Line 687: Toggle buttons visibility condition
- Lines 255-260: Image/Video URL fallback logic
- Lines 600-617: Status indicator logic

---

## Testing

1. Generate FLFI2V images
2. Verify toggle buttons appear
3. Click THEN button → Shows THEN image
4. Click NOW button → Shows NOW image
5. Verify status indicator shows checkmark

---

**Status:** ✅ Fixed and ready for use
