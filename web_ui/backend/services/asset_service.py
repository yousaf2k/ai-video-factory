"""
Asset library service.

Storage model (no metadata JSON): every asset is a single file named
"{id}-{Title}.{ext}" stored flat inside its category folder. The top-level
category folder determines the asset type (Images/Videos/Audio/Music via
config.ASSET_TYPES letter aliases), so renaming/moving an asset is a plain
file rename/move and the disk is always the source of truth.

Category addressing uses the type letter as the first segment, e.g.
"i/Characters/City" -> {library}/Images/Characters/City.
"""
import os
import re
import shutil
import uuid
import json
import hashlib
import logging
import threading
import subprocess
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

import config

logger = logging.getLogger(__name__)

# File extension -> type letter (config.ASSET_TYPES)
EXTENSION_TYPES = {
    ".png": "i", ".jpg": "i", ".jpeg": "i", ".webp": "i", ".gif": "i", ".bmp": "i",
    ".mp4": "v", ".webm": "v", ".mov": "v", ".avi": "v", ".mkv": "v",
    ".mp3": "a", ".wav": "a", ".ogg": "a", ".m4a": "a", ".flac": "a", ".aac": "a",
}

ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')
ASSET_ID_RE = re.compile(r"^[0-9a-f]{8}$")
MAX_SEARCH_RESULTS = 200
THUMB_WIDTH = 480

# Project media dirs -> asset type (None = decide by file extension)
PROJECT_MEDIA_DIRS = {
    "images": "image",
    "references": "image",
    "backgrounds": "image",
    "videos": "video",
    "narration": "audio",
    "audio": "audio",
    "editor": None,
}


