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

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.project_manager import ProjectManager
from core.image_generator import generate_images_for_shots
from core.shot_planner import plan_shots
from core.logger_config import get_logger
from web_ui.backend.websocket.manager import manager

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

        # Queue processor state
        self._queue_processor_running = False
        self._queue_processor_task = None # This is no longer used for the main loop, but might be for other tasks
        self._queue_processor_started = False
        self._queue_processor_thread: Optional[threading.Thread] = None # New thread object

    def _get_relative_path(self, path: str) -> str:
        """Convert absolute path to relative format using ProjectManager utility"""
        return self.project_manager._relativize_path(path)

    def _ensure_queue_processor_started(self):
        """Ensure background task is running"""
        # with open(r"c:\AI\ai_video_factory_v1\startup_debug.txt", "a") as f: f.write("[DEBUG] inside _ensure_queue_processor_started\n")

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

        with open(r"c:\AI\ai_video_factory_v1\startup_debug.txt", "a") as f: f.write("[DEBUG] loop: started\n")

        # Get concurrency limit
        limit = getattr(config, 'CONCURRENT_GENERATION_LIMIT', 2)
        semaphore = asyncio.Semaphore(limit)
        logger.info(f"Queue processor started with concurrency limit of {limit}")

        async def process_single_item(item: QueueItem):
            """Process a single queue item with semaphore control"""
            async with semaphore:
                try:
                    logger.info(f"Processing queue item {item.item_id}: {item.generation_type.value} for shot {item.shot_index}")
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

        # Track active tasks
        active_tasks = set()

        while self._queue_processor_running:
            try:
                # Get queue service
                queue_service = get_queue_service()

                # Check if queue is paused
                if queue_service.is_paused():
                    await asyncio.sleep(1)
                    continue

                # Clean up completed tasks
                active_tasks = {task for task in active_tasks if not task.done()}

                # Check if we've reached concurrency limit
                if len(active_tasks) >= limit:
                    await asyncio.sleep(0.5)
                    continue

                # Get next queued items (up to available slots)
                queued_items = queue_service.get_queue(status=QueueItemStatus.QUEUED)
                available_slots = limit - len(active_tasks)

                if not queued_items:
                    # No items to process, wait a bit
                    await asyncio.sleep(0.5)
                    continue

                # Start processing items (up to available slots)
                items_to_process = queued_items[:available_slots]
                for item in items_to_process:
                    task = asyncio.create_task(process_single_item(item))
                    active_tasks.add(task)

                # Small delay before checking for more items
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in queue processor loop: {e}")
                await asyncio.sleep(1)

        # Wait for remaining tasks to complete
        if active_tasks:
            logger.info(f"Waiting for {len(active_tasks)} active tasks to complete...")
            await asyncio.gather(*active_tasks, return_exceptions=True)

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
            project_meta = self.project_manager.get_project(item.project_id)
            project_title = project_meta.get('title', item.project_id) if project_meta else item.project_id

            logger.info(f"ABOUT TO AWAIT regenerate_shot_image for item {item.item_id}")
            print(f"[DEBUG] ABOUT TO AWAIT regenerate_shot_image for item {item.item_id}", flush=True)
            
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
                seed=item.seed
            )

            logger.info(f"Completed image generation for queue item {item.item_id}")
            print(f"[DEBUG] FINISHED AWAIT regenerate_shot_image for item {item.item_id}", flush=True)

        except Exception as e:
            logger.error(f"Error processing image generation for {item.item_id}: {e}")
            raise

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
            project_meta = self.project_manager.get_project(item.project_id)
            project_title = project_meta.get('title', item.project_id) if project_meta else item.project_id

            # Call regenerate_shot_video with overrides from the queue item
            await self.regenerate_shot_video(
                item.project_id,
                item.shot_index,
                force=True,
                video_mode=item.video_mode,
                video_workflow=item.video_workflow,
                project_title=project_title,
                video_variant=video_variant,
                append_image_prompt=item.append_image_prompt
            )

            logger.info(f"Completed video generation for queue item {item.item_id}")
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
        # TODO: Implement background generation
        logger.warning(f"Background generation not yet implemented for item {item.item_id}")
        raise NotImplementedError("Background generation not yet implemented")

    def cancel_project(self, project_id: str):
        """Mark a project as cancelled to halt background queue processing."""
        self.cancelled_projects.add(project_id)
        if project_id in self.queued_shots:
            self.queued_shots.pop(project_id)

        # Also cancel all queued items in QueueService
        queue_service = get_queue_service()
        queued_items = queue_service.get_queue(project_id=project_id)
        for item in queued_items:
            if item.status == QueueItemStatus.QUEUED:
                queue_service.mark_cancelled(item.item_id)

        logger.info(f"Marked project {project_id} as cancelled. Future queued items will be skipped.")

    def cancel_single_shot(self, project_id: str, shot_index: int):
        """Mark a single shot as cancelled to halt it from entering the queue."""
        if project_id not in self.cancelled_shots:
            self.cancelled_shots[project_id] = set()
        self.cancelled_shots[project_id].add(shot_index)
        if project_id in self.queued_shots and shot_index in self.queued_shots[project_id]:
            self.queued_shots[project_id].remove(shot_index)

        # Also cancel queued items in QueueService for this shot
        queue_service = get_queue_service()
        queued_items = queue_service.get_queue(project_id=project_id)
        for item in queued_items:
            if item.shot_index == shot_index and item.status == QueueItemStatus.QUEUED:
                queue_service.mark_cancelled(item.item_id)

        # If this is the currently actively generating shot, tell ComfyUI to stop
        if self.active_shots.get(project_id) == shot_index:
            from core.comfy_client import interrupt_generation
            logger.info(f"Shot {shot_index} is currently active. Sending interrupt to ComfyUI.")
            interrupt_generation()

        logger.info(f"Marked shot {shot_index} in project {project_id} as cancelled.")

    def cancel_scene_narration(self, project_id: str, scene_id: int):
        """Mark a scene narration as cancelled."""
        if project_id not in self.cancelled_scenes:
            self.cancelled_scenes[project_id] = set()
        self.cancelled_scenes[project_id].add(scene_id)
        if project_id in self.queued_scenes and scene_id in self.queued_scenes[project_id]:
            self.queued_scenes[project_id].remove(scene_id)
            
        # If this is the currently actively generating scene, tell ComfyUI to stop
        if self.active_scenes.get(project_id) == scene_id:
            from core.comfy_client import interrupt_generation
            logger.info(f"Scene {scene_id} is currently active. Sending interrupt to ComfyUI.")
            interrupt_generation()
            
        logger.info(f"Marked scene {scene_id} narration in project {project_id} as cancelled.")

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
        # Get project metadata for display
        project_meta = self.project_manager.get_project(project_id)
        project_title = project_meta.get('title', project_id) if project_meta else project_id

        # Extract shot details if available
        shot_id = shot.get('id') if shot else None
        scene_name = shot.get('scene_name') if shot else None
        character_name = shot.get('character_name') if shot else None

        # Check if FLFI2V
        is_flfi2v = shot.get('is_flfi2v', False) if shot else False

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
            prompt_override=getattr(request, 'prompt_override', None) if request else None,
            seed=getattr(request, 'seed', None) if request else None,
            image_mode=getattr(request, 'image_mode', None) if request else None,
            image_workflow=getattr(request, 'image_workflow', None) if request else None,
            video_mode=getattr(request, 'video_mode', None) if request else None,
            video_workflow=getattr(request, 'video_workflow', None) if request else None,
            image_variant=getattr(request, 'image_variant', None) if request else None,
            video_variant=getattr(request, 'video_variant', None) if request else None,
            append_image_prompt=getattr(request, 'append_image_prompt', None) if request else None
        )

    def _get_queue_item_id(
        self,
        project_id: str,
        shot_index: int,
        generation_type: GenerationType
    ) -> Optional[str]:
        """
        Get the queue item_id for a specific shot and generation type.

        Args:
            project_id: Project identifier
            shot_index: Shot index (1-based)
            generation_type: Type of generation

        Returns:
            Queue item ID or None if not found
        """
        queue_service = get_queue_service()
        queue_items = queue_service.get_queue(project_id=project_id)

        # Find matching queue item
        for item in queue_items:
            if (item.shot_index == shot_index and
                item.generation_type == generation_type and
                item.status in [QueueItemStatus.QUEUED, QueueItemStatus.ACTIVE]):
                return item.item_id

        return None

    def _mark_queue_item_active(
        self,
        project_id: str,
        shot_index: int,
        generation_type: GenerationType
    ):
        """Mark a queue item as active (started processing)."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type)
        if item_id:
            queue_service = get_queue_service()
            queue_service.mark_active(item_id)
            # Store active mapping for progress updates
            key = f"{project_id}:{shot_index}:{generation_type.value}"
            self.active_queue_items[key] = item_id
            logger.info(f"Marked queue item {item_id} as active ({generation_type.value}, shot {shot_index})")

    def _update_queue_item_progress(
        self,
        project_id: str,
        shot_index: int,
        generation_type: GenerationType,
        progress: int
    ):
        """Update progress for an active queue item."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type)
        if item_id:
            queue_service = get_queue_service()
            queue_service.update_progress(item_id, progress)
            logger.debug(f"Updated queue item {item_id} progress to {progress}%")

    def _mark_queue_item_completed(
        self,
        project_id: str,
        shot_index: int,
        generation_type: GenerationType,
        progress: int = 100
    ):
        """Mark a queue item as completed."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type)
        if item_id:
            queue_service = get_queue_service()
            queue_service.mark_completed(item_id, progress)
            # Remove from active tracking
            key = f"{project_id}:{shot_index}:{generation_type.value}"
            self.active_queue_items.pop(key, None)
            logger.info(f"Marked queue item {item_id} as completed ({generation_type.value}, shot {shot_index})")

    def _mark_queue_item_failed(
        self,
        project_id: str,
        shot_index: int,
        generation_type: GenerationType,
        error_message: str
    ):
        """Mark a queue item as failed."""
        item_id = self._get_queue_item_id(project_id, shot_index, generation_type)
        if item_id:
            queue_service = get_queue_service()
            queue_service.mark_failed(item_id, error_message)
            # Remove from active tracking
            key = f"{project_id}:{shot_index}:{generation_type.value}"
            self.active_queue_items.pop(key, None)
            logger.warning(f"Marked queue item {item_id} as failed: {error_message}")

    def add_single_shot_to_queue(
        self,
        project_id: str,
        shot_index: int,
        generation_type: GenerationType,
        request: Any
    ) -> list:
        """Add a single shot generation item to the background queue with overrides"""
        from web_ui.backend.services.queue_service import get_queue_service
        # Ensure queue processor is running
        self._ensure_queue_processor_started()

        shots = self.project_manager.get_shots(project_id)
        story = self.project_manager.get_story(project_id)
        shot = shots[shot_index - 1] if shot_index <= len(shots) else None

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
                if image_variant in ['then', 'both']:
                    items_to_add.append(self._create_queue_item(project_id, shot_index, GenerationType.THEN_IMAGE, shot, story, request))
                if image_variant in ['now', 'both']:
                    items_to_add.append(self._create_queue_item(project_id, shot_index, GenerationType.NOW_IMAGE, shot, story, request))
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

        queue_items = []
        for idx in request.shot_indices:
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

            logger.debug(f"Shot {idx}: force_images={force_images}, force_videos={force_videos}, image_generated={shot.get('image_generated')}, video_rendered={shot.get('video_rendered')}")

            # Create image queue item if regenerating images and not skipping
            if request.regenerate_images and not skip_images:
                # For FLFI2V shots, create separate items for THEN and NOW images
                if shot.get('is_flfi2v') and story.get('project_type') == 2:
                    # THEN image item
                    then_item = self._create_queue_item(
                        project_id, idx, GenerationType.THEN_IMAGE, shot, story, request=request
                    )
                    queue_items.append(then_item)
                    # NOW image item
                    now_item = self._create_queue_item(
                        project_id, idx, GenerationType.NOW_IMAGE, shot, story, request=request
                    )
                    queue_items.append(now_item)
                else:
                    # Standard image item
                    image_item = self._create_queue_item(
                        project_id, idx, GenerationType.IMAGE, shot, story, request=request
                    )
                    queue_items.append(image_item)

            # Create video queue item if regenerating videos and not skipping
            if request.regenerate_videos and not skip_videos:
                # For FLFI2V shots, create separate items for meeting and departure videos
                if shot.get('is_flfi2v') and story.get('project_type') == 2:
                    # Meeting video item
                    meeting_item = self._create_queue_item(
                        project_id, idx, GenerationType.MEETING_VIDEO, shot, story, request=request
                    )
                    queue_items.append(meeting_item)
                    # Departure video item
                    departure_item = self._create_queue_item(
                        project_id, idx, GenerationType.DEPARTURE_VIDEO, shot, story, request=request
                    )
                    queue_items.append(departure_item)
                else:
                    # Standard video item
                    video_item = self._create_queue_item(
                        project_id, idx, GenerationType.VIDEO, shot, story, request=request
                    )
                    queue_items.append(video_item)

        # Reorder items based on queue setting
        queue_setting = getattr(request, 'queue_setting', 'all_images_then_videos')
        if queue_setting == 'all_images_then_videos':
            logger.info(f"Reordering queue items for 'all_images_then_videos'")
            image_items = [item for item in queue_items if item.generation_type in [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE]]
            video_items = [item for item in queue_items if item.generation_type in [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO]]
            queue_items = image_items + video_items

        # Add all items to queue
        if queue_items:
            added_items = queue_service.add_items(queue_items)
            logger.info(f"Added {len(added_items)} items to queue for project {project_id}")

        # Also keep the old tracking for backward compatibility
        self.queued_shots[project_id] = set(request.shot_indices)

        logger.info(f"Added {len(queue_items)} items to queue for project {project_id}. Queue processor will handle generation.")

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
        project_title: Optional[str] = None, image_variant: str = None
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

            if shot_index < 1 or shot_index > len(shots):
                raise ValueError(f"Shot {shot_index} not found")

            shot = shots[shot_index - 1]
            project_type = story.get('project_type', 1) if story else 1

            # Handle FLFI2V shots
            if shot.get('is_flfi2v') and project_type == 2:
                results = await self._regenerate_flfi2v_images(
                    project_id, shot_index, shot, story, force,
                    image_mode, image_workflow, seed, project_title, image_variant
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
                if 'image_paths' not in shot:
                    shot['image_paths'] = []
                if old_image_path not in shot['image_paths']:
                    shot['image_paths'].append(old_image_path)
                    # Save updated image_paths immediately
                    self.project_manager._save_shots(project_id, shots)

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
                None  # No variant for standard shots
            )

            # Mark as generated
            self.project_manager.mark_image_generated(project_id, shot_index, image_path)

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
        seed: Optional[int], project_title: Optional[str], image_variant: str
    ) -> dict:
        """Regenerate THEN and/or NOW images for FLFI2V shot"""
        from web_ui.backend.models.story import ProjectType

        images_dir = self.project_manager.get_images_dir(project_id)
        os.makedirs(images_dir, exist_ok=True)

        scene_id = shot.get('scene_id', 0)
        scene = story['scenes'][scene_id] if scene_id < len(story.get('scenes', [])) else None
        set_prompt = scene.get('set_prompt', '') if scene else ''

        results = {}
        shots = self.project_manager.get_shots(project_id)

        # Get character reference images if available
        character_id = shot.get('character_id')
        then_reference = None
        now_reference = None

        if character_id and story.get('characters'):
            # Find character by matching character_id or index
            character = None
            for char in story['characters']:
                if str(char.get('scene_id', 0)) == str(character_id):
                    character = char
                    break

            if character:
                then_reference = character.get('then_reference_image_path')
                now_reference = character.get('now_reference_image_path')
                logger.info(f"Found reference images for character {character_id}: THEN={then_reference}, NOW={now_reference}")

        # Default to both if not specified
        if not image_variant:
            image_variant = "both"

        # Generate THEN image
        if image_variant in ["then", "both"]:
            if not shots[shot_index - 1].get('then_image_generated') or force:
                try:
                    # Preserve old THEN image before generating new one
                    old_then_path = shots[shot_index - 1].get('then_image_path')
                    if old_then_path:
                        if 'image_paths' not in shots[shot_index - 1]:
                            shots[shot_index - 1]['image_paths'] = []
                        if old_then_path not in shots[shot_index - 1]['image_paths']:
                            shots[shot_index - 1]['image_paths'].append(old_then_path)

                    print(f"[DEBUG] entering _regenerate_flfi2v_images THEN-block for shot {shot_index}")
                    logger.info(f"entering _regenerate_flfi2v_images THEN-block for shot {shot_index}")
                    then_prompt = shot.get('then_image_prompt', '')
                    if set_prompt:
                        then_prompt = f"{then_prompt}. Background: {set_prompt}"

                    next_version = self._get_next_image_version(images_dir, shot_index, "then")
                    image_filename = f"shot_{shot_index:03d}_then_{next_version:03d}.png"
                    image_path = os.path.join(images_dir, image_filename)

                    # Use seed=1 for first THEN image, otherwise use provided seed or None
                    then_seed = 1 if next_version == 1 else seed
                    if next_version == 1:
                        logger.info(f"FLFI2V shot {shot_index} THEN image using fixed seed: 1")

                    # Mark THEN_IMAGE queue item as active
                    self._mark_queue_item_active(project_id, shot_index, GenerationType.THEN_IMAGE)

                    # Broadcast progress
                    manager.broadcast_sync(project_id, {
                        "type": "progress",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
                        "generation_type": "then_image",
                        "progress": 0
                    })

                    # Determine workflow and reference for THEN
                    then_workflow = image_workflow
                    # Auto-switch to IP-Adapter workflow ONLY for ComfyUI mode with reference
                    actual_mode = image_mode or config.IMAGE_GENERATION_MODE
                    if then_reference and actual_mode == "comfyui":
                        if not then_workflow or then_workflow == "flux":
                            then_workflow = "flux_ipadapter_then"
                            logger.info(f"Using IP-Adapter workflow for THEN with reference: {then_reference}")

                    # Generate
                    result_path = await asyncio.to_thread(
                        self._generate_single_image,
                        project_id,
                        {**shot, 'image_prompt': then_prompt},
                        image_mode,
                        then_workflow,
                        then_seed,
                        None,  # No prompt override for FLFI2V
                        project_title,
                        "then",
                        then_reference,  # Pass THEN reference image
                        GenerationType.THEN_IMAGE  # Pass generation type for queue tracking
                    )

                    shots[shot_index - 1]['then_image_generated'] = True
                    shots[shot_index - 1]['then_image_path'] = self._get_relative_path(result_path)
                    results['then'] = shots[shot_index - 1]['then_image_path']

                    # Append to general image_paths for variations tracking
                    if 'image_paths' not in shots[shot_index - 1]:
                        shots[shot_index - 1]['image_paths'] = []
                    relative_path = shots[shot_index - 1]['then_image_path']
                    if relative_path not in shots[shot_index - 1]['image_paths']:
                        shots[shot_index - 1]['image_paths'].append(relative_path)

                    # Mark THEN_IMAGE queue item as completed
                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.THEN_IMAGE)

                    # Broadcast completion
                    manager.broadcast_sync(project_id, {
                        "type": "completed",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
                        "generation_type": "then_image"
                    })
                except Exception as e:
                    logger.error(f"Error generating THEN image for shot {shot_index}: {e}")
                    # Mark THEN_IMAGE queue item as failed
                    self._mark_queue_item_failed(project_id, shot_index, GenerationType.THEN_IMAGE, str(e))

                    # Broadcast error
                    manager.broadcast_sync(project_id, {
                        "type": "cancelled",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
                        "generation_type": "then_image",
                        "error": str(e)
                    })
                    # Continue to NOW image if "both" was requested
                    if image_variant == "then":
                        raise
            else:
                logger.info(f"FLFI2V shot {shot_index} THEN image already generated, skipping and marking completed")
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.THEN_IMAGE)

        # Generate NOW image
        if image_variant in ["now", "both"]:
            if not shots[shot_index - 1].get('now_image_generated') or force:
                try:
                    # Preserve old NOW image before generating new one
                    old_now_path = shots[shot_index - 1].get('now_image_path')
                    if old_now_path:
                        if 'image_paths' not in shots[shot_index - 1]:
                            shots[shot_index - 1]['image_paths'] = []
                        if old_now_path not in shots[shot_index - 1]['image_paths']:
                            shots[shot_index - 1]['image_paths'].append(old_now_path)

                    now_prompt = shot.get('now_image_prompt', '')
                    if set_prompt:
                        now_prompt = f"{now_prompt}. Background: {set_prompt}"

                    next_version = self._get_next_image_version(images_dir, shot_index, "now")
                    image_filename = f"shot_{shot_index:03d}_now_{next_version:03d}.png"
                    image_path = os.path.join(images_dir, image_filename)

                    # Use seed=1 for first NOW image, otherwise use provided seed or None
                    now_seed = 1 if next_version == 1 else seed
                    if next_version == 1:
                        logger.info(f"FLFI2V shot {shot_index} NOW image using fixed seed: 1")

                    # Mark NOW_IMAGE queue item as active
                    self._mark_queue_item_active(project_id, shot_index, GenerationType.NOW_IMAGE)

                    # Broadcast progress
                    manager.broadcast_sync(project_id, {
                        "type": "progress",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
                        "generation_type": "now_image",
                        "progress": 50 if image_variant == "both" else 0
                    })

                    # Determine workflow and reference for NOW
                    now_workflow = image_workflow
                    # Auto-switch to IP-Adapter workflow ONLY for ComfyUI mode with reference
                    actual_mode = image_mode or config.IMAGE_GENERATION_MODE
                    if now_reference and actual_mode == "comfyui":
                        if not now_workflow or now_workflow == "flux":
                            now_workflow = "flux_ipadapter_now"
                            logger.info(f"Using IP-Adapter workflow for NOW with reference: {now_reference}")

                    # Generate
                    result_path = await asyncio.to_thread(
                        self._generate_single_image,
                        project_id,
                        {**shot, 'image_prompt': now_prompt},
                        image_mode,
                        now_workflow,
                        now_seed,
                        None,  # No prompt override for FLFI2V
                        project_title,
                        "now",
                        now_reference,  # Pass NOW reference image
                        GenerationType.NOW_IMAGE  # Pass generation type for queue tracking
                    )

                    shots[shot_index - 1]['now_image_generated'] = True
                    shots[shot_index - 1]['now_image_path'] = self._get_relative_path(result_path)
                    results['now'] = shots[shot_index - 1]['now_image_path']

                    # Append to general image_paths for variations tracking
                    if 'image_paths' not in shots[shot_index - 1]:
                        shots[shot_index - 1]['image_paths'] = []
                    relative_path = shots[shot_index - 1]['now_image_path']
                    if relative_path not in shots[shot_index - 1]['image_paths']:
                        shots[shot_index - 1]['image_paths'].append(relative_path)

                    # Mark NOW_IMAGE queue item as completed
                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.NOW_IMAGE)

                    # Broadcast completion
                    manager.broadcast_sync(project_id, {
                        "type": "completed",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
                        "generation_type": "now_image"
                    })
                except Exception as e:
                    logger.error(f"Error generating NOW image for shot {shot_index}: {e}")
                    # Mark NOW_IMAGE queue item as failed
                    self._mark_queue_item_failed(project_id, shot_index, GenerationType.NOW_IMAGE, str(e))

                    # Broadcast error
                    manager.broadcast_sync(project_id, {
                        "type": "cancelled",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
                        "generation_type": "now_image",
                        "error": str(e)
                    })
                    # Only raise if this was the only variant requested
                    if image_variant == "now":
                        raise

        
            else:
                logger.info(f"FLFI2V shot {shot_index} NOW image already generated, skipping and marking completed")
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.NOW_IMAGE)
# Update standard image_path to NOW (for backward compatibility)
        if shots[shot_index - 1].get('now_image_path'):
            shots[shot_index - 1]['image_path'] = shots[shot_index - 1]['now_image_path']
            shots[shot_index - 1]['image_generated'] = True

        # Save shots
        self.project_manager._save_shots(project_id, shots)

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
        return absolute_path

    async def regenerate_shot_video(
        self, project_id: str, shot_index: int, force: bool = False,
        video_mode: Optional[str] = None, video_workflow: Optional[str] = None,
        project_title: Optional[str] = None, video_variant: str = None,
        append_image_prompt: Optional[str] = None
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

            if shot_index < 1 or shot_index > len(shots):
                raise ValueError(f"Shot {shot_index} not found")

            shot = shots[shot_index - 1]
            project_type = story.get('project_type', 1) if story else 1

            # Handle FLFI2V shots
            if shot.get('is_flfi2v') and project_type == 2:
                results = await self._regenerate_flfi2v_videos(
                    project_id, shot_index, shot, force,
                    video_mode, video_workflow, project_title, video_variant
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
                    self.project_manager._save_shots(project_id, shots)

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

            # Run in thread pool to avoid blocking
            video_path = await asyncio.to_thread(
                self._generate_single_video,
                project_id,
                shot,
                video_mode,
                video_workflow,
                project_title,
                append_image_prompt
            )

            # Mark as rendered
            self.project_manager.mark_video_rendered(project_id, shot_index, video_path)

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
        project_title: Optional[str], video_variant: str
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

        # Generate meeting video
        if video_variant in ["meeting", "both"]:
            if shot.get('meeting_video_prompt') and (not shots[shot_index - 1].get('meeting_video_rendered') or force):
                try:
                    # Preserve old meeting video before generating new one
                    old_meeting_path = shots[shot_index - 1].get('meeting_video_path')
                    if old_meeting_path:
                        if 'video_paths' not in shots[shot_index - 1]:
                            shots[shot_index - 1]['video_paths'] = []
                        if old_meeting_path not in shots[shot_index - 1]['video_paths']:
                            shots[shot_index - 1]['video_paths'].append(old_meeting_path)

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
                        "shot_id": shot.get('id'),
                        "generation_type": "meeting_video",
                        "progress": 0
                    })

                    # Generate
                    result_path = await asyncio.to_thread(
                        self._generate_flfi2v_video,
                        project_id,
                        shot,
                        "meeting",
                        video_mode,
                        video_workflow,
                        project_title,
                        video_filename,
                        meeting_seed,
                        None,  # last_frame_image_path
                        GenerationType.MEETING_VIDEO  # generation_type for queue tracking
                    )

                    shots[shot_index - 1]['meeting_video_rendered'] = True
                    shots[shot_index - 1]['meeting_video_path'] = self._get_relative_path(result_path)
                    results['meeting'] = shots[shot_index - 1]['meeting_video_path']

                    # Append to general video_paths for variations tracking
                    if 'video_paths' not in shots[shot_index - 1]:
                        shots[shot_index - 1]['video_paths'] = []
                    if shots[shot_index - 1]['meeting_video_path'] not in shots[shot_index - 1]['video_paths']:
                        shots[shot_index - 1]['video_paths'].append(shots[shot_index - 1]['meeting_video_path'])


                    # Mark MEETING_VIDEO queue item as completed
                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.MEETING_VIDEO)

                    # Broadcast completion
                    manager.broadcast_sync(project_id, {
                        "type": "completed",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
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
                        "shot_id": shot.get('id'),
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
            if shot.get('departure_video_prompt') and (not shots[shot_index - 1].get('departure_video_rendered') or force):
                try:
                    # Preserve old departure video before generating new one
                    old_departure_path = shots[shot_index - 1].get('departure_video_path')
                    if old_departure_path:
                        if 'video_paths' not in shots[shot_index - 1]:
                            shots[shot_index - 1]['video_paths'] = []
                        if old_departure_path not in shots[shot_index - 1]['video_paths']:
                            shots[shot_index - 1]['video_paths'].append(old_departure_path)

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
                        "shot_id": shot.get('id'),
                        "generation_type": "departure_video",
                        "progress": 50 if video_variant == "both" else 0
                    })

                    # Generate with last_frame_image
                    result_path = await asyncio.to_thread(
                        self._generate_flfi2v_video,
                        project_id,
                        shot,
                        "departure",
                        video_mode,
                        video_workflow,
                        project_title,
                        video_filename,
                        departure_seed,
                        last_frame_image,
                        GenerationType.DEPARTURE_VIDEO  # generation_type for queue tracking
                    )

                    shots[shot_index - 1]['departure_video_rendered'] = True
                    shots[shot_index - 1]['departure_video_path'] = self._get_relative_path(result_path)
                    results['departure'] = shots[shot_index - 1]['departure_video_path']

                    # Append to general video_paths for variations tracking
                    if 'video_paths' not in shots[shot_index - 1]:
                        shots[shot_index - 1]['video_paths'] = []
                    if shots[shot_index - 1]['departure_video_path'] not in shots[shot_index - 1]['video_paths']:
                        shots[shot_index - 1]['video_paths'].append(shots[shot_index - 1]['departure_video_path'])


                    # Mark DEPARTURE_VIDEO queue item as completed
                    self._mark_queue_item_completed(project_id, shot_index, GenerationType.DEPARTURE_VIDEO)

                    # Broadcast completion
                    manager.broadcast_sync(project_id, {
                        "type": "completed",
                        "project_id": project_id,
                        "shot_index": shot_index,
                        "shot_id": shot.get('id'),
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
                        "shot_id": shot.get('id'),
                        "generation_type": "departure_video",
                        "error": str(e)
                    })
                    # Only raise if this was the only variant requested
                    if video_variant == "departure":
                        raise

        
            else:
                logger.info(f"FLFI2V shot {shot_index} departure video already rendered or missing prompt, skipping and marking completed")
                self._mark_queue_item_completed(project_id, shot_index, GenerationType.DEPARTURE_VIDEO)
# Update standard video_path to meeting (for backward compatibility)
        if shots[shot_index - 1].get('meeting_video_path'):
            shots[shot_index - 1]['video_path'] = shots[shot_index - 1]['meeting_video_path']
            shots[shot_index - 1]['video_rendered'] = True

        # Save shots
        self.project_manager._save_shots(project_id, shots)

        logger.info(f"FLFI2V shot {shot_index} videos regenerated: {results}")
        return results

    async def generate_scene_background(
        self, project_id: str, scene_id: int, set_prompt: str,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        workflow: Optional[str] = None
    ) -> str:
        """
        Generate background image for a scene using AI

        Args:
            project_id: Project identifier
            scene_id: Scene ID in the story
            set_prompt: Background description prompt

        Returns:
            Path to generated background image
        """
        try:
            import config

            # Create backgrounds directory
            project_dir = self.project_manager.get_project_dir(project_id)
            backgrounds_dir = os.path.join(project_dir, "backgrounds")
            os.makedirs(backgrounds_dir, exist_ok=True)

            # Generate filename
            background_filename = f"scene_{scene_id}_background_001.png"
            background_path = os.path.join(backgrounds_dir, background_filename)

            # Broadcast 0% progress
            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "scene_id": scene_id,
                "step": "background_generation",
                "progress": 0
            })

            # Progress callback
            def on_step_progress(current, total):
                progress = int((current / total) * 100) if total > 0 else 0
                manager.broadcast_sync(project_id, {
                    "type": "progress",
                    "project_id": project_id,
                    "scene_id": scene_id,
                    "step": "background_generation",
                    "progress": progress
                })

            # Generate background using standard Flux workflow
            # Use override if provided, otherwise fallback to story set_prompt
            set_prompt = prompt if prompt else set_prompt # defined or story fallback
            actual_workflow = workflow if workflow else "flux"

            logger.info(f"Generating background for scene {scene_id} using prompt: {set_prompt[:60]}... (workflow: {actual_workflow})")

            result_path = await asyncio.to_thread(
                self._generate_single_image,
                project_id,
                {'image_prompt': set_prompt, 'index': scene_id},  # Use scene_id for indexing
                "comfyui",  # Always use ComfyUI for backgrounds
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

            # Broadcast completion
            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "scene_id": scene_id,
                "step": "background_generation",
                "background_image_path": relative_path
            })

            logger.info(f"Background generated for scene {scene_id}: {relative_path}")
            return relative_path

        except Exception as e:
            logger.error(f"Error generating background for scene {scene_id}: {e}")
            manager.broadcast_sync(project_id, {
                "type": "error",
                "project_id": project_id,
                "scene_id": scene_id,
                "step": "background_generation",
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

            # Run in thread pool to avoid blocking
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
        image_mode: str = None, image_workflow: str = None, seed: int = None
    ) -> str:
        """Generate a thumbnail image for the project"""
        try:
            logger.info(f"Generating {aspect_ratio} thumbnail for project {project_id}")
            
            # Load project to get story and thumbnail prompt
            project_meta = self.project_manager.get_project(project_id)
            if not project_meta:
                raise ValueError(f"Project {project_id} not found")
                
            story_path = os.path.join(self.project_manager.get_project_dir(project_id), "story.json")
            if not os.path.exists(story_path):
                raise ValueError(f"Story not found for project {project_id}")
                
            with open(story_path, 'r', encoding='utf-8') as f:
                import json
                story = json.load(f)
                
            prompt = story.get(f'thumbnail_prompt_{aspect_ratio.replace(":", "_")}')
            if not prompt:
                prompt = story.get('title', project_meta.get('idea', 'A cinematic thumbnail'))
                
            images_dir = self.project_manager.get_images_dir(project_id)
            os.makedirs(images_dir, exist_ok=True)
            
            filename = f"thumbnail_{aspect_ratio.replace(':', '_')}.png"
            image_path = os.path.join(images_dir, filename)
            
            if not force and os.path.exists(image_path):
                if aspect_ratio == "16:9" and "thumbnail_url" not in project_meta:
                    project_meta['thumbnail_url'] = f"/api/projects/{project_id}/images/{filename}"
                    self.project_manager._save_meta(project_id, project_meta)
                elif aspect_ratio == "9:16" and "thumbnail_url_9_16" not in project_meta:
                    project_meta['thumbnail_url_9_16'] = f"/api/projects/{project_id}/images/{filename}"
                    self.project_manager._save_meta(project_id, project_meta)
                return image_path
                
            # Progress callback
            def on_step_progress(current, total):
                progress = int((current / total) * 100) if total > 0 else 0
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
                mode=image_mode,
                workflow_name=image_workflow,
                seed=seed,
                step_progress_callback=on_step_progress
            )
            
            if aspect_ratio == "16:9":
                project_meta['thumbnail_url'] = f"/api/projects/{project_id}/images/{filename}"
                self.project_manager._save_meta(project_id, project_meta)
            elif aspect_ratio == "9:16":
                project_meta['thumbnail_url_9_16'] = f"/api/projects/{project_id}/images/{filename}"
                self.project_manager._save_meta(project_id, project_meta)

            manager.broadcast_sync(project_id, {
                "type": "completed",
                "project_id": project_id,
                "step": "thumbnail"
            })
            
            return result_path
            
        except Exception as e:
            logger.error(f"Error generating thumbnail for project {project_id}: {e}")
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

    def _generate_single_image(self, project_id: str, shot: Dict[str, Any],
                               mode: Optional[str] = None,
                               workflow_name: Optional[str] = None,
                               seed: Optional[int] = None,
                               prompt_override: Optional[str] = None,
                               project_title: Optional[str] = None,
                               variant: str = None,
                               reference_image_path: str = None,
                               generation_type: GenerationType = None,
                               output_dir: Optional[str] = None,
                               filename_override: Optional[str] = None) -> str:
        """Generate image for a single shot (synchronous)

        Args:
        """
        print(f"[DEBUG] entering _generate_single_image for item {project_id}")
        logger.info(f"entering _generate_single_image for item {project_id}")
        from core.image_generator import generate_image
        import config

        project_dir = self.project_manager.get_project_dir(project_id)
        images_dir = os.path.join(project_dir, "images")
        actual_dir = output_dir if output_dir else images_dir
        os.makedirs(actual_dir, exist_ok=True)

        shot_index = shot['index']
        # Use override prompt if provided, otherwise fall back to saved shot prompt
        prompt = prompt_override.strip() if prompt_override and prompt_override.strip() else shot.get('image_prompt', '')

        # Load project to get aspect_ratio
        project_meta = self.project_manager.load_project(project_id)
        aspect_ratio = project_meta.get('aspect_ratio', '16:9')

        # Generate versioned filename with optional variant suffix
        next_version = self._get_next_image_version(actual_dir, shot_index, variant, generation_type)
        
        if filename_override:
            # support versioning inside override if % format is present, or just use as is
            if "%" in filename_override:
                image_filename = filename_override % next_version
            else:
                image_filename = filename_override
        elif variant:
            image_filename = f"shot_{shot_index:03d}_{variant}_{next_version:03d}.png"
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
            self._update_queue_item_progress(project_id, shot_index, queue_gen_type, progress)

            manager.broadcast_sync(project_id, {
                "type": "progress",
                "project_id": project_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "generation_type": queue_gen_type.value,
                "progress": progress
            })

        # Generate using the core image_generator module
        # This correctly handles both Gemini and ComfyUI modes and workflows
        result_path = generate_image(
            prompt=prompt,
            output_path=image_path,
            aspect_ratio=aspect_ratio,  # Use project's aspect ratio
            mode=mode, # If None, uses config.IMAGE_GENERATION_MODE
            seed=seed,
            workflow_name=workflow_name, # If None, uses config.IMAGE_WORKFLOW
            step_progress_callback=on_step_progress,
            project_title=project_title,
            reference_image_path=reference_image_path  # Pass reference image for IP-Adapter
        )

        if not result_path or not os.path.exists(result_path):
            raise RuntimeError(f"Failed to generate image for shot {shot_index}")

        return result_path

    def _generate_single_video(self, project_id: str, shot: Dict[str, Any],
                               video_mode: Optional[str] = None,
                               workflow_path: Optional[str] = None,
                               project_title: Optional[str] = None,
                               append_image_prompt: Optional[str] = None) -> str:
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

        motion_prompt = shot.get('motion_prompt', '')
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
                project_title=project_title
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
            if workflow_path in video_workflows:
                workflow_config = video_workflows[workflow_path]
                workflow_path = workflow_config.get('workflow_path', workflow_path)
                workflow_description = workflow_config.get('description', 'No description')
                logger.info(f"Using video workflow: {workflow_name} ({workflow_description})")
            else:
                logger.info(f"Using video workflow: {workflow_path}")

            # Load and compile workflow for this shot
            shot_length = getattr(config, 'DEFAULT_SHOT_LENGTH', 5)
            template = load_workflow(workflow_path, video_length_seconds=shot_length, aspect_ratio=aspect_ratio)
            wf = compile_workflow(template, shot, video_length_seconds=shot_length)

            # Submit to ComfyUI
            result = submit(wf)
            prompt_id = result.get('prompt_id')
            if not prompt_id:
                raise RuntimeError(f"No prompt_id returned for shot {shot_index}")

            logger.info(f"Video submitted for shot {shot_index}: prompt_id={prompt_id}")

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

            source_path = get_output_file_path(video_info)
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
        generation_type: GenerationType = None
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

        template = load_workflow(workflow_path, aspect_ratio=aspect_ratio)
        wf = copy.deepcopy(template)

        # Get node IDs from config
        load_first_node_id = workflow_config.get('load_image_first_node_id', '128')
        load_last_node_id = workflow_config.get('load_image_last_node_id', '151')
        motion_prompt_node_id = workflow_config.get('motion_prompt_node_id', '93')
        seed_node_id = workflow_config.get('seed_node_id', '142')

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
        source_path = get_output_file_path(video_info)

        if os.path.exists(source_path):
            shutil.copy2(source_path, video_save_path)
            logger.info(f"FLFI2V video copied: {video_filename} ({os.path.getsize(video_save_path):,} bytes)")
            return video_save_path
        else:
            raise RuntimeError(f"FLFI2V video source file not found: {source_path}")


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
