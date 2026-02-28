"""
Stories API endpoints
"""
from fastapi import APIRouter, HTTPException, status
import sys
import os
import json
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from web_ui.backend.models.story import UpdateStoryRequest, RegenerateStoryRequest
from web_ui.backend.services.session_service import SessionService
from core.story_engine import build_story
from core.session_manager import SessionManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}/story", tags=["stories"])

# Initialize services
session_service = SessionService()
session_manager = SessionManager()


@router.get("")
async def get_story(session_id: str):
    """Get story JSON"""
    try:
        session = session_service.get_session(session_id)
        if not session.story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found for this session"
            )
        return session.story
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting story: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get story: {str(e)}"
        )


@router.put("")
async def update_story(session_id: str, request: UpdateStoryRequest):
    """Update story JSON"""
    try:
        # Load session metadata
        meta = session_manager.load_session(session_id)

        # Validate story structure
        story = request.story
        if not isinstance(story, dict):
            raise ValueError("Story must be a dictionary")

        if "scenes" not in story or not isinstance(story["scenes"], list):
            raise ValueError("Story must contain a 'scenes' array")

        # Validate scene durations if present
        for scene in story["scenes"]:
            if "scene_duration" in scene:
                duration = scene["scene_duration"]
                if not isinstance(duration, int) or duration < 5:
                    raise ValueError(f"Invalid scene_duration: {duration}. Must be at least 5 seconds")

        # Save story
        story_json = json.dumps(story, ensure_ascii=False, indent=2)
        session_manager.save_story(session_id, story_json)

        # Return updated session
        return session_service.get_session(session_id)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating story: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update story: {str(e)}"
        )


@router.post("/regenerate")
async def regenerate_story(session_id: str, request: RegenerateStoryRequest):
    """Regenerate story with new agent"""
    try:
        # Load session
        meta = session_manager.load_session(session_id)
        idea = meta["idea"]

        # Generate new story
        import config
        target_length = config.TARGET_VIDEO_LENGTH if hasattr(config, 'TARGET_VIDEO_LENGTH') else None

        story_json = build_story(idea, request.agent, target_length)

        # Save story
        session_manager.save_story(session_id, story_json)

        # Return updated session
        return session_service.get_session(session_id)

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error regenerating story: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate story: {str(e)}"
        )
