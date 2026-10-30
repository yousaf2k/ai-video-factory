"""Reference-sheet generation for reference-to-video (r2v) projects.

Prompt builders + generation helpers for the three sheet kinds:

- character sheets: one 8-view identity sheet per character (4 full-body
  views + 4 face close-ups) -> project images/ dir, stored on
  characters[].character_reference_image_path
- background sheets: one environment reference per scene (no characters)
  -> project backgrounds/ dir, stored on scenes[].background_image_path
- prop sheets: one product-style reference per story prop
  -> project references/ dir, stored on props[].reference_image_path

The web backend keeps its queue-driven processors (which call the same
prompt builders); this module makes the same capability available to the
CLI pipeline. All generators skip entries that already have a sheet on
disk (idempotent) unless force=True.
"""
import glob
import logging
import os
import re

logger = logging.getLogger(__name__)

DEFAULT_PHOTOREAL_STYLE = (
    "The style must be photorealistic, life-like live action shot on a DSLR "
    "camera with 35mm film and muted color tones, "
)


def _default_style_suffix(base_desc: str) -> str:
    """Apply the photorealistic default only when no style was specified."""
    if "style" in (base_desc or "").lower() or "aesthetic" in (base_desc or "").lower():
        return ""
    return DEFAULT_PHOTOREAL_STYLE


def character_sheet_prompt(base_desc: str) -> str:
    """8-view character reference sheet (4 full-body + 4 face close-ups)."""
    return (
        f'create a professional character reference sheet for "{base_desc}, white background, detailed skin texture" '
        f'divide the sheet into four different vertical columns, each representing a different angle for a total of eight shots, '
        f'TOP ROW: Full-body views from head to toe facing four different directions (front,side,three-qarter view, back). '
        f'All subjects in the top row must be fully visible including feet, with no cropping at the ankles, knees, or head. '
        f'BOTTOM ROW: Four close-up shots of the face (including front and profile views) corresponding to each of the full-body shots above. '
        f'{_default_style_suffix(base_desc)}'
        f'do not add any text.'
    )


def expression_sheet_prompt(base_desc: str) -> str:
    """Facial-expression grid for a character (opt-in identity anchor)."""
    return (
        f'create a professional facial expression reference sheet for "{base_desc}, white background, detailed skin texture" '
        f'divide the sheet into six panels in a 3x2 grid, each panel an identical face showing one expression: '
        f'joy, anger, fear, sadness, surprise, determination. '
        f'The face, hairstyle and all identity features stay exactly the same in every panel. '
        f'{_default_style_suffix(base_desc)}'
        f'do not add any text.'
    )


def background_sheet_prompt(location: str, style: str = "") -> str:
    """Strict environment reference plate for a scene — establishing view,
    absolutely no characters."""
    return (
        f"Environment reference plate: {location}. "
        f"This must be a pure background/environment image for compositing — "
        f"an EMPTY scene with absolutely no characters, no people, no figures, "
        f"no silhouettes and no faces anywhere in the frame. "
        f"Show the whole space in a wide establishing frame: terrain, "
        f"architecture and key stationary props with their materials, under "
        f"natural lighting for the scene's time of day. "
        f"{style + ', ' if style else ''}"
        f"cinematic, high detail, empty environment, no people."
    )


def background_base_text(scene: dict) -> str:
    """Base text for a scene's background-sheet prompt. The story LLM writes
    the detailed background description into set_prompt (location stays a
    short setting name); location is the fallback for stories generated
    before set_prompt existed."""
    return ((scene.get('set_prompt') or scene.get('location') or '')).strip()


# The story LLM writes set_prompt as "A WIDE ESTABLISHING VIEW of ..."; the
# grid template assigns its own per-panel angles, so that camera wording is
# stripped before the description is injected.
_ESTABLISHING_VIEW_PREFIX_RE = re.compile(
    r"^a\s+wide\s+establishing\s+(?:view|shot|frame)\s+of\s+", re.IGNORECASE)

