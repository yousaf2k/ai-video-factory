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
    video_paths: List[str] = Field(default_factory=list, description="All video paths (for variations)")
    scene_id: Optional[int] = Field(default=None, description="ID of the scene this shot belongs to")
    character_name: Optional[str] = Field(default=None, description="Human-readable character name")
    scene_name: Optional[str] = Field(default=None, description="Human-readable scene name")
    order_in_scene: Optional[int] = Field(default=0, description="Position within scene (0-based)")

    # FLFI2V mode fields
    is_flfi2v: bool = Field(default=False, description="Whether this shot uses FLFI2V (first/last frame image to video)")
    character_id: Optional[str] = Field(default=None, description="Character ID for FLFI2V shots")
    then_image_prompt: Optional[str] = Field(default=None, description="Prompt for THEN image (original appearance)")
    then_image_path: Optional[str] = Field(default=None, description="Path to THEN image")
    then_image_generated: bool = Field(default=False, description="Whether THEN image has been generated")
    now_image_prompt: Optional[str] = Field(default=None, description="Prompt for NOW image (current appearance)")
    now_image_path: Optional[str] = Field(default=None, description="Path to NOW image")
    now_image_generated: bool = Field(default=False, description="Whether NOW image has been generated")
    meeting_video_prompt: Optional[str] = Field(default=None, description="Prompt for meeting video")
    meeting_video_path: Optional[str] = Field(default=None, description="Path to meeting video")
    meeting_video_rendered: bool = Field(default=False, description="Whether meeting video has been rendered")
    departure_video_prompt: Optional[str] = Field(default=None, description="Prompt for departure/transitional video")
    departure_video_path: Optional[str] = Field(default=None, description="Path to departure video")
    departure_video_rendered: bool = Field(default=False, description="Whether departure video has been rendered")

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
    scene_id: Optional[int] = None
    # FLFI2V fields
    then_image_prompt: Optional[str] = None
    now_image_prompt: Optional[str] = None
    meeting_video_prompt: Optional[str] = None
    departure_video_prompt: Optional[str] = None


class RegenerateImageRequest(BaseModel):
    """Request to regenerate single shot image"""
    force: bool = Field(default=False, description="Force regeneration even if image exists")
    image_mode: Optional[str] = Field(default=None, description="Override image generation mode (gemini/comfyui)")
    image_workflow: Optional[str] = Field(default=None, description="Override image workflow for ComfyUI (e.g. flux2, sdxl)")
    seed: Optional[int] = Field(default=None, description="Optional specific seed for regeneration")
    prompt_override: Optional[str] = Field(default=None, description="Override the image prompt for this generation only")
    image_variant: Optional[str] = Field(default=None, description="Image variant for FLFI2V: 'then', 'now', or 'both'")



class RegenerateVideoRequest(BaseModel):
    """Request to regenerate single shot video"""
    force: bool = Field(default=False, description="Force regeneration even if video exists")
    video_mode: Optional[str] = Field(default=None, description="Override video generation mode (geminiweb/comfyui)")
    video_workflow: Optional[str] = Field(default=None, description="Override video workflow")
    video_variant: Optional[str] = Field(default=None, description="Video variant for FLFI2V: 'meeting', 'departure', or 'both'")


class BatchRegenerateRequest(BaseModel):
    """Request to batch regenerate shots"""
    shot_indices: List[int] = Field(..., description="List of shot indices to regenerate")
    regenerate_images: bool = Field(default=True, description="Regenerate images")
    regenerate_videos: bool = Field(default=True, description="Regenerate videos")
    force: bool = Field(default=False, description="Force regeneration (legacy, use granular flags)")
    force_images: Optional[bool] = Field(default=None, description="Force image regeneration")
    force_videos: Optional[bool] = Field(default=None, description="Force video regeneration")
    image_mode: Optional[str] = Field(default=None, description="Override image generation mode")
    image_workflow: Optional[str] = Field(default=None, description="Override image workflow")
    video_mode: Optional[str] = Field(default=None, description="Override video generation mode")
    video_workflow: Optional[str] = Field(default=None, description="Override video workflow")


class ReplanShotsRequest(BaseModel):
    """Request to re-plan shots from story"""
    max_shots: Optional[int] = Field(default=None, description="Maximum shots to generate")
    shots_agent: str = Field(default="default", description="Shots agent to use")


class SelectImageRequest(BaseModel):
    """Request to select a specific image as the active one for a shot"""
    image_path: str = Field(..., description="Path of the image to set as active")


class SelectVideoRequest(BaseModel):
    """Request to select a specific video as the active one for a shot"""
    video_path: str = Field(..., description="Path of the video to set as active")


class RemoveWatermarkRequest(BaseModel):
    """Request to remove watermark from a shot image"""
    variant: Optional[str] = Field(default=None, description="Image variant for FLFI2V: 'then' or 'now'")

