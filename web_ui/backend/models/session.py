"""
Pydantic models for session data
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class SessionStep(BaseModel):
    """Progress steps for session"""
    story: bool = False
    scene_graph: bool = False
    shots: bool = False
    images: bool = False
    videos: bool = False
    narration: bool = False


class SessionStats(BaseModel):
    """Statistics for session"""
    total_shots: int = 0
    images_generated: int = 0
    videos_rendered: int = 0
    narration_generated: bool = False


class SessionMetadata(BaseModel):
    """Session metadata model"""
    session_id: str
    timestamp: str
    idea: str
    started_at: str
    completed: bool = False
    completed_at: Optional[str] = None
    steps: SessionStep = Field(default_factory=SessionStep)
    stats: SessionStats = Field(default_factory=SessionStats)

    model_config = {
        "extra": "allow"
    }


class SessionListItem(BaseModel):
    """Session item for list view"""
    session_id: str
    timestamp: str
    idea: str
    started_at: str
    completed: bool
    total_shots: int
    images_generated: int
    videos_rendered: int

    @classmethod
    def from_metadata(cls, meta: dict) -> "SessionListItem":
        """Create from SessionManager metadata dict"""
        return cls(
            session_id=meta.get("session_id", ""),
            timestamp=meta.get("timestamp", ""),
            idea=meta.get("idea", ""),
            started_at=meta.get("started_at", ""),
            completed=meta.get("completed", False),
            total_shots=meta.get("stats", {}).get("total_shots", 0),
            images_generated=meta.get("stats", {}).get("images_generated", 0),
            videos_rendered=meta.get("stats", {}).get("videos_rendered", 0),
        )


class SessionDetail(SessionMetadata):
    """Full session detail with story and shots"""
    story: Optional[Dict[str, Any]] = None
    shots: Optional[List[Dict[str, Any]]] = None

    model_config = {
        "extra": "allow"
    }

    @classmethod
    def from_session_data(cls, meta: dict, story: dict = None, shots: list = None) -> "SessionDetail":
        """Create from SessionManager data"""
        # Filter meta to only include fields in the model if Pydantic is strict
        # But with extra="allow", this should work
        return cls(
            **meta,
            story=story,
            shots=shots
        )


class CreateSessionRequest(BaseModel):
    """Request to create a new session"""
    idea: str = Field(..., description="Video idea/prompt", min_length=1)
    session_id: Optional[str] = Field(default=None, description="Optional custom session ID")
    story_agent: str = Field(default="default", description="Story generation agent")
    image_agent: str = Field(default="default", description="Image prompt agent")
    video_agent: str = Field(default="default", description="Video motion agent")


class UpdateSessionRequest(BaseModel):
    """Request to update session metadata"""
    idea: Optional[str] = None
    completed: Optional[bool] = None
    story_agent: Optional[str] = None
    image_agent: Optional[str] = None
    video_agent: Optional[str] = None


class DuplicateSessionRequest(BaseModel):
    """Request to duplicate a session"""
    new_session_id: Optional[str] = None


class ResumeSessionRequest(BaseModel):
    """Request to resume from a specific step"""
    step: str = Field(..., description="Step to resume from (story, shots, images, videos, narration)")
