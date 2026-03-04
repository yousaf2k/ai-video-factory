"""
Pydantic models for shot data
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid

class Shot(BaseModel):
    """Shot model"""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8], description="Unique stable ID for this shot")
    index: int = Field(..., description="Shot index (1-based)")
    image_prompt: str = Field(..., description="Image generation prompt")
    motion_prompt: str = Field(..., description="Motion/video generation prompt")
    camera: str = Field(..., description="Camera movement type")
    narration: str = Field(default="", description="Shot narration")
    batch_number: int = Field(default=1, description="Batch number for multi-batch generation")
    image_generated: bool = Field(default=False, description="Whether image has been generated")
    image_path: Optional[str] = Field(default=None, description="Path to generated image")
    image_paths: List[str] = Field(default_factory=list, description="All image paths (for variations)")
    video_rendered: bool = Field(default=False, description="Whether video has been rendered")
    video_path: Optional[str] = Field(default=None, description="Path to rendered video")

    class Config:
        json_schema_extra = {
            "example": {
                "index": 1,
                "image_prompt": "A Roman soldier standing guard",
                "motion_prompt": "Camera slowly pans across the scene",
                "camera": "slow pan",
                "narration": "The soldiers stood vigilant",
                "batch_number": 1,
                "image_generated": True,
                "image_path": "output/sessions/session_xxx/images/shot_001.png",
                "image_paths": [],
                "video_rendered": False,
                "video_path": None
            }
        }


class UpdateShotsRequest(BaseModel):
    """Request to update shots (reorder, edit)"""
    shots: List[Dict[str, Any]]


class UpdateShotRequest(BaseModel):
    """Request to update a single shot"""
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    camera: Optional[str] = None
    narration: Optional[str] = None


class RegenerateImageRequest(BaseModel):
    """Request to regenerate single shot image"""
    force: bool = Field(default=False, description="Force regeneration even if image exists")
    image_mode: Optional[str] = Field(default=None, description="Override image generation mode (gemini/comfyui)")
    image_workflow: Optional[str] = Field(default=None, description="Override image workflow for ComfyUI (e.g. flux2, sdxl)")
    seed: Optional[int] = Field(default=None, description="Optional specific seed for regeneration")
    prompt_override: Optional[str] = Field(default=None, description="Override the image prompt for this generation only")



class RegenerateVideoRequest(BaseModel):
    """Request to regenerate single shot video"""
    force: bool = Field(default=False, description="Force regeneration even if video exists")
    video_workflow: Optional[str] = Field(default=None, description="Override video workflow")


class BatchRegenerateRequest(BaseModel):
    """Request to batch regenerate shots"""
    shot_indices: List[int] = Field(..., description="List of shot indices to regenerate")
    regenerate_images: bool = Field(default=True, description="Regenerate images")
    regenerate_videos: bool = Field(default=True, description="Regenerate videos")
    force: bool = Field(default=False, description="Force regeneration")
    image_mode: Optional[str] = Field(default=None, description="Override image generation mode")
    image_workflow: Optional[str] = Field(default=None, description="Override image workflow")
    video_workflow: Optional[str] = Field(default=None, description="Override video workflow")


class ReplanShotsRequest(BaseModel):
    """Request to re-plan shots from story"""
    max_shots: Optional[int] = Field(default=None, description="Maximum shots to generate")
    shots_agent: str = Field(default="default", description="Shots agent to use")


class SelectImageRequest(BaseModel):
    """Request to select a specific image as the active one for a shot"""
    image_path: str = Field(..., description="Path of the image to set as active")

