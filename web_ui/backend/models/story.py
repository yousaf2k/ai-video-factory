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
