# Visual Focus Guidelines Violation Report

## Date: 2026-02-26

## Problem Identified

The **image generation agent** (`agents/image/prehistoric_pov.md`) has NOT been updated with the visual focus guidelines that were added to the **story agent** (`agents/story/prehistoric_pov.md`).

## Guidelines from Story Agent (UPDATED)

From `agents/story/prehistoric_pov.md`:

**Visual Focus Guidelines**:
- ✅ Background Scene MUST be Sharp and Clear (dinosaurs, landscape, action)
- ✅ Hands Can Be Slightly Blurred (at edges/sides of frame)
- ✅ NO Bokeh Effect (no heavy blur that obscures background)
- ✅ Background Takes Priority (prehistoric environment is primary subject)

## Current State of Image Agent (VIOLATIONS)

The image agent `agents/image/prehistoric_pov.md` contains multiple violations:

### ❌ Violation Examples Found in Image Agent

**Line 91** (Scientific Documentation example):
```
"Shallow depth of field focusing on hands and specimen tool, Brachiosaurus softly blurred in background"
```
**Problem**: Brachiosaurus (the main subject!) is blurred
**Should be**: Sharp Brachiosaurus, hands can be slightly blurred

---

**Line 102** (Intimate Encounter example):
```
"Soft focus background, intimate proximity, dinosaur eye contact"
```
**Problem**: "Soft focus background" blurs the dinosaur
**Should be**: Sharp dinosaur, hands at frame edges can be soft

---

**Line 142** (Through-Foliage Encounter example):
```
"f/2.8 shallow depth of field"
```
**Problem**: f/2.8 creates very shallow DOF, blurs the background dinosaurs
**Should be**: f/4-f/5.6 for deeper DOF, keep dinosaurs sharp

---

**Line 173** (Intimate Encounter example):
```
"f/2.8 shallow depth of field, Soft focus background"
```
**Problem**: Explicitly states "soft focus background"
**Should be**: Remove soft focus reference

---

**Line 165** (Scientific Documentation example):
```
"Shallow depth of field focusing on hands and caliper, Brachiosaurus softly blurred in background"
```
**Problem**: Blurs the Brachiosaurus (main subject)
**Should be**: Sharp Brachiosaurus in background

---

## Issues Found in Actual Generated Prompts

From `output/sessions/session_20260226_142319/shots.json`:

### Shot 16 (index 16):
```
"distant Edmontosaurus herd blurred in background"
```
**Problem**: Explicitly blurs the dinosaurs
**Severity**: CRITICAL - obscures the main subject

---

### Shot 19 (index 19):
```
"Shallow depth of field highlighting the footprint, Edmontosaurus adding to the environment"
```
**Problem**: Focus on footprint instead of dinosaurs
**Severity**: HIGH - wrong primary subject

---

### Shot 23 (index 23):
```
"distant Edmontosaurus herd in soft focus background"
```
**Problem**: "Soft focus" blurs the dinosaurs
**Severity**: HIGH

---

### Shot 24 (index 24):
```
"shallow depth of field focusing on the flower, nature in the shot"
```
**Problem**: Focus on flower instead of dinosaurs in background
**Severity**: MEDIUM-MISSING MAIN SUBJECT

---

### Shot 25 (index 25):
```
"shallow depth of field focusing on the map, highlighting expedition"
```
**Problem**: Focus on map instead of Edmontosaurus
**Severity**: MEDIUM

---

### Shot 653 (line 653):
```
"blurred background showing Velociraptors"
```
**Problem**: Velociraptors (danger/thrill!) are blurred
**Severity**: CRITICAL

---

## Root Cause

The image agent was created/updated BEFORE the visual focus guidelines were added to the story agent. The two agents are now **out of sync**.

## Impact

When users generate videos using the prehistoric_pov agent:
1. **Story agent** correctly specifies: "Sharp background scene, hands can be soft"
2. **Image agent** generates prompts that: "Blur the background dinosaurs"
3. **Result**: Generated images have BLURRED DINOSAURS (the main subject!)
4. **Viewer experience**: Poor - can't see what they came to see

## Solution Required

Update `agents/image/prehistoric_pov.md` to match the visual guidelines from the story agent:

### Changes Needed:

1. **Add Visual Focus Guidelines section** to image agent
2. **Update all example prompts** to show sharp dinosaurs/background
3. **Remove "soft focus background"** from all examples
4. **Change aperture recommendations** from f/2.8 to f/4-f/5.6 (deeper DOF)
5. **Update template text** to specify sharp background
6. **Add explicit warnings** about NOT blurring the main subject

### Example Fixes Required:

**Example 1 - Scientific Documentation (Line 91)**
❌ BEFORE: "Shallow depth of field focusing on hands and specimen tool, Brachiosaurus softly blurred in background"
✅ AFTER: "Sharp focus on Brachiosaurus grazing in background, hands slightly blurred at frame edges holding specimen tool"

---

**Example 2 - Through-Foliage (Line 142)**
❌ BEFORE: "f/2.8 shallow depth of field"
✅ AFTER: "f/4 aperture for medium depth of field"

---

**Example 3 - Intimate Encounter (Line 173)**
❌ BEFORE: "f/2.8 shallow depth of field, Soft focus background"
✅ AFTER: "f/4 aperture, sharp focus on dinosaur in background, hands soft at frame edges"

---

## Priority

**SEVERITY**: HIGH

**URGENCY**: IMMEDIATE

Users are currently generating images with blurred dinosaurs, which defeats the purpose of the documentary. This needs to be fixed ASAP.

## Files Requiring Updates

1. **agents/image/prehistoric_pov.md** - Add visual focus guidelines (CRITICAL)
2. All example prompts in the file (8-10 examples need fixing)

## Test Procedure

After fixing:
1. Generate new story with prehistoric_pov agent
2. Check generated image prompts
3. Verify ALL prompts specify sharp dinosaurs/background
4. Confirm hands may be "soft" or "slightly blurred" but NEVER the main subject

---

**Report Generated**: 2026-02-26
**Status**: ⚠️ ACTION REQUIRED
**Next Step**: Update image agent with visual focus guidelines
