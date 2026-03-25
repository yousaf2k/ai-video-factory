# Viewing THEN and NOW Prompts in Shot Cards

**Date:** March 12, 2026
**Status:** Updated

---

## Overview

For FLFI2V shots, the prompt display now shows **different prompts based on the active mode**:
- **THEN mode** → Shows THEN image prompt and Meeting video prompt
- **NOW mode** → Shows NOW image prompt and Departure video prompt

---

## How to View Prompts

### Non-Editing Mode (Default)

When viewing a shot card (not editing):

#### Image Prompt Section
```
┌─────────────────────────────────────┐
│ Image Prompt [THEN badge]           │  ← Purple badge for THEN
│ Copy button                          │
└─────────────────────────────────────┘
[THEN prompt text here]
```

**Toggle to see different prompts:**
1. Click **THEN** button (purple) → Shows `then_image_prompt`
2. Click **NOW** button (pink) → Shows `now_image_prompt`
3. The badge color changes to match active mode

#### Motion Prompt Section
```
┌─────────────────────────────────────┐
│ Motion Prompt [MEETING badge]        │  ← Purple badge for Meeting
│ Copy button                          │
└─────────────────────────────────────┘
[Meeting video prompt here]
```

**Toggle to see different prompts:**
1. Switch view mode to "Video"
2. Click **Meeting** button (purple) → Shows `meeting_video_prompt`
3. Click **Departure** button (pink) → Shows `departure_video_prompt`

---

## Visual Indicators

### Image Mode Prompts

| Active Mode | Badge Color | Prompt Shown |
|-------------|-------------|--------------|
| THEN | 🟣 Purple | `then_image_prompt` |
| NOW | 🩷 Pink | `now_image_prompt` |

### Video Mode Prompts

| Active Mode | Badge Color | Prompt Shown |
|-------------|-------------|--------------|
| Meeting | 🟣 Purple | `meeting_video_prompt` |
| Departure | 🩷 Pink | `departure_video_prompt` |

---

## Copying Prompts

### Copy Button Behavior

The copy button automatically copies the **active** prompt:

- In image mode with THEN active → Copies THEN image prompt
- In image mode with NOW active → Copies NOW image prompt
- In video mode with Meeting active → Copies Meeting video prompt
- In video mode with Departure active → Copies Departure video prompt

**Visual feedback:** Button turns green with checkmark when copied

---

## Editing FLFI2V Prompts

When in edit mode, FLFI2V shots show **separate fields** for each prompt:

### Image Prompts (Edit Mode)

```
┌─────────────────────────────────────┐
│ THEN Image Prompt                   │  ← Purple label
│ [Textarea field]                    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ NOW Image Prompt                    │  ← Pink label
│ [Textarea field]                    │
└─────────────────────────────────────┘
```

### Motion Prompts (Edit Mode)

```
┌─────────────────────────────────────┐
│ Meeting Video Prompt                │  ← Purple label
│ [Textarea field]                    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Departure Video Prompt              │  ← Pink label
│ [Textarea field]                    │
└─────────────────────────────────────┘
```

---

## Regenerate Prompt Override

When you click "Regenerate Image" from the action menu:

1. The prompt textarea is **pre-populated** with the active mode's prompt:
   - THEN active → Pre-fills with `then_image_prompt`
   - NOW active → Pre-fills with `now_image_prompt`

2. You can edit the prompt before regenerating

3. The regeneration uses the **active mode's prompt**, not the standard `image_prompt`

---

## Prompt Fields Reference

### FLFI2V Shot Fields

**Image Prompts:**
- `then_image_prompt` - Younger character alone
- `now_image_prompt` - Both characters with selfie
- `image_prompt` - Fallback (usually set to `now_image_prompt`)

**Video Prompts:**
- `meeting_video_prompt` - Arrival at set
- `departure_video_prompt` - Leaving set
- `motion_prompt` - Fallback (usually set to `meeting_video_prompt`)

---

## Step-by-Step: View THEN Prompt

