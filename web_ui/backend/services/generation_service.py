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
        # Default to configured sessions directory
        import config
        sessions_dir = getattr(config, 'ABS_SESSIONS_DIR', None)
        
        if sessions_dir is None:
            # Fallback
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            sessions_dir = os.path.join(project_root, "output", "sessions")
        
        self.session_manager = SessionManager(sessions_dir)

    async def regenerate_shot_image(
        self, session_id: str, shot_index: int, force: bool = False,
        image_mode: Optional[str] = None, image_workflow: Optional[str] = None
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

            # Generate image for single shot
            logger.info(f"Regenerating image for shot {shot_index}")

            # Run in thread pool to avoid blocking
            image_path = await asyncio.to_thread(
                self._generate_single_image,
                session_id,
                shot,
                image_mode,
                image_workflow
            )

            # Mark as generated
            self.session_manager.mark_image_generated(session_id, shot_index, image_path)

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

            # Run in thread pool to avoid blocking
            video_path = await asyncio.to_thread(
                self._generate_single_video,
                session_id,
                shot,
                video_workflow
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

    def _generate_single_image(self, session_id: str, shot: Dict[str, Any], 
                               mode: Optional[str] = None, 
                               workflow_name: Optional[str] = None) -> str:
        """Generate image for a single shot (synchronous)"""
        from core.image_generator import generate_image
        import config

        images_dir = self.session_manager.get_images_dir(session_id)
        os.makedirs(images_dir, exist_ok=True)

        shot_index = shot['index']
        prompt = shot['image_prompt']
        
        # Generate filename: shot_001.png
        image_filename = f"shot_{shot_index:03d}.png"
        image_path = os.path.join(images_dir, image_filename)

        # Generate using the core image_generator module
        # This correctly handles both Gemini and ComfyUI modes and workflows
        result_path = generate_image(
            prompt=prompt,
            output_path=image_path,
            mode=mode, # If None, uses config.IMAGE_GENERATION_MODE
            workflow_name=workflow_name # If None, uses config.IMAGE_WORKFLOW
        )

        if not result_path or not os.path.exists(result_path):
            raise RuntimeError(f"Failed to generate image for shot {shot_index}")

        return result_path

    def _generate_single_video(self, session_id: str, shot: Dict[str, Any],
                               workflow_path: Optional[str] = None) -> str:
        """Generate video for a single shot (synchronous)"""
        from core.video_regenerator import regenerate_video_for_shot
        import config

        videos_dir = self.session_manager.get_videos_dir(session_id)
        os.makedirs(videos_dir, exist_ok=True)

        shot_index = shot['index']
        
        # The video_regenerator handles the full generation and returns the path
        video_path = regenerate_video_for_shot(
            session_id=session_id,
            shot_index=shot_index,
            workflow_path=workflow_path # If None, uses config.WORKFLOW_PATH
        )

        if not video_path or not os.path.exists(video_path):
            raise RuntimeError(f"Failed to generate video for shot {shot_index}")

        return video_path