BACKGROUND_GRID_TEMPLATE = (
    "A 2x2 grid of four panels showing the same {background_prompt} background "
    "from four different camera angles. Empty scene, no people or characters. "
    "Consistent location, lighting, color palette, and art style across all four panels.\n"
    "\n"
    "Panel 1 (top left): [ANGLE 1, e.g. \"wide establishing shot, eye level\"]\n"
    "Panel 2 (top right): [ANGLE 2, e.g. \"low angle looking up, dramatic perspective\"]\n"
    "Panel 3 (bottom left): [ANGLE 3, e.g. \"high angle / bird's-eye view looking down\"]\n"
    "Panel 4 (bottom right): [ANGLE 4, e.g. \"close-up detail shot of foreground elements, shallow depth of field\"]\n"
    "\n"
    "Aspect ratio of each panel: {aspect_ratio}, thin even white borders between "
    "panels, equal-sized panels, no text, no labels, no watermarks."
)


def background_grid_prompt(background_prompt: str, aspect_ratio: str = "16:9") -> str:
    """Wrap a background description in the 2x2 multi-angle grid template.

    One location rendered from four camera angles in a single image, so
    reference-driven renders (r2v) see the space from every side. Strips the
    story directors' leading "A WIDE ESTABLISHING VIEW of" camera wording —
    Panel 1 of the template carries its own angles.
    """
    desc = _ESTABLISHING_VIEW_PREFIX_RE.sub("", (background_prompt or "").strip())
    desc = desc.rstrip(".") or "scene environment"
    return (BACKGROUND_GRID_TEMPLATE
            .replace("{background_prompt}", desc)
            .replace("{aspect_ratio}", (aspect_ratio or "16:9").strip()))


def apply_background_style(prompt: str, background_style: str) -> str:
    """Append a dropdown-selected style (styles.json) to the end of a
    background prompt. Empty/None selections leave the prompt untouched."""
    if not background_style or not background_style.strip():
        return prompt
    return f"{(prompt or '').rstrip()} {background_style.strip()}"


def prop_sheet_prompt(prop: dict, style: str = "") -> str:
    """Product-style reference for a recurring object (vehicle/weapon/etc.)."""
    desc = prop.get('image_prompt') or prop.get('description') or prop.get('name', 'object')
    return (
        f"cinematic product reference shot of {prop.get('name', 'the object')}: {desc}. "
        f"The object alone on a clean neutral background, three-quarter front view, "
        f"materials and wear details clearly visible, consistent single light source. "
        f"{style + ', ' if style else ''}"
        f"do not add any text."
    )


def _next_version(directory: str, prefix: str) -> int:
    pattern = os.path.join(directory, f"{prefix}_*.png")
    version_re = re.compile(rf"{prefix}_(\d+)\.png$")
    max_version = 0
    for filepath in glob.glob(pattern) if os.path.exists(directory) else []:
        match = version_re.match(os.path.basename(filepath))
        if match:
            max_version = max(max_version, int(match.group(1)))
    return max_version + 1


def _generate_sheet(project_manager, project_id, media_dir, prefix, prompt,
                    aspect_ratio=None, image_mode=None, workflow=None,
                    seed=None, gemini_mode=None, project_title=None):
    """Generate one sheet image; returns its absolute path.

    Returns None on failure (per-sheet failures are non-fatal — a missing
    sheet just means the subject falls back to prompt-text-only).
    """
    from core.image_generator import generate_image

    directory = os.path.join(project_manager.get_project_dir(project_id), media_dir)
    os.makedirs(directory, exist_ok=True)
    output_path = os.path.join(directory, f"{prefix}_{_next_version(directory, prefix):03d}.png")

    try:
        result = generate_image(
            prompt,
            output_path,
            aspect_ratio=aspect_ratio,
            mode=image_mode,
            seed=seed,
            workflow_name=workflow,
            project_title=project_title,
            gemini_mode=gemini_mode,
        )
        return result or None
    except Exception as exc:
        logger.error(f"Sheet generation failed for {prefix}: {exc}")
        return None