1. **Generate images** for the FLFI2V shot
2. **Navigate to shot card**
3. **Click THEN button** (purple) in toggle controls
4. **View Image Prompt section**:
   - Badge shows "THEN" in purple
   - Displayed text is `then_image_prompt`
5. **Click copy button** to copy THEN prompt

---

## Step-by-Step: View NOW Prompt

1. **Generate images** for the FLFI2V shot
2. **Navigate to shot card**
3. **Click NOW button** (pink) in toggle controls
4. **View Image Prompt section**:
   - Badge shows "NOW" in pink
   - Displayed text is `now_image_prompt` (selfie composition)
5. **Click copy button** to copy NOW prompt

---

## Examples

### Example: The Godfather - THEN Image Prompt

```
Medium shot of young Marlon Brando as Don Vito Corleone in tuxedo,
rosary beads in hand, period-accurate 1970s costume, standing in dark
office setting, cinematic lighting, film grain texture, 1970s
cinematography style, neutral expression
```

### Example: The Godfather - NOW Image Prompt

```
Medium shot showing both characters side by side on dark movie set
background. On the left: young Marlon Brando as Don Vito Corleone in
tuxedo with rosary. On the right: older Marlon Brando in elegant dark
suit taking selfie with iPhone 15 Pro Max. Phone with titanium frame
and triple camera system clearly visible in his extended hand, screen
shows camera interface. Both look at camera, older Brando has nostalgic
smile. Cinematic lighting, modern 4K quality, warm tones, depth of field
with dark office background
```

---

## Technical Details

### Badge Component

```tsx
<span className={cn(
  "ml-2 text-[9px] px-1.5 py-0.5 rounded font-semibold",
  activeImageMode === 'then' ? "bg-purple-500 text-white" : "bg-pink-500 text-white"
)}>
  {activeImageMode === 'then' ? 'THEN' : 'NOW'}
</span>
```

### Prompt Display Logic

**Image Prompt:**
```tsx
{shot.is_flfi2v
  ? (activeImageMode === 'then' ? shot.then_image_prompt : shot.now_image_prompt)
  : shot.image_prompt}
```

**Motion Prompt:**
```tsx
{shot.is_flfi2v
  ? (activeVideoMode === 'meeting' ? shot.meeting_video_prompt : shot.departure_video_prompt)
  : shot.motion_prompt}
```

---

## File Modified

**File:** `web_ui/frontend/src/components/shots/ShotCard.tsx`

**Changes:**
- Lines 781-842: Updated prompt display sections
- Lines 313-389: Updated edit mode with FLFI2V fields
- Line 217: Updated regenerate pre-population

---

## Testing Checklist

- [ ] Click THEN button → Badge shows THEN, displays THEN prompt
- [ ] Click NOW button → Badge shows NOW, displays NOW prompt
- [ ] Switch to video mode → Shows Meeting/Departure toggles
- [ ] Edit shot → See separate THEN/NOW prompt fields
- [ ] Copy button → Copies active mode's prompt
- [ ] Regenerate → Pre-fills with active mode's prompt

---

## Troubleshooting

### Q: I only see "Image Prompt" with no badge

**A:** The shot is not FLFI2V. Only FLFI2V shots have THEN/NOW badges and toggle buttons.

### Q: I clicked THEN but still see NOW prompt

**A:** Try refreshing the page. If issue persists, check that `then_image_prompt` is populated in shots.json.

### Q: Can I edit both THEN and NOW prompts?

**A:** Yes! Click the "Edit" button on the shot card to see separate fields for each prompt.

### Q: Which prompt is used for regeneration?

**A:** The prompt of the **active mode**. If THEN is active, it uses `then_image_prompt`. If NOW is active, it uses `now_image_prompt`.

---

**Status:** ✅ Updated and ready for use

**Next Steps:**
1. Generate images for a FLFI2V shot
2. Use toggle buttons to switch between THEN and NOW
3. Observe prompt section changing based on active mode
4. Edit prompts to customize THEN/NOW separately
