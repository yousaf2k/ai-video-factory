"""
Pydantic models for story data
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import IntEnum


class ProjectType(IntEnum):
    """Project type enumeration"""
    DOCUMENTARY = 1
    THEN_VS_NOW = 2


class MovieMetadata(BaseModel):
    """Movie metadata for ThenVsNow projects"""
    year: Optional[int] = Field(default=None, description="Movie release year")
    cast: List[str] = Field(default_factory=list, description="List of cast members with their roles")
    director: Optional[str] = Field(default=None, description="Movie director")
    genre: Optional[str] = Field(default=None, description="Movie genre")


class YouTubeMetadata(BaseModel):
    """YouTube metadata for video publishing"""
    title_options: List[str] = Field(default_factory=list, description="SEO-optimized title options")
    seo_keywords: List[str] = Field(default_factory=list, description="SEO keywords for discoverability")
    chapters: List[Dict[str, Any]] = Field(default_factory=list, description="Video chapters with timestamps")
    description_preview: Optional[str] = Field(default=None, description="First 200 characters of description")


class Character(BaseModel):
    """Character model for ThenVsNow projects"""
    name: str = Field(..., description="Character/Actor name")
    scene_id: Optional[int] = Field(default=0, description="Scene ID this character belongs to")
    then_prompt: Optional[str] = Field(default=None, description="Prompt for THEN image (original appearance)")
    now_prompt: Optional[str] = Field(default=None, description="Prompt for NOW image (current appearance)")
    meeting_prompt: Optional[str] = Field(default=None, description="Prompt for meeting video")
    departure_prompt: Optional[str] = Field(default=None, description="Prompt for departure/transitional video")
    then_reference_image_path: Optional[str] = Field(default=None, description="Path to THEN reference photo for facial consistency")
    now_reference_image_path: Optional[str] = Field(default=None, description="Path to NOW reference photo for facial consistency")


class Scene(BaseModel):
    """Story scene model"""
    scene_name: Optional[str] = Field(default=None, description="Human-readable scene name (e.g., 'Main Cast', 'Supporting Cast')")
    location: str = Field(..., description="Scene location")
    characters: str = Field(..., description="Characters in scene")
    action: str = Field(..., description="Action happening")
    emotion: str = Field(..., description="Emotional tone")
    narration: str = Field(..., description="Narration text")
    scene_duration: Optional[int] = Field(default=None, description="Scene duration in seconds")
    narration_path: Optional[str] = Field(default=None, description="Active narration audio path")
    narration_paths: List[str] = Field(default_factory=list, description="All narration audio variations")
    set_prompt: Optional[str] = Field(default=None, description="Movie set background prompt (for ThenVsNow)")
    scene_image_path: Optional[str] = Field(default=None, description="Path to generated scene/set image (for departure video last frame)")
    background_image_path: Optional[str] = Field(default=None, description="Path to scene background image (uploaded or AI-generated)")
    background_generated: bool = Field(default=False, description="Whether background has been generated/uploaded")
    background_is_generated: bool = Field(default=False, description="True if AI-generated, False if uploaded")


class Story(BaseModel):
    """Story model"""
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    thumbnail_prompt_16_9: Optional[str] = None
    thumbnail_prompt_9_16: Optional[str] = None
    style: str
    total_duration: Optional[int] = None
    scenes: List[Scene]
    project_type: ProjectType = Field(default=ProjectType.DOCUMENTARY, description="Project type (documentary or then_vs_now)")
    characters: Optional[List[Character]] = Field(default=None, description="Characters for ThenVsNow projects")
    youtube_metadata: Optional[YouTubeMetadata] = Field(default=None, description="YouTube publishing metadata")
    movie_metadata: Optional[MovieMetadata] = Field(default=None, description="Movie metadata for ThenVsNow projects")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "The Last Roman Kingdom",
                "style": "Ultra cinematic documentary",
                "scenes": [
                    {
                        "location": "Roman Colosseum",
                        "characters": "Gladiators",
                        "action": "Fighting",
                        "emotion": "Tense",
                        "narration": "The crowd roars...",
                        "scene_duration": 60
                    }
                ]
            }
        }


class UpdateStoryRequest(BaseModel):
    """Request to update story"""
    story: Dict[str, Any]


class RegenerateStoryRequest(BaseModel):
    """Request to regenerate story"""
    agent: str = Field(default="default", description="New agent to use")


class GenerateSceneNarrationRequest(BaseModel):
    """Request to generate narration for a scene"""
    tts_method: Optional[str] = Field(default=None, description="TTS method override")
    tts_workflow: Optional[str] = Field(default=None, description="TTS workflow key")
    voice: Optional[str] = Field(default=None, description="Voice override")


class BatchGenerateNarrationRequest(BaseModel):
    """Request to batch generate narration for multiple scenes"""
    scene_indices: List[int] = Field(..., description="List of 0-based scene indices")
    tts_method: Optional[str] = None
    tts_workflow: Optional[str] = None
    voice: Optional[str] = None


class SelectSceneNarrationRequest(BaseModel):
    """Request to select active narration for a scene"""
    narration_path: str = Field(..., description="Relative path of the narration variation to set as active")
