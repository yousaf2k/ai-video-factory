"""
Configuration API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from core.agent_loader import list_agents, get_agent_loader
from core.workflow_loader import get_workflow_loader
from core.config_utils import update_env_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


class UpdateConfigRequest(BaseModel):
    """Request to update global configuration"""
    llm_provider: Optional[str] = None
    image_generation_mode: Optional[str] = None
    comfy_url: Optional[str] = None
    target_video_length: Optional[int] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None


class UpdateAgentRequest(BaseModel):
    """Request to update an agent prompt file"""
    content: str


class UpdateWorkflowRequest(BaseModel):
    """Request to update a workflow JSON file"""
    content: str


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


@router.post("")
async def update_config(request: UpdateConfigRequest):
    """Update global configuration"""
    try:
        updates = {}
        if request.llm_provider is not None:
            updates["LLM_PROVIDER"] = request.llm_provider
        if request.image_generation_mode is not None:
            updates["IMAGE_GENERATION_MODE"] = request.image_generation_mode
        if request.comfy_url is not None:
            updates["COMFY_URL"] = request.comfy_url
        if request.target_video_length is not None:
            updates["TARGET_VIDEO_LENGTH"] = request.target_video_length
        if request.gemini_api_key is not None:
            updates["GEMINI_API_KEY"] = request.gemini_api_key
        if request.openai_api_key is not None:
            updates["OPENAI_API_KEY"] = request.openai_api_key
        if request.elevenlabs_api_key is not None:
            updates["ELEVENLABS_API_KEY"] = request.elevenlabs_api_key

        if updates:
            update_env_config(updates)
            
            # Reload config in the current process (limited effect but good for some values)
            import config
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
        return {"status": "success", "message": "Configuration updated. Restart may be required for some changes."}

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update config: {str(e)}"
        )


@router.get("/agents/{agent_type}/{agent_id}")
async def get_agent_content(agent_type: str, agent_id: str):
    """Get content of an agent prompt file"""
    try:
        loader = get_agent_loader()
        content = loader.load_prompt(agent_type, agent_id)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        logger.error(f"Error loading agent content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_type}/{agent_id}")
async def update_agent_content(agent_type: str, agent_id: str, request: UpdateAgentRequest):
    """Update content of an agent prompt file"""
    try:
        loader = get_agent_loader()
        loader.save_prompt(agent_type, agent_id, request.content)
        return {"status": "success", "message": f"Agent {agent_id} updated"}
    except Exception as e:
        logger.error(f"Error updating agent content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def get_workflows():
    """Get list of available workflows by category"""
    try:
        loader = get_workflow_loader()
        all_workflows = loader.get_all_workflows()
        
        # Group by category
        workflows_by_category = {}
        for workflow in all_workflows:
            category = workflow.get("category", "unknown")
            if category not in workflows_by_category:
                workflows_by_category[category] = []
            workflows_by_category[category].append(workflow)
            
        return workflows_by_category
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{category}/{filename}")
async def get_workflow_content(category: str, filename: str):
    """Get content of a workflow JSON file"""
    try:
        loader = get_workflow_loader()
        content = loader.load_workflow(category, filename)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error(f"Error loading workflow content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{category}/{filename}")
async def update_workflow_content(category: str, filename: str, request: UpdateWorkflowRequest):
    """Update content of a workflow JSON file"""
    try:
        loader = get_workflow_loader()
        loader.save_workflow(category, filename, request.content)
        return {"status": "success", "message": f"Workflow {filename} updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating workflow content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
