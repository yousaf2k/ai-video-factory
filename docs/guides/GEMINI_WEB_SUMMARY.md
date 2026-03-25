# GeminiWeb Image Generation — Walkthrough

## Summary

Added a new image generation mode called **"geminiweb"** that uses Playwright browser automation to generate images via `gemini.google.com/app` (NanoBanana Pro model). The prompt includes both the image description and desired aspect ratio.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| [geminiweb_image_generator.py](file:///c:/AI/ai_video_factory_v1/core/geminiweb_image_generator.py) | **NEW** | Browser automation module using Playwright |
| [image_generator.py](file:///c:/AI/ai_video_factory_v1/core/image_generator.py) | Modified | Added [geminiweb](file:///c:/AI/ai_video_factory_v1/core/geminiweb_image_generator.py#427-663) mode dispatch in [generate_image()](file:///c:/AI/ai_video_factory_v1/core/image_generator.py#115-143) |
| [config.py](file:///c:/AI/ai_video_factory_v1/config.py) | Modified | Added `GEMINIWEB_CHROME_PROFILE`, `GEMINIWEB_TIMEOUT`, `GEMINIWEB_URL` |
| [page.tsx](file:///c:/AI/ai_video_factory_v1/web_ui/frontend/src/app/config/page.tsx) | Modified | Added "GeminiWeb" option to Image Mode dropdown |
| [requirements.txt](file:///c:/AI/ai_video_factory_v1/requirements.txt) | Modified | Added `playwright>=1.40.0` |

## Key Design Decisions

- **Persistent Chrome profile** (`output/chrome_profile/`) — Google login persists across runs, no re-auth needed
- **Clipboard paste input method** — Text is typed via the `navigator.clipboard.writeText()` API and pasted via `Ctrl+V` to safely bypass Chrome's TrustedHTML policies on the Quill editor.
- **Multiple image extraction strategies** — data URI → blob URL → HTTP download → screenshot fallback
- **Module-level browser reuse** — browser context stays alive across calls for performance
- **Lazy import** — `geminiweb_image_generator` only imported when mode is [geminiweb](file:///c:/AI/ai_video_factory_v1/core/geminiweb_image_generator.py#427-663)

## Verification Results

A live test was run to verify the full pipeline end-to-end. 
*(Note: Initial failures during the first test run were due to manual user interaction (logging in and typing the prompt) interrupting the Playwright automation).*

```
✅ Import test:      from core.geminiweb_image_generator import generate_image_geminiweb → OK
✅ Config test:      GEMINIWEB_CHROME_PROFILE, GEMINIWEB_TIMEOUT, GEMINIWEB_URL → all loaded
✅ Dispatcher test:  from core.image_generator import generate_image → routes correctly
✅ Live Generation:  Prompt submitted successfully and image generated and downloaded!
```

**Generated Image from the Live Test:**

![A beautiful sunset over mountains with golden light, photorealistic, cinematic](file:///c:/AI/ai_video_factory_v1/output/test/geminiweb_test.png)

## Setup Required

```bash
pip install playwright
playwright install chromium
```

On first run, **let Playwright launch Chrome and do not interact with the window while it is generating.** If you need to log in initially, the automation will fail for that run, but your login will be saved in the `output/chrome_profile` directory, and subsequent automated runs will work perfectly.