def ensure_character_sheets(project_manager, project_id, force=False,
                            expression=False, **gen_kwargs):
    """Generate missing character sheets; returns list of (index, relative_path) generated.

    When expression=True, generates expression grids into
    characters[].expression_reference_image_path instead (never automatic —
    caller opt-in).
    """
    story = project_manager.get_story(project_id) or {}
    style = story.get('style', '')
    generated = []
    for idx, char in enumerate(story.get('characters') or []):
        base_desc = char.get("image_prompt") or char.get("description") or char.get("name", "")
        if not base_desc:
            continue
        field = "expression_reference_image_path" if expression else "character_reference_image_path"
        existing = char.get(field)
        if existing and not force and _project_file_exists(project_manager, project_id, existing):
            continue
        prompt = expression_sheet_prompt(base_desc) if expression else character_sheet_prompt(base_desc)
        prefix = f"character_{idx:02d}" + ("_expr" if expression else "")
        path = _generate_sheet(project_manager, project_id, "images", prefix, prompt,
                               aspect_ratio=gen_kwargs.get('aspect_ratio') or "1:1", **{
                                   k: v for k, v in gen_kwargs.items() if k != 'aspect_ratio'})
        if not path:
            continue
        rel = project_manager.relativize_path(path)
        _set_story_field(project_manager, project_id,
                         lambda s, i=idx, f=field, r=rel: s['characters'][i].__setitem__(f, r)
                         if i < len(s.get('characters') or []) else None)
        generated.append((idx, rel))
    return generated


def ensure_background_sheets(project_manager, project_id, force=False, **gen_kwargs):
    """Generate missing per-scene background sheets; returns [(scene_id, rel_path)]."""
    story = project_manager.get_story(project_id) or {}
    generated = []
    for scene in story.get('scenes') or []:
        sid = scene.get('scene_id')
        location = scene.get('location')
        if sid is None or not location:
            continue
        existing = scene.get('background_image_path')
        if existing and not force and _project_file_exists(project_manager, project_id, existing):
            continue
        prompt = background_grid_prompt(
            background_base_text(scene), gen_kwargs.get('aspect_ratio') or "16:9")
        path = _generate_sheet(project_manager, project_id, "backgrounds",
                               f"background_{sid:03d}", prompt, **gen_kwargs)
        if not path:
            continue
        rel = project_manager.relativize_path(path)
        _set_story_field(project_manager, project_id, lambda s, s_id=sid, r=rel: _set_scene_bg(s, s_id, r))
        generated.append((sid, rel))
    return generated


def ensure_prop_sheets(project_manager, project_id, force=False, **gen_kwargs):
    """Generate missing per-prop reference sheets; returns [(prop_index, rel_path)]."""
    story = project_manager.get_story(project_id) or {}
    style = story.get('style', '')
    generated = []
    for idx, prop in enumerate(story.get('props') or []):
        name = prop.get('name')
        if not name:
            continue
        existing = prop.get('reference_image_path')
        if existing and not force and _project_file_exists(project_manager, project_id, existing):
            continue
        prompt = prop_sheet_prompt(prop, style)
        path = _generate_sheet(project_manager, project_id, "references",
                               f"prop_{idx:02d}", prompt, **gen_kwargs)
        if not path:
            continue
        rel = project_manager.relativize_path(path)
        _set_story_field(project_manager, project_id,
                         lambda s, i=idx, r=rel: s['props'][i].__setitem__('reference_image_path', r)
                         if i < len(s.get('props') or []) else None)
        generated.append((idx, rel))
    return generated


def _set_scene_bg(story, scene_id, rel_path):
    for scene in story.get('scenes') or []:
        if str(scene.get('scene_id')) == str(scene_id):
            scene['background_image_path'] = rel_path
            scene['background_generated'] = True
            scene['background_is_generated'] = True
            return


def _set_story_field(project_manager, project_id, modifier):
    project_manager.update_story_safely(project_id, modifier)


def _project_file_exists(project_manager, project_id, rel_path):
    p = (rel_path or '').replace('\\', '/')
    marker = f"output/projects/{project_id}/"
    if p.startswith(marker):
        p = p[len(marker):]
    abs_path = os.path.join(project_manager.get_project_dir(project_id), p)
    return os.path.exists(abs_path)
