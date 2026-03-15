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
    FAILED = "failed"


class QueueItem(BaseModel):
    """Individual queue item with metadata"""
    item_id: str = Field(..., description="Unique identifier for this queue item")
    session_id: str = Field(..., description="Session identifier")
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

    # Session metadata for display
    session_title: Optional[str] = Field(None, description="Session title")
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

    # Breakdown by type
    images: int = Field(default=0, description="Image generations (including THEN/NOW)")
    videos: int = Field(default=0, description="Video generations (including meeting/departure)")
    flfi2v: int = Field(default=0, description="FLFI2V items (multi-generation shots)")
    narrations: int = Field(default=0, description="Narration generations")
    backgrounds: int = Field(default=0, description="Background generations")

    # Session counts
    total_sessions: int = Field(default=0, description="Number of unique sessions in queue")

    class Config:
        use_enum_values = False


class ReorderRequest(BaseModel):
    """Request to reorder queue items"""
    item_ids: List[str] = Field(..., description="Ordered list of item IDs")


class PriorityUpdateRequest(BaseModel):
    """Request to update item priority"""
    priority: int = Field(..., ge=0, le=1000, description="New priority value (lower = higher priority)")
