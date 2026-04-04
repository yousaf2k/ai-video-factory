"""
Generation service - Async wrapper for core generation modules
"""
import sys
import os
import json
import re
import glob
import random
import asyncio
from typing import List, Dict, Any, Optional
import threading
import logging
import time
import shutil
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.project_manager import ProjectManager
from core.image_generator import generate_images_for_shots
from core.shot_planner import plan_shots
from core.logger_config import get_logger
from web_ui.backend.websocket.manager import manager
from web_ui.backend.models.story import ProjectType

logger = get_logger(__name__)

# Import queue models and service
from web_ui.backend.models.queue import (
    QueueItem,
    GenerationType,
    QueueItemStatus
)
from web_ui.backend.services.queue_service import get_queue_service


class GenerationService:
    """Service for async generation operations"""

    def __init__(self):
        # Default to configured projects directory
        import config
        projects_dir = getattr(config, 'ABS_PROJECTS_DIR', None)
        
        if projects_dir is None:
            # Fallback
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            projects_dir = os.path.join(project_root, "output", "projects")
        
        self.project_manager = ProjectManager(projects_dir)
        self.cancelled_projects = set()
        self.cancelled_shots: dict[str, set[int]] = {}
        self.cancelled_scenes: dict[str, set[int]] = {}
        self.queued_shots: dict[str, set[int]] = {}
        self.queued_scenes: dict[str, set[int]] = {}
        self.active_shots: dict[str, int] = {}
        self.active_scenes: dict[str, int] = {}

        # Track active queue items for progress updates
        # Maps (project_id, shot_index, generation_type) -> item_id
        self.active_queue_items: dict[str, str] = {}
        
        # Tracks true executing python-side tasks
        self.running_item_ids: set[str] = set()

        # Queue processor state
        self._queue_processor_running = False
        self._queue_processor_task = None # This is no longer used for the main loop, but might be for other tasks
        self._queue_processor_started = False
        self._queue_processor_thread: Optional[threading.Thread] = None # New thread object
        self._loop_wake_up: Optional[asyncio.Event] = None

    def is_item_running(self, item_id: str) -> bool:
        """Check if an item is physically doing backend work right now"""
        return item_id in getattr(self, 'running_item_ids', set())

    @staticmethod
    def get_item_engine(item: QueueItem) -> str:
        """Resolve which engine will process this item"""
        import config
        if item.generation_type in [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE, GenerationType.THUMBNAIL, GenerationType.BACKGROUND]:
            return item.image_mode or getattr(config, 'IMAGE_GENERATION_MODE', 'comfyui')
        elif item.generation_type in [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO]:
            return item.video_mode or getattr(config, 'VIDEO_GENERATION_MODE', 'comfyui')
        elif item.generation_type == GenerationType.NARRATION:
            return getattr(config, 'TTS_METHOD', 'local')
        return 'other'

    def _get_relative_path(self, path: str) -> str:
        """Convert absolute path to relative format using ProjectManager utility"""
        return self.project_manager.relativize_path(path)

    def _ensure_queue_processor_started(self):
        """Ensure background task is running"""
        # debug_file = config.resolve_path("startup_debug.txt")
        # with open(debug_file, "a") as f: f.write("[DEBUG] inside _ensure_queue_processor_started\n")

        if self._queue_processor_started:
            return

        if self._queue_processor_running:
            logger.warning("Queue processor already starting")
            return

        self._queue_processor_running = True
        self._queue_processor_started = True

        # Create background thread for queue processor
        def run_processor():
            import asyncio
            logger.info("Background thread starting queue processor loop")
            asyncio.run(self._queue_processor_loop())
            logger.info("Background thread queue processor loop finished")

        import threading
        thread = threading.Thread(target=run_processor, daemon=True)
        thread.start()
        logger.info("Started generation queue processor thread")

    async def _queue_processor_loop(self):
        """Background loop that processes queue items with concurrency limit"""
        import config

        # Initialize wake-up event in the correct loop
        self._loop_wake_up = asyncio.Event()

        debug_file = config.resolve_path("startup_debug.txt")
        with open(debug_file, "a") as f: f.write("[DEBUG] loop: started\n")

        # Get concurrency limits from config
        limits = getattr(config, 'CONCURRENT_GENERATION_LIMITS', {})
        default_limit = limits.get('default', getattr(config, 'CONCURRENT_GENERATION_LIMIT', 1))

        def get_limit_for_engine(engine: str) -> int:
            return limits.get(engine, default_limit)

        semaphores = {}
        def get_semaphore(engine: str):
            if engine not in semaphores:
                semaphores[engine] = asyncio.Semaphore(get_limit_for_engine(engine))
            return semaphores[engine]

        logger.info(f"Queue processor started with per-engine concurrency limits: {limits}")

        async def process_single_item(item: QueueItem, engine: str):
            """Process a single queue item with per-engine semaphore control"""
            async with get_semaphore(engine):
                self.running_item_ids.add(item.item_id)
                try:
                    logger.info(f"Processing queue item {item.item_id}: {item.generation_type.value} for shot {item.shot_index} on {engine}")
                    print(f"[DEBUG] getting queue_service", flush=True)
                    # Mark as active
                    queue_service = get_queue_service()
                    print(f"[DEBUG] mark_active", flush=True)
                    queue_service.mark_active(item.item_id)
                    print(f"[DEBUG] finished mark_active", flush=True)

                    # Process the item based on generation type
                    print(f"[DEBUG] routing generation type", flush=True)
                    if item.generation_type in [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE]:
                        print(f"[DEBUG] routing to process_image_generation", flush=True)
                        await self._process_image_generation(item)
                    elif item.generation_type in [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO]:
                        print(f"[DEBUG] routing to process_video_generation", flush=True)
                        await self._process_video_generation(item)
                    elif item.generation_type == GenerationType.NARRATION:
                        await self._process_narration_generation(item)
                    elif item.generation_type == GenerationType.BACKGROUND:
                        await self._process_background_generation(item)
                    elif item.generation_type == GenerationType.SOUNDFX:
                        await self._process_soundfx_generation(item)
                    elif item.generation_type == GenerationType.THUMBNAIL:
                        await self._process_thumbnail_generation(item)
                    else:
                        logger.warning(f"Unknown generation type: {item.generation_type}")
                        queue_service.mark_failed(item.item_id, f"Unknown generation type: {item.generation_type}")

                except Exception as e:
                    logger.error(f"Error processing queue item {item.item_id}: {e}")
                    queue_service = get_queue_service()
                    
                    # Check if already cancelled by user (e.g. via API)
                    current_item = queue_service.get_item(item.item_id)
                    if current_item and current_item.status in [QueueItemStatus.CANCELLED, QueueItemStatus.PAUSED]:
                        logger.info(f"Item {item.item_id} was cancelled, skipping failure status update")
                        return
                        
                    queue_service.mark_failed(item.item_id, str(e))
                finally:
                    self.running_item_ids.discard(item.item_id)

        # Track active tasks by engine
        active_tasks_by_engine = {
            'comfyui': set(),
            'geminiweb': set(),
            'gemini': set(),
            'other': set()
        }

        last_slot_log = 0

        while self._queue_processor_running:
            try:
                # Get queue service
                queue_service = get_queue_service()

                # Check if queue is paused
                if queue_service.is_paused():
                    try:
                        await asyncio.wait_for(self._loop_wake_up.wait(), timeout=5.0)
                        self._loop_wake_up.clear()
                    except asyncio.TimeoutError:
                        pass
                    continue

                # Clean up completed tasks
                for engine in list(active_tasks_by_engine.keys()):
                    active_tasks_by_engine[engine] = {task for task in active_tasks_by_engine[engine] if not task.done()}

                # Get next queued items
                queued_items = queue_service.get_queue(status=QueueItemStatus.QUEUED)

                if not queued_items:
                    # No items to process, wait for wake-up or timeout
                    try:
                        await asyncio.wait_for(self._loop_wake_up.wait(), timeout=2.0)
                        self._loop_wake_up.clear()
                    except asyncio.TimeoutError:
                        pass
                    continue

                # Sort items to prioritize images, then by priority
                def item_sort_key(item):
                    type_order = {
                        GenerationType.IMAGE: 0,
                        GenerationType.THEN_IMAGE: 0,
                        GenerationType.NOW_IMAGE: 0,
                        GenerationType.NARRATION: 1,
                        GenerationType.BACKGROUND: 1,
                        GenerationType.VIDEO: 2,
                        GenerationType.MEETING_VIDEO: 2,
                        GenerationType.DEPARTURE_VIDEO: 2,
                        GenerationType.SOUNDFX: 3
                    }
                    return (type_order.get(item.generation_type, 10), item.priority)

                queued_items.sort(key=item_sort_key)

                available_slots_by_engine = {
                    engine: max(0, get_limit_for_engine(engine) - len(tasks))
                    for engine, tasks in active_tasks_by_engine.items()
                }

                # Evaluate items checking dependencies and engine slots
                items_to_process = []
                project_shots_cache = {}
                from web_ui.backend.models.queue import PriorityUpdateRequest
                
                comfyui_is_running = None
                
                for item in queued_items:
                    engine = self.get_item_engine(item)
                    
                    if engine == 'comfyui':
                        if comfyui_is_running is None:
                            from core.comfy_client import is_comfyui_running
                            comfyui_is_running = await asyncio.to_thread(is_comfyui_running)
                            
                        if not comfyui_is_running:
                            if not hasattr(self, '_last_comfy_wait_log') or time.time() - getattr(self, '_last_comfy_wait_log', 0) > 10:
                                logger.info(f"ComfyUI is not running. Waiting for ComfyUI to start before processing item {item.item_id}...")
                                self._last_comfy_wait_log = time.time()
                            continue

                    if engine not in available_slots_by_engine:
                        available_slots_by_engine[engine] = max(0, get_limit_for_engine(engine) - len(active_tasks_by_engine.get(engine, set())))
                        if engine not in active_tasks_by_engine:
                            active_tasks_by_engine[engine] = set()

                    if available_slots_by_engine[engine] <= 0:
                        continue
                        
                    is_ready = True
                    skip_reason = None
                    
                    try:
                        if item.generation_type in [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO, GenerationType.THEN_IMAGE]:
                            if item.project_id not in project_shots_cache:
                                project_shots_cache[item.project_id] = self.project_manager.get_shots(item.project_id)
                            
                            shots = project_shots_cache[item.project_id]
                            if shots and item.shot_index is not None and 0 < item.shot_index <= len(shots):
                                shot = shots[item.shot_index - 1]
                                
                                if item.generation_type == GenerationType.VIDEO:
                                    if not shot.get('image_generated', False):
                                        is_ready = False
                                        skip_reason = "Base image not generated"
                                elif item.generation_type in [GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO]:
                                    if not (shot.get('now_image_generated', False) and shot.get('then_image_generated', False)):
                                        is_ready = False
                                        skip_reason = "THEN or NOW images not generated"
                                elif item.generation_type == GenerationType.THEN_IMAGE:
                                    # DECISION: For 'Then vs now Actor Face' agent, we don't require NOW image first
                                    is_actor_face = self._is_actor_face_agent(item.project_id)
                                    
                                    if not is_actor_face and not shot.get('now_image_generated', False):
                                        is_ready = False
                                        skip_reason = "NOW image not generated"
                        
                        if is_ready:
                            items_to_process.append((item, engine))
                            available_slots_by_engine[engine] -= 1
                    except Exception as meta_err:
                        logger.error(f"Failed to load metadata for project {item.project_id} while processing item {item.item_id}: {meta_err}")
                        # Skip this item for now as we can't verify dependencies
                        continue
                    else:
                        # Only log every 30 seconds per item to avoid spam
                        if not hasattr(self, '_skip_log_times'): self._skip_log_times = {}
                        now = time.time()
                        if now - self._skip_log_times.get(item.item_id, 0) > 30:
                            logger.info(f"Skipping queue item {item.item_id} ({item.generation_type.value} for shot {item.shot_index}) - {skip_reason}. Waiting for dependencies.")
                            self._skip_log_times[item.item_id] = now
                        
                        # NO update_priority here to avoid heavy disk writes in the loop

                for item, engine in items_to_process:
                    task = asyncio.create_task(process_single_item(item, engine))
                    if engine not in active_tasks_by_engine:
                        active_tasks_by_engine[engine] = set()
                    active_tasks_by_engine[engine].add(task)

                # Log slot status occasionally
                if time.time() - last_slot_log > 30:
                    last_slot_log = time.time()
                    slot_info = ", ".join([f"{k}: {available_slots_by_engine[k]}" for k in available_slots_by_engine])
                    logger.debug(f"Queue Status - Available Slots: {slot_info} | Active Tasks: {sum(len(v) for v in active_tasks_by_engine.values())}")

                # Wait for any task to complete OR a manual wake-up event
                # This makes the loop react instantly to task completion
                all_tasks = [asyncio.create_task(self._loop_wake_up.wait())]
                for engine_tasks in active_tasks_by_engine.values():
                    all_tasks.extend([t for t in engine_tasks if not t.done()])
                
                if all_tasks:
                    try:
                        # Wait up to 5 seconds or until something happens
                        done, pending = await asyncio.wait(all_tasks, timeout=5.0, return_when=asyncio.FIRST_COMPLETED)
                        
                        # Cleanup the wake-up task if it's still pending
                        for t in pending:
                            if t.get_coro().__name__ == 'wait': # It's our wake-up event task
                                t.cancel()
                    except Exception as wait_err:
                        logger.debug(f"Wait interrupted: {wait_err}")
                else:
                    # No active tasks, just wait for wake-up or timeout
                    try:
                        await asyncio.wait_for(self._loop_wake_up.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
                
                self._loop_wake_up.clear()

            except Exception as e:
                # Catch shutdown errors specifically to break the loop gracefully
                error_msg = str(e).lower()
                if "after shutdown" in error_msg or not self._queue_processor_running:
                    logger.info(f"Queue processor loop terminating due to shutdown: {e}")
                    break
                    
                logger.error(f"Error in queue processor loop: {e}")
                await asyncio.sleep(1)

        # Wait for remaining tasks to complete
        all_active = [task for engine_tasks in active_tasks_by_engine.values() for task in engine_tasks]
        if all_active:
            logger.info(f"Waiting for {len(all_active)} active tasks to complete...")
            await asyncio.gather(*all_active, return_exceptions=True)

        logger.info("Queue processor stopped")

    async def _process_image_generation(self, item: QueueItem):
        """Process image generation for a queue item"""
        try:
            # Determine if this is a FLFI2V variant
            if item.generation_type == GenerationType.THEN_IMAGE:
                image_variant = "then"
            elif item.generation_type == GenerationType.NOW_IMAGE:
                image_variant = "now"
            else:
                image_variant = None

            # Get project title
            story = self.project_manager.get_story(item.project_id)
            project_title = story.get('title', item.project_id) if story else item.project_id

            logger.info(f"ABOUT TO AWAIT regenerate_shot_image for item {item.item_id}")
            print(f"[DEBUG] ABOUT TO AWAIT regenerate_shot_image for item {item.item_id}", flush=True)
            
            def save_prompt_id(pid):
                item.comfyui_prompt_id = pid
                queue_service = get_queue_service()
                if item.status != QueueItemStatus.CANCELLED:
                    queue_service.update_item(item)
                    logger.debug(f"Saved ComfyUI prompt ID {pid} for item {item.item_id}")

            # Call regenerate_shot_image with overrides from the queue item
            await self.regenerate_shot_image(
                item.project_id,
                item.shot_index,
                force=True,
                image_mode=item.image_mode,
                image_workflow=item.image_workflow,
                prompt_override=item.prompt_override,
                project_title=project_title,
                image_variant=image_variant,
                seed=item.seed,
                prompt_id_callback=save_prompt_id,
                existing_prompt_id=item.comfyui_prompt_id,
                shot_id=item.shot_id,
                gemini_mode=item.gemini_mode
            )

            logger.info(f"Completed image generation for queue item {item.item_id}")
            print(f"[DEBUG] FINISHED AWAIT regenerate_shot_image for item {item.item_id}", flush=True)

        except Exception as e:
            logger.error(f"Error processing image generation for {item.item_id}: {e}")
            raise

    async def force_start_item(self, item_id: str):
        """
        Force start a queue item immediately, bypassing processor throttles.
        """
        queue_service = get_queue_service()
        item = queue_service.get_item(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found in queue")

        logger.info(f"Force starting queue item {item_id} ({item.generation_type.value})")

        # 1. Reset state to QUEUED so it can be marked active
        if item.status == QueueItemStatus.PAUSED:
            queue_service.resume_item(item_id)
        elif item.status in [QueueItemStatus.FAILED, QueueItemStatus.CANCELLED, QueueItemStatus.COMPLETED]:
            # Use requeue to reset counters/paths
            queue_service.requeue_item(item_id)

        # Re-fetch item to ensure state sync, then force mark to ACTIVE 
        # to guarantee the core processor doesn't pick it up too
        queue_service.mark_active(item_id)

        # 2. Trigger task execution in background bypassing semaphore
        async def run_now():
            try:
                if item.generation_type in [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE]:
                    await self._process_image_generation(item)
                elif item.generation_type in [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO]:
                    await self._process_video_generation(item)
                elif item.generation_type == GenerationType.NARRATION:
                    await self._process_narration_generation(item)
                elif item.generation_type == GenerationType.BACKGROUND:
                    await self._process_background_generation(item)
                elif item.generation_type == GenerationType.SOUNDFX:
                    await self._process_soundfx_generation(item)
                else:
                    logger.warning(f"Unknown generation type on force start: {item.generation_type}")
            except Exception as e:
                logger.error(f"Force start failed executing task {item_id}: {e}")
                # _process triggers usually handle failure markings internally
                # but single_image handlers lift exceptions

        # Execute immediately
        asyncio.create_task(run_now())
        self._wake_up_processor()
        return {"message": "Item force started successfully"}

    def _wake_up_processor(self):
        """Wake up the queue processor loop from its sleep/wait state"""
        if self._loop_wake_up:
            try:
                # Use call_soon_threadsafe if called from another thread
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    pass
                
                if loop and loop.is_running():
                    loop.call_soon_threadsafe(self._loop_wake_up.set)
                else:
                    # If we can't find a loop or it's not running, we can't set it easily
                    # But usually this is called within a loop or from a thread during generation
                    pass
            except Exception as e:
                logger.debug(f"Failed to wake up processor: {e}")

    async def _process_video_generation(self, item: QueueItem):
        """Process video generation for a queue item"""
        try:
            # Determine if this is a FLFI2V variant
            if item.generation_type == GenerationType.MEETING_VIDEO:
                video_variant = "meeting"
            elif item.generation_type == GenerationType.DEPARTURE_VIDEO:
                video_variant = "departure"
            else:
                video_variant = None

            # Get project title
            story = self.project_manager.get_story(item.project_id)
            project_title = story.get('title', item.project_id) if story else item.project_id

            def save_prompt_id(pid):
                item.comfyui_prompt_id = pid
                queue_service = get_queue_service()
                if item.status != QueueItemStatus.CANCELLED:
                    queue_service.update_item(item)
                    logger.debug(f"Saved ComfyUI video prompt ID {pid} for item {item.item_id}")

            # Call regenerate_shot_video with overrides from the queue item
            res = getattr(item, 'resolution', None)
            logger.info(f"[QUEUE] Processing video generation for shot {item.shot_index}. Resolution: {res or 'default'}")
            
            await self.regenerate_shot_video(
                item.project_id,
                item.shot_index,
                force=True,
                video_mode=item.video_mode,
                video_workflow=item.video_workflow,
                project_title=project_title,
                video_variant=video_variant,
                append_image_prompt=item.append_image_prompt,
                shot_id=item.shot_id,
                prompt_override=item.prompt_override,
                draft_low_res_video=getattr(item, 'draft_low_res_video', False),
                resolution=res,
                prompt_id_callback=save_prompt_id,
                existing_prompt_id=item.comfyui_prompt_id,
                gemini_mode=item.gemini_mode
            )

            logger.info(f"Completed video generation for queue item {item.item_id}")

            # Auto-chain: if generate_soundfx flag is set, queue a SOUNDFX item
            if getattr(item, 'generate_soundfx', False):
                logger.info(f"Auto-chaining sound FX generation for shot {item.shot_index} after video completion")
                try:
                    queue_service = get_queue_service()
                    shots = self.project_manager.get_shots(item.project_id)
                    story = self.project_manager.get_story(item.project_id)
                    shot = shots[item.shot_index - 1] if item.shot_index <= len(shots) else None
                    sfx_item = self._create_queue_item(
                        item.project_id, item.shot_index, GenerationType.SOUNDFX, shot, story
                    )
                    queue_service.add_items([sfx_item])
                    logger.info(f"Queued auto-chain SOUNDFX item for shot {item.shot_index}")
                except Exception as sfx_err:
                    logger.error(f"Failed to auto-chain sound FX for shot {item.shot_index}: {sfx_err}")
        except Exception as e:
            logger.error(f"Error processing video generation for {item.item_id}: {e}")
            raise

    async def _process_narration_generation(self, item: QueueItem):
        """Process narration generation for a queue item"""
        # TODO: Implement narration generation
        logger.warning(f"Narration generation not yet implemented for item {item.item_id}")
        raise NotImplementedError("Narration generation not yet implemented")

    async def _process_background_generation(self, item: QueueItem):
        """Process background generation for a queue item"""
        try:
            # Load story to get default set_prompt
            story = self.project_manager.get_story(item.project_id)
            scenes = story.get('scenes', [])
            
            scene = None
            for s in scenes:
                if s.get('scene_id') == item.scene_id:
                    scene = s
                    break
            
            if not scene:
                raise ValueError(f"Scene {item.scene_id} not found in story")
            
            set_prompt = scene.get('set_prompt')
            
            # Call generate_scene_background with overrides from the queue item
            await self.generate_scene_background(
                project_id=item.project_id,
                scene_id=item.scene_id,
                set_prompt=set_prompt,
                prompt=item.prompt_override,
                negative_prompt=None,
                seed=item.seed,
                workflow=item.image_workflow,
                image_mode=item.image_mode
            )

            logger.info(f"Completed background generation for queue item {item.item_id}")

        except Exception as e:
            logger.error(f"Error processing background generation for {item.item_id}: {e}")
            raise

    async def _process_soundfx_generation(self, item: QueueItem):
        """Process sound FX generation for a queue item"""
        try:
            story = self.project_manager.get_story(item.project_id)
            project_title = story.get('title', item.project_id) if story else item.project_id

            await self.generate_soundfx(
                item.project_id,
                item.shot_index,
                force=True
            )

            logger.info(f"Completed sound FX generation for queue item {item.item_id}")
        except Exception as e:
            logger.error(f"Error processing sound FX generation for {item.item_id}: {e}")
            raise

    def cancel_project(self, project_id: str):
        """Mark a project as cancelled to halt background queue processing."""
        self.cancelled_projects.add(project_id)
        if project_id in self.queued_shots:
            self.queued_shots.pop(project_id)

        # Also cancel all queued/active items in QueueService
        queue_service = get_queue_service()
        queued_items = queue_service.get_queue(project_id=project_id)
        for item in queued_items:
            if item.status in [QueueItemStatus.QUEUED, QueueItemStatus.ACTIVE]:
                queue_service.mark_cancelled(item.item_id)
                if item.status == QueueItemStatus.ACTIVE:
                    logger.info(f"Marking active item {item.item_id} as CANCELLED for project {project_id}")

        logger.info(f"Marked project {project_id} as cancelled. Future queued items will be skipped.")
        self._wake_up_processor()

    def cancel_single_shot(self, project_id: str, shot_index: int):
        """Mark a single shot as cancelled to halt it from entering the queue."""
        if project_id not in self.cancelled_shots:
            self.cancelled_shots[project_id] = set()
        self.cancelled_shots[project_id].add(shot_index)
        if project_id in self.queued_shots and shot_index in self.queued_shots[project_id]:
            self.queued_shots[project_id].remove(shot_index)

        # Also cancel queued/active items in QueueService for this shot
        queue_service = get_queue_service()
        queued_items = queue_service.get_queue(project_id=project_id)
        for item in queued_items:
            if item.shot_index == shot_index and item.status in [QueueItemStatus.QUEUED, QueueItemStatus.ACTIVE]:
                queue_service.mark_cancelled(item.item_id)
                if item.status == QueueItemStatus.ACTIVE:
                    logger.info(f"Marking active item {item.item_id} as CANCELLED for shot {shot_index}")

        # If this is the currently actively generating shot, tell ComfyUI to stop
        if self.active_shots.get(project_id) == shot_index:
            from core.comfy_client import interrupt_generation
            logger.info(f"Shot {shot_index} is currently active. Sending interrupt to ComfyUI.")
            interrupt_generation()

        logger.info(f"Marked shot {shot_index} in project {project_id} as cancelled.")
        self._wake_up_processor()

    def cancel_scene_narration(self, project_id: str, scene_id: int):
        """Mark a scene narration as cancelled."""
        if project_id not in self.cancelled_scenes:
            self.cancelled_scenes[project_id] = set()
        self.cancelled_scenes[project_id].add(scene_id)
        if project_id in self.queued_scenes and scene_id in self.queued_scenes[project_id]:
            self.queued_scenes[project_id].remove(scene_id)
            
        # Also cancel queued/active items in QueueService for this scene
        queue_service = get_queue_service()
        queued_items = queue_service.get_queue(project_id=project_id)
        for item in queued_items:
            if item.scene_id == scene_id and item.status in [QueueItemStatus.QUEUED, QueueItemStatus.ACTIVE]:
                queue_service.mark_cancelled(item.item_id)
                if item.status == QueueItemStatus.ACTIVE:
                    logger.info(f"Marking active item {item.item_id} as CANCELLED for scene {scene_id}")

        # If this is the currently actively generating scene, tell ComfyUI to stop
        if self.active_scenes.get(project_id) == scene_id:
            from core.comfy_client import interrupt_generation
            logger.info(f"Scene {scene_id} is currently active. Sending interrupt to ComfyUI.")
            interrupt_generation()
            
        logger.info(f"Marked scene {scene_id} narration in project {project_id} as cancelled.")
        self._wake_up_processor()

    def _create_queue_item(
        self,
        project_id: str,
        shot_index: Optional[int],
        generation_type: GenerationType,
        shot: dict = None,
        story: dict = None,
        request: Any = None
    ) -> QueueItem:
        """
        Create a QueueItem for tracking generation in the unified queue.

        Args:
            project_id: Project identifier
            shot_index: Shot index (1-based)
            generation_type: Type of generation
            shot: Shot data dictionary
            story: Story data dictionary

        Returns:
            QueueItem object
        """
        # Get project title
        story = self.project_manager.get_story(project_id)
        project_title = story.get('title', project_id) if story else project_id

        # Extract shot details if available
        shot_id = shot.get('id') if shot else None
        scene_name = shot.get('scene_name') if shot else None
        character_name = shot.get('character_name') if shot else None

        # Check if FLFI2V
        is_flfi2v = shot.get('is_flfi2v', False) if shot else False

        # Extract prompt override based on generation type
        prompt_override = None
        if request:
            prompt_override = getattr(request, 'prompt_override', None)
            if not prompt_override and generation_type == GenerationType.DEPARTURE_VIDEO:
                prompt_override = getattr(request, 'departure_prompt_override', None)
            if not prompt_override and generation_type == GenerationType.THEN_IMAGE:
                prompt_override = getattr(request, 'then_prompt_override', None)

        return QueueItem(
            item_id="",  # Will be assigned by QueueService
            project_id=project_id,
            shot_index=shot_index,
            scene_id=shot.get('scene_id') if shot else None,
            generation_type=generation_type,
            status=QueueItemStatus.QUEUED,
            progress=0,
            priority=100,  # Default priority
            is_flfi2v=is_flfi2v,
            character_name=character_name,
            project_title=project_title,
            scene_name=scene_name,
            shot_id=shot_id,
            prompt_override=prompt_override,
            seed=getattr(request, 'seed', None) if request else None,
            image_mode=getattr(request, 'image_mode', None) if request else None,
            image_workflow=getattr(request, 'image_workflow', None) if request else None,
            video_mode=getattr(request, 'video_mode', None) if request else None,
            video_workflow=getattr(request, 'video_workflow', None) if request else None,
            image_variant=getattr(request, 'image_variant', None) if request else None,
            video_variant=getattr(request, 'video_variant', None) if request else None,
            append_image_prompt=getattr(request, 'append_image_prompt', None) if request else None,
            generate_soundfx=getattr(request, 'generate_soundfx', False) if request else False,
            draft_low_res_video=getattr(request, 'draft_low_res_video', False) if request else False,
            resolution=(getattr(request, 'resolution', None) or None) if request else None,
            gemini_mode=(getattr(request, 'gemini_mode', None) or shot.get('gemini_mode', None) or config.GEMINIWEB_DEFAULT_MODE) if request else (shot.get('gemini_mode', None) or config.GEMINIWEB_DEFAULT_MODE)
        )

    def _get_queue_item_id(
        self,
        project_id: str,
        shot_index: Optional[int],
        generation_type: GenerationType,
        scene_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get the queue item_id for a specific shot/scene and generation type.

        Args:
            project_id: Project identifier
            shot_index: Shot index (1-based)
            generation_type: Type of generation
            scene_id: Optional scene identifier

        Returns:
            Queue item ID or None if not found
        """
        queue_service = get_queue_service()
        queue_items = queue_service.get_queue(project_id=project_id)

        # Find matching queue item
        for item in queue_items:
            # Match by shot index if provided
            if shot_index is not None and item.shot_index == shot_index:
                if (item.generation_type == generation_type and
                    item.status in [QueueItemStatus.QUEUED, QueueItemStatus.ACTIVE]):
                    return item.item_id
            # Match by scene ID if shot_index is None
            elif shot_index is None and scene_id is not None and item.scene_id == scene_id:
                if (item.generation_type == generation_type and
                    item.status in [QueueItemStatus.QUEUED, QueueItemStatus.ACTIVE]):
                    return item.item_id

        return None

    def _mark_queue_item_active(
        self,
        project_id: str,
        shot_index: Optional[int],
        generation_type: GenerationType,
        scene_id: Optional[int] = None
    ):
        """Mark a queue item as active (started processing)."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type, scene_id)
        if item_id:
            queue_service = get_queue_service()
            queue_service.mark_active(item_id)
            # Store active mapping for progress updates
            key_id = shot_index if shot_index is not None else f"s{scene_id}"
            key = f"{project_id}:{key_id}:{generation_type.value}"
            self.active_queue_items[key] = item_id
            logger.info(f"Marked queue item {item_id} as active ({generation_type.value}, id {key_id})")

    def _update_queue_item_progress(
        self,
        project_id: str,
        shot_index: Optional[int],
        generation_type: GenerationType,
        progress: int,
        scene_id: Optional[int] = None
    ):
        """Update progress for an active queue item."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type, scene_id)
        if item_id:
            queue_service = get_queue_service()
            queue_service.update_progress(item_id, progress)
            logger.debug(f"Updated queue item {item_id} progress to {progress}%")

    def _mark_queue_item_completed(
        self,
        project_id: str,
        shot_index: Optional[int],
        generation_type: GenerationType,
        progress: int = 100,
        scene_id: Optional[int] = None
    ):
        """Mark a queue item as completed."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type, scene_id)
        if item_id:
            queue_service = get_queue_service()
            queue_service.mark_completed(item_id, progress)
            # Remove from active tracking
            key_id = shot_index if shot_index is not None else f"s{scene_id}"
            key = f"{project_id}:{key_id}:{generation_type.value}"
            self.active_queue_items.pop(key, None)
            logger.info(f"Marked queue item {item_id} as completed ({generation_type.value}, id {key_id})")

    def _mark_queue_item_failed(
        self,
        project_id: str,
        shot_index: Optional[int],
        generation_type: GenerationType,
        error_message: str,
        scene_id: Optional[int] = None
    ):
        """Mark a queue item as failed."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type, scene_id)
        if item_id:
            queue_service = get_queue_service()
            queue_service.mark_failed(item_id, error_message)
            # Remove from active tracking
            key_id = shot_index if shot_index is not None else f"s{scene_id}"
            key = f"{project_id}:{key_id}:{generation_type.value}"
            self.active_queue_items.pop(key, None)
            logger.warning(f"Marked queue item {item_id} as failed: {error_message}")

    def add_single_shot_to_queue(
        self,
        project_id: str,
        shot_id_or_index: Any,
        generation_type: GenerationType,
        request: Any
    ) -> list:
        """Add a single shot generation item to the background queue with overrides"""
        from web_ui.backend.services.queue_service import get_queue_service
        # Ensure queue processor is running
        self._ensure_queue_processor_started()

        shots = self.project_manager.get_shots(project_id)
        story = self.project_manager.get_story(project_id)
        
        # Resolve shot by ID or Index
        shot = None
        shot_index = -1
        
        # Resolve shot by ID first
        for i, s in enumerate(shots):
            if s.get('id') == str(shot_id_or_index):
                shot = s
                shot_index = i + 1
                break
        
        # Fallback to Index if not found as ID
        if not shot and (isinstance(shot_id_or_index, int) or (isinstance(shot_id_or_index, str) and shot_id_or_index.isdigit())):
            idx = int(shot_id_or_index)
            if 1 <= idx <= len(shots):
                shot = shots[idx - 1]
                shot_index = idx

        
        if not shot:
            logger.warning(f"Could not resolve shot '{shot_id_or_index}' for project {project_id}")
            return []

        items_to_add = []
        project_type = story.get('project_type', 1) if story else 1

        logger.info(f"[DEBUG] add_single_shot_to_queue: request={request}")
        if request:
            logger.info(f"[DEBUG] add_single_shot_to_queue: image_variant={getattr(request, 'image_variant', 'N/A')}")
            logger.info(f"[DEBUG] add_single_shot_to_queue: video_variant={getattr(request, 'video_variant', 'N/A')}")


        # Replicate batch FLFI2V splits
        if shot and shot.get('is_flfi2v') and project_type == 2:
            if generation_type == GenerationType.IMAGE:
                image_variant = getattr(request, 'image_variant', 'both') or 'both'
                if image_variant in ['now', 'both']:
                    items_to_add.append(self._create_queue_item(project_id, shot_index, GenerationType.NOW_IMAGE, shot, story, request))
                if image_variant in ['then', 'both']:
                    items_to_add.append(self._create_queue_item(project_id, shot_index, GenerationType.THEN_IMAGE, shot, story, request))
            elif generation_type == GenerationType.VIDEO:
                video_variant = getattr(request, 'video_variant', 'both') or 'both'
                if video_variant in ['meeting', 'both']:
                    items_to_add.append(self._create_queue_item(project_id, shot_index, GenerationType.MEETING_VIDEO, shot, story, request))
                if video_variant in ['departure', 'both']:
                    items_to_add.append(self._create_queue_item(project_id, shot_index, GenerationType.DEPARTURE_VIDEO, shot, story, request))
            else:
                items_to_add.append(self._create_queue_item(project_id, shot_index, generation_type, shot, story, request))
        else:
            items_to_add.append(self._create_queue_item(project_id, shot_index, generation_type, shot, story, request))
        
        queue_service = get_queue_service()
        added_items = queue_service.add_items(items_to_add)
        self._wake_up_processor()
        return added_items

    def add_background_to_queue(
        self,
        project_id: str,
        scene_id: int,
        request: Any
    ) -> list:
        """Add a background generation item to the background queue"""
        from web_ui.backend.services.queue_service import get_queue_service
        # Ensure queue processor is running
        self._ensure_queue_processor_started()

        story = self.project_manager.get_story(project_id)
        project_title = story.get('title', project_id) if story else project_id
        
        # Find the scene
        scenes = story.get('scenes', [])
        scene = None
        for s in scenes:
            if s.get('scene_id') == scene_id:
                scene = s
                break
        
        scene_name = (scene.get('scene_name') if scene else None) or f"Scene {scene_id}"

        item = QueueItem(
            item_id="",  # Will be assigned by QueueService
            project_id=project_id,
            shot_index=None,
            scene_id=scene_id,
            generation_type=GenerationType.BACKGROUND,
            status=QueueItemStatus.QUEUED,
            progress=0,
            priority=50,  # Backgrounds higher priority
            is_flfi2v=True,
            project_title=project_title,
            scene_name=scene_name,
            prompt_override=getattr(request, 'prompt', None),
            seed=getattr(request, 'seed', None),
            image_mode=getattr(request, 'image_model', None),
            image_workflow=getattr(request, 'workflow', None)
        )
        
        queue_service = get_queue_service()
        added_items = queue_service.add_items([item])
        self._wake_up_processor()
        return added_items

    async def run_batch_generation(self, project_id: str, request: Any):
        """
        Add items to queue for batch generation.
        Actual processing is handled by the background queue processor.
        """
        from web_ui.backend.websocket.manager import manager
        import config

        # Ensure queue processor is running
        self._ensure_queue_processor_started()

        # Clear any old cancellation flags from previous runs
        if project_id in self.cancelled_projects:
            self.cancelled_projects.remove(project_id)
        if project_id in self.cancelled_shots:
            self.cancelled_shots.pop(project_id)

        # Create QueueItems and add to QueueService
        queue_service = get_queue_service()
        shots = self.project_manager.get_shots(project_id)
        story = self.project_manager.get_story(project_id)

        # Resolve indices from IDs if provided for better stability during reordering
        final_indices = []
        request_shot_ids = getattr(request, 'shot_ids', None)
        request_shot_indices = getattr(request, 'shot_indices', None)

        if request_shot_ids:
            # Map IDs to current indices
            id_to_index = {s.get('id'): i for i, s in enumerate(shots, 1) if s.get('id')}
            for s_id in request_shot_ids:
                if s_id in id_to_index:
                    final_indices.append(id_to_index[s_id])
                else:
                    logger.warning(f"Batch generation: Shot ID {s_id} not found in project {project_id}")
        elif request_shot_indices:
            final_indices = request_shot_indices
        
        if not final_indices:
            logger.warning(f"Batch generation: No valid shots to process for project {project_id}")
            return []

        # Process all shots into categories to enable proper prioritization
        now_images = []
        then_images = []
        standard_images = []
        video_items = []
        other_items = []

        for idx in final_indices:
            shot = shots[idx - 1] if idx <= len(shots) else None
            if not shot:
                continue

            # Resolve force flags, defaulting to True (force) if not provided
            force_images = getattr(request, 'force_images', None)
            if force_images is None:
                force_images = getattr(request, 'force', True)
                
            force_videos = getattr(request, 'force_videos', None)
            if force_videos is None:
                force_videos = getattr(request, 'force', True)

            # Determine if we should skip based on existence
            skip_images = not force_images and shot.get('image_generated', False)
            skip_videos = not force_videos and shot.get('video_rendered', False)

            # Create image queue items
            if request.regenerate_images and not skip_images:
                if shot.get('is_flfi2v') and story.get('project_type') == 2:
                    # Collect NOW and THEN separately for prioritization
                    now_item = self._create_queue_item(project_id, idx, GenerationType.NOW_IMAGE, shot, story, request=request)
                    then_item = self._create_queue_item(project_id, idx, GenerationType.THEN_IMAGE, shot, story, request=request)
                    now_images.append(now_item)
                    then_images.append(then_item)
                else:
                    image_item = self._create_queue_item(project_id, idx, GenerationType.IMAGE, shot, story, request=request)
                    standard_images.append(image_item)

            # Create video queue items
            if request.regenerate_videos and not skip_videos:
                if shot.get('is_flfi2v') and story.get('project_type') == 2:
                    meeting_item = self._create_queue_item(project_id, idx, GenerationType.MEETING_VIDEO, shot, story, request=request)
                    departure_item = self._create_queue_item(project_id, idx, GenerationType.DEPARTURE_VIDEO, shot, story, request=request)
                    video_items.append(meeting_item)
                    video_items.append(departure_item)
                else:
                    video_item = self._create_queue_item(project_id, idx, GenerationType.VIDEO, shot, story, request=request)
                    video_items.append(video_item)

        # Assemble the final queue in the priority order:
        # All NOW images globally first -> then THEN images -> Standard images -> All Videos
        # This satisfies the user's explicit request: "queue all now images first then then images"
        queue_items = []
        queue_items.extend(now_images)
        queue_items.extend(then_images)
        queue_items.extend(standard_images)
        queue_items.extend(video_items)
        queue_items.extend(other_items)

        if not queue_items:
            return []

        # Add all items to queue
        added_items = queue_service.add_items(queue_items)
        logger.info(f"Added {len(added_items)} items to queue for project {project_id}")

        # Also keep any old tracking for backward compatibility
        self.queued_shots[project_id] = set(request.shot_indices)

        logger.info(f"Added {len(queue_items)} items to queue for project {project_id}. Queue processor will handle generation.")
        return added_items

    async def run_batch_narration_generation(self, project_id: str, request: Any):
        """
        Background task to process a batch of scene narrations with a concurrency limit.
        """
        from web_ui.backend.websocket.manager import manager
        import config
        
        # Clear any old cancellation flags
        if project_id in self.cancelled_projects:
            self.cancelled_projects.remove(project_id)
        if project_id in self.cancelled_scenes:
            self.cancelled_scenes.pop(project_id)
            
        limit = getattr(config, 'CONCURRENT_GENERATION_LIMIT', 2)
        logger.info(f"Using concurrency limit of {limit} for batch narration")
        semaphore = asyncio.Semaphore(limit)
        
        # Tracking for UI
        self.queued_scenes[project_id] = set(request.scene_indices)
        
        async def process_scene(scene_index: int):
            if project_id in self.cancelled_projects:
                logger.info(f"Project {project_id} cancelled. Skipping scene {scene_index} narration.")
                return
            if project_id in self.cancelled_scenes and scene_index in self.cancelled_scenes[project_id]:
                logger.info(f"Scene {scene_index} narration cancelled. Skipping.")
                return
                
            async with semaphore:
                try:
                    if project_id in self.cancelled_projects:
                        return
                    if project_id in self.cancelled_scenes and scene_index in self.cancelled_scenes[project_id]:
                        return

                    if project_id in self.queued_scenes and scene_index in self.queued_scenes[project_id]:
                        self.queued_scenes[project_id].remove(scene_index)

                    self.active_scenes[project_id] = scene_index
                    try:
                        await self.regenerate_scene_narration(
                            project_id, scene_index,
                            tts_method=request.tts_method,
                            tts_workflow=request.tts_workflow,
                            voice=request.voice
                        )
                    finally:
                        self.active_scenes.pop(project_id, None)
                except Exception as e:
                    logger.error(f"Batch narration error on scene {scene_index}: {str(e)}")
                    manager.broadcast_sync(project_id, {
                        "type": "error",
                        "project_id": project_id,
                        "scene_index": scene_index,
                        "step": "narration",
                        "message": str(e)
                    })

        logger.info(f"Starting batch narration generation for {len(request.scene_indices)} scenes")
        tasks = [process_scene(idx) for idx in request.scene_indices]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Completed batch narration generation for project {project_id}")

    async def regenerate_shot_image(
        self, project_id: str, shot_index: int, force: bool = False,
        image_mode: Optional[str] = None, image_workflow: Optional[str] = None,
        seed: Optional[int] = None, prompt_override: Optional[str] = None,
        project_title: Optional[str] = None, image_variant: str = None,
        prompt_id_callback=None, existing_prompt_id=None,
        shot_id: str = None, gemini_mode: str = None
    ) -> str:
        """
        Regenerate image for a single shot

        Args:
            project_id: Project identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if image exists
            image_mode: Override generation mode
            image_workflow: Override ComfyUI workflow
            project_title: Optional title for Gemini Web chat persistence
            image_variant: For FLFI2V shots, which variant to generate ("then", "now", or "both")

        Returns:
            Path to generated image (or dict with "then"/"now" keys for FLFI2V)
        """
        try:
            print(f"[DEBUG] entering regenerate_shot_image for item {project_id} shot {shot_index} force={force}")
            logger.info(f"entering regenerate_shot_image for item {project_id} shot {shot_index} force={force}")
            # Load shots and story
            shots = self.project_manager.get_shots(project_id)
            story = self.project_manager.get_story(project_id)

            # Find the shot - prefer ID if provided
            shot = None
            if shot_id:
                for s in shots:
                    if s.get('id') == shot_id:
                        shot = s
                        # Update index for logs/variants if it moved
                        shot_index = s.get('index', shot_index)
                        break
            
            if not shot:
                if 1 <= shot_index <= len(shots):
                    shot = shots[shot_index - 1]
                    shot_id = shot.get('id')
                else:
                    raise ValueError(f"Shot {shot_index} (ID={shot_id}) not found")
            project_type = story.get('project_type', 1) if story else 1

            # Handle FLFI2V shots
            if shot.get('is_flfi2v') and project_type == 2:
                results = await self._regenerate_flfi2v_images(
                    project_id, shot_index, shot, story, force,
                    image_mode, image_workflow, seed, project_title, image_variant,
                    prompt_override=prompt_override,
                    shot_id=shot_id,
                    gemini_mode=gemini_mode
                )
                # Return the NOW image path for backward compatibility
                # (UI will use then_image_path/now_image_path for FLFI2V shots)
                return results.get('now') if isinstance(results, dict) else results

            # Standard documentary mode (existing code)
            # Check if already exists and not forcing
            if not force and shot.get('image_generated', False):
                logger.info(f"Shot {shot_index} already has image, skipping")
                return shot.get('image_path')

            # Preserve old image_path in image_paths before regenerating
            old_image_path = shot.get('image_path')
            if old_image_path:
                # We use update_shot_metadata which is atomic and handles path lists
                self.project_manager.update_shot_metadata(project_id, {'image_path': old_image_path}, shot_id=shot_id, shot_index=shot_index)

            # Generate image for single shot
            logger.info(f"Regenerating image for shot {shot_index}")

            # Mark queue item as active
            self._mark_queue_item_active(project_id, shot_index, GenerationType.IMAGE)

            # Broadcast initial 0% so UI resets from any stale progress
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "image",
                "progress": 0
            })

            # Get character reference images for standard shots
            reference_images = None
            import config
            actual_mode = image_mode or config.IMAGE_GENERATION_MODE
            if story.get('characters'):
                character_name = shot.get('character_name')
                character = None
                for char in story['characters']:
                    if char.get('name') == character_name:
                        character = char
                        break
                if character:
                    then_ref = character.get('then_reference_image_path')
                    now_ref = character.get('now_reference_image_path')
                    if actual_mode in ["geminiweb", "gemini"]:
                        reference_images = []
                        if then_ref:
                            reference_images.append(config.resolve_path(then_ref))
                        if now_ref:
                            reference_images.append(config.resolve_path(now_ref))
                        if not reference_images:
                            reference_images = None
                    else:
                        reference_images = then_ref or now_ref

            # Run in thread pool to avoid blocking
            image_path = await asyncio.to_thread(
                self._generate_single_image,
                project_id,
                shot,
                image_mode,
                image_workflow,
                seed,
                prompt_override,
                project_title,
                None,  # No variant for standard shots
                reference_images,
                None,  # generation_type
                gemini_mode=gemini_mode
            )

            # Mark as generated safely using shot_id
            self.project_manager.mark_image_generated(project_id, shot_index, image_path, shot_id=shot_id)

            # Mark queue item as completed
            self._mark_queue_item_completed(project_id, shot_index, GenerationType.IMAGE)

            # Broadcast completion to clear progress on frontend
            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "image"
            })

            logger.info(f"Shot {shot_index} image regenerated: {image_path}")
            return image_path

        except Exception as e:
            logger.error(f"Error regenerating shot {shot_index} image: {e}")
            # Mark queue item as failed
            self._mark_queue_item_failed(project_id, shot_index, GenerationType.IMAGE, str(e))

            # Broadcast cancelled event to clear loading state in UI
            manager.broadcast_sync(project_id, {
                "type": "cancelled",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "image",
                "error": str(e)
            })
            raise

    async def _regenerate_flfi2v_images(
        self, project_id: str, shot_index: int, shot: dict, story: dict,
        force: bool, image_mode: Optional[str], image_workflow: Optional[str],
        seed: Optional[int], project_title: Optional[str], image_variant: str,
        prompt_override: Optional[str] = None,
        shot_id: str = None,
        gemini_mode: str = None
    ) -> dict:
        """Regenerate THEN and/or NOW images for FLFI2V shot"""
        from web_ui.backend.models.story import ProjectType
        import os
        import config
        from web_ui.backend.websocket.manager import manager
        from web_ui.backend.models.queue import GenerationType

        images_dir = self.project_manager.get_images_dir(project_id)
        os.makedirs(images_dir, exist_ok=True)

        results = {}
        actual_mode = image_mode or config.IMAGE_GENERATION_MODE
        shots = self.project_manager.get_shots(project_id)
        
        # Find the correct shot - prefer ID if provided
        shot_to_use = None
        if shot_id:
            for s in shots:
                if s.get('id') == shot_id:
                    shot_to_use = s
                    # Update index for logs/variants if it moved
                    shot_index = s.get('index', shot_index)
                    break
        
        if not shot_to_use:
            if 1 <= shot_index <= len(shots):
                shot_to_use = shots[shot_index - 1]
                shot_id = shot_to_use.get('id')
            else:
                raise ValueError(f"Shot {shot_index} (ID={shot_id}) not found")

        # Resolve scene-level background (set_prompt) for more accurate environment generation
        scenes = story.get('scenes', [])
        scene_id = shot_to_use.get('scene_id') if shot_to_use else shot.get('scene_id')
        scene = next((s for s in scenes if s.get('scene_id') == scene_id), {})
        set_prompt = scene.get('set_prompt', '') or story.get('set_prompt', '')

        # Character Resolution: Resolve reference images from character_id
        then_reference = ''
        now_reference = ''
        character_id = shot_to_use.get('character_id') if shot_to_use else None
        
        if character_id and 'characters' in story:
            # character_id format: char_{scene_id:02d}_{char_idx:02d}
            # Although the ID contains indices, we search for robustness
            for char_obj in story['characters']:
                # The character objects in story don't have IDs yet, but they have name and prompts
                # We match the name if present, or use the char_id to derive scene/index
                char_name = shot_to_use.get('character_name', '')
                if char_obj.get('name') == char_name:
                    then_reference = char_obj.get('then_reference_image_path', '')
                    now_reference = char_obj.get('now_reference_image_path', '')
                    logger.info(f"Resolved reference images for character '{char_name}': then={then_reference}, now={now_reference}")
                    break
        
        # Fallback to top-level if still empty (not expected for FLFI2V)
        if not then_reference: then_reference = story.get('then_reference_image_path', '')
        if not now_reference: now_reference = story.get('now_reference_image_path', '')

        # ── Recovery scan: ensure all existing then_*/now_* files are tracked ──
        existing_paths = shot_to_use.get('image_paths', [])
        existing_basenames = {os.path.basename(p) for p in existing_paths}
        
        import glob
        recovered_variations = []
        for pattern in [f"shot_{shot_index:03d}_then_*.png", f"shot_{shot_index:03d}_now_*.png"]:
            for filepath in glob.glob(os.path.join(images_dir, pattern)):
                if os.path.basename(filepath) not in existing_basenames:
                    recovered_variations.append(filepath)
                    logger.info(f"Recovery: found missing variation {os.path.basename(filepath)}")
        
        if recovered_variations:
            if 'image_paths' not in shot_to_use:
                shot_to_use['image_paths'] = []
            for v in recovered_variations:
                if v not in shot_to_use['image_paths']:
                    shot_to_use['image_paths'].append(v)
            self.project_manager.update_shot_metadata(project_id, {'image_paths': shot_to_use['image_paths']}, shot_id=shot_id)

        # Generate NOW image
        if image_variant in ["now", "both"]:
            if not shot_to_use.get('now_image_generated') or force:
                try:
                    # Preserve old NOW image
                    old_now_path = shot_to_use.get('now_image_path')
                    if old_now_path:
                        if 'image_paths' not in shot_to_use:
                            shot_to_use['image_paths'] = []
                        if old_now_path not in shot_to_use['image_paths']:
                            shot_to_use['image_paths'].append(old_now_path)
                            self.project_manager.update_shot_metadata(project_id, {'image_paths': shot_to_use['image_paths']}, shot_id=shot_id)

                    now_prompt = prompt_override if prompt_override and prompt_override.strip() else shot_to_use.get('now_image_prompt', '')
                    if set_prompt:
                        # Helper to append with proper spacing
                        def append_set(p, s):
                            if not s: return p
                            if not p: return s
                            return f"{p}. {s}" if not p.strip().endswith('.') else f"{p} {s}"
                        now_prompt = append_set(now_prompt, set_prompt)
                    
                    next_version = self._get_next_image_version(images_dir, shot_index, "now")
                    image_filename = f"shot_{shot_index:03d}_now_{next_version:03d}.png"
                    image_path = os.path.join(images_dir, image_filename)
                    now_seed = 1 if next_version == 1 else seed

                    self._mark_queue_item_active(project_id, shot_index, GenerationType.NOW_IMAGE)
                    manager.broadcast_sync(project_id, {
                        "type": "progress", "project_id": project_id, "shot_index": shot_index, "shot_id": shot_id,
                        "generation_type": "now_image", "progress": 0
                    })

                    now_workflow = image_workflow
                    now_reference_to_use = []
                    if actual_mode in ["geminiweb", "gemini"]:
                        if then_reference: now_reference_to_use.append(config.resolve_path(then_reference))
                        if now_reference: now_reference_to_use.append(config.resolve_path(now_reference))
                        if not now_reference_to_use: now_reference_to_use = None
                    elif now_reference and actual_mode == "comfyui":
                        if not now_workflow or now_workflow == "flux":
                            now_workflow = "flux_ipadapter_now"

                    result_path = await asyncio.to_thread(
                        self._generate_single_image, project_id, {**shot_to_use, 'image_prompt': now_prompt},
                        image_mode, now_workflow, now_seed, None, project_title, "now", now_reference_to_use, GenerationType.NOW_IMAGE,
                        gemini_mode=gemini_mode
                    )

                    shot_to_use['now_image_generated'] = True
                    shot_to_use['now_image_path'] = self._get_relative_path(result_path)
                    results['now'] = shot_to_use['now_image_path']

                    if 'image_paths' not in shot_to_use:
                        shot_to_use['image_paths'] = []
                    if shot_to_use['now_image_path'] not in shot_to_use['image_paths']:
                        shot_to_use['image_paths'].append(shot_to_use['now_image_path'])

                    self.project_manager.update_shot_metadata(project_id, {
                        'now_image_generated': True,
                        'now_image_path': shot_to_use['now_image_path'],
                        'image_paths': shot_to_use['image_paths']
                    }, shot_id=shot_id)

                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.NOW_IMAGE)
                    manager.broadcast_sync(project_id, {
                        "type": "completed", "project_id": project_id, "shot_index": shot_index, "shot_id": shot_id, "generation_type": "now_image"
                    })
                except Exception as e:
                    logger.error(f"Error generating NOW image for shot {shot_index}: {e}")
                    self._mark_queue_item_failed(project_id, shot_index, GenerationType.NOW_IMAGE, str(e))
                    manager.broadcast_sync(project_id, {
                        "type": "cancelled", "project_id": project_id, "shot_index": shot_index, "shot_id": shot_id, "generation_type": "now_image", "error": str(e)
                    })
                    if image_variant == "now": raise
            else:
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.NOW_IMAGE)

        # Generate THEN image
        if image_variant in ["then", "both"]:
            if not shot_to_use.get('then_image_generated') or force:
                try:
                    # DECISION: For 'Then vs now Actor Face' agent, we don't require or use NOW image
                    is_actor_face = self._is_actor_face_agent(project_id)
                    current_now = shot_to_use.get('now_image_path')
                    
                    if not is_actor_face and not current_now:
                        logger.info(f"NOW image missing for shot {shot_index}. Auto-generating NOW image first.")
                        # Call self recursively with variant="now" to ensure it's generated
                        # We use force=True to ensure it's actually generated since we're here because it's missing
                        await self._regenerate_flfi2v_images(
                            project_id, shot_index, shot_to_use, story, True, 
                            image_mode, image_workflow, seed, project_title, "now",
                            shot_id=shot_id, gemini_mode=gemini_mode
                        )
                        # Refresh shot data after recursive call
                        shots = self.project_manager.get_shots(project_id)
                        for s in shots:
                            if s.get('id') == shot_id:
                                shot_to_use = s
                                break
                        current_now = shot_to_use.get('now_image_path')
                        if not current_now:
                            raise ValueError(f"Failed to auto-generate NOW image for shot {shot_index}")

                    old_then_path = shot_to_use.get('then_image_path')
                    if old_then_path:
                        if 'image_paths' not in shot_to_use:
                            shot_to_use['image_paths'] = []
                        if old_then_path not in shot_to_use['image_paths']:
                            shot_to_use['image_paths'].append(old_then_path)
                            self.project_manager.update_shot_metadata(project_id, {'image_paths': shot_to_use['image_paths']}, shot_id=shot_id)

                    then_prompt = prompt_override if prompt_override and prompt_override.strip() else shot_to_use.get('then_image_prompt', '')
                    # Note: per user request, background (set_prompt) is NOT added to THEN prompts

                    next_version = self._get_next_image_version(images_dir, shot_index, "then")
                    
                    # Special logic for Gemini Edit prompts
                    active_prompt_override = prompt_override
                    if active_prompt_override and active_prompt_override == shot_to_use.get('then_image_prompt'):
                        active_prompt_override = None

                    self._mark_queue_item_active(project_id, shot_index, GenerationType.THEN_IMAGE)
                    manager.broadcast_sync(project_id, {
                        "type": "progress", "project_id": project_id, "shot_index": shot_index, "shot_id": shot_id,
                        "generation_type": "then_image", "progress": 0
                    })

                    then_workflow = image_workflow
                    
                    # For Actor Face agent, we don't use 'now' as reference
                    then_reference_to_use = []
                    if not is_actor_face and current_now:
                        then_reference_to_use.append(config.resolve_path(current_now))
                    
                    if actual_mode in ["geminiweb", "gemini"] and then_reference:
                        then_reference_to_use.append(config.resolve_path(then_reference))
                        logger.info(f"Added character reference for THEN generation: {then_reference}")
                    
                    if actual_mode == "comfyui":
                        if not then_workflow or then_workflow == "flux":
                            then_workflow = "flux_ipadapter_then"

                    result_path = await asyncio.to_thread(
                        self._generate_single_image, project_id, {**shot_to_use, 'image_prompt': then_prompt},
                        image_mode, then_workflow, seed, active_prompt_override, project_title, "then", then_reference_to_use, GenerationType.THEN_IMAGE,
                        gemini_mode=gemini_mode
                    )

                    shot_to_use['then_image_generated'] = True
                    shot_to_use['then_image_path'] = self._get_relative_path(result_path)
                    results['then'] = shot_to_use['then_image_path']

                    if 'image_paths' not in shot_to_use:
                        shot_to_use['image_paths'] = []
                    if shot_to_use['then_image_path'] not in shot_to_use['image_paths']:
                        shot_to_use['image_paths'].append(shot_to_use['then_image_path'])
                    
                    self.project_manager.update_shot_metadata(project_id, {
                        'then_image_generated': True,
                        'then_image_path': shot_to_use['then_image_path'],
                        'image_paths': shot_to_use['image_paths']
                    }, shot_id=shot_id)

                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.THEN_IMAGE)
                    manager.broadcast_sync(project_id, {
                        "type": "completed", "project_id": project_id, "shot_index": shot_index, "shot_id": shot_id, "generation_type": "then_image"
                    })
                except Exception as e:
                    logger.error(f"Error generating THEN image for shot {shot_index}: {e}")
                    self._mark_queue_item_failed(project_id, shot_index, GenerationType.THEN_IMAGE, str(e))
                    manager.broadcast_sync(project_id, {
                        "type": "cancelled", "project_id": project_id, "shot_index": shot_index, "shot_id": shot_id, "generation_type": "then_image", "error": str(e)
                    })
                    if image_variant == "then": raise
            else:
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.THEN_IMAGE)

        # Update standard image_path to NOW (for backward compatibility)
        if shot_to_use.get('now_image_path'):
            self.project_manager.update_shot_metadata(project_id, {
                'image_path': shot_to_use['now_image_path'],
                'image_generated': True
            }, shot_id=shot_id)

        logger.info(f"FLFI2V shot {shot_index} images regenerated: {results}")
        return results

    def _get_relative_path(self, absolute_path: str) -> str:
        """Convert absolute path to relative path from output directory"""
        import config
        abs_output = getattr(config, 'ABS_OUTPUT_DIR', '')
        if abs_output and absolute_path.startswith(abs_output):
            # Get the path after ABS_OUTPUT_DIR
            rel_path = absolute_path[len(abs_output):].lstrip(os.sep).replace(os.sep, '/')
            # Ensure it starts with 'output/' for getMediaUrl compatibility
            # Remove any leading slashes to avoid double slashes
            rel_path = rel_path.lstrip('/')
            if not rel_path.startswith('output/'):
                rel_path = f'output/{rel_path}'
            return rel_path
    async def regenerate_shot_video(
        self, project_id: str, shot_index: int, force: bool = False,
        video_mode: Optional[str] = None, video_workflow: Optional[str] = None,
        project_title: Optional[str] = None, video_variant: str = None,
        append_image_prompt: Optional[str] = None, draft_low_res_video: bool = False,
        prompt_id_callback=None, existing_prompt_id=None,
        shot_id: str = None, prompt_override: Optional[str] = None,
        resolution: Optional[str] = None, gemini_mode: Optional[str] = None
    ) -> str:
        """
        Regenerate video for a single shot

        Args:
            project_id: Project identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if video exists
            video_mode: Override generation mode
            video_workflow: Override workflow
            project_title: Optional title for Gemini Web chat persistence
            video_variant: For FLFI2V shots, which variant to generate ("meeting", "departure", or "both")

        Returns:
            Path to generated video (or dict with "meeting"/"departure" keys for FLFI2V)
        """
        try:
            # Load shots and story
            shots = self.project_manager.get_shots(project_id)
            story = self.project_manager.get_story(project_id)

            # Find the shot - prefer ID if provided
            shot = None
            if shot_id:
                for s in shots:
                    if s.get('id') == shot_id:
                        shot = s
                        # Update index for logs/variants if it moved
                        shot_index = s.get('index', shot_index)
                        break
            
            if not shot:
                if 1 <= shot_index <= len(shots):
                    shot = shots[shot_index - 1]
                    shot_id = shot.get('id')
                else:
                    raise ValueError(f"Shot {shot_index} (ID={shot_id}) not found")
            project_type = story.get('project_type', 1) if story else 1

            # Handle FLFI2V shots
            if shot.get('is_flfi2v') and project_type == 2:
                results = await self._regenerate_flfi2v_videos(
                    project_id, shot_index, shot, force,
                    video_mode, video_workflow, project_title, video_variant,
                    draft_low_res_video=draft_low_res_video,
                    shot_id=shot_id, prompt_override=prompt_override,
                    resolution=resolution, gemini_mode=gemini_mode
                )
                # Return the meeting video path for backward compatibility
                # (UI will use meeting_video_path/departure_video_path for FLFI2V shots)
                return results.get('meeting') if isinstance(results, dict) else results

            # Standard documentary mode (existing code)
            # Check if image exists
            if not shot.get('image_generated', False) or not shot.get('image_path'):
                raise ValueError(f"Shot {shot_index} has no image, cannot generate video")

            # Check if already exists and not forcing
            if not force and shot.get('video_rendered', False):
                logger.info(f"Shot {shot_index} already has video, skipping")
                return shot.get('video_path')

            # Preserve old video_path in video_paths before regenerating
            old_video_path = shot.get('video_path')
            if old_video_path:
                if 'video_paths' not in shot:
                    shot['video_paths'] = []
                if old_video_path not in shot['video_paths']:
                    shot['video_paths'].append(old_video_path)
                    # Save updated video_paths immediately
                    self.project_manager.update_shot_metadata(project_id, {'video_paths': shot['video_paths']}, shot_id=shot_id)

            # Generate video for single shot
            logger.info(f"Regenerating video for shot {shot_index} using mode {video_mode or 'default'}")

            # Broadcast initial 0% so UI resets from any stale progress
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "progress": 0
            })

            # Since _generate_single_video is async def, await it directly!
            # (Was incorrectly using asyncio.to_thread before)
            video_path = await self._generate_single_video(
                project_id,
                shot,
                video_mode,
                video_workflow,
                project_title,
                append_image_prompt,
                draft_low_res_video=draft_low_res_video,
                prompt_id_callback=prompt_id_callback,
                existing_prompt_id=existing_prompt_id,
                prompt_override=prompt_override,
                resolution=resolution,
                gemini_mode=gemini_mode
            )

            # Mark as rendered safely
            self.project_manager.mark_video_rendered(project_id, shot_index, video_path, shot_id=shot_id)

            # Mark queue item as completed
            self._mark_queue_item_completed(project_id, shot_index, GenerationType.VIDEO)

            # Broadcast completion to clear progress on frontend
            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "video"
            })

            logger.info(f"Shot {shot_index} video regenerated: {video_path}")
            return video_path

        except Exception as e:
            logger.error(f"Error regenerating shot {shot_index} video: {e}")
            # Broadcast cancelled event to clear loading state in UI
            manager.broadcast_sync(project_id, {
                "type": "cancelled",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id')
            })
            raise



    async def generate_soundfx(
        self, project_id: str, shot_index: int, force: bool = False
    ) -> str:
        """
        Generate sound effects for a shot's video using MMAudio ComfyUI workflow.

        Args:
            project_id: Project identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if sound FX already exists

        Returns:
            Path to generated video with sound effects
        """
        try:
            shots = self.project_manager.get_shots(project_id)

            if shot_index < 1 or shot_index > len(shots):
                raise ValueError(f"Shot {shot_index} not found")

            shot = shots[shot_index - 1]

            # Check if video exists
            video_path = shot.get('video_path')
            if not video_path:
                raise ValueError(f"Shot {shot_index} has no video, cannot generate sound FX")

            # Check if already exists and not forcing
            if not force and shot.get('soundfx_generated', False):
                logger.info(f"Shot {shot_index} already has sound FX, skipping")
                return shot.get('soundfx_path')

            logger.info(f"Generating sound FX for shot {shot_index}")

            # Mark queue item as active
            self._mark_queue_item_active(project_id, shot_index, GenerationType.SOUNDFX)

            # Broadcast initial 0% progress
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "soundfx",
                "progress": 0
            })

            # Run in thread pool to avoid blocking
            soundfx_path = await asyncio.to_thread(
                self._generate_soundfx_comfyui,
                project_id,
                shot
            )

            # Update shot with soundfx path atomically
            self.project_manager.update_shot_metadata(
                project_id, 
                {
                    'soundfx_path': self.project_manager.relativize_path(soundfx_path),
                    'soundfx_generated': True
                }, 
                shot_id=shot.get('id'), 
                shot_index=shot_index
            )

            # Mark queue item as completed
            self._mark_queue_item_completed(project_id, shot_index, GenerationType.SOUNDFX)

            # Broadcast completion
            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "soundfx"
            })

            logger.info(f"Shot {shot_index} sound FX generated: {soundfx_path}")
            return soundfx_path

        except Exception as e:
            logger.error(f"Error generating sound FX for shot {shot_index}: {e}")
            # Mark queue item as failed
            self._mark_queue_item_failed(project_id, shot_index, GenerationType.SOUNDFX, str(e))
            # Broadcast cancelled event to clear loading state
            manager.broadcast_sync(project_id, {
                "type": "cancelled",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shots[shot_index - 1].get('id') if shot_index <= len(shots) else None,
                "generation_type": "soundfx",
                "error": str(e)
            })
            raise

    def _generate_soundfx_comfyui(self, project_id: str, shot: Dict[str, Any]) -> str:
        """Generate sound effects for a shot video using MMAudio ComfyUI workflow (synchronous).

        Loads the workflow/soundfx/mmaudio.json template, uploads the shot video
        to ComfyUI, sets the prompt, submits, waits, and copies the output.
        """
        import shutil
        import config
        import requests as http_requests
        from core.comfy_client import submit, wait_for_prompt_completion_with_progress, get_output_file_path

        shot_index = shot['index']
        videos_dir = self.project_manager.get_videos_dir(project_id)
        os.makedirs(videos_dir, exist_ok=True)

        # Resolve video path
        video_rel_path = shot.get('video_path', '')
        video_abs_path = config.resolve_path(video_rel_path)

        if not os.path.exists(video_abs_path):
            raise RuntimeError(f"Video file not found for shot {shot_index}: {video_abs_path}")

        # Upload video to ComfyUI input folder
        comfy_url = getattr(config, 'COMFY_URL', 'http://127.0.0.1:8188')
        video_filename = os.path.basename(video_abs_path)
        upload_url = f"{comfy_url}/upload/image"
        with open(video_abs_path, 'rb') as f:
            resp = http_requests.post(
                upload_url,
                files={"image": (video_filename, f, "video/mp4")},
                data={"subfolder": "", "type": "input"}
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to upload video to ComfyUI: {resp.text}")
        uploaded_name = resp.json().get('name', video_filename)
        logger.info(f"Uploaded video to ComfyUI input: {uploaded_name}")

        # Load mmaudio workflow template
        workflow_path = os.path.join(config.PROJECT_ROOT, 'workflow', 'soundfx', 'mmaudio.json')
        with open(workflow_path, 'r', encoding='utf-8') as f:
            wf = json.load(f)

        # Set inputs on the workflow nodes
        # Node 91: VHS_LoadVideo - set the video input
        if '91' in wf:
            wf['91']['inputs']['video'] = uploaded_name

        # Node 92: MMAudioSampler - set the prompt (use motion prompt as scene audio description)
        if '92' in wf:
            prompt_text = shot.get('motion_prompt', '')
            wf['92']['inputs']['prompt'] = prompt_text

        # Node 97: VHS_VideoCombine - set filename prefix
        if '97' in wf:
            wf['97']['inputs']['filename_prefix'] = f"soundfx_{shot_index:03d}"

        # Submit to ComfyUI
        result = submit(wf)
        prompt_id = result.get('prompt_id')
        if not prompt_id:
            raise RuntimeError(f"No prompt_id returned for sound FX shot {shot_index}")

        logger.info(f"Sound FX submitted for shot {shot_index}: prompt_id={prompt_id}")

        last_reported_progress = -1

        def on_step_progress(current, total):
            nonlocal last_reported_progress
            # Check for cancellation
            if project_id in self.cancelled_shots and shot_index in self.cancelled_shots[project_id]:
                raise InterruptedError(f"Shot {shot_index} sound FX was cancelled")
            if project_id in self.cancelled_projects:
                raise InterruptedError(f"Project {project_id} was cancelled")

            progress = int((current / total) * 100) if total > 0 else 0
            if progress == last_reported_progress:
                return
            last_reported_progress = progress

            self._update_queue_item_progress(project_id, shot_index, GenerationType.SOUNDFX, progress)

            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": "soundfx",
                "progress": progress
            })

        # Wait for completion with progress callback
        wait_result = wait_for_prompt_completion_with_progress(
            prompt_id,
            progress_callback=on_step_progress,
            timeout=getattr(config, 'VIDEO_RENDER_TIMEOUT', 1800)
        )

        if not wait_result.get('success'):
            raise RuntimeError(f"Sound FX generation failed for shot {shot_index}: {wait_result.get('error')}")

        # Get output files
        outputs = wait_result.get('outputs', [])
        video_outputs = [o for o in outputs if o['type'] == 'video']

        if not video_outputs:
            raise RuntimeError(f"No video output for sound FX shot {shot_index}")

        # Copy output to project folder
        video_info = video_outputs[0]
        base_name, ext = os.path.splitext(video_filename)
        sfx_filename = f"{base_name}_sfx{ext}"
        sfx_save_path = os.path.join(videos_dir, sfx_filename)

        # Extraction of filename from video_info dict
        source_filename = video_info.get('filename') if isinstance(video_info, dict) else video_info
        source_subfolder = video_info.get('subfolder') if isinstance(video_info, dict) else None
        
        logger.debug(f"[SOUNDFX] Resolving output path: filename={source_filename}, subfolder={source_subfolder}")
        source_path = get_output_file_path(source_filename, project_id, subfolder=source_subfolder)
        
        if not isinstance(source_path, str):
            logger.error(f"[SOUNDFX] source_path is NOT a string: {type(source_path)}")
            if hasattr(source_path, '__await__'):
                logger.error("[SOUNDFX] CRITICAL: source_path is a coroutine! get_output_file_path might be async.")

        if os.path.exists(source_path):
            shutil.copy2(source_path, sfx_save_path)
            logger.info(f"Sound FX video copied: {sfx_filename} ({os.path.getsize(sfx_save_path):,} bytes)")
            return sfx_save_path
        else:
            raise RuntimeError(f"Sound FX source file not found: {source_path}")

    def _find_next_shot_for_departure(self, current_shot: dict, all_shots: list, story: dict) -> dict:
        """
        Find next shot for departure video with cross-scene and circular support.

        Transition Rules:
        1. Within scene: next shot in same scene
        2. Cross scene: first shot of next scene (at last shot of scene)
        3. Circular: first shot of first scene (at last shot of last scene)

        Args:
            current_shot: The current shot dict
            all_shots: List of all shot dicts
            story: Story dict with scenes array

        Returns:
            Dict with keys: next_shot, transition_type, last_frame_image, description
        """
        current_scene_id = current_shot.get('scene_id')
        scenes = story.get('scenes', [])

        # Debug logging
        logger.info(f"[DEPARTURE] Finding next shot for departure - Shot {current_shot.get('index')}, scene_id={current_scene_id}")

        # Group shots by scene_id
        shots_by_scene = {}
        for shot in all_shots:
            sid = shot.get('scene_id', 0)
            if sid not in shots_by_scene:
                shots_by_scene[sid] = []
            shots_by_scene[sid].append(shot)

        logger.info(f"[DEPARTURE] Shots by scene: {[(sid, len(shots)) for sid, shots in shots_by_scene.items()]}")

        # Sort shots within each scene by order_in_scene, then index
        for sid in shots_by_scene:
            shots_by_scene[sid].sort(key=lambda s: (s.get('order_in_scene', 0), s.get('index', 0)))

        current_scene_shots = shots_by_scene.get(current_scene_id, [])
        logger.info(f"[DEPARTURE] Current scene ({current_scene_id}) has {len(current_scene_shots)} shots")

        # Group shots by scene_id
        shots_by_scene = {}
        for shot in all_shots:
            sid = shot.get('scene_id', 0)
            if sid not in shots_by_scene:
                shots_by_scene[sid] = []
            shots_by_scene[sid].append(shot)

        # Sort shots within each scene by order_in_scene, then index
        for sid in shots_by_scene:
            shots_by_scene[sid].sort(key=lambda s: (s.get('order_in_scene', 0), s.get('index', 0)))

        current_scene_shots = shots_by_scene.get(current_scene_id, [])

        # Find current position
        current_id = current_shot.get('id')
        current_pos = next((i for i, s in enumerate(current_scene_shots) if s.get('id') == current_id), 0)

        # Rule 1: Within scene transition
        if current_pos < len(current_scene_shots) - 1:
            next_shot = current_scene_shots[current_pos + 1]
            then_image = next_shot.get('then_image_path')

            if then_image:
                current_char_name = current_shot.get('character_name', f'Shot {current_shot.get("index")}')
                next_char_name = next_shot.get('character_name', f'Shot {next_shot.get("index")}')
                scene_name = current_shot.get('scene_name', f'Scene {current_scene_id}')
                logger.info(f"[DEPARTURE] WITHIN-SCENE: shot {current_shot.get('index')} -> shot {next_shot.get('index')}")
                # For within-scene departure, use THEN image (traveling to past era of next character)
                return {
                    'next_shot': next_shot,
                    'transition_type': 'within_scene',
                    'last_frame_image': then_image,
                    'description': f'Within {scene_name}: {current_char_name} -> {next_char_name}'
                }
            else:
                # Shot exists but no THEN image - this is an error
                error_msg = f"THEN image not generated for shot {next_shot.get('index')} ({next_shot.get('character_name')}). Please generate THEN images first."
                logger.error(f"[DEPARTURE] {error_msg}")
                raise ValueError(error_msg)

        # Rule 2: Cross-scene transition
        # Find current scene's index in scenes array
        current_scene_index = None
        for i, sc in enumerate(scenes):
            if sc.get('scene_id') == current_scene_id:
                current_scene_index = i
                break

        # Debug logging
        logger.info(f"[DEPARTURE] Current shot {current_shot.get('index')}: scene_id={current_scene_id}, current_scene_index={current_scene_index}")
        scene_list = [f"{i}: scene_id={sc.get('scene_id')} ({sc.get('scene_name')})" for i, sc in enumerate(scenes)]
        logger.info(f"[DEPARTURE] Available scenes: {scene_list}")
        logger.info(f"[DEPARTURE] Total scenes: {len(scenes)}")

        # Check subsequent scenes for valid shots with THEN images
        if current_scene_index is not None:
            current_scene_name = current_shot.get('scene_name', f'Scene {current_scene_id}')
            current_char_name = current_shot.get('character_name', f'Shot {current_shot.get("index")}')

            # Loop through all subsequent scenes
            for offset in range(1, len(scenes) - current_scene_index):
                next_scene_index = current_scene_index + offset
                if next_scene_index >= len(scenes):
                    break

                next_scene = scenes[next_scene_index]
                next_scene_id = next_scene.get('scene_id')
                next_scene_name = next_scene.get('scene_name', f'Scene {next_scene_id}')
                next_scene_shots = shots_by_scene.get(next_scene_id, [])

                logger.info(f"[DEPARTURE] Checking scene {next_scene_index}: scene_id={next_scene_id}, name={next_scene_name}, shots_count={len(next_scene_shots)}")

                if next_scene_shots:
                    next_shot = next_scene_shots[0]
                    then_image = next_shot.get('then_image_path')

                    if then_image:
                        next_char_name = next_shot.get('character_name', f'Shot {next_shot.get("index")}')
                        # Found a scene with a valid THEN image
                        logger.info(f"[DEPARTURE] CROSS-SCENE: Using scene {next_scene_id}'s first shot (shot {next_shot.get('index')}) THEN image")
                        return {
                            'next_shot': next_shot,
                            'transition_type': 'cross_scene',
                            'last_frame_image': then_image,
                            'description': f'Cross-scene: {current_scene_name} -> {next_scene_name} ({current_char_name} -> {next_char_name})'
                        }
                    else:
                        # Shot exists but no THEN image - this is an error
                        error_msg = f"THEN image not generated for shot {next_shot.get('index')} ({next_shot.get('character_name')}) in scene {next_scene_name}. Please generate THEN images first."
                        logger.error(f"[DEPARTURE] {error_msg}")
                        raise ValueError(error_msg)
                else:
                    logger.info(f"[DEPARTURE] Scene {next_scene_id} has no shots, checking next scene...")

            logger.warning(f"[DEPARTURE] No subsequent scenes with valid THEN images found, falling back to circular")
        else:
            logger.warning(f"[DEPARTURE] Cross-scene transition not available: current_scene_index={current_scene_index}, total_scenes={len(scenes)}")

        # Rule 3: Circular transition
        if scenes:
            current_scene_name = current_shot.get('scene_name', f'Scene {current_scene_id}')
            current_char_name = current_shot.get('character_name', f'Shot {current_shot.get("index")}')

            # Try to find first scene with valid THEN image
            for scene in scenes:
                first_scene_id = scene.get('scene_id', 0)
                first_scene_name = scene.get('scene_name', f'Scene {first_scene_id}')
                first_scene_shots = shots_by_scene.get(first_scene_id, [])

                if first_scene_shots:
                    first_shot = first_scene_shots[0]
                    then_image = first_shot.get('then_image_path')

                    if then_image:
                        first_char_name = first_shot.get('character_name', f'Shot {first_shot.get("index")}')
                        logger.info(f"[DEPARTURE] Using CIRCULAR transition to scene {first_scene_id} ({first_scene_name})")
                        return {
                            'next_shot': first_shot,
                            'transition_type': 'circular',
                            'last_frame_image': then_image,
                            'description': f'Circular loop: {current_scene_name} -> {first_scene_name} ({current_char_name} -> {first_char_name})'
                        }
                    else:
                        # Shot exists but no THEN image - this is an error
                        error_msg = f"THEN image not generated for shot {first_shot.get('index')} ({first_shot.get('character_name')}) in scene {first_scene_name}. Please generate THEN images first."
                        logger.error(f"[DEPARTURE] {error_msg}")
                        raise ValueError(error_msg)
                else:
                    logger.info(f"[DEPARTURE] Scene {first_scene_id} has no shots, checking next scene...")

        # Fallback: return current shot
        logger.warning(f"[DEPARTURE] Using FALLBACK: current shot's NOW image")
        return {
            'next_shot': current_shot,
            'transition_type': 'fallback',
            'last_frame_image': current_shot.get('now_image_path') or current_shot.get('image_path'),
            'description': 'Fallback: using current shot'
        }

    async def _regenerate_flfi2v_videos(
        self, project_id: str, shot_index: int, shot: dict,
        force: bool, video_mode: Optional[str], video_workflow: Optional[str],
        project_title: Optional[str], video_variant: str, draft_low_res_video: bool = False,
        shot_id: str = None, prompt_override: Optional[str] = None,
        resolution: Optional[str] = None, gemini_mode: Optional[str] = None
    ) -> dict:
        """Regenerate meeting and/or departure videos for FLFI2V shot"""
        shots = self.project_manager.get_shots(project_id)
        results = {}

        # Default to both if not specified
        if not video_variant:
            video_variant = "both"

        # Check if we have both images
        if not shots[shot_index - 1].get('then_image_path') or not shots[shot_index - 1].get('now_image_path'):
            raise ValueError(f"FLFI2V shot {shot_index} requires both THEN and NOW images")

        # Use FLFI2V workflow by default
        if not video_workflow:
            video_workflow = "wan22_flfi2v"

        # ── Recovery scan: ensure all existing variation files are tracked ──
        videos_dir = self.project_manager.get_videos_dir(project_id)
        os.makedirs(videos_dir, exist_ok=True)
        
        current_shot = shots[shot_index - 1]
        existing_paths = current_shot.get('video_paths', [])
        existing_basenames = {os.path.basename(p) for p in existing_paths}
        
        recovered_variations = []
        for pattern in [f"shot_{shot_index:03d}_meeting_*.mp4", f"shot_{shot_index:03d}_departure_*.mp4"]:
            for filepath in glob.glob(os.path.join(videos_dir, pattern)):
                if os.path.basename(filepath) not in existing_basenames:
                    recovered_variations.append(filepath)
                    logger.info(f"Video Recovery: found missing variation {os.path.basename(filepath)}")
        
        if recovered_variations:
            if 'video_paths' not in current_shot:
                current_shot['video_paths'] = []
            for v in recovered_variations:
                rel_v = self._get_relative_path(v)
                if rel_v not in current_shot['video_paths']:
                    current_shot['video_paths'].append(rel_v)
            self.project_manager.update_shot_metadata(project_id, {'video_paths': current_shot['video_paths']}, shot_id=shot_id)

        # Generate meeting video
        if video_variant in ["meeting", "both"]:
            # Prompt fallback: use override if provided, then meeting_video_prompt OR motion_prompt
            meeting_prompt = prompt_override or shot.get('meeting_video_prompt') or shot.get('motion_prompt')
            logger.info(f"FLFI2V shot {shot_index} Meeting Resolved Prompt: {meeting_prompt}")
            
            if meeting_prompt and (not current_shot.get('meeting_video_rendered') or force):
                try:
                    # Preserve old meeting video before generating new one
                    old_meeting_path = current_shot.get('meeting_video_path')
                    if old_meeting_path:
                        if 'video_paths' not in current_shot:
                            current_shot['video_paths'] = []
                        if old_meeting_path not in current_shot['video_paths']:
                            current_shot['video_paths'].append(old_meeting_path)

                    next_version = self._get_next_video_version(
                        self.project_manager.get_videos_dir(project_id), shot_index, "meeting"
                    )
                    video_filename = f"shot_{shot_index:03d}_meeting_{next_version:03d}.mp4"

                    # Use seed=1 for first meeting video
                    meeting_seed = 1 if next_version == 1 else None
                    if next_version == 1:
                        logger.info(f"FLFI2V shot {shot_index} meeting video using fixed seed: 1")

                    # Mark MEETING_VIDEO queue item as active
                    self._mark_queue_item_active(project_id, shot_index, GenerationType.MEETING_VIDEO)

                    # Broadcast progress
                    manager.broadcast_sync(project_id, {
                        "type": "progress",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot_id or shot.get('id'),
                        "generation_type": "meeting_video",
                        "progress": 0
                    })

                    # Generate (passing the effective prompt)
                    # We create a temporary shot dict with the effective prompt to make sure _generate_flfi2v_video picks it up
                    temp_shot = shot.copy()
                    temp_shot['meeting_video_prompt'] = meeting_prompt

                    result_path = await asyncio.to_thread(
                        self._generate_flfi2v_video,
                        project_id,
                        temp_shot,
                        "meeting",
                        video_mode,
                        video_workflow,
                        project_title,
                        video_filename,
                        meeting_seed,
                        None,  # last_frame_image_path
                        GenerationType.MEETING_VIDEO,  # generation_type for queue tracking
                        draft_low_res_video=draft_low_res_video,
                        prompt_override=prompt_override,
                        resolution=resolution,
                        gemini_mode=gemini_mode
                    )

                    current_shot['meeting_video_rendered'] = True
                    current_shot['meeting_video_path'] = self._get_relative_path(result_path)
                    results['meeting'] = current_shot['meeting_video_path']

                    # Append to general video_paths for variations tracking
                    if 'video_paths' not in current_shot:
                        current_shot['video_paths'] = []
                    if current_shot['meeting_video_path'] not in current_shot['video_paths']:
                        current_shot['video_paths'].append(current_shot['meeting_video_path'])


                    # Mark MEETING_VIDEO queue item as completed
                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.MEETING_VIDEO)

                    # Broadcast completion
                    manager.broadcast_sync(project_id, {
                        "type": "completed",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot_id or shot.get('id'),
                        "generation_type": "meeting_video"
                    })
                except Exception as e:
                    logger.error(f"Error generating meeting video for shot {shot_index}: {e}")
                    # Mark MEETING_VIDEO queue item as failed
                    self._mark_queue_item_failed(project_id, shot_index, GenerationType.MEETING_VIDEO, str(e))

                    # Broadcast error
                    manager.broadcast_sync(project_id, {
                        "type": "cancelled",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot_id or shot.get('id'),
                        "generation_type": "meeting_video",
                        "error": str(e)
                    })
                    # Continue to departure video if "both" was requested
                    if video_variant == "meeting":
                        raise
            else:
                logger.info(f"FLFI2V shot {shot_index} meeting video already rendered or missing prompt, skipping and marking completed")
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.MEETING_VIDEO)

        # Generate departure video
        if video_variant in ["departure", "both"]:
            # Prompt fallback: use override if provided, then departure_video_prompt OR motion_prompt
            departure_prompt = prompt_override or shot.get('departure_video_prompt') or shot.get('motion_prompt')
            logger.info(f"FLFI2V shot {shot_index} Departure Resolved Prompt: {departure_prompt}")
            
            if departure_prompt and (not current_shot.get('departure_video_rendered') or force):
                try:
                    # Preserve old departure video before generating new one
                    old_departure_path = current_shot.get('departure_video_path')
                    if old_departure_path:
                        if 'video_paths' not in current_shot:
                            current_shot['video_paths'] = []
                        if old_departure_path not in current_shot['video_paths']:
                            current_shot['video_paths'].append(old_departure_path)

                    next_version = self._get_next_video_version(
                        self.project_manager.get_videos_dir(project_id), shot_index, "departure"
                    )
                    video_filename = f"shot_{shot_index:03d}_departure_{next_version:03d}.mp4"

                    # Use seed=1 for first departure video
                    departure_seed = 1 if next_version == 1 else None
                    if next_version == 1:
                        logger.info(f"FLFI2V shot {shot_index} departure video using fixed seed: 1")

                    # Find next shot for departure video using intelligent transition algorithm
                    story = self.project_manager.get_story(project_id)
                    transition_result = self._find_next_shot_for_departure(shot, shots, story)
                    last_frame_image = transition_result['last_frame_image']

                    logger.info(f"Departure transition: {transition_result['transition_type']}")
                    logger.info(f"  -> {transition_result.get('description', '')}")

                    # Mark DEPARTURE_VIDEO queue item as active
                    self._mark_queue_item_active(project_id, shot_index, GenerationType.DEPARTURE_VIDEO)

                    # Broadcast progress
                    manager.broadcast_sync(project_id, {
                        "type": "progress",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot_id or shot.get('id'),
                        "generation_type": "departure_video",
                        "progress": 50 if video_variant == "both" else 0
                    })

                    # Generate (passing effective prompt)
                    temp_shot = shot.copy()
                    temp_shot['departure_video_prompt'] = departure_prompt

                    result_path = await asyncio.to_thread(
                        self._generate_flfi2v_video,
                        project_id,
                        temp_shot,
                        "departure",
                        video_mode,
                        video_workflow,
                        project_title,
                        video_filename,
                        departure_seed,
                        last_frame_image,
                        GenerationType.DEPARTURE_VIDEO,  # generation_type for queue tracking
                        draft_low_res_video=draft_low_res_video,
                        prompt_override=prompt_override,
                        resolution=resolution,
                        gemini_mode=gemini_mode
                    )

                    current_shot['departure_video_rendered'] = True
                    current_shot['departure_video_path'] = self._get_relative_path(result_path)
                    results['departure'] = current_shot['departure_video_path']

                    # Append to general video_paths for variations tracking
                    if 'video_paths' not in current_shot:
                        current_shot['video_paths'] = []
                    if current_shot['departure_video_path'] not in current_shot['video_paths']:
                        current_shot['video_paths'].append(current_shot['departure_video_path'])


                    # Mark DEPARTURE_VIDEO queue item as completed
                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.DEPARTURE_VIDEO)

                    # Broadcast completion
                    manager.broadcast_sync(project_id, {
                        "type": "completed",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot_id or shot.get('id'),
                        "generation_type": "departure_video"
                    })
                except Exception as e:
                    logger.error(f"Error generating departure video for shot {shot_index}: {e}")
                    # Mark DEPARTURE_VIDEO queue item as failed
                    self._mark_queue_item_failed(project_id, shot_index, GenerationType.DEPARTURE_VIDEO, str(e))

                    # Broadcast error
                    manager.broadcast_sync(project_id, {
                        "type": "cancelled",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot_id or shot.get('id'),
                        "generation_type": "departure_video",
                        "error": str(e)
                    })
                    # Only raise if this was the only variant requested
                    if video_variant == "departure":
                        raise

            
            else:
                logger.info(f"FLFI2V shot {shot_index} departure video already rendered or missing prompt, skipping and marking completed")
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.DEPARTURE_VIDEO)
        
        # Update shot metadata atomically
        updates = {
            'video_path': results.get('meeting'),
            'video_rendered': 'meeting' in results,
            'meeting_video_path': results.get('meeting'),
            'meeting_video_rendered': 'meeting' in results,
            'departure_video_path': results.get('departure'),
            'departure_video_rendered': 'departure' in results
        }
        # Filter out None values to avoid overwriting existing data if a variant failed
        updates = {k: v for k, v in updates.items() if v is not None}
        
        self.project_manager.update_shot_metadata(project_id, updates, shot_id=shot_id or shot.get('id'), shot_index=shot_index)

        logger.info(f"FLFI2V shot {shot_index} videos regenerated: {results}")
        return results

    async def generate_scene_background(
        self, project_id: str, scene_id: int, set_prompt: str,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        workflow: Optional[str] = None,
        image_mode: Optional[str] = None
    ) -> str:
        """
        Generate background image for a scene using AI

        Args:
            project_id: Project identifier
            scene_id: Scene ID in the story
            set_prompt: Background description prompt
            image_mode: Provider (comfyui, geminiweb, etc.)

        Returns:
            Path to generated background image
        """
        try:
            import config

            # Create backgrounds directory
            project_dir = self.project_manager.get_project_dir(project_id)
            backgrounds_dir = os.path.join(project_dir, "backgrounds")
            os.makedirs(backgrounds_dir, exist_ok=True)

            # Mark as active in queue
            self._mark_queue_item_active(project_id, None, GenerationType.BACKGROUND, scene_id=scene_id)

            # Broadcast 0% progress
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "scene_id": scene_id,
                "generation_type": "background",
                "step": "background_generation",
                "progress": 0
            })

            # Generate background using standard Flux workflow
            # Use override if provided, otherwise fallback to story set_prompt
            set_prompt = prompt if prompt else set_prompt # defined or story fallback
            actual_workflow = workflow if workflow else "flux"

            logger.info(f"Generating background for scene {scene_id} using prompt: {set_prompt[:60]}... (workflow: {actual_workflow}, mode: {image_mode})")

            result_path = await asyncio.to_thread(
                self._generate_single_image,
                project_id,
                {'image_prompt': set_prompt, 'index': scene_id},  # Use scene_id for indexing
                image_mode,  # Use the passed provider mode
                actual_workflow,
                seed, # Pass direct seed down to inherit first-time logic from _generate_single_image
                set_prompt,  # Use set_prompt directly
                None,  # No project title for backgrounds
                None,  # No variant
                None,  # No reference image for backgrounds
                GenerationType.BACKGROUND,
                backgrounds_dir,
                f"background_{scene_id:03d}_%03d.png"
            )
            if not result_path or not os.path.exists(result_path):
                raise RuntimeError(f"Failed to generate background for scene {scene_id}")

            # Convert to relative path
            relative_path = self._get_relative_path(result_path)

            # Load and update story
            story_path = os.path.join(project_dir, "story.json")
            with open(story_path, 'r', encoding='utf-8') as f:
                story_data = json.load(f)

            scenes = story_data.get('scenes', [])

            # Find scene by scene_id
            scene_found = False
            for i, scene in enumerate(scenes):
                if str(scene.get('scene_id')) == str(scene_id):
                    scenes[i]['background_image_path'] = relative_path
                    scenes[i]['background_generated'] = True
                    scenes[i]['background_is_generated'] = True  # AI-generated
                    scene_found = True
                    break

            if not scene_found:
                raise RuntimeError(f"Scene with scene_id {scene_id} not found in story.json")
            
            # Save story
            with open(story_path, 'w', encoding='utf-8') as f:
                json.dump(story_data, f, indent=4, ensure_ascii=False)

            # Mark as completed in queue
            self._mark_queue_item_completed(project_id, None, GenerationType.BACKGROUND, scene_id=scene_id)

            # Broadcast completion
            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "scene_id": scene_id,
                "generation_type": "background",
                "step": "background_generation",
                "background_image_path": relative_path
            })

            logger.info(f"Background generated for scene {scene_id}: {relative_path}")
            return relative_path

        except Exception as e:
            logger.error(f"Error generating background for scene {scene_id}: {e}")
            self._mark_queue_item_failed(project_id, None, GenerationType.BACKGROUND, str(e), scene_id=scene_id)
            manager.broadcast_sync(project_id, {
                "type": "error",
                "project_id": project_id,
                "scene_id": scene_id,
                "generation_type": "background",
                "message": str(e)
            })
            raise

    async def regenerate_scene_narration(
        self, project_id: str, scene_id: int,
        tts_method: Optional[str] = None,
        tts_workflow: Optional[str] = None,
        voice: Optional[str] = None
    ) -> str:
        """
        Regenerate narration for a single scene
        """
        from core.narration_generator import generate_scene_narration
        import json

        try:
            # Clear cancellation for this scene
            if project_id in self.cancelled_scenes and scene_id in self.cancelled_scenes[project_id]:
                self.cancelled_scenes[project_id].remove(scene_id)

            # Load story to get narration text
            project_dir = self.project_manager.get_project_dir(project_id)
            story_path = os.path.join(project_dir, "story.json")
            with open(story_path, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            
            scenes = story_data.get('scenes', [])
            if scene_id < 0 or scene_id >= len(scenes):
                raise ValueError(f"Scene index {scene_id} out of range")
            
            scene = scenes[scene_id]
            text = scene.get('narration', '')
            if not text:
                raise ValueError(f"Scene {scene_id} has no narration text")

            # Broadcast 0%
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "scene_id": scene_id,
                "step": "narration",
                "progress": 0
            })

            # Run generation
            # Note: generate_scene_narration is currently synchronous in the core
            # We'll wrap it in to_thread, but it doesn't support fine-grained progress yet
            # except for ComfyUI which could be extended. 
            # For now, we'll do 50% and 100% logic.
            
            result = await asyncio.to_thread(
                generate_scene_narration,
                project_id, scene_id, text, 
                tts_method, tts_workflow, voice
            )
            
            if result["status"] == "success":
                # Update story.json with the new path
                rel_path = result["rel_path"]
                scene['narration_path'] = rel_path
                if 'narration_paths' not in scene:
                    scene['narration_paths'] = []
                if rel_path not in scene['narration_paths']:
                    scene['narration_paths'].append(rel_path)
                
                with open(story_path, 'w', encoding='utf-8') as f:
                    json.dump(story_data, f, indent=4)
                
                # Broadcast completion
                manager.broadcast_sync(project_id, {
                    "type": "completed",
                    "project_id": project_id,
                    "scene_id": scene_id,
                    "step": "narration",
                    "narration_path": rel_path
                })
                
                return rel_path
            else:
                raise RuntimeError(result.get("message", "Narration generation failed"))

        except Exception as e:
            logger.error(f"Error generating narration for scene {scene_id}: {e}")
            manager.broadcast_sync(project_id, {
                "type": "error",
                "project_id": project_id,
                "scene_id": scene_id,
                "step": "narration",
                "message": str(e)
            })
            raise


    async def replan_shots(
        self,
        project_id: str,
        max_shots: Optional[int] = None,
        shots_agent: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Re-plan shots from story

        Args:
            project_id: Project identifier
            max_shots: Maximum shots to generate
            shots_agent: Shots agent to use

        Returns:
            List of shot dictionaries
        """
        try:
            # Load story
            project_dir = self.project_manager.get_project_dir(project_id)
            story_path = os.path.join(project_dir, "story.json")

            if not os.path.exists(story_path):
                raise ValueError("Story not found for this project")

            with open(story_path, 'r', encoding='utf-8') as f:
                story_json = f.read()

            # Plan shots
            logger.info(f"Re-planning shots for project {project_id}")

            # Load project meta to check type
            project_meta = self.project_manager.get_project(project_id)
            story_data = json.loads(story_json)
            
            # Check project type (1=Doc, 2=ThenVsNow, 3=Movie)
            p_type = project_meta.get('project_type')
            if p_type is None:
                p_type = story_data.get('project_type')
            
            # Type 2 is ThenVsNow (uses specialized local generator)
            is_then_vs_now = (p_type == ProjectType.THEN_VS_NOW or p_type == 2)
            
            # Type 3 is Movie (uses standard LLM planner)
            is_movie = (p_type == ProjectType.MOVIE or p_type == 3)

            if is_then_vs_now:
                logger.info(f"Detected ThenVsNow project for {project_id}, using specialized shot generator")
                from core.story_engine import generate_shots_from_then_vs_now_story
                shots = generate_shots_from_then_vs_now_story(story_data)
            elif is_movie:
                logger.info(f"Detected Movie project for {project_id}, using standard shot planner")
                # Run standard planner in thread pool to avoid blocking
                shots = await asyncio.to_thread(
                    plan_shots,
                    story_json,
                    max_shots=max_shots,
                    shots_agent=shots_agent
                )
            else:
                # Run standard planner in thread pool to avoid blocking
                shots = await asyncio.to_thread(
                    plan_shots,
                    story_json,
                    max_shots=max_shots,
                    shots_agent=shots_agent
                )

            # Save shots
            self.project_manager.save_shots(project_id, shots)

            logger.info(f"Re-planned {len(shots)} shots")
            return shots

        except Exception as e:
            logger.error(f"Error re-planning shots: {e}")
            raise

    async def generate_thumbnail(
        self, project_id: str, aspect_ratio: str = "16:9", force: bool = False,
        image_mode: str = None, image_workflow: str = None, seed: int = None,
        is_poster: bool = False
    ) -> str:
        """Enqueue a thumbnail generation task"""
        try:
            logger.info(f"Queueing {aspect_ratio} thumbnail for project {project_id}")
            
            queue_service = get_queue_service()
            
            # Check if project exists
            project_meta = self.project_manager.get_project(project_id)
            if not project_meta:
                raise ValueError(f"Project {project_id} not found")
                
            # Create queue item
            from web_ui.backend.models.queue import QueueItem, GenerationType
            
            item = QueueItem(
                item_id=f"thumbnail_{project_id}_{aspect_ratio.replace(':', '_')}_{uuid.uuid4().hex[:4]}",
                project_id=project_id,
                generation_type=GenerationType.THUMBNAIL,
                aspect_ratio=aspect_ratio,
                is_poster=is_poster,
                image_mode=image_mode,
                image_workflow=image_workflow,
                seed=seed,
                priority=50, # Thumbnails usually higher priority than shots
                project_title=project_meta.get('title', 'Project Thumbnail')
            )
            
            queue_service.add_items([item])
            self._ensure_queue_processor_started()
            
            return item.item_id
            
        except Exception as e:
            logger.error(f"Error queueing thumbnail: {e}")
            raise

    async def _process_thumbnail_generation(self, item: QueueItem):
        """Internal processor for enqueued thumbnail tasks"""
        project_id = item.project_id
        aspect_ratio = item.aspect_ratio or "16:9"
        is_poster = item.is_poster
        
        try:
            logger.info(f"Processing queued {aspect_ratio} thumbnail for project {project_id}")
            
            # Load project and story
            project_meta = self.project_manager.get_project(project_id)
            story = self.project_manager.get_story(project_id)
            
            prompt_key = f'poster_thumbnail_prompt_{aspect_ratio.replace(":", "_")}' if is_poster else f'thumbnail_prompt_{aspect_ratio.replace(":", "_")}'
            prompt = story.get(prompt_key)
            if not prompt:
                prompt = story.get('title', project_meta.get('idea', 'A cinematic thumbnail'))
                
            images_dir = self.project_manager.get_images_dir(project_id)
            os.makedirs(images_dir, exist_ok=True)
            
            prefix = "poster_thumbnail" if is_poster else "thumbnail"
            filename = f"{prefix}_{aspect_ratio.replace(':', '_')}.png"
            image_path = os.path.join(images_dir, filename)
            
            # Progress callback
            def on_step_progress(current, total):
                progress = int((current / total) * 100) if total > 0 else 0
                queue_service = get_queue_service()
                queue_service.update_progress(item.item_id, progress)
                
                # Also broadcast to project room
                manager.broadcast_sync(project_id, {
                    "type": "progress",
                    "project_id": project_id,
                    "step": "thumbnail",
                    "progress": progress
                })

            from core.image_generator import generate_image
            
            result_path = await asyncio.to_thread(
                generate_image,
                prompt=prompt,
                output_path=image_path,
                aspect_ratio=aspect_ratio,
                mode=item.image_mode,
                workflow_name=item.image_workflow,
                seed=item.seed,
                step_progress_callback=on_step_progress
            )
            
            if not result_path:
                raise ValueError("Image generation failed")

            # Update final metadata safely
            def modify_meta(meta):
                key = 'poster_thumbnail_url' if is_poster else 'thumbnail_url'
                key_916 = 'poster_thumbnail_url_9_16' if is_poster else 'thumbnail_url_9_16'
                relative_url = f"/api/projects/{project_id}/images/{filename}"
                
                if aspect_ratio == "16:9":
                    meta[key] = relative_url
                elif aspect_ratio == "9:16":
                    meta[key_916] = relative_url
                elif aspect_ratio == "21:8":
                    meta['thumbnail_url_21_8'] = relative_url
            
            self.project_manager.update_meta_safely(project_id, modify_meta)

            # Mark as completed in queue
            queue_service = get_queue_service()
            queue_service.mark_completed(item.item_id)
            
            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "step": "thumbnail"
            })
            
        except Exception as e:
            logger.error(f"Error processing thumbnail task {item.item_id}: {e}")
            queue_service = get_queue_service()
            queue_service.mark_failed(item.item_id, str(e))
            raise
            
    def _get_next_image_version(self, images_dir: str, shot_index: int, variant: str = None, generation_type: GenerationType = None) -> int:
        """Find the next available version number for a shot image.

        Scans for existing files like shot_001_001.png, shot_001_002.png, etc.
        For FLFI2V variants, scans for shot_001_then_001.png or shot_001_now_001.png
        Returns the next version number (starting from 1).
        """
        if generation_type == GenerationType.BACKGROUND:
            pattern = os.path.join(images_dir, f"background_{shot_index:03d}_*.png")
            version_re = re.compile(rf"background_{shot_index:03d}_(\d+)\.png$")
        elif variant:
            pattern = os.path.join(images_dir, f"shot_{shot_index:03d}_{variant}_*.png")
            version_re = re.compile(rf"shot_{shot_index:03d}_{variant}_(\d+)\.png$")
        else:
            pattern = os.path.join(images_dir, f"shot_{shot_index:03d}_*.png")
            version_re = re.compile(rf"shot_{shot_index:03d}_(\d+)\.png$")

        existing_files = glob.glob(pattern) if os.path.exists(images_dir) else []

        max_version = 0

        for filepath in existing_files:
            filename = os.path.basename(filepath)
            match = version_re.match(filename)
            if match:
                version = int(match.group(1))
                max_version = max(max_version, version)

        return max_version + 1

    def _get_next_video_version(self, videos_dir: str, shot_index: int, variant: str = None) -> int:
        """Find the next available version number for a shot video.

        Scans for existing files like shot_001_001.mp4, shot_001_002.mp4, etc.
        For FLFI2V variants, scans for shot_001_meeting_001.mp4 or shot_001_departure_001.mp4
        Returns the next version number (starting from 1).
        """
        if variant:
            pattern = os.path.join(videos_dir, f"shot_{shot_index:03d}_{variant}_*.mp4")
            version_re = re.compile(rf"shot_{shot_index:03d}_{variant}_(\d+)\.mp4$")
        else:
            pattern = os.path.join(videos_dir, f"shot_{shot_index:03d}_*.mp4")
            version_re = re.compile(rf"shot_{shot_index:03d}_(\d+)\.mp4$")

        existing_files = glob.glob(pattern) if os.path.exists(videos_dir) else []

        max_version = 0

        for filepath in existing_files:
            filename = os.path.basename(filepath)
            match = version_re.match(filename)
            if match:
                version = int(match.group(1))
                max_version = max(max_version, version)

        return max_version + 1

    def _generate_single_image(
        self, project_id: str, shot: Dict[str, Any],
        image_mode: Optional[str], workflow_name: Optional[str],
        seed: Optional[int] = None, prompt_override: Optional[str] = None,
        project_title: Optional[str] = None, image_variant: str = None,
        reference_images: Optional[List[str]] = None,
        generation_type: GenerationType = None,
        gemini_mode: Optional[str] = None
    ) -> str:
        """Generate image for a single shot (synchronous)

        Args:
        """
        print(f"[DEBUG] entering _generate_single_image for item {project_id}")
        logger.info(f"entering _generate_single_image for item {project_id}")
        from core.image_generator import generate_image
        import config

        project_dir = self.project_manager.get_project_dir(project_id)
        images_dir = os.path.join(project_dir, "images")
        actual_dir = images_dir
        os.makedirs(actual_dir, exist_ok=True)

        shot_index = shot['index']
        # Use override prompt if provided, otherwise fall back to saved shot prompt
        prompt = prompt_override.strip() if prompt_override and prompt_override.strip() else shot.get('image_prompt', '')

        # Load project to get aspect_ratio
        project_meta = self.project_manager.load_project(project_id)
        aspect_ratio = project_meta.get('aspect_ratio', '16:9')

        # Generate versioned filename with optional variant suffix
        next_version = self._get_next_image_version(actual_dir, shot_index, image_variant, generation_type)
        
        if image_variant:
            image_filename = f"shot_{shot_index:03d}_{image_variant}_{next_version:03d}.png"
        else:
            image_filename = f"shot_{shot_index:03d}_{next_version:03d}.png"
        image_path = os.path.join(actual_dir, image_filename)

        # 1st time generation for a shot uses seed 1, next generations use random
        # If specific seed provided, use it
        if seed is None:
            seed = 1 if next_version == 1 else random.randint(0, 2**32 - 1)

        last_reported_progress = -1

        # Progress callback to bridge ComfyUI steps to our WebSocket
        def on_step_progress(current, total):
            nonlocal last_reported_progress
            # Check for cancellation
            if project_id in self.cancelled_shots and shot_index in self.cancelled_shots[project_id]:
                raise InterruptedError(f"Shot {shot_index} was cancelled")
            if project_id in self.cancelled_projects:
                raise InterruptedError(f"Project {project_id} was cancelled")

            progress = int((current / total) * 100) if total > 0 else 0
            
            if progress == last_reported_progress:
                return
            last_reported_progress = progress

            # Update queue item progress for the correct generation type
            queue_gen_type = generation_type or GenerationType.IMAGE
            
            if queue_gen_type == GenerationType.BACKGROUND:
                self._update_queue_item_progress(project_id, None, queue_gen_type, progress, scene_id=shot_index)
            else:
                self._update_queue_item_progress(project_id, shot_index, queue_gen_type, progress)

            # Prepare broadcast data
            broadcast_data = {
                "type": "progress",
                "project_id": project_id,
                "generation_type": queue_gen_type.value,
                "progress": progress
            }
            
            if queue_gen_type == GenerationType.BACKGROUND:
                broadcast_data["scene_id"] = shot_index
            else:
                broadcast_data["shot_index"] = shot_index
                broadcast_data["shot_id"] = shot.get('id')

            manager.broadcast_sync(project_id, broadcast_data)

        # Generate using the core image_generator module
        # This correctly handles both Gemini and ComfyUI modes and workflows
        result_path = generate_image(
            prompt=prompt,
            output_path=image_path,
            aspect_ratio=aspect_ratio,  # Use project's aspect ratio
            mode=image_mode, # If None, uses config.IMAGE_GENERATION_MODE
            seed=seed,
            workflow_name=workflow_name, # If None, uses config.IMAGE_WORKFLOW
            step_progress_callback=on_step_progress,
            project_title=project_title,
            reference_images=reference_images,  # Pass reference image for IP-Adapter
            gemini_mode=gemini_mode
        )

        if not result_path or not os.path.exists(result_path):
            raise RuntimeError(f"Failed to generate image for shot {shot_index}")

        return result_path

    async def _generate_single_video(self, project_id: str, shot: Dict[str, Any],
                               video_mode: Optional[str] = None,
                               workflow_path: Optional[str] = None,
                               project_title: Optional[str] = None,
                               append_image_prompt: Optional[str] = None,
                               draft_low_res_video: bool = False,
                               prompt_id_callback=None,
                               existing_prompt_id=None,
                               prompt_override: Optional[str] = None,
                               resolution: Optional[str] = None,
                               gemini_mode: Optional[str] = None) -> str:
        """Generate video for a single shot (synchronous)"""
        import shutil
        import config
        from core.video_regenerator import generate_unique_video_filename

        videos_dir = self.project_manager.get_videos_dir(project_id)
        os.makedirs(videos_dir, exist_ok=True)

        shot_index = shot['index']
        mode = video_mode or getattr(config, 'VIDEO_GENERATION_MODE', 'comfyui')
        
        # Avoid modifying the original reference
        shot = shot.copy()

        # Resolve prompt append choice
        append_image_choice = append_image_prompt
        if append_image_choice is None:
            if getattr(config, 'APPEND_IMAGE_TO_MOTION_PROMPT', False):
                append_image_choice = getattr(config, 'IMAGE_PROMPT_APPEND_POSITION', 'end')
            else:
                append_image_choice = 'none'

        motion_prompt = prompt_override.strip() if prompt_override and prompt_override.strip() else shot.get('motion_prompt', '')
        image_prompt = shot.get('image_prompt', '')

        if append_image_choice != "none" and image_prompt:
            if append_image_choice == "start":
                shot['motion_prompt'] = f"{image_prompt}, {motion_prompt}"
            elif append_image_choice == "end":
                shot['motion_prompt'] = f"{motion_prompt}, {image_prompt}"
            logger.info(f"Appended image prompt to motion prompt for shot {shot_index} ({append_image_choice})")

        if mode == 'geminiweb':
            from core.geminiweb_video_generator import generate_video_geminiweb
            
            video_filename, video_save_path = generate_unique_video_filename(videos_dir, shot_index)
            motion_prompt = shot.get('motion_prompt', "Animate this image realistically")
            rel_image_path = shot.get('image_path', '')
            
            # Resolve image path
            abs_image_path = os.path.join(getattr(config, 'PROJECT_ROOT', ''), 'output', rel_image_path.replace("/", os.sep))
            if not os.path.exists(abs_image_path):
                 abs_image_path = os.path.join(getattr(config, 'ABS_OUTPUT_DIR', ''), rel_image_path.replace("/", os.sep))
            
            # Broadcast 50% for Gemini Web (linear isn't possible)
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "progress": 50
            })
            
            video_res = generate_video_geminiweb(
                image_path=abs_image_path,
                motion_prompt=motion_prompt,
                output_path=video_save_path,
                project_title=project_title,
                gemini_mode=gemini_mode
            )
            
            if not video_res:
                raise RuntimeError(f"Gemini Web video generation failed for shot {shot_index}")
                
            self.project_manager.mark_video_rendered(project_id, shot_index, video_save_path)
            return video_save_path
        else:
            from core.prompt_compiler import load_workflow, compile_workflow
            from core.comfy_client import submit, wait_for_prompt_completion_with_progress, get_output_file_path

            # Load project to get aspect_ratio
            project_meta = self.project_manager.load_project(project_id)
            aspect_ratio = project_meta.get('aspect_ratio', '16:9')

            # Determine workflow path and resolve alias if needed
            if not workflow_path:
                workflow_path = getattr(config, 'VIDEO_WORKFLOW', 'wan22')

            # If workflow_path is an alias in VIDEO_WORKFLOWS, resolve it to the actual file path
            video_workflows = getattr(config, 'VIDEO_WORKFLOWS', {})
            workflow_name = workflow_path  # Store the original alias/name
            workflow_config = None
            if workflow_path in video_workflows:
                workflow_config = video_workflows[workflow_path]
                workflow_path = workflow_config.get('workflow_path', workflow_path)
                workflow_description = workflow_config.get('description', 'No description')
                logger.info(f"Using video workflow: {workflow_name} ({workflow_description})")
            else:
                logger.info(f"Using video workflow: {workflow_path}")

            # Load and compile workflow for this shot
            shot_length = getattr(config, 'DEFAULT_SHOT_LENGTH', 5)

            # DEEP RESUME CHECK
            skip_submit = False
            if existing_prompt_id:
                logger.info(f"Deep Resume: Attempting to reconnect to ComfyUI video prompt '{existing_prompt_id}'")
                try:
                    from core.comfy_client import http_session
                    h_resp = http_session.get(f"{config.COMFY_URL}/history/{existing_prompt_id}", timeout=5)
                    q_resp = http_session.get(f"{config.COMFY_URL}/queue", timeout=5)
                    is_valid = False
                    if h_resp.status_code == 200 and existing_prompt_id in h_resp.json():
                        is_valid = True
                    elif q_resp.status_code == 200:
                        q_data = q_resp.json()
                        for q_item in q_data.get("queue_running", []) + q_data.get("queue_pending", []):
                            if len(q_item) > 1 and q_item[1] == existing_prompt_id:
                                is_valid = True
                                break
                    if is_valid:
                        logger.info(f"Deep Resume: Prompt '{existing_prompt_id}' is still active! Re-attaching...")
                        prompt_id = existing_prompt_id
                        skip_submit = True
                    else:
                        logger.info(f"Deep Resume: Prompt '{existing_prompt_id}' not found. Submitting new generation.")
                except Exception as e:
                    logger.warning(f"Deep Resume validation failed: {e}. Submitting new generation.")

            if not skip_submit:
                template = load_workflow(workflow_path, video_length_seconds=shot_length, aspect_ratio=aspect_ratio, draft_low_res_video=draft_low_res_video, workflow_config=workflow_config, resolution=resolution)
                wf = compile_workflow(template, shot, video_length_seconds=shot_length, workflow_config=workflow_config)

                # Submit to ComfyUI
                result = submit(wf)
                prompt_id = result.get('prompt_id')
                if not prompt_id:
                    raise RuntimeError(f"No prompt_id returned for shot {shot_index}")
                logger.info(f"Video submitted for shot {shot_index}: prompt_id={prompt_id}")
                
                if prompt_id_callback:
                    try:
                        prompt_id_callback(prompt_id)
                    except Exception as e:
                        logger.error(f"Error in prompt_id_callback: {e}")

            last_reported_progress = -1

            # Progress callback to bridge ComfyUI steps to our WebSocket
            def on_step_progress(current, total):
                nonlocal last_reported_progress
                # Check for cancellation
                if project_id in self.cancelled_shots and shot_index in self.cancelled_shots[project_id]:
                    raise InterruptedError(f"Shot {shot_index} was cancelled")
                if project_id in self.cancelled_projects:
                    raise InterruptedError(f"Project {project_id} was cancelled")

                progress = int((current / total) * 100) if total > 0 else 0
                
                if progress == last_reported_progress:
                    return
                last_reported_progress = progress

                # Update queue item progress
                self._update_queue_item_progress(project_id, shot_index, GenerationType.VIDEO, progress)

                manager.broadcast_sync(project_id, {
                    "type": "progress",
                    "project_id": project_id,
                    "shot_index": shot_index,
                    "shot_id": shot.get('id'),
                    "generation_type": "video",
                    "progress": progress
                })

            # Wait for completion with progress updates
            wait_result = wait_for_prompt_completion_with_progress(
                prompt_id, 
                progress_callback=on_step_progress,
                timeout=getattr(config, 'VIDEO_RENDER_TIMEOUT', 1800)
            )

            if not wait_result.get('success'):
                raise RuntimeError(f"Video render failed for shot {shot_index}: {wait_result.get('error')}")

            # Get output files
            outputs = wait_result.get('outputs', [])
            video_outputs = [o for o in outputs if o['type'] == 'video']

            if not video_outputs:
                raise RuntimeError(f"No video output for shot {shot_index}")

            # Copy video to project folder
            video_info = video_outputs[0]
            video_filename, video_save_path = generate_unique_video_filename(videos_dir, shot_index)

            # Extraction of filename from video_info dict
            source_filename = video_info.get('filename') if isinstance(video_info, dict) else video_info
            source_subfolder = video_info.get('subfolder') if isinstance(video_info, dict) else None
            
            logger.debug(f"[VIDEO] Resolving output path: filename={source_filename}, subfolder={source_subfolder}")
            source_path = get_output_file_path(source_filename, project_id, subfolder=source_subfolder)
            
            if not isinstance(source_path, str):
                 logger.error(f"[VIDEO] source_path is NOT a string: {type(source_path)}")

            if os.path.exists(source_path):
                shutil.copy2(source_path, video_save_path)
                logger.info(f"Video copied: {video_filename} ({os.path.getsize(video_save_path):,} bytes)")

                # Mark as rendered
                self.project_manager.mark_video_rendered(project_id, shot_index, video_save_path)
                return video_save_path
            else:
                raise RuntimeError(f"Video source file not found: {source_path}")

    def _generate_flfi2v_video(
        self, project_id: str, shot: Dict[str, Any],
        variant: str, video_mode: Optional[str],
        workflow_name: Optional[str], project_title: Optional[str],
        video_filename: str, seed: Optional[int] = None,
        last_frame_image_path: Optional[str] = None,
        generation_type: GenerationType = None,
        draft_low_res_video: bool = False,
        prompt_override: Optional[str] = None,
        resolution: Optional[str] = None,
        gemini_mode: Optional[str] = None
    ) -> str:
        """Generate FLFI2V video for a single shot (synchronous)

        Args:
            variant: "meeting" or "departure"
            video_filename: The filename to save the video as
            seed: Optional seed for deterministic generation (use 1 for first video)
            last_frame_image_path: For departure videos, the next character's NOW image or scene image
            generation_type: The generation type (MEETING_VIDEO, DEPARTURE_VIDEO) for queue tracking

        Video logic:
        - Meeting: THEN image (first frame) + NOW image (last frame)
        - Departure: NOW image (first frame) + next character's NOW image or scene image (last frame)
        """
        import shutil
        import copy
        import config
        from core.prompt_compiler import load_workflow
        from core.comfy_client import submit, wait_for_prompt_completion_with_progress, get_output_file_path

        videos_dir = self.project_manager.get_videos_dir(project_id)
        os.makedirs(videos_dir, exist_ok=True)
        video_save_path = os.path.join(videos_dir, video_filename)

        shot_index = shot['index']

        # Load project to get aspect_ratio
        project_meta = self.project_manager.load_project(project_id)
        aspect_ratio = project_meta.get('aspect_ratio', '16:9')

        # Load FLFI2V workflow
        workflow_config = config.VIDEO_WORKFLOWS.get(workflow_name, {})
        workflow_path = workflow_config.get('workflow_path')

        if not workflow_path:
            raise RuntimeError(f"FLFI2V workflow {workflow_name} not found in VIDEO_WORKFLOWS")

        workflow_description = workflow_config.get('description', 'No description')
        logger.info(f"Using FLFI2V video workflow: {workflow_name} ({workflow_description})")

        template = load_workflow(workflow_path, aspect_ratio=aspect_ratio, draft_low_res_video=draft_low_res_video, workflow_config=workflow_config, resolution=resolution)
        wf = copy.deepcopy(template)

        # Get node IDs from config (with smart handles for missing keys)
        load_first_node_id = workflow_config.get('load_image_first_node_id') or workflow_config.get('load_image_node_id') or '128'
        load_last_node_id = workflow_config.get('load_image_last_node_id') or '151'
        motion_prompt_node_id = workflow_config.get('motion_prompt_node_id') or '93'
        seed_node_id = workflow_config.get('seed_node_id') or '142'

        # Set seed if provided (for first video generation)
        if seed is not None and seed_node_id in wf:
            wf[seed_node_id]["inputs"]["value"] = seed
            logger.info(f"FLFI2V video generation using seed: {seed}")

        # Inject images based on variant
        if variant == "meeting":
            # Meeting: THEN image (first frame) + NOW image (last frame)
            then_image = shot.get('then_image_path') or shot.get('image_path')
            if then_image:
                then_path = config.resolve_path(then_image).replace('\\', '/')
                if load_first_node_id in wf:
                    wf[load_first_node_id]["inputs"]["image"] = then_path
                    logger.info(f"Meeting video first frame: {then_image}")

            now_image = shot.get('now_image_path') or shot.get('image_path')
            if now_image:
                now_path = config.resolve_path(now_image).replace('\\', '/')
                if load_last_node_id in wf:
                    wf[load_last_node_id]["inputs"]["image"] = now_path
                    logger.info(f"Meeting video last frame: {now_image}")

        elif variant == "departure":
            # Departure: NOW image (first frame) + next character's NOW image or scene image (last frame)
            now_image = shot.get('now_image_path') or shot.get('image_path')
            if now_image:
                now_path = config.resolve_path(now_image).replace('\\', '/')
                if load_first_node_id in wf:
                    wf[load_first_node_id]["inputs"]["image"] = now_path
                    logger.info(f"Departure video first frame: {now_image}")

            if last_frame_image_path:
                # Use next character's NOW image or scene image
                last_frame_path = config.resolve_path(last_frame_image_path).replace('\\', '/')
                if load_last_node_id in wf:
                    wf[load_last_node_id]["inputs"]["image"] = last_frame_path
                    logger.info(f"Departure video last frame: {last_frame_image_path}")
            else:
                # Fallback to NOW image if no last frame provided
                if shot.get('now_image_path'):
                    now_path = config.resolve_path(shot['now_image_path']).replace('\\', '/')
                    if load_last_node_id in wf:
                        wf[load_last_node_id]["inputs"]["image"] = now_path
                        logger.warning(f"Departure video last frame: Using current character's NOW image (fallback)")

        # Inject motion prompt based on variant
        if prompt_override and prompt_override.strip():
            motion_prompt = prompt_override.strip()
            logger.info(f"FLFI2V video using prompt_override: {motion_prompt[:50]}...")
        else:
            motion_prompt = shot.get(
                'departure_video_prompt' if variant == 'departure' else 'meeting_video_prompt',
                "Animate this scene"
            )

        if motion_prompt_node_id in wf:
            wf[motion_prompt_node_id]["inputs"]["text"] = motion_prompt

        # Submit to ComfyUI
        result = submit(wf)
        prompt_id = result.get('prompt_id')
        if not prompt_id:
            raise RuntimeError(f"No prompt_id returned for FLFI2V shot {shot_index}")

        logger.info(f"FLFI2V video submitted for shot {shot_index} ({variant}): prompt_id={prompt_id}")

        last_reported_progress = -1

        # Progress callback
        def on_step_progress(current, total):
            nonlocal last_reported_progress
            if project_id in self.cancelled_shots and shot_index in self.cancelled_shots[project_id]:
                raise InterruptedError(f"Shot {shot_index} was cancelled")
            if project_id in self.cancelled_projects:
                raise InterruptedError(f"Project {project_id} was cancelled")

            progress = int((current / total) * 100) if total > 0 else 0
            
            if progress == last_reported_progress:
                return
            last_reported_progress = progress

            # Update queue item progress for the correct generation type
            queue_gen_type = generation_type or GenerationType.VIDEO
            self._update_queue_item_progress(project_id, shot_index, queue_gen_type, progress)

            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": queue_gen_type.value,
                "progress": progress
            })

        # Wait for completion
        wait_result = wait_for_prompt_completion_with_progress(
            prompt_id,
            progress_callback=on_step_progress,
            timeout=getattr(config, 'VIDEO_RENDER_TIMEOUT', 1800)
        )

        if not wait_result.get('success'):
            raise RuntimeError(f"FLFI2V video render failed for shot {shot_index}: {wait_result.get('error')}")

        # Get output files
        outputs = wait_result.get('outputs', [])
        video_outputs = [o for o in outputs if o['type'] == 'video']

        if not video_outputs:
            raise RuntimeError(f"No video output for FLFI2V shot {shot_index}")

        # Copy video to project folder
        video_info = video_outputs[0]
        
        # Extraction of filename from video_info dict
        source_filename = video_info.get('filename') if isinstance(video_info, dict) else video_info
        source_subfolder = video_info.get('subfolder') if isinstance(video_info, dict) else None
        
        logger.debug(f"[FLFI2V] Resolving output path: filename={source_filename}, subfolder={source_subfolder}")
        source_path = get_output_file_path(source_filename, project_id, subfolder=source_subfolder)

        if not isinstance(source_path, str):
            logger.error(f"[FLFI2V] source_path is NOT a string: {type(source_path)}")

        if os.path.exists(source_path):
            shutil.copy2(source_path, video_save_path)
            logger.info(f"FLFI2V video copied: {video_filename} ({os.path.getsize(video_save_path):,} bytes)")
            return video_save_path
        else:
            raise RuntimeError(f"FLFI2V video source file not found: {source_path}")


    def _is_actor_face_agent(self, project_id: str) -> bool:
        """Check if project uses the 'Then vs now Actor Face' agent"""
        try:
            meta = self.project_manager.get_project(project_id)
            agent = meta.get('story_agent', '')
            # Match against the exact agent name (likely includes the path)
            return "then_vs_now/then_vs_now_actor_faces" in agent
        except Exception as e:
            logger.error(f"Error checking agent for project {project_id}: {e}")
            return False


# Global singleton instance
_generation_service = None
_service_lock = threading.Lock()


def get_generation_service() -> GenerationService:
    """Get global GenerationService instance"""
    global _generation_service
    with _service_lock:
        if _generation_service is None:
            _generation_service = GenerationService()
        return _generation_service
