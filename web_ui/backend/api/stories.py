"""
Stories API endpoints
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
import sys
import os
import json
import logging
import asyncio
import uuid
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from web_ui.backend.models.story import (
    UpdateStoryRequest, RegenerateStoryRequest,
    GenerateSceneNarrationRequest, BatchGenerateNarrationRequest,
    SelectSceneNarrationRequest, BackgroundGenerationRequest
)
from web_ui.backend.services.project_service import ProjectService
from web_ui.backend.services.generation_service import get_generation_service
from core.story_engine import build_story
from core.project_manager import ProjectManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects/{project_id}/story", tags=["stories"])

# Initialize services
project_service = ProjectService()
project_manager = ProjectManager()
generation_service = get_generation_service()


@router.post("/scenes/{scene_id}/generate-narration")
async def generate_scene_narration(project_id: str, scene_id: int, request: GenerateSceneNarrationRequest):
    """Generate narration for a single scene"""
    try:
        # Start background task
        asyncio.create_task(generation_service.regenerate_scene_narration(
            project_id, scene_id,
            tts_method=request.tts_method,
            tts_workflow=request.tts_workflow,
            voice=request.voice
        ))
        return {"status": "queued", "message": f"Narration generation for scene {scene_id} started"}
    except Exception as e:
        logger.error(f"Error starting narration generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start narration generation: {str(e)}"
        )


@router.post("/batch-generate-narration")
async def batch_generate_narration(project_id: str, request: BatchGenerateNarrationRequest):
    """Batch generate narration for multiple scenes"""
    try:
        # Start background task
        asyncio.create_task(generation_service.run_batch_narration_generation(
            project_id, request
        ))
        return {"status": "queued", "message": f"Batch narration generation for {len(request.scene_indices)} scenes started"}
    except Exception as e:
        logger.error(f"Error starting batch narration generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch narration generation: {str(e)}"
        )


@router.post("/scenes/{scene_id}/cancel-narration")
async def cancel_scene_narration(project_id: str, scene_id: int):
    """Cancel narration generation for a scene"""
    try:
        generation_service.cancel_scene_narration(project_id, scene_id)
        return {"status": "success", "message": f"Cancelled narration for scene {scene_id}"}
    except Exception as e:
        logger.error(f"Error cancelling narration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel narration: {str(e)}"
        )


@router.post("/scenes/{scene_id}/select-narration")
async def select_scene_narration(project_id: str, scene_id: int, request: SelectSceneNarrationRequest):
    """Select the active narration variation for a scene"""
    try:
        # Load story
        project_dir = project_manager.get_project_dir(project_id)
        story_path = os.path.join(project_dir, "story.json")
        with open(story_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)
        
        scenes = story_data.get('scenes', [])
        if scene_id < 0 or scene_id >= len(scenes):
            raise ValueError(f"Scene index {scene_id} out of range")
        
        scene = scenes[scene_id]
        
        # Verify the path exists in narration_paths
        if 'narration_paths' not in scene or request.narration_path not in scene['narration_paths']:
            raise ValueError("Narration path not found in variations")
        
        # Update active path
        scene['narration_path'] = request.narration_path
        
        # Save story
        with open(story_path, 'w', encoding='utf-8') as f:
            json.dump(story_data, f, indent=4)
        
        # Broadcast the change
        from web_ui.backend.websocket.manager import manager
        manager.broadcast_sync(project_id, {
            "type": "narration_selected",
            "project_id": project_id,
            "scene_id": scene_id,
            "narration_path": request.narration_path
        })
        
        return {"status": "success", "narration_path": request.narration_path}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error selecting narration: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("")
async def get_story(project_id: str):
    """Get story JSON"""
    try:
        project = project_service.get_project(project_id)
        if not project.story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found for this project"
            )
        return project.story
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting story: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get story: {str(e)}"
        )


@router.put("")
async def update_story(project_id: str, request: UpdateStoryRequest):
    """Update story JSON"""
    try:
        # Load project metadata
        meta = project_manager.load_project(project_id)

        # Validate story structure
        story = request.story
        if not isinstance(story, dict):
            raise ValueError("Story must be a dictionary")

        if "scenes" not in story or not isinstance(story["scenes"], list):
            raise ValueError("Story must contain a 'scenes' array")

        # Validate scene durations if present
        for scene in story["scenes"]:
            if "scene_duration" in scene:
                duration = scene["scene_duration"]
                if not isinstance(duration, int) or duration < 5:
                    raise ValueError(f"Invalid scene_duration: {duration}. Must be at least 5 seconds")

        # Save story
        story_json = json.dumps(story, ensure_ascii=False, indent=2)
        project_manager.save_story(project_id, story_json)

        # Return updated project
        return project_service.get_project(project_id)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating story: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update story: {str(e)}"
        )


@router.post("/regenerate")
async def regenerate_story(project_id: str, request: RegenerateStoryRequest):
    """Regenerate story with new agent"""
    try:
        # Load project
        meta = project_manager.load_project(project_id)
        idea = meta["idea"]

        # Generate new story
        import config
        # Use total_duration from meta if exists, otherwise fallback to config
        target_length = meta.get("total_duration")
        if target_length is None:
            target_length = config.TARGET_VIDEO_LENGTH if hasattr(config, 'TARGET_VIDEO_LENGTH') else None

        # Get aspect_ratio from meta, default to 16:9
        aspect_ratio = meta.get("aspect_ratio", "16:9")

        story_json = build_story(idea, request.agent, target_length, aspect_ratio)

        # Save story
        project_manager.save_story(project_id, story_json)

        # Return updated project
        return project_service.get_project(project_id)

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error regenerating story: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate story: {str(e)}"
        )


@router.post("/characters/{character_index}/upload-reference")
async def upload_character_reference(
    project_id: str,
    character_index: int,
    variant: str,
    file: UploadFile = File(...)
):
    """
    Upload reference image for a character (THEN or NOW variant)

    Args:
        project_id: Project identifier
        character_index: 0-based index of the character in story.characters
        variant: "then" or "now" - which variant to upload
        file: Image file to upload
    """
    try:
        # Validate variant
        if variant not in ["then", "now"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid variant '{variant}'. Must be 'then' or 'now'"
            )

        # Load story
        project_dir = project_manager.get_project_dir(project_id)
        story_path = os.path.join(project_dir, "story.json")

        if not os.path.exists(story_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story not found for project {project_id}"
            )

        with open(story_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)

        characters = story_data.get('characters', [])

        if character_index < 0 or character_index >= len(characters):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Character index {character_index} out of range (0-{len(characters)-1})"
            )

        character = characters[character_index]

        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        # Create references directory
        import config
        references_dir = os.path.join(project_dir, "references")
        os.makedirs(references_dir, exist_ok=True)

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.png'
        unique_filename = f"{uuid.uuid4().hex[:8]}_{variant}_ref{file_extension}"
        file_path = os.path.join(references_dir, unique_filename)

        # Save uploaded file
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # Update character model
        field_name = f"{variant}_reference_image_path"
        relative_path = f"output/projects/{project_id}/references/{unique_filename}"
        character[field_name] = relative_path

        # Save story
        with open(story_path, 'w', encoding='utf-8') as f:
            json.dump(story_data, f, indent=4, ensure_ascii=False)

        # Broadcast update
        from web_ui.backend.websocket.manager import manager
        manager.broadcast_sync(project_id, {
            "type": "story_updated",
            "project_id": project_id,
            "story": story_data
        })

        logger.info(f"Uploaded {variant.upper()} reference for character {character_index}: {unique_filename}")

        return {
            "status": "success",
            "character_index": character_index,
            "variant": variant,
            "image_path": relative_path,
            "message": f"{variant.upper()} reference image uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading character reference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload reference image: {str(e)}"
        )


@router.post("/scenes/{scene_id}/upload-background")
async def upload_scene_background(
    project_id: str,
    scene_id: int,
    file: UploadFile = File(...)
):
    """
    Upload background image for a scene

    Args:
        project_id: Project identifier
        scene_id: Scene ID in the story
        file: Background image file to upload
    """
    try:
        # Load story
        project_dir = project_manager.get_project_dir(project_id)
        story_path = os.path.join(project_dir, "story.json")

        if not os.path.exists(story_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story not found for project {project_id}"
            )

        with open(story_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)

        scenes = story_data.get('scenes', [])

        # Find scene by scene_id
        scene = None
        scene_index = -1
        for i, s in enumerate(scenes):
            if s.get('scene_id') == scene_id:
                scene = s
                scene_index = i
                break

        if scene is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene with scene_id {scene_id} not found"
            )

        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        # Create backgrounds directory
        backgrounds_dir = os.path.join(project_dir, "backgrounds")
        os.makedirs(backgrounds_dir, exist_ok=True)

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.png'
        unique_filename = f"scene_{scene_id}_background{file_extension}"
        file_path = os.path.join(backgrounds_dir, unique_filename)

        # Save uploaded file
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # Update scene model
        relative_path = f"output/projects/{project_id}/backgrounds/{unique_filename}"
        scenes[scene_index]['background_image_path'] = relative_path
        scenes[scene_index]['background_generated'] = True
        scenes[scene_index]['background_is_generated'] = False  # Uploaded, not generated

        # Save story
        with open(story_path, 'w', encoding='utf-8') as f:
            json.dump(story_data, f, indent=4, ensure_ascii=False)

        # Broadcast update
        from web_ui.backend.websocket.manager import manager
        manager.broadcast_sync(project_id, {
            "type": "story_updated",
            "project_id": project_id,
            "story": story_data
        })

        logger.info(f"Uploaded background for scene {scene_id}: {unique_filename}")

        return {
            "status": "success",
            "scene_id": scene_id,
            "image_path": relative_path,
            "source": "uploaded",
            "message": "Background image uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading scene background: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload background: {str(e)}"
        )


@router.post("/scenes/{scene_id}/generate-background")
async def generate_scene_background(project_id: str, scene_id: int, request: BackgroundGenerationRequest):
    """
    Generate background image for a scene using AI

    Args:
        project_id: Project identifier
        scene_id: Scene ID in the story
    """
    try:
        # Load story
        project_dir = project_manager.get_project_dir(project_id)
        story_path = os.path.join(project_dir, "story.json")

        if not os.path.exists(story_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story not found for project {project_id}"
            )

        with open(story_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)

        scenes = story_data.get('scenes', [])

        # Find scene by scene_id
        scene = None
        scene_index = -1
        for i, s in enumerate(scenes):
            if s.get('scene_id') == scene_id:
                scene = s
                scene_index = i
                break

        if scene is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene with scene_id {scene_id} not found"
            )

        # Check if scene has set_prompt
        set_prompt = scene.get('set_prompt')
        if not set_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scene {scene_id} does not have a set_prompt for background generation"
            )

        # Start background generation task
        asyncio.create_task(generation_service.generate_scene_background(
            project_id=project_id, 
            scene_id=scene_id,
            set_prompt=set_prompt,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            seed=request.seed,
            workflow=request.workflow
        ))

        return {
            "status": "queued",
            "scene_id": scene_id,
            "message": f"Background generation for scene {scene_id} started"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating scene background: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start background generation: {str(e)}"
        )
