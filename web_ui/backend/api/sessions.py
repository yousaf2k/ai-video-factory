"""
Sessions API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
import logging

from web_ui.backend.models.session import (
    SessionListItem, SessionDetail, CreateSessionRequest,
    UpdateSessionRequest, DuplicateSessionRequest
)
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
