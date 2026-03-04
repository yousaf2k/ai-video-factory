"""
Generation service - Async wrapper for core generation modules
"""
import sys
import os
import re
import glob
import random
import asyncio
from typing import List, Dict, Any, Optional
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.session_manager import SessionManager
from core.image_generator import generate_images_for_shots
from core.shot_planner import plan_shots
from core.logger_config import get_logger
from web_ui.backend.websocket.manager import manager

logger = get_logger(__name__)


class GenerationService:
    """Service for async generation operations"""

    def __init__(self):
        # Default to configured sessions directory
        import config
        sessions_dir = getattr(config, 'ABS_SESSIONS_DIR', None)
        
        if sessions_dir is None:
            # Fallback
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            sessions_dir = os.path.join(project_root, "output", "sessions")
        
        self.session_manager = SessionManager(sessions_dir)
        self.cancelled_sessions = set()
        self.cancelled_shots: dict[str, set[int]] = {}
        self.queued_shots: dict[str, set[int]] = {}

    def cancel_session(self, session_id: str):
        """Mark a session as cancelled to halt background queue processing."""
        self.cancelled_sessions.add(session_id)
        if session_id in self.queued_shots:
            self.queued_shots.pop(session_id)
        logger.info(f"Marked session {session_id} as cancelled. Future queued items will be skipped.")

    def cancel_single_shot(self, session_id: str, shot_index: int):
        """Mark a single shot as cancelled to halt it from entering the queue."""
        if session_id not in self.cancelled_shots:
            self.cancelled_shots[session_id] = set()
        self.cancelled_shots[session_id].add(shot_index)
        if session_id in self.queued_shots and shot_index in self.queued_shots[session_id]:
            self.queued_shots[session_id].remove(shot_index)
        logger.info(f"Marked shot {shot_index} in session {session_id} as cancelled.")

    async def run_batch_generation(self, session_id: str, request: Any):
        """
        Background task to process a batch of generations sequentially with a concurrency limit.
        Since ComfyUI takes time, this prevents destroying progress on browser refresh.
        """
        from web_ui.backend.websocket.manager import manager
        import config
        
        # Clear any old cancellation flags from previous runs
        if session_id in self.cancelled_sessions:
            self.cancelled_sessions.remove(session_id)
        if session_id in self.cancelled_shots:
            self.cancelled_shots.pop(session_id)
            
        limit = getattr(config, 'CONCURRENT_GENERATION_LIMIT', 2)
        logger.info(f"Using concurrency limit of {limit} for batch generation")
        semaphore = asyncio.Semaphore(limit)
        
        # Populate the queued tracking dict for UI refreshes
        self.queued_shots[session_id] = set(request.shot_indices)
        
        # Helper to process a single shot synchronously within the bounded async loop
        async def process_shot(shot_index: int):
            # Abort before even acquiring semaphore if session or shot was cancelled
            if session_id in self.cancelled_sessions:
                logger.info(f"Session {session_id} cancelled. Skipping background shot {shot_index}.")
                return
            if session_id in self.cancelled_shots and shot_index in self.cancelled_shots[session_id]:
                logger.info(f"Shot {shot_index} cancelled explicitly. Skipping background generation.")
                return
                
            async with semaphore:
                try:
                    # Double check inside semaphore just in case it took a while to acquire
                    if session_id in self.cancelled_sessions:
                        logger.info(f"Session {session_id} cancelled (after wait). Skipping shot {shot_index}.")
                        return
                    if session_id in self.cancelled_shots and shot_index in self.cancelled_shots[session_id]:
                        logger.info(f"Shot {shot_index} cancelled explicitly (after wait). Skipping.")
                        return

                    # Drop from queued tracking state (it is now actively generating)
                    if session_id in self.queued_shots and shot_index in self.queued_shots[session_id]:
                        self.queued_shots[session_id].remove(shot_index)

                    # Load current shot state in case we need to skip existing images
                    # (only load if we're actually generating images to save disk IO)
                    shot_wants_skip = False
                    if request.regenerate_images and not request.force:
                        try:
                            session = self.session_manager.get_session(session_id)
                            if session and session.shots:
                                shot_data = next((s for s in session.shots if s.get('index') == shot_index), None)
                                if shot_data and shot_data.get('image_generated') and shot_data.get('image_path'):
                                    shot_wants_skip = True
                                    logger.info(f"Batch generation skipping existing image for shot {shot_index}")
                        except Exception as e:
                            logger.warning(f"Failed to check shot state before batch: {e}")

                    # 1. Regenerate Image
                    if request.regenerate_images and not shot_wants_skip:
                        await self.regenerate_shot_image(
                            session_id, shot_index, force=request.force,
                            image_mode=request.image_mode, image_workflow=request.image_workflow
                        )

                    # 2. Regenerate Video
                    if request.regenerate_videos:
                        await self.regenerate_shot_video(
                            session_id, shot_index, force=request.force,
                            video_workflow=request.video_workflow
                        )
                    
                    # Ensure websocket completes for this shot if it hasn't somehow
                    manager.broadcast_sync(session_id, {
                        "type": "completed",
                        "session_id": session_id,
                        "shot_index": shot_index
                    })

                except Exception as e:
                    logger.error(f"Batch error on shot {shot_index}: {str(e)}")
                    # Broadcast error/cancel so UI spinner doesn't run forever
                    manager.broadcast_sync(session_id, {
                        "type": "cancelled",
                        "session_id": session_id,
                        "shot_index": shot_index
                    })

        # Launch all tasks bounded by the semaphore
        logger.info(f"Starting server-side batch generation for {len(request.shot_indices)} shots")
        tasks = [process_shot(idx) for idx in request.shot_indices]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Completed server-side batch generation for session {session_id}")

    async def regenerate_shot_image(
        self, session_id: str, shot_index: int, force: bool = False,
        image_mode: Optional[str] = None, image_workflow: Optional[str] = None,
        seed: Optional[int] = None, prompt_override: Optional[str] = None
    ) -> str:
        """
        Regenerate image for a single shot

        Args:
            session_id: Session identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if image exists
            image_mode: Override generation mode
            image_workflow: Override ComfyUI workflow

        Returns:
            Path to generated image
        """
        try:
            # Load shots
            shots = self.session_manager.get_shots(session_id)

            if shot_index < 1 or shot_index > len(shots):
                raise ValueError(f"Shot {shot_index} not found")

            shot = shots[shot_index - 1]

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
                    self.session_manager._save_shots(session_id, shots)

            # Generate image for single shot
            logger.info(f"Regenerating image for shot {shot_index}")

            # Broadcast initial 0% so UI resets from any stale progress
            manager.broadcast_sync(session_id, {
                "type": "progress",
                "session_id": session_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "progress": 0
            })

            # Run in thread pool to avoid blocking
            image_path = await asyncio.to_thread(
                self._generate_single_image,
                session_id,
                shot,
                image_mode,
                image_workflow,
                seed,
                prompt_override
            )

            # Mark as generated
            self.session_manager.mark_image_generated(session_id, shot_index, image_path)

            # Broadcast completion to clear progress on frontend
            manager.broadcast_sync(session_id, {
                "type": "completed",
                "session_id": session_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id')
            })

            logger.info(f"Shot {shot_index} image regenerated: {image_path}")
            return image_path

        except Exception as e:
            logger.error(f"Error regenerating shot {shot_index} image: {e}")
            raise

    async def regenerate_shot_video(
        self, session_id: str, shot_index: int, force: bool = False,
        video_workflow: Optional[str] = None
    ) -> str:
        """
        Regenerate video for a single shot

        Args:
            session_id: Session identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if video exists
            video_workflow: Override workflow

        Returns:
            Path to generated video
        """
        try:
            # Load shots
            shots = self.session_manager.get_shots(session_id)

            if shot_index < 1 or shot_index > len(shots):
                raise ValueError(f"Shot {shot_index} not found")

            shot = shots[shot_index - 1]

            # Check if image exists
            if not shot.get('image_generated', False) or not shot.get('image_path'):
                raise ValueError(f"Shot {shot_index} has no image, cannot generate video")

            # Check if already exists and not forcing
            if not force and shot.get('video_rendered', False):
                logger.info(f"Shot {shot_index} already has video, skipping")
                return shot.get('video_path')

            # Generate video for single shot
            logger.info(f"Regenerating video for shot {shot_index}")
            
            # Broadcast initial 0% so UI resets from any stale progress
            manager.broadcast_sync(session_id, {
                "type": "progress",
                "session_id": session_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "progress": 0
            })

            # Run in thread pool to avoid blocking
            video_path = await asyncio.to_thread(
                self._generate_single_video,
                session_id,
                shot,
                video_workflow
            )

            # Mark as rendered
            self.session_manager.mark_video_rendered(session_id, shot_index, video_path)
            
            # Broadcast completion to clear progress on frontend
            manager.broadcast_sync(session_id, {
                "type": "completed",
                "session_id": session_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id')
            })

            logger.info(f"Shot {shot_index} video regenerated: {video_path}")
            return video_path

        except Exception as e:
            logger.error(f"Error regenerating shot {shot_index} video: {e}")
            raise


    async def replan_shots(
        self,
        session_id: str,
        max_shots: Optional[int] = None,
        shots_agent: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Re-plan shots from story

        Args:
            session_id: Session identifier
            max_shots: Maximum shots to generate
            shots_agent: Shots agent to use

        Returns:
            List of shot dictionaries
        """
        try:
            # Load story
            session_dir = self.session_manager.get_session_dir(session_id)
            story_path = os.path.join(session_dir, "story.json")

            if not os.path.exists(story_path):
                raise ValueError("Story not found for this session")

            with open(story_path, 'r', encoding='utf-8') as f:
                story_json = f.read()

            # Plan shots
            logger.info(f"Re-planning shots for session {session_id}")

            # Run in thread pool to avoid blocking
            shots = await asyncio.to_thread(
                plan_shots,
                story_json,
                max_shots=max_shots,
                shots_agent=shots_agent
            )

            # Save shots
            self.session_manager.save_shots(session_id, shots)

            logger.info(f"Re-planned {len(shots)} shots")
            return shots

        except Exception as e:
            logger.error(f"Error re-planning shots: {e}")
            raise

    async def generate_thumbnail(
        self, session_id: str, aspect_ratio: str = "16:9", force: bool = False,
        image_mode: str = None, image_workflow: str = None, seed: int = None
    ) -> str:
        """Generate a thumbnail image for the session"""
        try:
            logger.info(f"Generating {aspect_ratio} thumbnail for session {session_id}")
            
            # Load session to get story and thumbnail prompt
            session_meta = self.session_manager.get_session(session_id)
            if not session_meta:
                raise ValueError(f"Session {session_id} not found")
                
            story_path = os.path.join(self.session_manager.get_session_dir(session_id), "story.json")
            if not os.path.exists(story_path):
                raise ValueError(f"Story not found for session {session_id}")
                
            with open(story_path, 'r', encoding='utf-8') as f:
                import json
                story = json.load(f)
                
            prompt = story.get(f'thumbnail_prompt_{aspect_ratio.replace(":", "_")}')
            if not prompt:
                prompt = story.get('title', session_meta.get('idea', 'A cinematic thumbnail'))
                
            images_dir = self.session_manager.get_images_dir(session_id)
            os.makedirs(images_dir, exist_ok=True)
            
            filename = f"thumbnail_{aspect_ratio.replace(':', '_')}.png"
            image_path = os.path.join(images_dir, filename)
            
            if not force and os.path.exists(image_path):
                if aspect_ratio == "16:9" and "thumbnail_url" not in session_meta:
                    session_meta['thumbnail_url'] = f"/api/sessions/{session_id}/images/{filename}"
                    self.session_manager._save_meta(session_id, session_meta)
                elif aspect_ratio == "9:16" and "thumbnail_url_9_16" not in session_meta:
                    session_meta['thumbnail_url_9_16'] = f"/api/sessions/{session_id}/images/{filename}"
                    self.session_manager._save_meta(session_id, session_meta)
                return image_path
                
            # Progress callback
            def on_step_progress(current, total):
                progress = int((current / total) * 100) if total > 0 else 0
                manager.broadcast_sync(session_id, {
                    "type": "progress",
                    "session_id": session_id,
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
                session_meta['thumbnail_url'] = f"/api/sessions/{session_id}/images/{filename}"
                self.session_manager._save_meta(session_id, session_meta)
            elif aspect_ratio == "9:16":
                session_meta['thumbnail_url_9_16'] = f"/api/sessions/{session_id}/images/{filename}"
                self.session_manager._save_meta(session_id, session_meta)

            manager.broadcast_sync(session_id, {
                "type": "completed",
                "session_id": session_id,
                "step": "thumbnail"
            })
            
            return result_path
            
        except Exception as e:
            logger.error(f"Error generating thumbnail for session {session_id}: {e}")
            raise

    def _get_next_image_version(self, images_dir: str, shot_index: int) -> int:
        """Find the next available version number for a shot image.
        
        Scans for existing files like shot_001_001.png, shot_001_002.png, etc.
        Returns the next version number (starting from 1).
        """
        pattern = os.path.join(images_dir, f"shot_{shot_index:03d}_*.png")
        existing_files = glob.glob(pattern)
        
        max_version = 0
        version_re = re.compile(rf"shot_{shot_index:03d}_(\d+)\.png$")
        
        for filepath in existing_files:
            filename = os.path.basename(filepath)
            match = version_re.match(filename)
            if match:
                version = int(match.group(1))
                max_version = max(max_version, version)
        
        return max_version + 1

    def _generate_single_image(self, session_id: str, shot: Dict[str, Any], 
                               mode: Optional[str] = None, 
                               workflow_name: Optional[str] = None,
                               seed: Optional[int] = None,
                               prompt_override: Optional[str] = None) -> str:
        """Generate image for a single shot (synchronous)"""
        from core.image_generator import generate_image
        import config

        images_dir = self.session_manager.get_images_dir(session_id)
        os.makedirs(images_dir, exist_ok=True)

        shot_index = shot['index']
        # Use override prompt if provided, otherwise fall back to saved shot prompt
        prompt = prompt_override.strip() if prompt_override and prompt_override.strip() else shot['image_prompt']

        
        # Generate versioned filename: shot_001_001.png, shot_001_002.png, etc.
        next_version = self._get_next_image_version(images_dir, shot_index)
        image_filename = f"shot_{shot_index:03d}_{next_version:03d}.png"
        image_path = os.path.join(images_dir, image_filename)

        # 1st time generation for a shot uses seed 1, next generations use random
        # If specific seed provided, use it
        if seed is None:
            seed = 1 if next_version == 1 else random.randint(0, 2**32 - 1)

        # Progress callback to bridge ComfyUI steps to our WebSocket
        def on_step_progress(current, total):
            progress = int((current / total) * 100) if total > 0 else 0
            manager.broadcast_sync(session_id, {
                "type": "progress",
                "session_id": session_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
                "progress": progress
            })

        # Generate using the core image_generator module
        # This correctly handles both Gemini and ComfyUI modes and workflows
        result_path = generate_image(
            prompt=prompt,
            output_path=image_path,
            mode=mode, # If None, uses config.IMAGE_GENERATION_MODE
            seed=seed,
            workflow_name=workflow_name, # If None, uses config.IMAGE_WORKFLOW
            step_progress_callback=on_step_progress
        )

        if not result_path or not os.path.exists(result_path):
            raise RuntimeError(f"Failed to generate image for shot {shot_index}")

        return result_path

    def _generate_single_video(self, session_id: str, shot: Dict[str, Any],
                               workflow_path: Optional[str] = None) -> str:
        """Generate video for a single shot (synchronous)"""
        import shutil
        from core.prompt_compiler import load_workflow, compile_workflow
        from core.comfy_client import submit, wait_for_prompt_completion_with_progress, get_output_file_path
        from core.video_regenerator import generate_unique_video_filename
        import config

        videos_dir = self.session_manager.get_videos_dir(session_id)
        os.makedirs(videos_dir, exist_ok=True)

        shot_index = shot['index']

        # Determine workflow path
        if not workflow_path:
            workflow_path = config.WORKFLOW_PATH

        # Load and compile workflow for this shot
        shot_length = getattr(config, 'DEFAULT_SHOT_LENGTH', 5)
        template = load_workflow(workflow_path, video_length_seconds=shot_length)
        wf = compile_workflow(template, shot, video_length_seconds=shot_length)

        # Submit to ComfyUI
        result = submit(wf)
        prompt_id = result.get('prompt_id')
        if not prompt_id:
            raise RuntimeError(f"No prompt_id returned for shot {shot_index}")

        logger.info(f"Video submitted for shot {shot_index}: prompt_id={prompt_id}")

        # Progress callback to bridge ComfyUI steps to our WebSocket
        def on_step_progress(current, total):
            progress = int((current / total) * 100) if total > 0 else 0
            manager.broadcast_sync(session_id, {
                "type": "progress",
                "session_id": session_id,
                "shot_index": shot_index,
                "shot_id": shot.get('id'),
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

        # Copy video to session folder
        video_info = video_outputs[0]
        video_filename, video_save_path = generate_unique_video_filename(videos_dir, shot_index)

        source_path = get_output_file_path(video_info)
        if os.path.exists(source_path):
            shutil.copy2(source_path, video_save_path)
            logger.info(f"Video copied: {video_filename} ({os.path.getsize(video_save_path):,} bytes)")

            # Mark as rendered
            self.session_manager.mark_video_rendered(session_id, shot_index, video_save_path)
            return video_save_path
        else:
            raise RuntimeError(f"Video source file not found: {source_path}")
