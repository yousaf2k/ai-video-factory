# FLFI2V Creative Direction Update: Selfie Composition

**Date:** March 12, 2026
**Status:** Updated

---

## New Creative Direction

The NOW images now feature a **medium shot selfie composition** showing both THEN (younger) and NOW (older) versions of each character together in the same frame.

### Key Changes

#### Before: Separate Images
- **THEN image:** Younger character alone on set
- **NOW image:** Older character alone on set
- UI toggle switches between two separate images

#### After: Combined Selfie
- **THEN image:** Younger character alone (unchanged)
- **NOW image:** **Both characters together** - older character taking selfie with iPhone 15 Pro Max, younger character visible beside them
- UI toggle still switches, but NOW image shows both characters

---

## NOW Image Composition Details

### Composition: Medium Shot Side-by-Side

**Layout:**
```
┌─────────────────────────────────────┐
│  Movie Set Background               │
│                                     │
│  [YOUNGER]  [OLDER + iPhone]       │
│   THEN           NOW               │
│                                     │
└─────────────────────────────────────┘
```

**Elements:**
1. **Left side:** Younger version of character in original movie attire
2. **Right side:** Older version of character in modern attire
3. **Action:** Older character extends arm holding iPhone 15 Pro Max
4. **iPhone:** Clearly visible with titanium frame and triple camera system
5. **Phone screen:** Shows camera app interface
6. **Both characters:** Looking at camera, nostalgic expression
7. **Shot type:** Medium shot (waist up)
8. **Background:** Same movie set for both characters

---

## Prompt Structure

### THEN Prompt (Unchanged)
```
Medium shot of young actor in original movie attire, period-accurate costume,
iconic character pose, standing on movie set, cinematic lighting, film grain
texture, [era] cinematography style, neutral expression
```

### NOW Prompt (NEW)
```
Medium shot showing both characters side by side on the same movie set background.
On the left: the original younger version of the character from the film in
period-accurate costume. On the right: the current older version of the actor
taking a selfie with an iPhone 15 Pro Max. The older actor extends arm holding
the phone, iPhone 15 Pro Max is clearly visible in frame with screen showing
camera interface. Both characters look at camera, the older actor has a nostalgic
smile. Cinematic lighting, modern 4K quality, depth of field with movie set in background
```

---

## Technical Specifications

### iPhone 15 Pro Max Details

**Visual Requirements:**
- Titanium frame visible
- Triple camera system visible
- Screen shows camera app interface
- Phone clearly in actor's hand
- Natural grip position
- Screen facing actor (selfie angle)

**Keywords to Include:**
- "iPhone 15 Pro Max"
- "titanium frame"
- "triple camera system"
- "taking selfie"
- "phone visible in frame"
- "screen showing camera interface"

### Shot Composition

**Camera:** Medium shot (waist up)
**Framing:** Both characters fully visible
**Spacing:** Side-by-side, slight gap between characters
**Depth:** Shallow depth of field with movie set in background
**Lighting:** Cinematic, natural set lighting
**Expression:** Nostalgic smile on older character, neutral on younger

---

## Example Prompts

### The Godfather - Marlon Brando as Don Vito Corleone

**THEN Prompt:**
```
Medium shot of young Marlon Brando as Don Vito Corleone in tuxedo,
rosary beads in hand, period-accurate 1970s costume, standing in dark
office setting, cinematic lighting, film grain texture, 1970s cinematography
style, neutral expression
```

**NOW Prompt:**
```
Medium shot showing both characters side by side on dark movie set background.
On the left: young Marlon Brando as Don Vito Corleone in tuxedo with rosary.
On the right: older Marlon Brando in elegant dark suit taking selfie with iPhone
15 Pro Max. Phone with titanium frame and triple camera system clearly visible
in his extended hand, screen shows camera interface. Both look at camera,
older Brando has nostalgic smile. Cinematic lighting, modern 4K quality,
warm tones, depth of field with dark office background
```

---

## Scene Descriptions

### Meeting Scene (Updated)
```
[Meeting] Actor walks onto the set holding iPhone 15 Pro Max, younger version
of self visible beside them, touching the controls while capturing moment
on phone, looking around in awe while a grip walks past with a light
```

