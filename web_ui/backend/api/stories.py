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
from pydantic import BaseModel, Field
from typing import Optional

class GenerateCharacterReferenceRequest(BaseModel):
    variant: str = Field(..., description="'then', 'now', or 'character'")
    prompt_override: Optional[str] = None
    image_mode: Optional[str] = None
    image_workflow: Optional[str] = None
    seed: Optional[int] = None
    gemini_mode: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_thinking: Optional[str] = None
from web_ui.backend.services.project_service import ProjectService
from web_ui.backend.services.generation_service import get_generation_service
from core.story_engine import build_story, normalize_scene_ids
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


@router.delete("/scenes/{scene_id}/narration")
async def delete_scene_narration(project_id: str, scene_id: int):
    """Delete the generated narration audio for a scene (active + all variations)"""
    try:
        project_dir = project_manager.get_project_dir(project_id)
        story_path = os.path.join(project_dir, "story.json")
        with open(story_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)

        scenes = story_data.get('scenes', [])
        if scene_id < 0 or scene_id >= len(scenes):
            raise ValueError(f"Scene index {scene_id} out of range")

        scene = scenes[scene_id]

        # Collect every narration file referenced by the scene
        rel_paths = list(scene.get('narration_paths', []))
        if scene.get('narration_path') and scene['narration_path'] not in rel_paths:
            rel_paths.append(scene['narration_path'])

        narration_dir = os.path.realpath(os.path.join(project_dir, "narration"))
        deleted = []
        for rel_path in rel_paths:
            # rel paths look like "narration/scene_001_....wav"
            file_path = os.path.realpath(os.path.join(project_dir, rel_path))
            if not file_path.startswith(narration_dir + os.sep):
                logger.warning(f"Skipping narration path outside project narration dir: {rel_path}")
                continue
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted.append(rel_path)

        # Clear the narration refs on the FRESH story under the project lock
        def clear_scene_narration(current_story):
            current_scenes = current_story.get('scenes', [])
            if 0 <= scene_id < len(current_scenes):
                current_scenes[scene_id].pop('narration_path', None)
                current_scenes[scene_id].pop('narration_paths', None)

        story_data = project_manager.update_story_safely(project_id, clear_scene_narration) or story_data

        from web_ui.backend.websocket.manager import manager
        manager.broadcast_sync(project_id, {
            "type": "narration_deleted",
            "project_id": project_id,
            "scene_id": scene_id,
            "deleted": deleted
        })

        return {"status": "success", "deleted": deleted}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
    except Exception as e:
        logger.error(f"Error deleting narration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete narration: {str(e)}"
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

        # Update active path on the FRESH story under the project lock
        def select_scene_narration(current_story):
            current_scenes = current_story.get('scenes', [])
            if 0 <= scene_id < len(current_scenes):
                current_scenes[scene_id]['narration_path'] = request.narration_path

        story_data = project_manager.update_story_safely(project_id, select_scene_narration) or story_data
        
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

        # Pin scene_ids to array positions (0-based) so shots, background
        # sheets and the r2v reference sync stay keyed to the right scenes
        normalize_scene_ids(story)

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


@router.post("/generate")
async def generate_story(project_id: str, request: RegenerateStoryRequest):
    """Generate story with new director"""
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

        from web_ui.backend.models.story import ProjectType

        # Import ASMR story builder
        from core.story_engine import build_story_asmr_glass_cutting

        is_then_vs_now = meta.get('project_type') == ProjectType.THEN_VS_NOW or request.director == "then_vs_now" or request.director.startswith("then_vs_now/")
        is_asmr = meta.get('project_type') == ProjectType.ASMR_GLASS_CUTTING or request.director == "asmr_glass_cutting" or request.director.startswith("asmr/")

        if is_asmr:
            logger.info(f"Generating ASMR glass cutting story with director: {request.director}")
            story_json = build_story_asmr_glass_cutting(
                idea=idea,
                director_name=request.director,
                shot_duration=meta.get("shot_duration", 5),
                aspect_ratio=aspect_ratio
            )
            story = json.loads(story_json)
            shots = story.pop('shots', [])

            # Save story.json
            project_manager.save_story(project_id, json.dumps(story, indent=2, ensure_ascii=False))

            # Update shots.json
            project_manager.save_shots(project_id, shots)

            # Update project metadata (fresh meta read under the project lock)
            def mark_asmr_story_meta(current_meta):
                current_meta['steps']['story'] = True
                current_meta['stats']['total_shots'] = len(shots)
            meta = project_manager.update_meta_safely(project_id, mark_asmr_story_meta) or meta

            return {
                "story": story,
                "shots": shots,
                "meta": meta
            }

        elif is_then_vs_now:
            from core.story_engine import build_story_then_vs_now

            logger.info(f"Regenerating ThenVsNow story with director: {request.director}")
            story_json = build_story_then_vs_now(
                movie_name=idea,
                director_name=request.director,
                target_length=target_length,
                aspect_ratio=aspect_ratio
            )
            story = json.loads(story_json)
            shots = story.pop('shots', [])
            
            # Save story.json
            project_manager.save_story(project_id, json.dumps(story, indent=2, ensure_ascii=False))

            # Save shots.json atomically under the project lock
            project_manager.save_shots(project_id, shots)
                
            # Update metadata (fresh meta read under the project lock)
            def mark_thenvsnow_meta(current_meta):
                current_meta['steps']['story'] = True
                current_meta['steps']['scene_graph'] = True
                current_meta['steps']['shots'] = True
                current_meta['stats']['total_shots'] = len(shots)
            project_manager.update_meta_safely(project_id, mark_thenvsnow_meta)
            
            logger.info(f"ThenVsNow story regenerated with {len(shots)} shots")
            return project_service.get_project(project_id)
        else:
            story_json = build_story(idea, request.director, target_length, aspect_ratio)
            # The dedicated ThenVsNow/ASMR builders stamp project_type into the
            # story themselves; the generic (documentary/movie) path doesn't —
            # stamp it from project metadata so clients can group by type.
            try:
                story_data = json.loads(story_json)
                story_data['project_type'] = story_data.get('project_type') or meta.get('project_type', ProjectType.DOCUMENTARY)
                story_json = json.dumps(story_data, indent=2, ensure_ascii=False)
            except Exception:
                pass
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
        variant: "then", "now", or "character" - which variant to upload
        file: Image file to upload
    """
    try:
        # Validate variant
        if variant not in ["then", "now", "character"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid variant '{variant}'. Must be 'then', 'now', or 'character'"
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

        # Update character model on the FRESH story under the project lock
        field_name = f"{variant}_reference_image_path"
        relative_path = f"output/projects/{project_id}/references/{unique_filename}"

        def set_character_ref(current_story):
            current_characters = current_story.get('characters', [])
            if 0 <= character_index < len(current_characters):
                current_characters[character_index][field_name] = relative_path

        story_data = project_manager.update_story_safely(project_id, set_character_ref) or story_data

        # Character references flow to shots as asset references — attach the
        # uploaded image to the character's shots so generation picks it up from
        # reference_asset_ids instead of name matching.
        if variant == "character":
            try:
                project_manager.sync_character_asset_refs(project_id)
            except Exception as sync_err:
                logger.warning(f"Could not sync character asset refs after upload: {sync_err}")

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


@router.post("/characters/{character_index}/generate-reference")
async def generate_character_reference(
    project_id: str,
    character_index: int,
    request: GenerateCharacterReferenceRequest
):
    """Generate reference image for a character using AI"""
    try:
        if request.variant not in ["then", "now", "character"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid variant '{request.variant}'. Must be 'then', 'now', or 'character'"
            )

        generation_service.queue_character_image(
            project_id=project_id,
            character_index=character_index,
            request=request
        )

        return {
            "status": "queued",
            "character_index": character_index,
            "variant": request.variant,
            "message": f"{request.variant.upper()} reference image generation added to queue"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queueing character reference generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue reference image generation: {str(e)}"
        )


@router.post("/props/{prop_index}/generate-reference")
async def generate_prop_reference(
    project_id: str,
    prop_index: int,
    request: GenerateCharacterReferenceRequest
):
    """Generate reference sheet for a story prop (r2v projects).

    Mirrors the character reference endpoint; prop_index indexes story.props.
    """
    try:
        story = project_manager.get_story(project_id)
        props = (story or {}).get('props') or []
        if not (0 <= prop_index < len(props)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prop index {prop_index} not found (story has {len(props)} prop(s))"
            )

        from web_ui.backend.models.queue import QueueItem, QueueItemStatus, GenerationType
        from web_ui.backend.services.queue_service import get_queue_service
        from web_ui.backend.services.generation_service import get_generation_service

        generation_service = get_generation_service()
        generation_service._ensure_queue_processor_started()
        item = QueueItem(
            item_id="",
            project_id=project_id,
            character_index=prop_index,
            generation_type=GenerationType.PROP_IMAGE,
            prompt_override=getattr(request, 'prompt_override', None),
            image_mode=getattr(request, 'image_mode', None),
            image_workflow=getattr(request, 'image_workflow', None),
            seed=getattr(request, 'seed', None),
            gemini_mode=getattr(request, 'gemini_mode', None),
            status=QueueItemStatus.QUEUED,
            progress=0,
            priority=40,
        )
        added = get_queue_service().add_items([item])
        generation_service._wake_up_processor()

        return {
            "status": "queued",
            "prop_index": prop_index,
            "message": "Prop reference sheet generation added to queue"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queueing prop reference generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue prop reference generation: {str(e)}"
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

        # Update scene model on the FRESH story under the project lock
        relative_path = f"output/projects/{project_id}/backgrounds/{unique_filename}"

        def set_scene_background(current_story):
            for current_scene in current_story.get('scenes', []):
                if current_scene.get('scene_id') == scene_id:
                    current_scene['background_image_path'] = relative_path
                    current_scene['background_generated'] = True
                    current_scene['background_is_generated'] = False  # Uploaded, not generated
                    return

        story_data = project_manager.update_story_safely(project_id, set_scene_background) or story_data

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

        # Check if scene has set_prompt. Reference-sheet (r2v) projects don't
        # need one: the queue handler builds the background-sheet prompt from
        # the scene location (background_sheet_prompt).
        set_prompt = scene.get('set_prompt')
        if not set_prompt:
            vgt = generation_service._get_project_video_generation_type(project_id) or 'i2v'
            if not (vgt == 'r2v' and scene.get('location')):
                detail = (f"Scene {scene_id} does not have a set_prompt for background generation")
                if vgt == 'r2v':
                    detail += " (add a scene location to generate a reference-sheet background)"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=detail
                )

        # Add to background generation queue
        generation_service.add_background_to_queue(
            project_id=project_id,
            scene_id=scene_id,
            request=request
        )

        return {
            "status": "queued",
            "scene_id": scene_id,
            "message": f"Background generation for scene {scene_id} added to queue"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating scene background: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start background generation: {str(e)}"
        )