def sanitize_title(name: str) -> str:
    """Windows-safe title: strip illegal chars/control chars and trailing dots/spaces."""
    cleaned = ILLEGAL_FILENAME_CHARS.sub(" ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or "Untitled"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug or "library"


def parse_asset_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    """Split "{id}-{Title}{ext}" into (id, title, ext); None if not in the scheme."""
    base, ext = os.path.splitext(filename)
    if "-" not in base:
        return None
    asset_id, _, title = base.partition("-")
    if not ASSET_ID_RE.match(asset_id) or not title:
        return None
    return asset_id, title, ext


def _find_child_dir(parent: str, name: str) -> Optional[str]:
    """Case-insensitive child directory lookup; returns the on-disk name or None."""
    try:
        entries = os.listdir(parent)
    except (FileNotFoundError, NotADirectoryError):
        return None
    for entry in entries:
        if entry.lower() == name.lower() and os.path.isdir(os.path.join(parent, entry)):
            return entry
    return None


_SHOT_FILE_RE = re.compile(r"^shot_(\d+)(?:_(\d+))?(?:_([a-z]+))?(?:_\d+)*$", re.IGNORECASE)


def pretty_media_title(media_dir: str, filename: str) -> str:
    """Human display name for project media, derived from naming patterns."""
    stem = os.path.splitext(filename)[0]
    m = _SHOT_FILE_RE.match(stem)
    if m:
        n, _counter, variant = int(m.group(1)), m.group(2), m.group(3)
        if media_dir == "images":
            base = f"Shot {n} image"
            if variant:
                return f"Shot {n} {variant.upper()} image" if variant.lower() in ("then", "now") else f"Shot {n} image ({variant})"
            return base
        if media_dir == "videos":
            return f"Shot {n} video"
    if stem.startswith("thumbnail"):
        return "Thumbnail"
    return stem.replace("_", " ").strip() or filename


def _list_dir_mtimes(directory: str) -> Dict[str, float]:
    """Filename -> file mtime for regular files directly inside directory."""
    result = {}
    try:
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            try:
                if os.path.isfile(full):
                    result[entry] = os.path.getmtime(full)
            except OSError:
                continue
    except (FileNotFoundError, NotADirectoryError):
        pass
    return result


def _sha256(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _find_duplicate(directory: str, src_path: str, exclude: Optional[str] = None) -> Optional[str]:
    """Find a managed file in directory with identical content to src_path.
    Size-gated: only same-size candidates are hashed."""
    try:
        src_size = os.path.getsize(src_path)
    except OSError:
        return None
    src_hash = None
    for filename in _safe_list_files(directory):
        if filename == exclude or parse_asset_filename(filename) is None:
            continue
        candidate = os.path.join(directory, filename)
        try:
            if os.path.getsize(candidate) != src_size:
                continue
        except OSError:
            continue
        if src_hash is None:
            src_hash = _sha256(src_path)
        try:
            if _sha256(candidate) == src_hash:
                return filename
        except OSError:
            continue
    return None


def _safe_list_files(directory: str) -> List[str]:
    try:
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    except (FileNotFoundError, NotADirectoryError):
        return []


class AssetService:
    """Scans and mutates the on-disk asset library. The disk is the source of
    truth; a per-directory cache keyed on the directory mtime just avoids
    re-listing folders on every request."""

    def __init__(self):
        self._lock = threading.RLock()
        self._dir_cache: Dict[str, Tuple[float, List[str]]] = {}

    # ------------------------------------------------------------------
    # Libraries
    # ------------------------------------------------------------------

    def list_libraries(self) -> List[Dict[str, Any]]:
        dirs = config.get_asset_library_dirs()
        libraries, used_slugs = [], set()
        for i, path in enumerate(dirs):
            slug, n = slugify(os.path.basename(path) or f"library-{i + 1}"), 2
            while slug in used_slugs:
                slug, n = f"{slug}-{n}", n + 1
            used_slugs.add(slug)
            libraries.append({
                "slug": slug,
                "name": os.path.basename(path) or f"Library {i + 1}",
                "path": path,
                "is_default": i == 0,
                "exists": os.path.isdir(path),
            })
        return libraries

    def _library_path(self, library_slug: Optional[str]) -> str:
        libraries = self.list_libraries()
        if not library_slug:
            return libraries[0]["path"]
        for lib in libraries:
            if lib["slug"] == library_slug:
                return lib["path"]
        raise FileNotFoundError(f"Unknown asset library: {library_slug}")

    @staticmethod
    def _ensure_type_folders(library_path: str) -> None:
        for info in config.ASSET_TYPES.values():
            os.makedirs(os.path.join(library_path, info["folder"]), exist_ok=True)

    # ------------------------------------------------------------------
    # Category resolution
    # ------------------------------------------------------------------

    def resolve_category(self, library_path: str, cat: str, create: bool = False) -> Tuple[str, str, List[str]]:
        """Resolve "i/Characters/City" -> (letter, absolute dir, on-disk segments).

        Segments are matched case-insensitively; missing segments are created
        only when create=True."""
        parts = [p for p in (cat or "").split("/") if p]
        if not parts:
            raise ValueError("Category must start with a type letter (i/v/a/m)")
        letter = parts[0].lower()
        if letter not in config.ASSET_TYPES:
            raise ValueError(f"Unknown asset type letter: {letter}")

        current = os.path.join(library_path, config.ASSET_TYPES[letter]["folder"])
        resolved: List[str] = []
        for segment in parts[1:]:
            name = sanitize_title(segment)
            existing = _find_child_dir(current, name)
            if existing:
                current = os.path.join(current, existing)
                resolved.append(existing)
            elif create:
                os.makedirs(current, exist_ok=True)
                os.makedirs(os.path.join(current, name), exist_ok=True)
                current = os.path.join(current, name)
                resolved.append(name)
            else:
                raise FileNotFoundError(f"Category not found: {cat}")
        return letter, current, resolved

    def _validate_cat(self, cat: str) -> str:
        parts = [p for p in (cat or "").split("/") if p]
        if not parts or parts[0].lower() not in config.ASSET_TYPES:
            raise ValueError(f"Category must start with a type letter (i/v/a/m): {cat}")
        return "/".join([parts[0].lower()] + parts[1:])

    # ------------------------------------------------------------------
    # Scanning / entries
    # ------------------------------------------------------------------

    def _list_files(self, directory: str) -> List[str]:
        try:
            mtime = os.path.getmtime(directory)
        except OSError:
            return []
        cached = self._dir_cache.get(directory)
        if cached and cached[0] == mtime:
            return cached[1]
        filenames = sorted(_list_dir_mtimes(directory).keys())
        self._dir_cache[directory] = (mtime, filenames)
        return filenames

    def _entry(self, letter: str, dir_abs: str, segments: List[str], filename: str) -> Optional[Dict[str, Any]]:
        parsed = parse_asset_filename(filename)
        if not parsed:
            return None
        asset_id, title, ext = parsed
        library_slug = None
        for lib in self.list_libraries():
            if dir_abs.lower().startswith(lib["path"].lower() + os.sep):
                library_slug = lib["slug"]
                break
        url = "/api/assets/" + "/".join([letter] + segments + [asset_id])
        entry = {
            "ref": f"{letter}/{asset_id}",
            "library": library_slug,
            "id": asset_id,
            "title": title,
            "type": config.ASSET_TYPES[letter]["type"],
            "letter": letter,
            "cat": "/".join([letter] + segments),
            "category": "/".join([config.ASSET_TYPES[letter]["folder"]] + segments),
            "filename": filename,
            "path": os.path.join(dir_abs, filename),
            "ext": ext.lstrip("."),
            "url": url,
            "thumb_url": url if letter == "i" else (url + "/thumb" if letter == "v" else None),
            "size_bytes": 0,
            "modified_at": None,
        }
        try:
            full = os.path.join(dir_abs, filename)
            st = os.stat(full)
            entry["size_bytes"] = st.st_size
            entry["modified_at"] = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
        except OSError:
            pass
        return entry

    def list_category(self, cat: str, library_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        cat = self._validate_cat(cat)
        library_path = self._library_path(library_slug)
        with self._lock:
            letter, dir_abs, segments = self.resolve_category(library_path, cat, create=False)
        entries = []
        for filename in self._list_files(dir_abs):
            entry = self._entry(letter, dir_abs, segments, filename)
            if entry:
                entries.append(entry)
        return entries

    def list_all(self, library_slug: Optional[str] = None, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Flat recursive listing of every managed asset (search / counts)."""
        library_path = self._library_path(library_slug)
        results: List[Dict[str, Any]] = []
        for letter, info in config.ASSET_TYPES.items():
            if type_filter and info["type"] != type_filter:
                continue
            root = os.path.join(library_path, info["folder"])
            for dir_abs, _dirs, files in os.walk(root):
                if os.path.basename(dir_abs) == ".thumbs":
                    continue
                rel = os.path.relpath(dir_abs, root)
                segments = [] if rel == "." else rel.split(os.sep)
                for filename in files:
                    entry = self._entry(letter, dir_abs, segments, filename)
                    if entry:
                        results.append(entry)
                        if len(results) >= MAX_SEARCH_RESULTS:
                            return results
        return results

    def get_tree(self, library_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        library_path = self._library_path(library_slug)
        with self._lock:
            self._ensure_type_folders(library_path)
        nodes = []
        for letter, info in config.ASSET_TYPES.items():
            root = os.path.join(library_path, info["folder"])

            def build(dir_abs: str, segments: List[str]) -> Dict[str, Any]:
                path = "/".join([letter] + segments)
                children = []
                try:
                    subdirs = sorted(
                        d for d in os.listdir(dir_abs)
                        if os.path.isdir(os.path.join(dir_abs, d)) and d != ".thumbs"
                    )
                except (FileNotFoundError, NotADirectoryError):
                    subdirs = []
                for d in subdirs:
                    children.append(build(os.path.join(dir_abs, d), segments + [d]))
                managed = sum(1 for f in self._list_files(dir_abs) if parse_asset_filename(f))
                return {"name": segments[-1] if segments else info["folder"],
                        "letter": letter, "path": path, "count": managed, "children": children}

            nodes.append(build(root, []))
        return nodes

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def _mint_asset_id(self, directory: str) -> str:
        taken = {f.split("-", 1)[0] for f in self._list_files(directory)}
        for _ in range(100):
            candidate = uuid.uuid4().hex[:8]
            if candidate not in taken:
                return candidate
        raise RuntimeError("Could not mint a unique asset id")

    def _unique_title(self, directory: str, asset_id: str, title: str, ignore_filename: Optional[str] = None) -> str:
        existing_titles = set()
        for f in self._list_files(directory):
            if f == ignore_filename:
                continue
            parsed = parse_asset_filename(f)
            if parsed:
                existing_titles.add(parsed[1].lower())
        if title.lower() not in existing_titles:
            return title
        n = 2
        while f"{title} ({n})".lower() in existing_titles:
            n += 1
        return f"{title} ({n})"

    def upload(self, files: List[Tuple[str, Any]], cat: str, library_slug: Optional[str] = None) -> Dict[str, Any]:
        """files: list of (original_filename, binary file object). Returns saved
        entries plus skipped files. Files whose extension doesn't match the
        target category's type are auto-routed to the mirrored category under
        the correct type folder."""
        cat = self._validate_cat(cat)
        library_path = self._library_path(library_slug)
        saved, skipped, rerouted = [], [], []
        with self._lock:
            self._ensure_type_folders(library_path)
            target_letter, target_dir, target_segments = self.resolve_category(library_path, cat, create=True)
            for original_name, fileobj in files:
                ext = os.path.splitext(original_name or "")[1].lower()
                letter = EXTENSION_TYPES.get(ext)
                if not letter:
                    skipped.append({"filename": original_name, "reason": f"Unsupported file type: {ext or 'none'}"})
                    continue
                dest_letter, dest_dir, dest_segments = target_letter, target_dir, target_segments
                if letter != target_letter:
                    mirrored = "/".join([letter] + target_segments)
                    dest_letter, dest_dir, dest_segments = self.resolve_category(library_path, mirrored, create=True)
                    rerouted.append({"filename": original_name, "to": mirrored})

                asset_id = self._mint_asset_id(dest_dir)
                title = self._unique_title(dest_dir, asset_id, sanitize_title(os.path.splitext(original_name)[0]))
                filename = f"{asset_id}-{title}{ext}"
                dest = os.path.join(dest_dir, filename)
                with open(dest, "wb") as out:
                    shutil.copyfileobj(fileobj, out)
                try:
                    os.utime(dest)
                except OSError:
                    pass

                # Content dedup: remove the copy if an identical managed file exists here
                duplicate = _find_duplicate(dest_dir, dest, exclude=filename)
                if duplicate:
                    os.remove(dest)
                    skipped.append({"filename": original_name, "reason": f"Duplicate of {duplicate}"})
                    continue

                entry = self._entry(dest_letter, dest_dir, dest_segments, filename)
                if entry:
                    saved.append(entry)
                self._dir_cache.pop(dest_dir, None)
        return {"saved": saved, "skipped": skipped, "rerouted": rerouted}

    def import_file(
        self, src_path: str, cat: str, title: Optional[str] = None,
        library_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Copy an existing media file (e.g. a project's shot image/video) into the
        library under `cat`. Same naming/dedup/reroute rules as upload."""
        cat = self._validate_cat(cat)
        ext = os.path.splitext(src_path)[1].lower()
        letter = EXTENSION_TYPES.get(ext)
        if not letter:
            raise ValueError(f"Unsupported file type: {ext or 'none'}")
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"Source file not found: {src_path}")
        library_path = self._library_path(library_slug)
        saved, skipped, rerouted = [], [], []
        with self._lock:
            self._ensure_type_folders(library_path)
            target_letter, target_dir, target_segments = self.resolve_category(library_path, cat, create=True)
            dest_letter, dest_dir, dest_segments = target_letter, target_dir, target_segments
            if letter != target_letter:
                mirrored = "/".join([letter] + target_segments)
                dest_letter, dest_dir, dest_segments = self.resolve_category(library_path, mirrored, create=True)
                rerouted.append({"filename": os.path.basename(src_path), "to": mirrored})

            duplicate = _find_duplicate(dest_dir, src_path)
            if duplicate:
                skipped.append({
                    "filename": os.path.basename(src_path),
                    "reason": f"Duplicate of {duplicate}",
                })
            else:
                asset_id = self._mint_asset_id(dest_dir)
                default_title = sanitize_title(os.path.splitext(os.path.basename(src_path))[0])
                final_title = self._unique_title(
                    dest_dir, asset_id, sanitize_title(title) if title else default_title
                )
                filename = f"{asset_id}-{final_title}{ext}"
                shutil.copyfile(src_path, os.path.join(dest_dir, filename))
                entry = self._entry(dest_letter, dest_dir, dest_segments, filename)
                if entry:
                    saved.append(entry)
                self._dir_cache.pop(dest_dir, None)
        return {"saved": saved, "skipped": skipped, "rerouted": rerouted}

    def _locate(self, ref: str) -> Tuple[str, str, str, str]:
        """ref -> (letter, library_path, dir_abs, filename). Library refs only:
        "{letter}/{id}" (default library) or "{lib_slug}/{letter}/{id}".
        Resolution scans the matching main-category subtree so refs survive
        category moves."""
        parts = [p for p in (ref or "").split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Invalid asset ref: {ref}")
        library_slug = None
        if len(parts) == 3:
            library_slug, letter, asset_id = parts
        else:
            letter, asset_id = parts[-2], parts[-1]
        if letter not in config.ASSET_TYPES or not ASSET_ID_RE.match(asset_id):
            raise ValueError(f"Invalid asset ref: {ref}")
        library_path = self._library_path(library_slug)
        root = os.path.join(library_path, config.ASSET_TYPES[letter]["folder"])
        for dir_abs, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d != ".thumbs"]
            for f in files:
                if f.startswith(f"{asset_id}-") and parse_asset_filename(f):
                    return letter, library_path, dir_abs, f
        raise FileNotFoundError(f"Asset not found: {ref}")

    def get_entry(self, ref: str, probe: bool = False) -> Dict[str, Any]:
        letter, library_path, dir_abs, filename = self._locate(ref)
        root = os.path.join(library_path, config.ASSET_TYPES[letter]["folder"])
        rel = os.path.relpath(dir_abs, root)
        segments = [] if rel == "." else rel.split(os.sep)
        entry = self._entry(letter, dir_abs, segments, filename)
        if not entry:
            raise FileNotFoundError(f"Asset not in scheme: {ref}")
        if probe:
            entry["media"] = probe_media(os.path.join(dir_abs, filename), entry["type"])
        return entry

    def rename(self, ref: str, title: str) -> Dict[str, Any]:
        new_title = sanitize_title(title)
        with self._lock:
            letter, library_path, dir_abs, filename = self._locate(ref)
            parsed = parse_asset_filename(filename)
            if not parsed:
                raise ValueError(f"File is not in the asset naming scheme: {filename}")
            asset_id, _, ext = parsed
            unique = self._unique_title(dir_abs, asset_id, new_title, ignore_filename=filename)
            new_name = f"{asset_id}-{unique}{ext}"
            if new_name != filename:
                os.rename(os.path.join(dir_abs, filename), os.path.join(dir_abs, new_name))
                self._dir_cache.pop(dir_abs, None)
            return self.get_entry(ref)

    def move(self, ref: str, to_cat: str) -> Dict[str, Any]:
        to_cat = self._validate_cat(to_cat)
        with self._lock:
            letter, library_path, dir_abs, filename = self._locate(ref)
            target_letter, target_dir, target_segments = self.resolve_category(library_path, to_cat, create=True)
            if target_letter != letter:
                raise ValueError("Moving between type folders (Images/Videos/...) is not supported")
            if os.path.abspath(target_dir) == os.path.abspath(dir_abs):
                return self.get_entry(ref)
            dest = os.path.join(target_dir, filename)
            if os.path.exists(dest):
                raise ValueError(f"A file named {filename} already exists in the target category")
            shutil.move(os.path.join(dir_abs, filename), dest)
            self._dir_cache.pop(dir_abs, None)
            self._dir_cache.pop(target_dir, None)
            return self.get_entry(ref)

    def delete(self, ref: str, force: bool = False) -> Dict[str, Any]:
        with self._lock:
            letter, library_path, dir_abs, filename = self._locate(ref)
            usage = self.find_usage(ref)
            if usage and not force:
                return {"deleted": False, "usage": usage}
            os.remove(os.path.join(dir_abs, filename))
            self._dir_cache.pop(dir_abs, None)
            thumb = self._thumb_path(library_path, letter, ref.rsplit("/", 1)[-1])
            if os.path.exists(thumb):
                os.remove(thumb)
            return {"deleted": True, "usage": usage}

    def find_usage(self, ref: str) -> List[str]:
        """Project ids whose shots.json reference this asset."""
        usage = []
        projects_dir = config.ABS_PROJECTS_DIR
        try:
            project_ids = os.listdir(projects_dir)
        except (FileNotFoundError, NotADirectoryError):
            return usage
        for project_id in project_ids:
            shots_file = os.path.join(projects_dir, project_id, "shots.json")
            if not os.path.isfile(shots_file):
                continue
            try:
                with open(shots_file, "r", encoding="utf-8") as f:
                    shots = json.load(f)
            except (OSError, ValueError):
                continue
            for shot in shots if isinstance(shots, list) else []:
                refs = shot.get("reference_asset_ids") or []
                if ref in refs:
                    usage.append(project_id)
                    break
        return usage

    def adopt(self, ref_path: str, library_slug: Optional[str] = None) -> Dict[str, Any]:
        """Rename a non-scheme file "{cat}/{filename}" into "{id}-{title}.ext"."""
        cat = self._validate_cat(ref_path.rsplit("/", 1)[0]) if "/" in ref_path else None
        filename = ref_path.rsplit("/", 1)[-1]
        if not cat:
            raise ValueError("ref_path must look like 'i/Characters/myphoto.png'")
        library_path = self._library_path(library_slug)
        with self._lock:
            letter, dir_abs, segments = self.resolve_category(library_path, cat, create=False)
            src = os.path.join(dir_abs, filename)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"File not found: {ref_path}")
            if parse_asset_filename(filename):
                raise ValueError(f"File already follows the naming scheme: {filename}")
            ext = os.path.splitext(filename)[1].lower()
            if ext not in EXTENSION_TYPES:
                raise ValueError(f"Unsupported file type: {ext}")
            asset_id = self._mint_asset_id(dir_abs)
            title = self._unique_title(dir_abs, asset_id, sanitize_title(os.path.splitext(filename)[0]))
            new_name = f"{asset_id}-{title}{ext}"
            os.rename(src, os.path.join(dir_abs, new_name))
            self._dir_cache.pop(dir_abs, None)
            entry = self._entry(letter, dir_abs, segments, new_name)
            return entry or {"filename": new_name}

    def create_category(self, cat: str, name: str, library_slug: Optional[str] = None) -> Dict[str, Any]:
        library_path = self._library_path(library_slug)
        with self._lock:
            letter, _dir, segments = self.resolve_category(library_path, cat, create=True)
            full_path = "/".join([letter] + segments + [sanitize_title(name)])
            self.resolve_category(library_path, full_path, create=True)
            return {"cat": full_path}

    def delete_category(self, cat: str, library_slug: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        cat = self._validate_cat(cat)
        if "/" not in cat:
            raise ValueError("Top-level type folders (Images/Videos/Audio/Music) cannot be deleted")
        library_path = self._library_path(library_slug)
        with self._lock:
            letter, dir_abs, segments = self.resolve_category(library_path, cat, create=False)
            stats = self._category_stats(dir_abs)
            if (stats["assets"] > 0 or stats["subcategories"] > 0) and not force:
                return {"deleted": False, "cat": cat, **stats}
            shutil.rmtree(dir_abs)
            self._invalidate_dir_cache(os.path.dirname(dir_abs))
            # Only the requested category is removed — parent categories stay
            # (empty or not), matching what the user selected for deletion.
            return {"deleted": True, "cat": cat, **stats}

    def _category_stats(self, dir_abs: str) -> Dict[str, int]:
        """Recursive counts: managed assets and subcategory folders below dir_abs."""
        assets, subcategories = 0, 0
        for root, dirs, files in os.walk(dir_abs):
            dirs[:] = [d for d in dirs if d != ".thumbs"]
            if root != dir_abs:
                subcategories += 1
            assets += sum(1 for f in files if parse_asset_filename(f))
        return {"assets": assets, "subcategories": subcategories}

    def _invalidate_dir_cache(self, path: str) -> None:
        """Drop scan caches for path and everything below it."""
        prefix = path.rstrip(os.sep) + os.sep
        for key in [k for k in self._dir_cache if k == path or k.startswith(prefix)]:
            self._dir_cache.pop(key, None)

    def _move_category_dir(self, library_path: str, cat: str, new_cat: str) -> Tuple[str, str]:
        """Move/rename a category folder on disk. Both paths are letter-addressed."""
        cat = self._validate_cat(cat)
        new_cat = self._validate_cat(new_cat)
        if cat.split("/", 1)[0] != new_cat.split("/", 1)[0]:
            raise ValueError("Categories can only move within the same type folder")
        if new_cat == cat or new_cat.startswith(cat + "/"):
            raise ValueError("Cannot move a category into itself or one of its subcategories")
        if "/" not in new_cat:
            raise ValueError("Top-level type folders cannot be moved or renamed")
        with self._lock:
            _, src_dir, _ = self.resolve_category(library_path, cat, create=False)
            new_parent_cat = new_cat.rsplit("/", 1)[0]
            _, dst_parent_dir, _ = self.resolve_category(library_path, new_parent_cat, create=True)
            new_name = sanitize_title(new_cat.rsplit("/", 1)[1])
            dst = os.path.join(dst_parent_dir, new_name)
            if os.path.exists(dst):
                raise ValueError(f"Category already exists: {new_cat}")
            src_parent = os.path.dirname(src_dir)
            shutil.move(src_dir, dst)
            self._invalidate_dir_cache(src_parent)
            self._invalidate_dir_cache(dst_parent_dir)
            return cat, new_cat

    def move_category(self, cat: str, to_parent: str, library_slug: Optional[str] = None) -> Dict[str, Any]:
        """Re-parent a category, e.g. i/Characters/City -> i/Environments/City."""
        if "/" not in cat:
            raise ValueError("Top-level type folders cannot be moved or renamed")
        library_path = self._library_path(library_slug)
        to_parent = self._validate_cat(to_parent)
        name = cat.rsplit("/", 1)[-1]
        old, new = self._move_category_dir(library_path, cat, f"{to_parent}/{name}")
        return {"cat": old, "new_cat": new}

    def rename_category(self, cat: str, name: str, library_slug: Optional[str] = None) -> Dict[str, Any]:
        """Rename a category in place."""
        if "/" not in cat:
            raise ValueError("Top-level type folders cannot be moved or renamed")
        library_path = self._library_path(library_slug)
        name = sanitize_title(name)
        parent = cat.rsplit("/", 1)[0]
        old, new = self._move_category_dir(library_path, cat, f"{parent}/{name}")
        return {"cat": old, "new_cat": new}

    # ------------------------------------------------------------------
    # Serving / thumbnails
    # ------------------------------------------------------------------

    def resolve_file(self, letter: str, category_path: str, asset_id: str, library_slug: Optional[str] = None) -> str:
        """The /api/assets/{letter}/{category}/{id} URL scheme -> absolute file path."""
        if letter not in config.ASSET_TYPES:
            raise ValueError(f"Unknown asset type letter: {letter}")
        library_path = self._library_path(library_slug)
        if category_path:
            letter_, dir_abs, _segments = self.resolve_category(library_path, f"{letter}/{category_path}", create=False)
        else:
            dir_abs = os.path.join(library_path, config.ASSET_TYPES[letter]["folder"])
        prefix = f"{asset_id}-"
        for filename in self._list_files(dir_abs):
            if filename.startswith(prefix) and parse_asset_filename(filename):
                return os.path.join(dir_abs, filename)
        raise FileNotFoundError(f"No asset with id {asset_id} in {letter}/{category_path}")

    def _thumb_path(self, library_path: str, letter: str, asset_id: str) -> str:
        return os.path.join(library_path, ".thumbs", f"{letter}_{asset_id}.jpg")

    def get_thumb(self, letter: str, category_path: str, asset_id: str, library_slug: Optional[str] = None) -> str:
        """Path to a thumbnail. Images: the original file. Videos: cached ffmpeg
        poster frame. Audio/music: raises FileNotFoundError (UI shows an icon)."""
        file_path = self.resolve_file(letter, category_path, asset_id, library_slug)
        if letter == "i":
            return file_path
        if letter != "v":
            raise FileNotFoundError("No thumbnail available for audio assets")
        library_path = self._library_path(library_slug)
        thumb = self._thumb_path(library_path, letter, asset_id)
        if os.path.isfile(thumb):
            return thumb
        os.makedirs(os.path.dirname(thumb), exist_ok=True)
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise FileNotFoundError("ffmpeg not available for thumbnail generation")
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-ss", "1", "-i", file_path,
               "-frames:v", "1", "-vf", f"scale={THUMB_WIDTH}:-2", thumb]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0 or not os.path.isfile(thumb):
            raise FileNotFoundError("Thumbnail generation failed")
        return thumb

    # ------------------------------------------------------------------
    # Ref resolution (library + project media) and project media listing
    # ------------------------------------------------------------------

    def resolve_ref(self, ref: str, probe: bool = False) -> Dict[str, Any]:
        """Resolve any ref shape into a normalized dict.

        Shapes: "i/{id}" / "{lib_slug}/i/{id}" (library) and
        "p/{project_id}/{media_dir}/{filename}" (other projects' media)."""
        ref = (ref or "").strip()
        if ref.startswith("p/"):
            return self._resolve_project_ref(ref, probe)
        return self._resolve_library_ref(ref, probe)

    def resolve_refs(self, refs: List[str], probe: bool = False) -> List[Dict[str, Any]]:
        return [self.resolve_ref(r, probe) for r in (refs or [])]

    def collect_shot_image_refs(self, shot: Dict[str, Any]) -> List[str]:
        """Absolute paths of a shot's attached image-type asset references that exist
        on disk — the list generation uses as reference images. Order follows the
        shot's reference_asset_ids (first = primary). Missing refs are skipped."""
        refs = shot.get("reference_asset_ids") or []
        if not refs:
            return []
        paths: List[str] = []
        for entry in self.resolve_refs(refs):
            if not entry.get("exists"):
                logger.warning(f"Skipping missing asset reference: {entry['ref']}")
                continue
            if entry.get("type") == "image" and entry.get("path"):
                paths.append(entry["path"])
        return paths

    def _missing_ref(self, ref: str, kind: str) -> Dict[str, Any]:
        first = ref.split("/")[1] if "/" in ref else ""
        letter = first if first in config.ASSET_TYPES else None
        type_by_dir = PROJECT_MEDIA_DIRS.get(first)
        return {
            "ref": ref, "kind": kind,
            "title": ref.rsplit("/", 1)[-1],
            "type": (config.ASSET_TYPES[letter]["type"] if letter else type_by_dir) or "image",
            "letter": letter,
            "url": "", "thumb_url": None, "source": None,
            "path": None,
            "exists": False, "size_bytes": 0, "modified_at": None,
        }

    def _resolve_library_ref(self, ref: str, probe: bool) -> Dict[str, Any]:
        try:
            entry = self.get_entry(ref, probe=probe)
        except (FileNotFoundError, ValueError):
            return self._missing_ref(ref, "library")
        entry["kind"] = "library"
        entry["exists"] = True
        entry["source"] = entry.get("library")
        return entry

    def _resolve_project_ref(self, ref: str, probe: bool) -> Dict[str, Any]:
        parts = ref.split("/", 3)
        if len(parts) < 4 or parts[2] not in PROJECT_MEDIA_DIRS:
            return self._missing_ref(ref, "project")
        _, project_id, media_dir, filename = parts
        full = os.path.join(config.ABS_PROJECTS_DIR, project_id, media_dir, filename)
        ext = os.path.splitext(filename)[1].lower()
        type_ = PROJECT_MEDIA_DIRS.get(media_dir) or EXTENSION_TYPES.get(ext)
        entry = {
            "ref": ref,
            "kind": "project",
            "title": pretty_media_title(media_dir, filename),
            "type": type_ or "image",
            "letter": None,
            "url": f"/api/projects/{project_id}/{media_dir}/{filename}",
            "thumb_url": f"/api/projects/{project_id}/{media_dir}/{filename}" if type_ == "image" else None,
            "source": project_id,
            "path": full,
            "exists": os.path.isfile(full),
            "size_bytes": 0,
            "modified_at": None,
        }
        if entry["exists"]:
            try:
                st = os.stat(full)
                entry["size_bytes"] = st.st_size
                entry["modified_at"] = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
            except OSError:
                pass
        if probe and entry["exists"]:
            entry["media"] = probe_media(full, entry["type"])
        return entry

    def list_project_media(self, project_id: str) -> List[Dict[str, Any]]:
        """All media files of one project as resolvable asset entries."""
        base = os.path.join(config.ABS_PROJECTS_DIR, project_id)
        if not os.path.isdir(base):
            raise FileNotFoundError(f"Project {project_id} not found")
        entries: List[Dict[str, Any]] = []
        for media_dir, default_type in PROJECT_MEDIA_DIRS.items():
            d = os.path.join(base, media_dir)
            if not os.path.isdir(d):
                continue
            for filename in sorted(os.listdir(d)):
                full = os.path.join(d, filename)
                if not os.path.isfile(full):
                    continue
                ext = os.path.splitext(filename)[1].lower()
                type_ = default_type or EXTENSION_TYPES.get(ext)
                if not type_:
                    continue
                try:
                    st = os.stat(full)
                    size, modified = st.st_size, datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
                except OSError:
                    size, modified = 0, None
                entries.append({
                    "ref": f"p/{project_id}/{media_dir}/{filename}",
                    "kind": "project",
                    "title": pretty_media_title(media_dir, filename),
                    "type": type_,
                    "letter": None,
                    "url": f"/api/projects/{project_id}/{media_dir}/{filename}",
                    "thumb_url": f"/api/projects/{project_id}/{media_dir}/{filename}" if type_ == "image" else None,
                    "source": project_id,
                    "path": full,
                    "exists": True,
                    "size_bytes": size,
                    "modified_at": modified,
                })
        return entries


def probe_media(path: str, asset_type: str) -> Dict[str, Any]:
    """Best-effort ffprobe: width/height (images/videos) and duration (audio/video)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", path],
            capture_output=True, timeout=30,
        )
        data = json.loads(result.stdout.decode("utf-8", errors="replace") or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}
    media: Dict[str, Any] = {}
    for stream in data.get("streams", []):
        if media.get("width") is None and stream.get("width"):
            media["width"] = stream["width"]
            media["height"] = stream["height"]
        if media.get("duration_sec") is None and stream.get("duration"):
            try:
                media["duration_sec"] = round(float(stream["duration"]), 2)
            except ValueError:
                pass
    if media.get("duration_sec") is None and data.get("format", {}).get("duration"):
        try:
            media["duration_sec"] = round(float(data["format"]["duration"]), 2)
        except ValueError:
            pass
    return media


_asset_service: Optional[AssetService] = None


def get_asset_service() -> AssetService:
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service
