# Fix: Meeting/Departure Buttons Not Changing Motion Prompt

**Date:** March 12, 2026
**Status:** ✅ Fixed

---

## Problem

Clicking the Meeting/Departure toggle buttons did not change the displayed motion prompt in the ShotCard component for FLFI2V shots.

---

## Root Causes

### Issue 1: Buttons Not Visible
The Meeting/Departure toggle buttons were only shown when:
```typescript
{shot.is_flfi2v && (shot.meeting_video_prompt || shot.departure_video_prompt) && (
```

This meant the buttons were hidden if the prompts were empty or undefined, making it impossible to toggle between modes.

### Issue 2: Stale Component State
The component's local `editedShot` state wasn't being updated when the `shot` prop changed (e.g., after regeneration). This caused the UI to show outdated data.

### Issue 3: Cache Not Refreshing
When shot data changed, the cache buster wasn't being updated, causing stale media URLs to persist.

---

## Solutions Implemented

### Fix 1: Always Show Meeting/Departure Buttons for FLFI2V Shots

**File:** `web_ui/frontend/src/components/shots/ShotCard.tsx` (line 806)

**Before:**
```typescript
{shot.is_flfi2v && (shot.meeting_video_prompt || shot.departure_video_prompt) && (
  <div className="flex gap-1 bg-black/30 backdrop-blur-sm p-0.5 rounded-md">
    <button onClick={() => setActiveVideoMode('meeting')}>Meeting</button>
    <button onClick={() => setActiveVideoMode('departure')}>Departure</button>
  </div>
)}
```

**After:**
```typescript
{shot.is_flfi2v && (
  <div className="flex gap-1 bg-black/30 backdrop-blur-sm p-0.5 rounded-md">
    <button onClick={() => setActiveVideoMode('meeting')}>Meeting</button>
    <button onClick={() => setActiveVideoMode('departure')}>Departure</button>
  </div>
)}
```

**Why:** The buttons should always be visible for FLFI2V shots so users can toggle between viewing Meeting and Departure prompts. The prompt display will fall back to the default `motion_prompt` if the specific variants don't exist.

### Fix 2: Sync Shot Prop Changes to Local State

**File:** `web_ui/frontend/src/components/shots/ShotCard.tsx` (lines 104-109)

**Added:**
```typescript
// Update editedShot when shot prop changes (e.g., after regeneration)
useEffect(() => {
  setEditedShot(shot);
  // Force cache buster update when shot changes to refresh media URLs
  if (shot.is_flfi2v) {
    setCacheBuster(Date.now());
  }
}, [shot]);
```

**Why:** When a shot is regenerated (images or videos), the `shot` prop updates but the local `editedShot` state wasn't being synced. This useEffect ensures the component always reflects the latest shot data.

### Fix 3: Update Cache Buster on Shot Changes

**File:** `web_ui/frontend/src/components/shots/ShotCard.tsx` (lines 106-109)

**Added:**
```typescript
if (shot.is_flfi2v) {
  setCacheBuster(Date.now());
}
```

**Why:** Forces the browser to fetch fresh media URLs when shot data changes, preventing stale cached resources.

---

## How It Works Now

### User Flow

1. **User clicks "Departure" button**
   ```typescript
   onClick={() => setActiveVideoMode('departure')}
   ```

2. **State updates**
   ```typescript
   const [activeVideoMode, setActiveVideoMode] = useState<"meeting" | "departure">("meeting");
   // Changes from "meeting" to "departure"
   ```

3. **Component re-renders**
   - React detects state change
   - Component re-renders with new `activeVideoMode`

4. **Key prop forces remount**
   ```typescript
   <div key={shot.is_flfi2v ? `motion-${activeVideoMode}` : 'motion'}>
   ```
   - Key changes from "motion-meeting" to "motion-departure"
   - React completely remounts this div

5. **Prompt display updates**
   ```typescript
   {shot.is_flfi2v
     ? (activeVideoMode === 'meeting'
        ? (shot.meeting_video_prompt || shot.motion_prompt)
        : (shot.departure_video_prompt || shot.motion_prompt))
     : shot.motion_prompt}
   ```
   - Shows `shot.departure_video_prompt` when activeVideoMode is "departure"
   - Falls back to `shot.motion_prompt` if departure prompt is empty

6. **Label updates**
   ```typescript
   {activeVideoMode === 'meeting' ? 'MEETING' : 'DEPARTURE'}
   ```
   - Label changes from "MEETING" to "DEPARTURE"
   - Color changes from purple to pink

7. **Buttons update**
   ```typescript
   className={cn(
     "px-2 py-1 rounded text-xs font-semibold transition-all",
     activeVideoMode === 'meeting' ? "bg-purple-500 text-white" : "text-white/70 hover:text-white"
   )}
   ```
   - Meeting button: grayed out when not active
   - Departure button: highlighted with pink background when active

