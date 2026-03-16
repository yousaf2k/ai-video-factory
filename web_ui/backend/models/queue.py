"""
Queue data models for AI Video Factory
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class GenerationType(str, Enum):
    """Type of generation task"""
    IMAGE = "image"
    VIDEO = "video"
    THEN_IMAGE = "then_image"
    NOW_IMAGE = "now_image"
    MEETING_VIDEO = "meeting_video"
    DEPARTURE_VIDEO = "departure_video"
    NARRATION = "narration"
    BACKGROUND = "background"


class QueueItemStatus(str, Enum):
    """Status of a queue item"""
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    FAILED = "failed"


class QueueItem(BaseModel):
    """Individual queue item with metadata"""
    item_id: str = Field(..., description="Unique identifier for this queue item")
    project_id: str = Field(..., description="Project identifier")
    shot_index: Optional[int] = Field(None, description="Shot index (1-based)")
    scene_id: Optional[int] = Field(None, description="Scene ID for narrations/backgrounds")
    generation_type: GenerationType = Field(..., description="Type of generation")
    status: QueueItemStatus = Field(default=QueueItemStatus.QUEUED, description="Current status")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")
    priority: int = Field(default=100, description="Priority (lower = higher priority)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="When generation started")
    completed_at: Optional[datetime] = Field(None, description="When generation completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # FLFI2V flags
    is_flfi2v: bool = Field(default=False, description="Is this a FLFI2V shot?")
    character_name: Optional[str] = Field(None, description="Character name for FLFI2V shots")

    # Override parameters for Single-Shot Queue support
    prompt_override: Optional[str] = Field(None, description="Custom prompt overlay")
    seed: Optional[int] = Field(None, description="Execution seed")
    image_mode: Optional[str] = Field(None, description="Image generation mode speed parameter")
    image_workflow: Optional[str] = Field(None, description="Override Image Workflow template")
    video_mode: Optional[str] = Field(None, description="Video generation mode speed parameter")
    video_workflow: Optional[str] = Field(None, description="Override Video Workflow template")
    image_variant: Optional[str] = Field(None, description="Image variant (then/now)")
    video_variant: Optional[str] = Field(None, description="Video variant (meeting/departure)")
    append_image_prompt: Optional[str] = Field(None, description="Append image prompt position ('none', 'start', 'end')")

    # Project metadata for display
    project_title: Optional[str] = Field(None, description="Project title")
    scene_name: Optional[str] = Field(None, description="Scene name")
    shot_id: Optional[str] = Field(None, description="Shot UUID")

    class Config:
        use_enum_values = False


class QueueStatistics(BaseModel):
    """Aggregated queue statistics"""
    total: int = Field(..., description="Total items in queue")
    queued: int = Field(..., description="Items waiting to be processed")
    active: int = Field(..., description="Items currently being processed")
    completed: int = Field(..., description="Items completed successfully")
    cancelled: int = Field(..., description="Items cancelled by user")
    failed: int = Field(..., description="Items that failed with errors")
    paused: int = Field(default=0, description="Items currently paused")

    # Breakdown by type
    images: int = Field(default=0, description="Image generations (including THEN/NOW)")
    videos: int = Field(default=0, description="Video generations (including meeting/departure)")
    flfi2v: int = Field(default=0, description="FLFI2V items (multi-generation shots)")
    narrations: int = Field(default=0, description="Narration generations")
    backgrounds: int = Field(default=0, description="Background generations")

    # Project counts
    total_projects: int = Field(default=0, description="Number of unique projects in queue")

    class Config:
        use_enum_values = False


class ReorderRequest(BaseModel):
    """Request to reorder queue items"""
    item_ids: List[str] = Field(..., description="Ordered list of item IDs")


class PriorityUpdateRequest(BaseModel):
    """Request to update item priority"""
    priority: int = Field(..., ge=0, le=1000, description="New priority value (lower = higher priority)")


class BulkActionRequest(BaseModel):
    """Request for bulk actions on queue items"""
    item_ids: List[str] = Field(..., description="List of item IDs to act upon")
