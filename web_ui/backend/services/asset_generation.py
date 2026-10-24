"""Background generation straight into the Asset Library.

Starts an image / video / sound generation from a prompt (and, for video and
sound, a source asset reference), writing the result into a library category
as a normal "{id}-{Title}.{ext}" asset.

Images and videos run through the shared QueueService (same queue as project
shots — visible in the Queue UI, per-engine concurrency limits, persistence);
this service keeps an in-memory registry that mirrors each run's status for
the asset API and grid placeholders. Sound runs as a direct asyncio task.
Status is polled via the API; completed jobs resolve to a normal library ref.

Reuse map (same code paths as project shot generation):
    image -> core.image_generator.generate_image        (Gemini/ComfyUI/GeminiWeb/Flow)
    video -> core.prompt_compiler + core.comfy_client   (ComfyUI i2v workflows)
             core.geminiweb_video_generator             (geminiweb mode)
    audio -> SOUNDFX_WORKFLOWS (MMAudio video-to-sound) + ffmpeg audio extract
"""
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import config
from web_ui.backend.models.queue import GenerationType, QueueItem
from web_ui.backend.services.asset_service import get_asset_service, parse_asset_filename
from web_ui.backend.services.queue_service import get_queue_service

logger = logging.getLogger(__name__)

KIND_LETTER = {"image": "i", "video": "v", "audio": "a"}
KIND_EXT = {"image": ".png", "video": ".mp4", "audio": ".mp3"}
ACTIVE_STATUSES = ("queued", "running")
QUEUE_PROJECT_ID = "__assets__"  # synthetic project grouping asset runs in the Queue UI


def _default_title(prompt: str) -> str:
    """First few words of the prompt as a fallback asset title."""
    words = (prompt or "").strip().split()
    return " ".join(words[:5]) if words else "Generated"


def asset_folder_name(letter: str, segments: List[str]) -> str:
    """Flow/GeminiWeb project identity for asset generations, formatted
    "Assets <TypeFolder> <CategorySubfolders>", e.g.
    "Assets Images Characters City" — every asset category gets its own
    browser workspace. Internal whitespace is collapsed to single spaces."""
    parts = ["Assets", config.ASSET_TYPES[letter]["folder"]] + segments
    return re.sub(r"\s+", " ", " ".join(parts))


def _display_cat(cat: str) -> str:
    """'i/Characters' -> 'Images/Characters' — type letters are internal
    aliases; user-facing text uses the folder names."""
    parts = [p for p in cat.split("/") if p]
    if not parts or parts[0] not in config.ASSET_TYPES:
        return cat
    return "/".join([config.ASSET_TYPES[parts[0]]["folder"]] + parts[1:])


def _require_ref_path(ref: str, expect_type: str) -> str:
    entry = get_asset_service().resolve_ref(ref)
    if not entry.get("exists") or not entry.get("path"):
        raise RuntimeError(f"Source asset not found: {ref}")
    if entry.get("type") != expect_type:
        raise RuntimeError(f"Source asset must be a {expect_type}: {ref}")
    return entry["path"]


# ----------------------------------------------------------------------
# Runners (module-level so the queue processor can execute them)
# ----------------------------------------------------------------------

async def run_asset_image(
    gen: Dict[str, Any],
    on_progress: Optional[Callable[[int], None]] = None,
    on_prompt_id: Optional[Callable[[str], None]] = None,
) -> None:
    """Generate one image into gen['path']. Raises on failure."""
    from core.image_generator import generate_image

    reference_paths = []
    if gen.get("reference_refs"):
        for entry in get_asset_service().resolve_refs(gen["reference_refs"] or []):
            if entry.get("type") == "image" and entry.get("path"):
                reference_paths.append(entry["path"])

    def step_progress(current, total):
        if total and on_progress:
            on_progress(min(99, int(current / total * 100)))

    result = await asyncio.to_thread(
        generate_image,
        prompt=gen["prompt"],
        output_path=gen["path"],
        aspect_ratio=gen.get("aspect_ratio") or None,
        seed=gen.get("seed"),
        mode=gen.get("mode") or None,
        workflow_name=gen.get("workflow"),
        step_progress_callback=step_progress,
        reference_images=reference_paths or None,
        gemini_mode=gen.get("gemini_mode") or None,
        # Browser modes (Flow/GeminiWeb) use the category folder as the
        # project/chat identity — each asset folder gets its own workspace.
        project_title=gen.get("folder") or None,
        prompt_id_callback=on_prompt_id,
    )
    if not result or not os.path.isfile(gen["path"]):
        raise RuntimeError("Image generation failed — no output produced")