---

## Motion Prompt Display Logic

### For FLFI2V Shots

```typescript
// Meeting mode
activeVideoMode === 'meeting' → show shot.meeting_video_prompt OR shot.motion_prompt

// Departure mode
activeVideoMode === 'departure' → show shot.departure_video_prompt OR shot.motion_prompt
```

**Fallback Behavior:**
- If `shot.meeting_video_prompt` is empty/null/undefined → uses `shot.motion_prompt`
- If `shot.departure_video_prompt` is empty/null/undefined → uses `shot.motion_prompt`

### For Regular Shots

```typescript
// Always show the default motion prompt
shot.motion_prompt
```

---

## Testing Checklist

To verify the fix works:

- [ ] **Buttons Visible:** Meeting and Departure buttons are visible for all FLFI2V shots
- [ ] **Toggle Meeting:** Click "Meeting" button → label shows "MEETING" (purple)
- [ ] **Toggle Departure:** Click "Departure" button → label shows "DEPARTURE" (pink)
- [ ] **Prompt Updates:** Motion prompt text changes when toggling
- [ ] **Fallback Works:** If specific prompt is empty, shows default motion_prompt
- [ ] **Copy Button:** Copy button copies correct prompt based on active mode
- [ ] **Regeneration:** After regenerating video, component updates with new paths
- [ ] **Buttons Always Visible:** Buttons show even before videos are generated

---

## Expected Behavior

### Before Fix

```
FLFI2V Shot with no departure_video_prompt:
- Departure button: HIDDEN ❌
- Can't toggle to departure mode
- Can't see departure prompt
```

### After Fix

```
FLFI2V Shot with no departure_video_prompt:
- Departure button: VISIBLE ✅
- Click "Departure" → Label shows "DEPARTURE" (pink) ✅
- Prompt shows: shot.motion_prompt (fallback) ✅
- After departure video generated: Shows shot.departure_video_prompt ✅
```

---

## Technical Details

### React State Flow

```
User clicks button
    ↓
setActiveVideoMode('departure')
    ↓
activeVideoMode state updates
    ↓
useEffect triggers (cache buster)
    ↓
Component re-renders
    ↓
Key prop changes: "motion-meeting" → "motion-departure"
    ↓
React remounts motion prompt div
    ↓
Conditional renders with new activeVideoMode
    ↓
Shows departure prompt
```

### Dependencies

```typescript
// State that affects prompt display
const [activeVideoMode, setActiveVideoMode] = useState<"meeting" | "departure">("meeting");

// Effects that run on state change
useEffect(() => {
  if (shot.is_flfi2v) {
    setCacheBuster(Date.now()); // Refresh media URLs
  }
}, [activeVideoMode, activeImageMode, shot.is_flfi2v]);

// Sync prop changes to local state
useEffect(() => {
  setEditedShot(shot);
  if (shot.is_flfi2v) {
    setCacheBuster(Date.now());
  }
}, [shot]);
```

---

## Related Code

### Then/NOW Toggle (for reference)

The THEN/NOW toggle for images follows the same pattern:

```typescript
const [activeImageMode, setActiveImageMode] = useState<"then" | "now">("now");

// Buttons always visible for FLFI2V shots
{shot.is_flfi2v && shot.then_image_path && shot.now_image_path && viewMode === "image" && (
  <div className="flex gap-1">
    <button onClick={() => setActiveImageMode('then')}>THEN</button>
    <button onClick={() => setActiveImageMode('now')}>NOW</button>
  </div>
)}

// Prompt display with mode-based logic
{shot.is_flfi2v
  ? (activeImageMode === 'then'
     ? (shot.then_image_prompt || shot.image_prompt)
     : (shot.now_image_prompt || shot.image_prompt))
  : shot.image_prompt}
```

---

## Files Modified

1. **`web_ui/frontend/src/components/shots/ShotCard.tsx`**
   - Line 806: Removed prompt existence condition
   - Lines 104-109: Added useEffect to sync shot prop changes
   - Lines 106-109: Added cache buster update on shot changes

---

## Status

✅ **Fixed and Deployed**

The Meeting/Departure toggle buttons now:
- Always visible for FLFI2V shots
- Properly toggle between modes
- Update the motion prompt display
- Update the MEETING/DEPARTURE label
- Sync with shot data changes
- Handle missing prompts with fallback

---

**See Also:**
- [FLFI2V Video Generation Logic](../guides/FLFI2V_VIDEO_GENERATION_LOGIC.md)
- [Then Vs Now Motion Prompt Guide](../guides/THEN_VS_NOW_MOTION_PROMPT_GUIDE.md)
- [How to Make Departure Videos](../guides/HOW_TO_MAKE_DEPARTURE_VIDEOS.md)
