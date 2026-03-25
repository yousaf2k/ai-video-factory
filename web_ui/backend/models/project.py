"""
Pydantic models for project data
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any
from datetime import datetime


class ProjectStep(BaseModel):
    """Progress steps for project"""
    story: bool = False
    scene_graph: bool = False
    shots: bool = False
    images: bool = False
    videos: bool = False
    narration: bool = False


class ProjectStats(BaseModel):
    """Statistics for project"""
    total_shots: int = 0
    images_generated: int = 0
    videos_rendered: int = 0
    narration_generated: bool = False


class ProjectMetadata(BaseModel):
    """Project metadata model"""
    project_id: str
    timestamp: str
    idea: str
    started_at: str
    completed: bool = False
    completed_at: Optional[str] = None
    steps: ProjectStep = Field(default_factory=ProjectStep)
    stats: ProjectStats = Field(default_factory=ProjectStats)

    model_config = {
        "extra": "allow"
    }


class ProjectListItem(BaseModel):
    """Project item for list view"""
    project_id: str
    timestamp: str
    idea: str
    started_at: str
    completed: bool
    total_shots: int
    images_generated: int
    videos_rendered: int
    thumbnail_url: Optional[str] = None
    story: Optional[Dict[str, Any]] = None

    @classmethod
    def from_metadata(cls, meta: dict, story: dict = None) -> "ProjectListItem":
        """Create from ProjectManager metadata dict"""
        return cls(
            project_id=meta.get("project_id", ""),
            timestamp=meta.get("timestamp", ""),
            idea=meta.get("idea", ""),
            started_at=meta.get("started_at", ""),
            completed=meta.get("completed", False),
            total_shots=meta.get("stats", {}).get("total_shots", 0),
            images_generated=meta.get("stats", {}).get("images_generated", 0),
            videos_rendered=meta.get("stats", {}).get("videos_rendered", 0),
            thumbnail_url=meta.get("thumbnail_url"),
            story=story,
        )


class ProjectDetail(ProjectMetadata):
    """Full project detail with story and shots"""
    story: Optional[Dict[str, Any]] = None
    shots: Optional[List[Dict[str, Any]]] = None

    model_config = {
        "extra": "allow"
    }

    @classmethod
    def from_project_data(cls, meta: dict, story: dict = None, shots: list = None) -> "ProjectDetail":
        """Create from ProjectManager data"""
        # Filter meta to only include fields in the model if Pydantic is strict
        # But with extra="allow", this should work
        return cls(
            **meta,
            story=story,
            shots=shots
        )


class CreateProjectRequest(BaseModel):
    """Request to create a new project"""
    idea: str = Field(..., description="Video idea/prompt", min_length=1)
    project_id: Optional[str] = Field(default=None, description="Optional custom project ID")
    story_agent: str = Field(default="default", description="Story generation agent")
    shots_agent: str = Field(default="default", description="Shots prompt agent")
    total_duration: Optional[int] = Field(default=None, description="Target video length in seconds")
    prompts_file: Optional[str] = Field(default=None, description="Path to a custom prompts file")
    aspect_ratio: str = Field(default="16:9", description="Video aspect ratio (16:9 or 9:16)")

    @field_validator('aspect_ratio')
    @classmethod
    def validate_aspect_ratio(cls, v):
        if v not in ["16:9", "9:16"]:
            raise ValueError("aspect_ratio must be '16:9' or '9:16'")
        return v


class UpdateProjectRequest(BaseModel):
    """Request to update project metadata"""
    idea: Optional[str] = None
    completed: Optional[bool] = None
    story_agent: Optional[str] = None
    shots_agent: Optional[str] = None
    aspect_ratio: Optional[str] = Field(default=None, description="Video aspect ratio (16:9 or 9:16)")

    @field_validator('aspect_ratio')
    @classmethod
    def validate_aspect_ratio(cls, v):
        if v is not None and v not in ["16:9", "9:16"]:
            raise ValueError("aspect_ratio must be '16:9' or '9:16'")
        return v


class DuplicateProjectRequest(BaseModel):
    """Request to duplicate a project"""
    new_project_id: Optional[str] = None


class ResumeProjectRequest(BaseModel):
    """Request to resume from a specific step"""
    step: str = Field(..., description="Step to resume from (story, shots, images, videos, narration)")
