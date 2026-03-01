"""
Shots API endpoints
"""
from fastapi import APIRouter, HTTPException, status
import sys
import os
import json
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from web_ui.backend.models.shot import (
    UpdateShotsRequest, UpdateShotRequest, RegenerateImageRequest,
    RegenerateVideoRequest, BatchRegenerateRequest, ReplanShotsRequest
)
from web_ui.backend.services.session_service import SessionService
from web_ui.backend.services.generation_service import GenerationService
from web_ui.backend.models.shot import Shot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}/shots", tags=["shots"])

# Initialize services
session_service = SessionService()
generation_service = GenerationService()


@router.get("")
async def get_shots(session_id: str):
    """Get all shots for a session"""
    try:
        session = session_service.get_session(session_id)
        return session.shots or []
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting shots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shots: {str(e)}"
        )


@router.get("/{shot_index}")
async def get_shot(session_id: str, shot_index: int):
    """Get a single shot by index"""
    try:
        shots = await get_shots(session_id)

        # shot_index is 1-based in the API, 0-based in the list
        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        return shots[shot_index - 1]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shot: {str(e)}"
        )


@router.put("")
async def update_shots(session_id: str, request: UpdateShotsRequest):
    """Update shots (reorder, edit prompts)"""
    try:
        # Convert dicts to Shot models
        shots = [Shot(**shot) for shot in request.shots]

        # Update shots.json
        session_dir = os.path.join(config.ABS_SESSIONS_DIR, session_id)
        shots_path = os.path.join(session_dir, "shots.json")

        # Save updated shots
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump([shot.dict() for shot in shots], f, indent=2, ensure_ascii=False)

        # Return updated session
        return session_service.get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating shots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update shots: {str(e)}"
        )


@router.put("/{shot_index}")
async def update_shot(session_id: str, shot_index: int, request: UpdateShotRequest):
    """Update a single shot's prompts"""
    try:
        shots = await get_shots(session_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        # Update only the fields that are provided
        shot = shots[shot_index - 1]
        if request.image_prompt is not None:
            shot['image_prompt'] = request.image_prompt
        if request.motion_prompt is not None:
            shot['motion_prompt'] = request.motion_prompt
        if request.camera is not None:
            shot['camera'] = request.camera
        if request.narration is not None:
            shot['narration'] = request.narration

        # Save updated shots
        session_dir = session_service.get_session_dir(session_id)
        shots_path = os.path.join(session_dir, "shots.json")

        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return shot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update shot: {str(e)}"
        )


@router.post("/{shot_index}/regenerate-image")
async def regenerate_shot_image(session_id: str, shot_index: int, request: RegenerateImageRequest):
    """Regenerate image for a single shot"""
    try:
        result = await generation_service.regenerate_shot_image(
            session_id, shot_index, force=request.force,
            image_mode=request.image_mode, image_workflow=request.image_workflow
        )
        return {"status": "success", "image_path": result}
    except Exception as e:
        logger.error(f"Error regenerating image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate image: {str(e)}"
        )


@router.post("/{shot_index}/regenerate-video")
async def regenerate_shot_video(session_id: str, shot_index: int, request: RegenerateVideoRequest):
    """Regenerate video for a single shot"""
    try:
        result = await generation_service.regenerate_shot_video(
            session_id, shot_index, force=request.force,
            video_workflow=request.video_workflow
        )
        return {"status": "success", "video_path": result}
    except Exception as e:
        logger.error(f"Error regenerating video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate video: {str(e)}"
        )


@router.post("/batch-regenerate")
async def batch_regenerate(session_id: str, request: BatchRegenerateRequest):
    """Regenerate multiple shots"""
    try:
        results = []

        for shot_index in request.shot_indices:
            result = {
                "shot_index": shot_index,
                "image": None,
                "video": None
            }

            if request.regenerate_images:
                try:
                    image_path = await generation_service.regenerate_shot_image(
                        session_id, shot_index, force=request.force,
                        image_mode=request.image_mode, image_workflow=request.image_workflow
                    )
                    result["image"] = "success"
                except Exception as e:
                    result["image"] = f"failed: {str(e)}"

            if request.regenerate_videos:
                try:
                    video_path = await generation_service.regenerate_shot_video(
                        session_id, shot_index, force=request.force,
                        video_workflow=request.video_workflow
                    )
                    result["video"] = "success"
                except Exception as e:
                    result["video"] = f"failed: {str(e)}"

            results.append(result)

        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Error in batch regeneration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch regenerate: {str(e)}"
        )


@router.post("/replan")
async def replan_shots(session_id: str, request: ReplanShotsRequest):
    """Re-plan shots from story"""
    try:
        shots = await generation_service.replan_shots(
            session_id,
            max_shots=request.max_shots,
            image_agent=request.image_agent,
            video_agent=request.video_agent
        )
        return {"status": "success", "shots": shots}
    except Exception as e:
        logger.error(f"Error replanning shots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replan shots: {str(e)}"
        )
