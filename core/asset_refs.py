"""Resolve asset references to absolute file paths (core-side).

Shared by the CLI pipeline; the web backend has its own richer resolver in
web_ui/backend/services/asset_service.py (URL serving, usage tracking), but
both understand the same two reference shapes:

- project refs: "p/{project_id}/{media_dir}/{filename}"
- library refs: "i/{8-char-id}" (optionally prefixed "{lib_slug}/i/{id}",
  where the slug maps to a configured ASSET_LIBRARY_DIRS entry by name)

Library assets are files named "{id}-{Title}.{ext}" — the filename is the
metadata, so resolution searches the type folder for the id prefix.
"""
import logging
import os

import config

logger = logging.getLogger(__name__)

# ref prefix -> ASSET_TYPES letter
_REF_TYPE_LETTERS = {
    "image": "i",
    "images": "i",
    "i": "i",
    "video": "v",
    "videos": "v",
    "v": "v",
    "audio": "a",
    "a": "a",
    "music": "m",
    "m": "m",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def resolve_project_ref(ref: str):
    """'p/{pid}/{media_dir}/{filename}' -> absolute path (or None)."""
    parts = (ref or "").strip().replace("\\", "/").split("/")
    if len(parts) != 4 or parts[0] != "p":
        return None
    _, project_id, media_dir, filename = parts
    if not project_id or not filename or media_dir not in ("images", "references", "backgrounds", "audio", "videos"):
        return None
    path = os.path.join(config.ABS_PROJECTS_DIR, project_id, media_dir, filename)
    return path if os.path.exists(path) else None


def resolve_library_ref(ref: str):
    """'i/{id}' or '{lib_slug}/i/{id}' -> absolute path (or None).

    Searches the matching type folder of every configured library root for a
    file named "{id}-...". The optional slug selects a library root first
    (matched against the root directory's name).
    """
    parts = (ref or "").strip().replace("\\", "/").split("/")
    if len(parts) == 2:
        slug, letter, asset_id = None, parts[0], parts[1]
    elif len(parts) == 3:
        slug, letter, asset_id = parts
    else:
        return None
    if letter not in _REF_TYPE_LETTERS.values() and letter not in _REF_TYPE_LETTERS:
        return None
    letter = _REF_TYPE_LETTERS.get(letter, letter)
    if not asset_id:
        return None

    type_folder = config.ASSET_TYPES.get(letter, {}).get("folder")
    if not type_folder:
        return None

    roots = config.get_asset_library_dirs()
    if slug:
        roots = [r for r in roots if os.path.basename(r.rstrip("/\\")).lower() == slug.lower()] or roots

    for root in roots:
        folder = os.path.join(root, type_folder)
        if not os.path.isdir(folder):
            continue
        prefix = f"{asset_id}-"
        for dirpath, _dirnames, filenames in os.walk(folder):
            for fn in filenames:
                if fn.startswith(prefix):
                    return os.path.join(dirpath, fn)
    return None


def resolve_ref(ref: str):
    """Any asset ref -> absolute path (or None)."""
    ref = (ref or "").strip()
    if not ref:
        return None
    if ref.startswith("p/"):
        return resolve_project_ref(ref)
    if "/" in ref:
        return resolve_library_ref(ref)
    return None


def resolve_refs_to_paths(refs, existing_only=True, extensions=None):
    """Ordered list of refs -> ordered list of existing absolute paths.

    Refs that don't resolve (missing file, unknown shape) are dropped with a
    debug log; order is preserved (order = reference priority).
    """
    exts = set(extensions) if extensions else None
    paths = []
    for ref in refs or []:
        path = resolve_ref(ref) if isinstance(ref, str) else None
        if not path:
            logger.debug(f"Asset ref did not resolve: {ref!r}")
            continue
        if exts is not None and os.path.splitext(path)[1].lower() not in exts:
            logger.debug(f"Asset ref filtered by extension: {ref!r} -> {path}")
            continue
        paths.append(path)
    return paths


def resolve_shot_video_reference_paths(shot, max_refs=None):
    """Shot -> ordered list of existing reference-image file paths.

    Uses the shot's reference_asset_ids (which sync_shot_video_refs filled in
    priority order: characters -> background -> props), filtered to image
    files. Non-image refs (audio/video) are excluded here — they attach
    through separate video_ref_asset_ids handling.
    """
    refs = shot.get('reference_asset_ids') or []
    paths = resolve_refs_to_paths(refs, extensions=IMAGE_EXTENSIONS)
    if max_refs is not None:
        paths = paths[:max_refs]
    return paths
