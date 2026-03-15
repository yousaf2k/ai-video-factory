"""
Sessions API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import os

from web_ui.backend.models.session import (
    SessionListItem, SessionDetail, CreateSessionRequest,
    UpdateSessionRequest, DuplicateSessionRequest
)
from pydantic import BaseModel

class GenerateThumbnailRequest(BaseModel):
    aspect_ratio: str = "16:9"
    force: bool = False
    image_mode: Optional[str] = None
    image_workflow: Optional[str] = None
    seed: Optional[int] = None

from web_ui.backend.services.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Initialize session service
session_service = SessionService()


@router.get("", response_model=List[SessionListItem])
async def list_sessions():
    """List all sessions"""
    logger.info("list_sessions endpoint called")
    try:
        sessions = session_service.list_sessions()
        logger.info(f"Returning {len(sessions)} sessions")
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.post("", response_model=SessionDetail, status_code=status.HTTP_201_CREATED)
async def create_session(request: CreateSessionRequest):
    """Create a new session"""
    try:
        return session_service.create_session(request)
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """Get session details"""
    try:
        return session_service.get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.put("/{session_id}", response_model=SessionDetail)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """Update session metadata"""
    try:
        session_service.update_session(session_id, request)
        return session_service.get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        success = session_service.delete_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.post("/{session_id}/duplicate", response_model=SessionDetail)
async def duplicate_session(session_id: str, request: DuplicateSessionRequest = None):
    """Duplicate a session"""
    try:
        new_session_id = request.new_session_id if request else None
        return session_service.duplicate_session(session_id, new_session_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    except Exception as e:
        logger.error(f"Error duplicating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate session: {str(e)}"
        )


@router.get("/{session_id}/images/{filename}", response_class=FileResponse)
async def get_session_image(session_id: str, filename: str):
    """Serve a session image file directly"""
    try:
        images_dir = session_service.get_images_dir(session_id)
        image_path = os.path.join(images_dir, filename)
        
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image {filename} not found for session {session_id}"
            )
            
        return FileResponse(image_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filename} for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve image: {str(e)}"
        )


@router.get("/{session_id}/videos/{filename}", response_class=FileResponse)
async def get_session_video(session_id: str, filename: str):
    """Serve a session video file directly"""
    try:
        videos_dir = session_service.get_videos_dir(session_id)
        video_path = os.path.join(videos_dir, filename)
        
        if not os.path.exists(video_path) or not os.path.isfile(video_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video {filename} not found for session {session_id}"
            )
            
        return FileResponse(video_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving video {filename} for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve video: {str(e)}"
        )


@router.post("/{session_id}/thumbnail")
async def generate_thumbnail(session_id: str, request: GenerateThumbnailRequest):
    """Generate a thumbnail for the session"""
    try:
        from web_ui.backend.services.generation_service import get_generation_service
        gen_service = get_generation_service()
        
        image_path = await gen_service.generate_thumbnail(
            session_id, 
            aspect_ratio=request.aspect_ratio, 
            force=request.force,
            image_mode=request.image_mode,
            image_workflow=request.image_workflow,
            seed=request.seed
        )
        
        filename = os.path.basename(image_path)
        thumbnail_url = f"/api/sessions/{session_id}/images/{filename}"
        
        return {"status": "success", "thumbnail_url": thumbnail_url}
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thumbnail: {str(e)}"
        )