async def run_asset_video(
    gen: Dict[str, Any],
    on_progress: Optional[Callable[[int], None]] = None,
) -> None:
    """Generate one video into gen['path'] from gen['image_ref']."""
    image_path = _require_ref_path(gen["image_ref"], "image")
    mode = getattr(config, "VIDEO_GENERATION_MODE", "comfyui")

    # r2v-style workflows take extra reference images; other workflows ignore them
    reference_paths = []
    if gen.get("reference_refs"):
        for entry in get_asset_service().resolve_refs(gen["reference_refs"]):
            if entry.get("type") == "image" and entry.get("path"):
                reference_paths.append(entry["path"])

    def step_progress(current, total):
        if total and on_progress:
            on_progress(min(99, int(current / total * 100)))

    if mode == "geminiweb":
        from core.geminiweb_video_generator import generate_video_geminiweb

        result = await asyncio.to_thread(
            generate_video_geminiweb,
            image_path=image_path,
            motion_prompt=gen["prompt"],
            output_path=gen["path"],
        )
        if not result:
            raise RuntimeError("Gemini Web video generation failed")
        return

    from core.prompt_compiler import load_workflow, compile_workflow
    from core.comfy_client import submit, async_wait_for_prompt_completion_with_progress, get_output_file_path

    wf_name = gen.get("workflow") or getattr(config, "VIDEO_WORKFLOW", "wan22")
    video_workflows = getattr(config, "VIDEO_WORKFLOWS", {})
    workflow_config = video_workflows.get(wf_name)
    workflow_path = workflow_config.get("workflow_path") if workflow_config else wf_name

    shot_length = gen.get("duration") or getattr(config, "DEFAULT_SHOT_LENGTH", 5)
    shot = {"index": 1, "image_path": image_path, "motion_prompt": gen["prompt"], "duration": shot_length}

    template = await asyncio.to_thread(
        load_workflow,
        workflow_path,
        video_length_seconds=shot_length,
        aspect_ratio=gen.get("aspect_ratio") or "16:9",
        workflow_config=workflow_config,
    )
    wf = compile_workflow(
        template, shot,
        video_length_seconds=shot_length,
        workflow_config=workflow_config,
        reference_images=reference_paths or None,
    )

    result = submit(wf)
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return a prompt_id")
    logger.info(f"Asset video generation submitted: {gen['id']} prompt_id={prompt_id}")

    wait = await async_wait_for_prompt_completion_with_progress(
        prompt_id, progress_callback=step_progress,
        timeout=getattr(config, "VIDEO_RENDER_TIMEOUT", 1800),
    )
    if not wait.get("success"):
        raise RuntimeError(f"Video render failed: {wait.get('error')}")
    videos = [o for o in wait.get("outputs", []) if o.get("type") == "video"]
    if not videos:
        raise RuntimeError("No video output produced")
    info = videos[0]
    source = get_output_file_path(
        info.get("filename") if isinstance(info, dict) else info,
        None,
        subfolder=info.get("subfolder") if isinstance(info, dict) else None,
    )
    if not isinstance(source, str) or not os.path.isfile(source):
        raise RuntimeError(f"Video output file not found: {source}")
    shutil.copy2(source, gen["path"])


