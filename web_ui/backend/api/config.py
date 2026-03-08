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
import asyncio
import threading
import subprocess

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
            "shots": [],
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
            "video_workflow": getattr(config, 'VIDEO_WORKFLOW', 'wan22'),
            "default_story_agent": getattr(config, 'DEFAULT_STORY_AGENT', 'default'),
            "default_shots_agent": getattr(config, 'DEFAULT_SHOTS_AGENT', 'default'),
            "comfy_url": getattr(config, 'COMFY_URL', 'http://127.0.0.1:8188'),
            "target_video_length": getattr(config, 'TARGET_VIDEO_LENGTH', None),
            "default_max_shots": getattr(config, 'DEFAULT_MAX_SHOTS', 0),
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
        if hasattr(request, 'video_workflow') and request.video_workflow is not None:
            updates["VIDEO_WORKFLOW"] = request.video_workflow
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
@router.post("/launch-browser")
async def launch_browser():
    """Launch a Playwright browser with persistent context and stealth"""
    try:
        def run_playwright():
            try:
                # Use a separate thread to run Playwright since it's interactive
                from playwright.sync_api import sync_playwright
                from playwright_stealth import stealth
                import config
                
                with sync_playwright() as p:
                    # Apply global hook if using version 2.0.x
                    try:
                        from playwright_stealth import Stealth
                        Stealth().hook_playwright_context(p)
                    except (ImportError, AttributeError):
                        pass
                        
                    # Use profile path from config to share session with image generation
                    profile_path = getattr(config, 'GEMINIWEB_CHROME_PROFILE', os.path.abspath(os.path.join("output", "chrome_profile")))
                    os.makedirs(profile_path, exist_ok=True)
                        
                    logger.info(f"Launching browser with profile: {profile_path}")
                    
                    # Launch persistent context with same settings as image generation
                    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
                    browser_type = getattr(p, browser_type_name, p.chromium)
                    
                    # Channel and args depend on browser type
                    channel = None
                    launch_args = []
                    
                    if browser_type_name == "chromium":
                        channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')
                        # Map to avoid "channel 'xxx' is not supported"
                        valid_chromium_channels = ["chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge", "msedge-beta", "msedge-dev", "msedge-canary"]
                        if channel not in valid_chromium_channels:
                            channel = None
                            
                        launch_args = [
                            "--start-maximized", 
                            "--disable-blink-features=AutomationControlled",
                            "--no-first-run",
                            "--no-default-browser-check",
                        ]
                        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    elif browser_type_name == "firefox":
                        launch_args = ["-start-maximized"]
                        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
                    else:
                        user_agent = None # Let Playwright decide

                    browser_context = browser_type.launch_persistent_context(
                        user_data_dir=profile_path,
                        headless=False,
                        channel=channel,
                        args=launch_args,
                        viewport={'width': 1280, 'height': 900},
                        user_agent=user_agent,
                        locale='en-US',
                        timezone_id='America/New_York',
                        ignore_default_args=['--enable-automation'],
                        no_viewport=False
                    )
                    
                    # Apply stealth to context - handle different versions of playwright-stealth
                    try:
                        # Version 2.0.x (class-based)
                        from playwright_stealth import Stealth
                        Stealth().apply_stealth_sync(browser_context)
                    except (ImportError, AttributeError):
                        # Version 1.x.x (function-based)
                        try:
                            from playwright_stealth import stealth_sync
                            stealth_sync(browser_context)
                        except (ImportError, AttributeError):
                            pass
                    
                    page = browser_context.pages[0]
                    page.goto("https://accounts.google.com")
                    
                    # Keep the browser open until the user closes it manually
                    # This is tricky in a backend process, but launch_persistent_context 
                    # will wait if we don't close it immediately. 
                    # However, to avoid blocking the whole thread forever, 
                    # we just let it run. In sync mode, it might block the thread.
                    
                    # We can use a simple loop or just page.pause() if we want it to stay
                    # but since it's a separate thread, blocking is fine.
                    # A better way is to wait for the page to be closed.
                    page.wait_for_event("close", timeout=0)
                    browser_context.close()
            except Exception as e:
                logger.error(f"Error in playwright thread: {e}")

        # Start browser in a background thread to not block the API response
        thread = threading.Thread(target=run_playwright, daemon=True)
        thread.start()
        
        return {"status": "success", "message": "Browser launched. Please check your desktop."}
    except ImportError:
        raise HTTPException(status_code=500, detail="playwright or playwright-stealth not installed. Please run pip install.")
    except Exception as e:
        logger.error(f"Error launching browser: {e}")
        raise HTTPException(status_code=500, detail=str(e))
