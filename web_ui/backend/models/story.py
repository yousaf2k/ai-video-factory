"""
Pydantic models for story data
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Scene(BaseModel):
    """Story scene model"""
    location: str = Field(..., description="Scene location")
    characters: str = Field(..., description="Characters in scene")
    action: str = Field(..., description="Action happening")
    emotion: str = Field(..., description="Emotional tone")
    narration: str = Field(..., description="Narration text")
    scene_duration: Optional[int] = Field(default=None, description="Scene duration in seconds")
    narration_path: Optional[str] = Field(default=None, description="Active narration audio path")
    narration_paths: List[str] = Field(default_factory=list, description="All narration audio variations")


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
