"""
Generation service - Async wrapper for core generation modules
"""
import sys
import os
import asyncio
from typing import List, Dict, Any, Optional
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.session_manager import SessionManager
from core.image_generator import generate_images_for_shots
from core.video_regenerator import regenerate_videos
from core.shot_planner import plan_shots
from core.logger_config import get_logger

logger = get_logger(__name__)


class GenerationService:
    """Service for async generation operations"""

    def __init__(self):
        self.session_manager = SessionManager()

    async def regenerate_shot_image(
        self, session_id: str, shot_index: int, force: bool = False
    ) -> str:
        """
        Regenerate image for a single shot

        Args:
            session_id: Session identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if image exists

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

            # Generate image for single shot
            logger.info(f"Regenerating image for shot {shot_index}")

            # Run in thread pool to avoid blocking
            image_path = await asyncio.to_thread(
                self._generate_single_image,
                session_id,
                shot
            )

            # Mark as generated
            self.session_manager.mark_image_generated(session_id, shot_index, image_path)

            logger.info(f"Shot {shot_index} image regenerated: {image_path}")
            return image_path

        except Exception as e:
            logger.error(f"Error regenerating shot {shot_index} image: {e}")
            raise

    async def regenerate_shot_video(
        self, session_id: str, shot_index: int, force: bool = False
    ) -> str:
        """
        Regenerate video for a single shot

        Args:
            session_id: Session identifier
            shot_index: Shot number (1-based)
            force: Force regeneration even if video exists

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

            # Run in thread pool to avoid blocking
            video_path = await asyncio.to_thread(
                self._generate_single_video,
                session_id,
                shot
            )

            # Mark as rendered
            self.session_manager.mark_video_rendered(session_id, shot_index, video_path)

            logger.info(f"Shot {shot_index} video regenerated: {video_path}")
            return video_path

        except Exception as e:
            logger.error(f"Error regenerating shot {shot_index} video: {e}")
            raise

    async def replan_shots(
        self,
        session_id: str,
        max_shots: Optional[int] = None,
        image_agent: str = "default",
        video_agent: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Re-plan shots from story

        Args:
            session_id: Session identifier
            max_shots: Maximum shots to generate
            image_agent: Image prompt agent to use
            video_agent: Video motion agent to use

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
                image_agent=image_agent,
                video_agent=video_agent
            )

            # Save shots
            self.session_manager.save_shots(session_id, shots)

            logger.info(f"Re-planned {len(shots)} shots")
            return shots

        except Exception as e:
            logger.error(f"Error re-planning shots: {e}")
            raise

    def _generate_single_image(self, session_id: str, shot: Dict[str, Any]) -> str:
        """Generate image for a single shot (synchronous)"""
        # Import here to avoid issues
        from core.image_generator import generate_image_gemini, generate_image_comfyui
        import config

        images_dir = self.session_manager.get_images_dir(session_id)
        os.makedirs(images_dir, exist_ok=True)

        shot_index = shot['index']
        prompt = shot['image_prompt']
        negative_prompt = getattr(config, 'DEFAULT_NEGATIVE_PROMPT', '')

        # Generate based on mode
        if config.IMAGE_GENERATION_MODE == "gemini":
            image_filename = f"shot_{shot_index:03d}.png"
            image_path = os.path.join(images_dir, image_filename)

            generate_image_gemini(
                prompt=prompt,
                output_path=image_path,
                negative_prompt=negative_prompt
            )
        else:  # comfyui
            # Use ComfyUI generation
            image_filename = f"shot_{shot_index:03d}.png"
            image_path = os.path.join(images_dir, image_filename)

            # Call ComfyUI to generate image
            # For now, return a placeholder path
            logger.warning(f"ComfyUI generation not yet implemented for single shot")

        return image_path

    def _generate_single_video(self, session_id: str, shot: Dict[str, Any]) -> str:
        """Generate video for a single shot (synchronous)"""
        from core.video_regenerator import regenerate_video_for_shot
        import config

        videos_dir = self.session_manager.get_videos_dir(session_id)
        os.makedirs(videos_dir, exist_ok=True)

        shot_index = shot['index']
        video_filename = f"shot_{shot_index:03d}.mp4"
        video_path = os.path.join(videos_dir, video_filename)

        # Generate video
        # For now, this is a placeholder - the actual implementation would call
        # the ComfyUI video generation pipeline
        logger.info(f"Generating video for shot {shot_index}: {video_path}")

        return video_path