class AssetGenerationService:
    """In-memory registry of library generation jobs. Images/videos are
    executed by the shared queue processor; this registry mirrors their
    status for the asset API and grid placeholders. Sound runs directly."""

    def __init__(self):
        self._lock = threading.Lock()
        self._gens: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, request: Any) -> Dict[str, Any]:
        """Validate the request, reserve the target asset path and schedule
        the generation (queue for image/video, task for sound). Returns the
        initial status dict."""
        kind = (getattr(request, "kind", "") or "").strip().lower()
        if kind not in KIND_LETTER:
            raise ValueError(f"kind must be one of: {', '.join(KIND_LETTER)}")
        prompt = (getattr(request, "prompt", "") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")

        letter = KIND_LETTER[kind]
        cat = (getattr(request, "cat", "") or letter).strip("/")
        cat_parts = [p for p in cat.split("/") if p]
        if cat_parts[0].lower() != letter:
            folder = config.ASSET_TYPES[letter]["folder"]
            raise ValueError(f"A {kind} asset must target the {folder} category (got {cat})")

        kind_reqs = {
            "video": ("image_ref", "a source image (i2v workflows animate a first frame)"),
            "audio": ("video_ref", "a source video (sound FX workflows generate audio from video)"),
        }
        if kind in kind_reqs:
            field, why = kind_reqs[kind]
            if not getattr(request, field, None):
                raise ValueError(f"{field} is required for {kind} generation ({why})")

        service = get_asset_service()
        ext = KIND_EXT[kind]
        title = getattr(request, "title", None) or _default_title(prompt)
        letter, dir_abs, segments, filename, final_path = service.prepare_target(
            cat, title, ext, getattr(request, "library", None)
        )
        parsed = parse_asset_filename(filename) or ("", title, ext)
        ref = f"{letter}/{parsed[0]}"

        # GeminiWeb picker selection, transported as "<model>|<thinking>"
        # (same convention as project shot generation).
        gemini_model = getattr(request, "gemini_model", None)
        gemini_thinking = getattr(request, "gemini_thinking", None)
        gemini_mode = (
            f"{gemini_model or ''}|{gemini_thinking or ''}"
            if (gemini_model or gemini_thinking)
            else None
        )

        gen: Dict[str, Any] = {
            "id": uuid.uuid4().hex[:12],
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "message": None,
            "prompt": prompt,
            "cat": "/".join([letter] + segments),
            "folder": asset_folder_name(letter, segments),
            "title": parsed[1],
            "library": getattr(request, "library", None),
            "mode": getattr(request, "mode", None) or None,
            "gemini_mode": gemini_mode,
            "workflow": getattr(request, "workflow", None) or None,
            "aspect_ratio": getattr(request, "aspect_ratio", None) or None,
            "seed": getattr(request, "seed", None),
            "duration": getattr(request, "duration", None),
            "image_ref": getattr(request, "image_ref", None),
            "video_ref": getattr(request, "video_ref", None),
            "reference_refs": list(getattr(request, "reference_refs", None) or []),
            "queue_item_id": None,
            "path": final_path,
            "ref": ref,
            "url": None,
            "thumb_url": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "started_at": None,
            "finished_at": None,
        }

        # Register first — the queue processor may pick the item up
        # immediately and needs the registry entry for status mirroring.
        with self._lock:
            self._gens[gen["id"]] = gen

        if kind in ("image", "video"):
            self._enqueue(gen)
        else:
            task = asyncio.create_task(self._run_audio_task(gen))
            self._tasks[gen["id"]] = task

        logger.info(f"Asset generation started: {gen['id']} kind={kind} cat={gen['cat']}")
        return self._public(gen)

    def _enqueue(self, gen: Dict[str, Any]) -> None:
        """Submit an image/video run to the shared QueueService."""
        item = QueueItem(
            item_id=f"queue_{uuid.uuid4().hex[:8]}",
            project_id=QUEUE_PROJECT_ID,
            generation_type=GenerationType.ASSET_IMAGE if gen["kind"] == "image" else GenerationType.ASSET_VIDEO,
            prompt_override=gen["prompt"],
            seed=gen.get("seed"),
            image_mode=gen.get("mode") if gen["kind"] == "image" else None,
            image_workflow=gen.get("workflow") if gen["kind"] == "image" else None,
            video_mode=getattr(config, "VIDEO_GENERATION_MODE", "comfyui"),
            video_workflow=gen.get("workflow") if gen["kind"] == "video" else None,
            aspect_ratio=gen.get("aspect_ratio"),
            gemini_mode=gen.get("gemini_mode"),
            output_path=gen["path"],
            asset_gen_id=gen["id"],
            asset_folder=gen.get("folder"),
            source_ref=gen.get("image_ref") or gen.get("video_ref"),
            reference_refs=gen.get("reference_refs") or None,
            duration_sec=gen.get("duration"),
            project_title="Asset Library",
            scene_name=_display_cat(gen["cat"]),
        )
        gen["queue_item_id"] = item.item_id
        get_queue_service().add_items([item])

    def get(self, gen_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            gen = self._gens.get(gen_id)
            return self._public(gen) if gen else None

    def get_internal(self, gen_id: str) -> Optional[Dict[str, Any]]:
        """Raw registry entry including internal fields (path). For the queue
        processor only — never return this through the API."""
        with self._lock:
            gen = self._gens.get(gen_id)
            return dict(gen) if gen else None

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            gens = sorted(self._gens.values(), key=lambda g: g["created_at"], reverse=True)
            return [self._public(g) for g in gens[:50]]

    def cancel(self, gen_id: str) -> Dict[str, Any]:
        with self._lock:
            gen = self._gens.get(gen_id)
            if not gen:
                raise FileNotFoundError(f"Generation not found: {gen_id}")
            if gen["status"] not in ACTIVE_STATUSES:
                return self._public(gen)
            queue_item_id = gen.get("queue_item_id")
            task = self._tasks.get(gen_id)
        if queue_item_id:
            try:
                get_queue_service().mark_cancelled(queue_item_id)
            except Exception as e:
                logger.warning(f"Failed to cancel queue item {queue_item_id}: {e}")
        elif task and not task.done():
            task.cancel()
        self.finalize_cancelled(gen_id)
        return self.get(gen_id) or {}

    # ------------------------------------------------------------------
    # Queue-side status mirroring (called by the queue processor)
    # ------------------------------------------------------------------

    def mark_running(self, gen_id: str) -> None:
        self._update(gen_id, status="running", started_at=datetime.utcnow().isoformat(timespec="seconds") + "Z")

    def set_progress(self, gen_id: str, progress: int) -> None:
        self._update(gen_id, progress=max(0, min(99, int(progress))))

    def finalize_success(self, gen_id: str) -> None:
        gen = self._gens.get(gen_id)
        if not gen or gen["status"] not in ACTIVE_STATUSES:
            return
        service = get_asset_service()
        service._invalidate_dir_cache(os.path.dirname(gen["path"]))
        try:
            entry = service.get_entry(gen["ref"])
        except Exception:
            entry = {}
        self._update(
            gen_id,
            status="completed",
            progress=100,
            message=None,
            url=entry.get("url"),
            thumb_url=entry.get("thumb_url"),
            finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )
        logger.info(f"Asset generation completed: {gen_id} -> {gen['ref']}")

    def finalize_failure(self, gen_id: str, error: str) -> None:
        gen = self._gens.get(gen_id)
        if not gen or gen["status"] not in ACTIVE_STATUSES:
            return
        self._cleanup(gen)
        get_asset_service()._invalidate_dir_cache(os.path.dirname(gen["path"]))
        self._update(
            gen_id,
            status="failed",
            error=str(error),
            finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )

    def finalize_cancelled(self, gen_id: str) -> None:
        gen = self._gens.get(gen_id)
        if not gen:
            return
        self._cleanup(gen)
        self._update(
            gen_id,
            status="cancelled",
            finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )

    # ------------------------------------------------------------------
    # Sound runner (direct task; sounds don't go through the queue)
    # ------------------------------------------------------------------

    async def _run_audio_task(self, gen: Dict[str, Any]) -> None:
        self.mark_running(gen["id"])
        try:
            await self._run_audio(gen)
            self.finalize_success(gen["id"])
        except asyncio.CancelledError:
            self.finalize_cancelled(gen["id"])
            raise
        except Exception as e:
            logger.error(f"Asset generation {gen['id']} failed: {e}", exc_info=True)
            self.finalize_failure(gen["id"], str(e))

    async def _run_audio(self, gen: Dict[str, Any]) -> None:
        import requests as http_requests
        from core.comfy_client import submit, async_wait_for_prompt_completion_with_progress, get_output_file_path

        video_path = _require_ref_path(gen["video_ref"], "video")

        comfy_url = getattr(config, "COMFY_URL", "http://127.0.0.1:8188")

        def _upload() -> str:
            with open(video_path, "rb") as f:
                resp = http_requests.post(
                    f"{comfy_url}/upload/image",
                    files={"image": (os.path.basename(video_path), f, "video/mp4")},
                    data={"subfolder": "", "type": "input"},
                    timeout=600,
                )
            resp.raise_for_status()
            return resp.json().get("name", os.path.basename(video_path))

        uploaded = await asyncio.to_thread(_upload)

        wf_key = gen.get("workflow") or getattr(config, "SOUNDFX_WORKFLOW", "mmaudio")
        all_wfs = getattr(config, "SOUNDFX_WORKFLOWS", {})
        if wf_key not in all_wfs and "default" in all_wfs:
            wf_key = "default"
        if wf_key not in all_wfs:
            raise RuntimeError("No sound FX workflow discovered (check workflow/soundfx and ComfyUI)")
        wf_info = all_wfs[wf_key]
        with open(wf_info["workflow_path"], "r", encoding="utf-8") as f:
            wf = json.load(f)

        if wf_info.get("load_video_node_id") and wf_info["load_video_node_id"] in wf:
            wf[wf_info["load_video_node_id"]]["inputs"]["video"] = uploaded
        if wf_info.get("sampler_node_id") and wf_info["sampler_node_id"] in wf:
            wf[wf_info["sampler_node_id"]]["inputs"]["prompt"] = gen["prompt"]
        if wf_info.get("combine_node_id") and wf_info["combine_node_id"] in wf:
            wf[wf_info["combine_node_id"]]["inputs"]["filename_prefix"] = f"assetgen_{gen['id']}"

        def on_progress(current, total):
            if total:
                self.set_progress(gen["id"], min(99, int(current / total * 100)))

        result = submit(wf)
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")

        wait = await async_wait_for_prompt_completion_with_progress(
            prompt_id, progress_callback=on_progress,
            timeout=getattr(config, "VIDEO_RENDER_TIMEOUT", 1800),
        )
        if not wait.get("success"):
            raise RuntimeError(f"Sound generation failed: {wait.get('error')}")

        outputs = wait.get("outputs", [])
        media = [o for o in outputs if o.get("type") in ("audio", "video")]
        if not media:
            raise RuntimeError("No audio output produced")
        info = media[0]
        source = get_output_file_path(
            info.get("filename") if isinstance(info, dict) else info,
            None,
            subfolder=info.get("subfolder") if isinstance(info, dict) else None,
        )
        if not isinstance(source, str) or not os.path.isfile(source):
            raise RuntimeError(f"Sound output file not found: {source}")

        ext = os.path.splitext(source)[1].lower()
        if ext == ".mp3":
            shutil.copy2(source, gen["path"])
            return

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required to extract audio from the generated file")
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", source, "-vn",
               "-acodec", "libmp3lame", "-q:a", "2", gen["path"]]
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=600)
        if proc.returncode != 0 or not os.path.isfile(gen["path"]):
            raise RuntimeError("Failed to extract audio from the generated output")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update(self, gen_id: str, **fields: Any) -> None:
        with self._lock:
            gen = self._gens.get(gen_id)
            if gen:
                gen.update(fields)

    def _cleanup(self, gen: Dict[str, Any]) -> None:
        """Remove a partial output file so a failed job doesn't leave junk."""
        try:
            if gen.get("path") and os.path.isfile(gen["path"]):
                os.remove(gen["path"])
        except OSError:
            pass

    @staticmethod
    def _public(gen: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in gen.items() if k not in ("path",)}


_asset_generation: Optional[AssetGenerationService] = None


def get_asset_generation_service() -> AssetGenerationService:
    global _asset_generation
    if _asset_generation is None:
        _asset_generation = AssetGenerationService()
    return _asset_generation