### Departure Scene (Updated)
```
[Departure] Actor takes one last look at the set with younger self beside them,
both smile at iPhone camera capturing final memory, they walk away from set
into shadows together
```

---

## Video Prompts

### Meeting Video (Updated)
```
Slow push-in camera move, older actor walks onto the iconic set with younger
self visible beside them, holding iPhone 15 Pro Max to capture the moment,
eyes widening in recognition, hand touching familiar prop, subtle production
crew in background, atmospheric lighting
```

### Departure Video (Updated)
```
Slow pull-out camera move, older actor takes one last look with younger self
beside them, both smile at camera through iPhone screen as they capture final
memory, bittersweet expression, walking away from set into shadows together,
cross-fade effect, emotional crescendo
```

---

## Thumbnail Prompts

### 16:9 Thumbnail (Updated)
```
Movie poster style with 'THEN VS NOW' text, medium shot showing younger
character on left and older character taking selfie with iPhone on right,
both on iconic movie set background
```

### 9:16 Thumbnail (Updated)
```
Vertical movie poster with 'THEN VS NOW' text, medium shot of older actor
holding iPhone 15 Pro Max taking selfie with younger version beside them
on movie set
```

---

## Why This Approach

### Benefits

1. **Visual storytelling:** Shows the passage of time directly
2. **Relatable:** Selfie is a modern, familiar action
3. **Connection:** Both characters interact, creating emotional resonance
4. **Technology:** iPhone 15 Pro Max adds contemporary relevance
5. **Composition:** Medium shot captures both faces clearly
6. **Nostalgia:** Older character capturing memory with younger self

### Creative Intent

- **Reunion theme:** Characters literally "meet" through the selfie
- **Memory capture:** iPhone represents documenting the moment
- **Time bridge:** Phone screen becomes portal between eras
- **Personal:** Selfie creates intimate, authentic feel

---

## Generation Notes

### For Image Generation Models

**Important:** When generating NOW images, ensure:
- Both characters are visible in frame
- iPhone is clearly visible and recognizable as iPhone 15 Pro Max
- Selfie composition looks natural (not forced)
- Both characters have proper facial visibility
- Movie set background is consistent with THEN image
- Medium shot framing (waist up) is maintained

### Quality Checks

✅ Both characters visible and recognizable
✅ iPhone 15 Pro Max clearly visible with titanium frame
✅ Phone screen showing camera interface
✅ Medium shot composition maintained
✅ Movie set background consistent
✅ Natural selfie arm position
✅ Both characters looking at camera
✅ Nostalgic, emotional expression

---

## Testing Checklist

- [ ] THEN image shows younger character alone
- [ ] NOW image shows both characters side-by-side
- [ ] iPhone 15 Pro Max is visible in NOW image
- [ ] Phone screen shows camera interface
- [ ] Medium shot framing maintained
- [ ] Both characters looking at camera
- [ ] Movie set background consistent
- [ ] Nostalgic expression on older character
- [ ] Natural selfie composition

---

## File Modified

**File:** `agents/story/then_vs_now.md`

**Changes:**
- Lines 53-60: Character prompts (now_prompt updated)
- Lines 31-32: Thumbnail prompts updated
- Lines 67-69: Scene descriptions updated
- Lines 77-79: Departure scene updated
- Lines 7-8: Important notes added

---

## Example Output

When generating a "The Godfather" project, the NOW image prompt will be:

```
Medium shot showing both characters side by side on dark movie set background.
On the left: young Marlon Brando as Don Vito Corleone in tuxedo with rosary.
On the right: older Marlon Brando in elegant dark suit taking selfie with iPhone
15 Pro Max. Phone with titanium frame and triple camera system clearly visible
in his extended hand, screen shows camera interface. Both look at camera,
older Brando has nostalgic smile. Cinematic lighting, modern 4K quality,
warm tones, depth of field with dark office background. Background:
Detailed description of the movie set background: dark office with period furniture,
warm lamp lighting, vintage desk and chair, atmospheric shadows, rich wood tones,
1970s production design.
```

---

**Status:** ✅ Updated and ready for use

**Next Steps:**
1. Create a new ThenVsNow project
2. Generate images to see the new selfie composition
3. Verify iPhone 15 Pro Max is visible
4. Check that both characters appear in NOW images
