"""Background generation straight into the Asset Library.

Starts an image / video / sound generation from a prompt (and, for video and
sound, a source asset reference), writing the result into a library category
as a normal "{id}-{Title}.{ext}" asset. Generations run as asyncio tasks and
are tracked in memory; the API exposes start + status polling.

Reuse map (same code paths as project shot generation):
    image -> core.image_generator.generate_image        (Gemini/ComfyUI/GeminiWeb)
    video -> core.prompt_compiler + core.comfy_client   (ComfyUI i2v workflows)
             core.geminiweb_video_generator             (geminiweb mode)
    audio -> SOUNDFX_WORKFLOWS (MMAudio video-to-sound) + ffmpeg audio extract
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import config
from web_ui.backend.services.asset_service import get_asset_service, parse_asset_filename

logger = logging.getLogger(__name__)

KIND_LETTER = {"image": "i", "video": "v", "audio": "a"}
KIND_EXT = {"image": ".png", "video": ".mp4", "audio": ".mp3"}
ACTIVE_STATUSES = ("queued", "running")


def _default_title(prompt: str) -> str:
    """First few words of the prompt as a fallback asset title."""
    words = (prompt or "").strip().split()
    return " ".join(words[:5]) if words else "Generated"


class AssetGenerationService:
    """In-memory registry of library generation jobs. Status is polled via the
    API; completed jobs resolve to a normal library asset ref."""

    def __init__(self):
        self._lock = threading.Lock()
        self._gens: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, request: Any) -> Dict[str, Any]:
        """Validate the request, reserve the target asset path and schedule the
        generation task. Returns the initial status dict."""
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

        gen: Dict[str, Any] = {
            "id": uuid.uuid4().hex[:12],
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "message": None,
            "prompt": prompt,
            "cat": "/".join([letter] + segments),
            "title": parsed[1],
            "library": getattr(request, "library", None),
            "workflow": getattr(request, "workflow", None) or None,
            "aspect_ratio": getattr(request, "aspect_ratio", None) or None,
            "seed": getattr(request, "seed", None),
            "duration": getattr(request, "duration", None),
            "image_ref": getattr(request, "image_ref", None),
            "video_ref": getattr(request, "video_ref", None),
            "reference_refs": list(getattr(request, "reference_refs", None) or []),
            "path": final_path,
            "ref": ref,
            "url": None,
            "thumb_url": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "started_at": None,
            "finished_at": None,
        }
        with self._lock:
            self._gens[gen["id"]] = gen
        task = asyncio.create_task(self._run(gen))
        self._tasks[gen["id"]] = task
        logger.info(f"Asset generation started: {gen['id']} kind={kind} cat={gen['cat']}")
        return self._public(gen)

    def get(self, gen_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            gen = self._gens.get(gen_id)
            return self._public(gen) if gen else None

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
            task = self._tasks.get(gen_id)
        if task and not task.done():
            task.cancel()
        gen["status"] = "cancelled"
        gen["finished_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return self._public(gen)

    # ------------------------------------------------------------------
    # Runners
    # ------------------------------------------------------------------

    async def _run(self, gen: Dict[str, Any]) -> None:
        self._set(gen, status="running", started_at=datetime.utcnow().isoformat(timespec="seconds") + "Z")
        runners = {"image": self._run_image, "video": self._run_video, "audio": self._run_audio}
        service = get_asset_service()
        try:
            await runners[gen["kind"]](gen)
            # Directory mtimes are unreliable on Windows — rescan the target folder
            service._invalidate_dir_cache(os.path.dirname(gen["path"]))
            entry = service.get_entry(gen["ref"])
            self._set(
                gen,
                status="completed",
                progress=100,
                message=None,
                url=entry.get("url"),
                thumb_url=entry.get("thumb_url"),
                finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            )
            logger.info(f"Asset generation completed: {gen['id']} -> {gen['ref']}")
        except asyncio.CancelledError:
            self._cleanup(gen)
            self._set(gen, status="cancelled", finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z")
            raise
        except Exception as e:
            logger.error(f"Asset generation {gen['id']} failed: {e}", exc_info=True)
            self._cleanup(gen)
            service._invalidate_dir_cache(os.path.dirname(gen["path"]))
            self._set(
                gen,
                status="failed",
                error=str(e),
                finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            )

    def _cleanup(self, gen: Dict[str, Any]) -> None:
        """Remove a partial output file so a failed job doesn't leave junk."""
        try:
            if gen.get("path") and os.path.isfile(gen["path"]):
                os.remove(gen["path"])
        except OSError:
            pass

    async def _run_image(self, gen: Dict[str, Any]) -> None:
        from core.image_generator import generate_image

        reference_paths = []
        if gen.get("reference_refs"):
            for entry in self._resolve_refs(gen["reference_refs"]):
                if entry.get("type") == "image" and entry.get("path"):
                    reference_paths.append(entry["path"])

        def on_progress(current, total):
            if total:
                self._set(gen, progress=min(99, int(current / total * 100)))

        result = await asyncio.to_thread(
            generate_image,
            prompt=gen["prompt"],
            output_path=gen["path"],
            aspect_ratio=gen.get("aspect_ratio") or None,
            seed=gen.get("seed"),
            workflow_name=gen.get("workflow"),
            step_progress_callback=on_progress,
            reference_images=reference_paths or None,
        )
        if not result or not os.path.isfile(gen["path"]):
            raise RuntimeError("Image generation failed — no output produced")

    async def _run_video(self, gen: Dict[str, Any]) -> None:
        image_path = self._require_ref_path(gen["image_ref"], "image")
        mode = getattr(config, "VIDEO_GENERATION_MODE", "comfyui")

        def on_progress(current, total):
            if total:
                self._set(gen, progress=min(99, int(current / total * 100)))

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

        shot_length = getattr(config, "DEFAULT_SHOT_LENGTH", 5)
        shot = {"index": 1, "image_path": image_path, "motion_prompt": gen["prompt"]}
        if gen.get("duration"):
            shot["duration"] = gen["duration"]

        template = await asyncio.to_thread(
            load_workflow,
            workflow_path,
            video_length_seconds=shot_length,
            aspect_ratio=gen.get("aspect_ratio") or "16:9",
            workflow_config=workflow_config,
        )
        wf = compile_workflow(template, shot, video_length_seconds=shot_length, workflow_config=workflow_config)

        result = submit(wf)
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")
        logger.info(f"Asset video generation submitted: {gen['id']} prompt_id={prompt_id}")

        wait = await async_wait_for_prompt_completion_with_progress(
            prompt_id, progress_callback=on_progress,
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

    async def _run_audio(self, gen: Dict[str, Any]) -> None:
        import requests as http_requests
        from core.comfy_client import submit, async_wait_for_prompt_completion_with_progress, get_output_file_path

        video_path = self._require_ref_path(gen["video_ref"], "video")

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
                self._set(gen, progress=min(99, int(current / total * 100)))

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

    def _resolve_refs(self, refs: List[str]) -> List[Dict[str, Any]]:
        try:
            return get_asset_service().resolve_refs(refs or [])
        except Exception:
            return []

    def _require_ref_path(self, ref: str, expect_type: str) -> str:
        entry = get_asset_service().resolve_ref(ref)
        if not entry.get("exists") or not entry.get("path"):
            raise RuntimeError(f"Source asset not found: {ref}")
        if entry.get("type") != expect_type:
            raise RuntimeError(f"Source asset must be a {expect_type}: {ref}")
        return entry["path"]

    @staticmethod
    def _set(gen: Dict[str, Any], **fields: Any) -> None:
        gen.update(fields)

    @staticmethod
    def _public(gen: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in gen.items() if k not in ("path",)}


_asset_generation: Optional[AssetGenerationService] = None


def get_asset_generation_service() -> AssetGenerationService:
    global _asset_generation
    if _asset_generation is None:
        _asset_generation = AssetGenerationService()
    return _asset_generation
