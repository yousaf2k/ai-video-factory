"""
Configuration API endpoints
"""
from fastapi import APIRouter, HTTPException
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from core.agent_loader import list_agents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/agents")
async def get_agents():
    """Get list of available agents for each stage"""
    try:
        # List all agents
        all_agents = list_agents()

        # Group by type
        agents_by_type = {
            "story": [],
            "image": [],
            "video": [],
            "narration": []
        }

        for agent_info in all_agents:
            agent_type = agent_info.get("type", "unknown")
            agent_id = agent_info.get("id", "unknown")
            agent_name = agent_info.get("name", agent_id)

            if agent_type in agents_by_type:
                agents_by_type[agent_type].append({
                    "id": agent_id,
                    "name": agent_name,
                    "type": agent_type
                })

        # Sort alphabetically by name
        for agent_type in agents_by_type:
            agents_by_type[agent_type].sort(key=lambda x: x["name"])

        return agents_by_type

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.get("")
async def get_config():
    """Get all configuration values (safe subset)"""
    try:
        import config

        # Return safe configuration values
        safe_config = {
            "llm_provider": config.LLM_PROVIDER,
            "image_generation_mode": config.IMAGE_GENERATION_MODE,
            "video_generation_mode": getattr(config, 'VIDEO_GENERATION_MODE', 'comfyui'),
            "default_story_agent": getattr(config, 'DEFAULT_STORY_AGENT', 'default'),
            "default_image_agent": getattr(config, 'DEFAULT_IMAGE_AGENT', 'default'),
            "default_video_agent": getattr(config, 'DEFAULT_VIDEO_AGENT', 'default'),
            "comfy_url": getattr(config, 'COMFY_URL', 'http://127.0.0.1:8188'),
            "target_video_length": getattr(config, 'TARGET_VIDEO_LENGTH', None),
        }

        return safe_config

    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get config: {str(e)}"
        )
