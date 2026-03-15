"""
Shots API endpoints
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File
import sys
import os
import json
import logging
import uuid
import re
import shutil
import config

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from web_ui.backend.models.shot import (
    UpdateShotsRequest, UpdateShotRequest, RegenerateImageRequest,
    RegenerateVideoRequest, BatchRegenerateRequest, ReplanShotsRequest,
    SelectImageRequest, SelectVideoRequest, RemoveWatermarkRequest
)
from web_ui.backend.services.project_service import ProjectService
from web_ui.backend.services.generation_service import get_generation_service
from web_ui.backend.models.shot import Shot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects/{project_id}/shots", tags=["shots"])

# Initialize services
project_service = ProjectService()
generation_service = get_generation_service()


@router.get("")
async def get_shots(project_id: str):
    """Get all shots for a project"""
    try:
        project = project_service.get_project(project_id)
        return project.shots or []
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting shots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shots: {str(e)}"
        )


@router.get("/queue-status")
async def get_queue_status(project_id: str):
    """Get the current queue of shots waiting to be generation with full details"""
    try:
        from web_ui.backend.services.queue_service import get_queue_service
        from web_ui.backend.models.queue import QueueItemStatus

        queue_service = get_queue_service()
        queue_items = queue_service.get_queue(project_id=project_id)

        # Organize by status
        queued = []
        active = []
        completed = []
        failed = []

        for item in queue_items:
            item_data = {
                "shot_index": item.shot_index,
                "scene_id": item.scene_id,
                "generation_type": item.generation_type.value,
                "status": item.status.value,
                "progress": item.progress,
                "item_id": item.item_id,
                "is_flfi2v": item.is_flfi2v,
                "created_at": item.created_at.isoformat()
            }

            if item.status == QueueItemStatus.QUEUED:
                queued.append(item_data)
            elif item.status == QueueItemStatus.ACTIVE:
                active.append(item_data)
            elif item.status == QueueItemStatus.COMPLETED:
                completed.append(item_data)
            elif item.status == QueueItemStatus.FAILED:
                failed.append(item_data)

        return {
            "queued_items": queued,
            "active_items": active,
            "completed_items": completed,
            "failed_items": failed,
            "total_items": len(queue_items)
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.get("/queue-items")
async def get_project_queue_items(project_id: str):
    """Get all queue items for this project with full details"""
    try:
        from web_ui.backend.services.queue_service import get_queue_service

        queue_service = get_queue_service()
        queue_items = queue_service.get_queue(project_id=project_id)

        # Return full queue items
        return {
            "items": [item.model_dump(mode='json') for item in queue_items],
            "total": len(queue_items)
        }
    except Exception as e:
        logger.error(f"Error getting project queue items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue items: {str(e)}"
        )


@router.get("/{shot_index}")
async def get_shot(project_id: str, shot_index: int):
    """Get a single shot by index"""
    try:
        shots = await get_shots(project_id)

        # shot_index is 1-based in the API, 0-based in the list
        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        return shots[shot_index - 1]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shot: {str(e)}"
        )


@router.put("")
async def update_shots(project_id: str, request: UpdateShotsRequest):
    """Update shots (reorder, edit prompts)"""
    try:
        # We take the raw dicts directly because we will manually update string paths inside them later without fighting the immutable pydantic models
        shots_dicts = request.shots

        # Ensure all incoming shots have an ID (for backwards compatibility with old projects or newly inserted UI blank shots)
        for shot in shots_dicts:
            if 'id' not in shot or not shot.get('id'):
                shot['id'] = str(uuid.uuid4())[:8]

        # Update shots.json and perform safe renaming of associated media
        project_dir = os.path.join(config.ABS_PROJECTS_DIR, project_id)
        shots_path = os.path.join(project_dir, "shots.json")
        images_dir = os.path.join(project_dir, "images")
        videos_dir = os.path.join(project_dir, "videos")

        # Create dirs if they don't exist yet (e.g., if inserting a shot very early on)
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)

        # ----------------------------------------------------
        # Two-Pass File Renaming Strategy for Shot Reordering/Deletion
        # ----------------------------------------------------
        # We need to rename physical files like `shot_003_001.png` to `shot_002_001.png`
        # if shot 3 became shot 2.
        
        # Build maps for renamed files. We use a UUID `.tmp` pass first to prevent collisions (e.g. 2->3 while 3->4)
        tmp_id = str(uuid.uuid4())[:8]

        # Regex to extract the shot prefix: "shot_003_..."
        prefix_re = re.compile(r"^(shot_)(\d+)(_.*)$")

        def get_new_filename(current_filename: str, new_index: int) -> str:
            """Given 'shot_003_001.png' and new_index 2, returns 'shot_002_001.png'"""
            if not current_filename:
                return current_filename
            match = prefix_re.match(current_filename)
            if match:
                return f"{match.group(1)}{new_index:03d}{match.group(3)}"
            return current_filename

        # List of all renaming instructions
        # Tuple format: (absolute_source_path, absolute_tmp_path, absolute_final_path, file_type)
        rename_operations = []

        # Iterate over all incoming shots to detect discrepancies between their current index vs string names
        for shot in shots_dicts:
            true_index = shot['index']

            # Check primary image_path
            current_image_path = shot.get('image_path')
            if current_image_path:
                basename = os.path.basename(current_image_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        # Index shifted. Schedule rename.
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"
                        
                        src = os.path.join(images_dir, basename)
                        tmp = os.path.join(images_dir, tmp_basename)
                        dst = os.path.join(images_dir, new_basename)
                        
                        rename_operations.append((src, tmp, dst))
                        # Update the dict path explicitly with proper prefix
                        shot['image_path'] = os.path.join("output", "projects", project_id, "images", new_basename).replace('\\', '/')

            # Check alternative image_paths
            current_image_paths = shot.get('image_paths', [])
            new_image_paths = []
            for img_path in current_image_paths:
                basename = os.path.basename(img_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"
                        
                        src = os.path.join(images_dir, basename)
                        tmp = os.path.join(images_dir, tmp_basename)
                        dst = os.path.join(images_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        new_image_paths.append(os.path.join("output", "projects", project_id, "images", new_basename).replace('\\', '/'))
                    else:
                        new_image_paths.append(img_path) # unchanged
                else:
                    new_image_paths.append(img_path)
            shot['image_paths'] = new_image_paths

            # Check video_path
            current_video_path = shot.get('video_path')
            if current_video_path:
                basename = os.path.basename(current_video_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"
                        
                        src = os.path.join(videos_dir, basename)
                        tmp = os.path.join(videos_dir, tmp_basename)
                        dst = os.path.join(videos_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        shot['video_path'] = os.path.join("output", "projects", project_id, "videos", new_basename).replace('\\', '/')

            # Check alternative video_paths
            current_video_paths = shot.get('video_paths', [])
            new_video_paths = []
            for vid_path in current_video_paths:
                basename = os.path.basename(vid_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"

                        src = os.path.join(videos_dir, basename)
                        tmp = os.path.join(videos_dir, tmp_basename)
                        dst = os.path.join(videos_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        new_video_paths.append(os.path.join("output", "projects", project_id, "videos", new_basename).replace('\\', '/'))
                    else:
                        new_video_paths.append(vid_path) # unchanged
                else:
                    new_video_paths.append(vid_path)
            shot['video_paths'] = new_video_paths

            # ----------------------------------------------------
            # FLFI2V-specific fields: handle renaming for THEN/NOW images
            # and meeting/departure videos
            # ----------------------------------------------------
            # THEN image path
            then_image_path = shot.get('then_image_path')
            if then_image_path:
                basename = os.path.basename(then_image_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"

                        src = os.path.join(images_dir, basename)
                        tmp = os.path.join(images_dir, tmp_basename)
                        dst = os.path.join(images_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        shot['then_image_path'] = os.path.join("output", "projects", project_id, "images", new_basename).replace('\\', '/')

            # NOW image path
            now_image_path = shot.get('now_image_path')
            if now_image_path:
                basename = os.path.basename(now_image_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"

                        src = os.path.join(images_dir, basename)
                        tmp = os.path.join(images_dir, tmp_basename)
                        dst = os.path.join(images_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        shot['now_image_path'] = os.path.join("output", "projects", project_id, "images", new_basename).replace('\\', '/')

            # Meeting video path
            meeting_video_path = shot.get('meeting_video_path')
            if meeting_video_path:
                basename = os.path.basename(meeting_video_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"

                        src = os.path.join(videos_dir, basename)
                        tmp = os.path.join(videos_dir, tmp_basename)
                        dst = os.path.join(videos_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        shot['meeting_video_path'] = os.path.join("output", "projects", project_id, "videos", new_basename).replace('\\', '/')

            # Departure video path
            departure_video_path = shot.get('departure_video_path')
            if departure_video_path:
                basename = os.path.basename(departure_video_path)
                match = prefix_re.match(basename)
                if match:
                    embedded_idx = int(match.group(2))
                    if embedded_idx != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"

                        src = os.path.join(videos_dir, basename)
                        tmp = os.path.join(videos_dir, tmp_basename)
                        dst = os.path.join(videos_dir, new_basename)

                        rename_operations.append((src, tmp, dst))
                        shot['departure_video_path'] = os.path.join("output", "projects", project_id, "videos", new_basename).replace('\\', '/')

        # Execute Pass 1: Move to temporary files (prevents filename collisions during shifting)
        for src, tmp, dst in rename_operations:
            if os.path.exists(src):
                try:
                    shutil.move(src, tmp)
                except Exception as e:
                    logger.warning(f"Failed temp rename {src} -> {tmp}: {e}")

        # Execute Pass 2: Move temporary files to final correct destinations
        for src, tmp, dst in rename_operations:
            if os.path.exists(tmp):
                try:
                    # Cleanup if destination already exists (from an orphaned file)
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(tmp, dst)
                    logger.info(f"Permanently renamed shot media to {dst}")
                except Exception as e:
                    logger.warning(f"Failed final rename {tmp} -> {dst}: {e}")

        # Save updated shots JSON
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots_dicts, f, indent=2, ensure_ascii=False)

        # Return updated project
        return project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating shots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update shots: {str(e)}"
        )


@router.put("/{shot_index}")
async def update_shot(project_id: str, shot_index: int, request: UpdateShotRequest):
    """Update a single shot's prompts"""
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        # Update only the fields that are provided
        shot = shots[shot_index - 1]
        if request.image_prompt is not None:
            shot['image_prompt'] = request.image_prompt
        if request.motion_prompt is not None:
            shot['motion_prompt'] = request.motion_prompt
        if request.camera is not None:
            shot['camera'] = request.camera
        if request.narration is not None:
            shot['narration'] = request.narration
        if request.scene_id is not None:
            shot['scene_id'] = request.scene_id
        # FLFI2V fields
        if request.then_image_prompt is not None:
            shot['then_image_prompt'] = request.then_image_prompt
        if request.now_image_prompt is not None:
            shot['now_image_prompt'] = request.now_image_prompt
        if request.meeting_video_prompt is not None:
            shot['meeting_video_prompt'] = request.meeting_video_prompt
        if request.departure_video_prompt is not None:
            shot['departure_video_prompt'] = request.departure_video_prompt

        # Save updated shots
        project_dir = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return shot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update shot: {str(e)}"
        )


@router.post("/{shot_index}/remove-watermark")
async def remove_shot_watermark(project_id: str, shot_index: int, request: RemoveWatermarkRequest):
    """Remove watermark from the currently active image of this shot"""
    from core.geminiweb_subprocess import _remove_watermark

    try:
        shots = await get_shots(project_id)
        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]

        # Determine which image path to use based on variant
        variant = request.variant
        if variant == 'then':
            image_path = shot.get('then_image_path') or shot.get('image_path')
        elif variant == 'now':
            image_path = shot.get('now_image_path') or shot.get('image_path')
        else:
            # For regular shots or when no variant specified, use image_path
            image_path = shot.get('image_path')

        if not image_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shot has no image for variant '{variant or 'default'}'"
            )

        # Resolve the path using the config helper which handles all edge cases
        abs_image_path = config.resolve_path(image_path)

        if not os.path.exists(abs_image_path):
            logger.error(f"Image file not found: {abs_image_path}")
            logger.error(f"Original path: {image_path}")
            # Try listing files in the project directory for debugging
            project_dir = os.path.join(getattr(config, 'ABS_PROJECTS_DIR', 'output/projects'), project_id)
            images_dir = os.path.join(project_dir, 'images')
            if os.path.exists(images_dir):
                logger.error(f"Files in images directory: {os.listdir(images_dir)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image file not found on disk"
            )

        logger.info(f"Removing watermark for shot {shot_index} (variant={variant}): {abs_image_path}")
        _remove_watermark(abs_image_path)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing watermark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove watermark: {str(e)}"
        )
@router.post("/{shot_index}/regenerate-image")
async def regenerate_shot_image(project_id: str, shot_index: int, request: RegenerateImageRequest):
    """Regenerate image for a single shot with background queue execution"""
    try:
        from web_ui.backend.models.queue import GenerationType
        result_items = generation_service.add_single_shot_to_queue(
            project_id, shot_index, GenerationType.IMAGE, request
        )
        return {
            "status": "queued", 
            "message": f"Queued image generation for shot {shot_index}",
            "item_count": len(result_items)
        }
    except Exception as e:
        logger.error(f"Error regenerating image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate image: {str(e)}"
        )


@router.post("/{shot_index}/regenerate-video")
async def regenerate_shot_video(project_id: str, shot_index: int, request: RegenerateVideoRequest):
    """Regenerate video for a single shot with background queue execution"""
    try:
        from web_ui.backend.models.queue import GenerationType
        result_items = generation_service.add_single_shot_to_queue(
            project_id, shot_index, GenerationType.VIDEO, request
        )
        return {
            "status": "queued", 
            "message": f"Queued video generation for shot {shot_index}",
            "item_count": len(result_items)
        }
    except Exception as e:
        logger.error(f"Error regenerating video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate video: {str(e)}"
        )


from fastapi import BackgroundTasks

@router.post("/batch-regenerate")
async def batch_regenerate(project_id: str, request: BatchRegenerateRequest, background_tasks: BackgroundTasks):
    """Queue multiple shots for regeneration using a background task"""
    try:
        # Schedule the batch string on the backend
        background_tasks.add_task(
            generation_service.run_batch_generation,
            project_id,
            request
        )
        
        return {
            "status": "queued", 
            "message": f"Queued {len(request.shot_indices)} shots for generation",
            "shot_count": len(request.shot_indices)
        }
    except Exception as e:
        logger.error(f"Error queuing batch generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue batch generation: {str(e)}"
        )

@router.post("/{shot_index}/select-image")
async def select_shot_image(project_id: str, shot_index: int, request: SelectImageRequest):
    """Select a specific image as the active one for a shot"""
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]

        # Verify the requested path exists in image_paths
        image_paths = shot.get('image_paths', [])
        if request.image_path not in image_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image path not found in shot's image_paths"
            )

        # Update the active image_path
        shot['image_path'] = request.image_path

        # Save updated shots
        project_dir = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return {"status": "success", "image_path": request.image_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting image for shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select image: {str(e)}"
        )


@router.delete("/{shot_index}/images")
async def delete_shot_image_variation(project_id: str, shot_index: int, image_path: str):
    """Delete a specific image variation from disk and from the shot record.

    Query param: image_path — the relative path of the image to delete.
    If the deleted image was the active one, the next available variation is promoted.
    """
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]
        image_paths: list = shot.get('image_paths', [])

        if image_path not in image_paths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image path not found in shot's image_paths"
            )

        # Remove from the list
        image_paths.remove(image_path)
        shot['image_paths'] = image_paths

        # If it was the active image, promote the first remaining variation (if any)
        if shot.get('image_path') == image_path:
            shot['image_path'] = image_paths[0] if image_paths else None
            shot['image_generated'] = bool(image_paths)

        # Attempt to delete the physical file
        abs_path = None
        for base in [config.PROJECT_ROOT, config.ABS_OUTPUT_DIR if hasattr(config, 'ABS_OUTPUT_DIR') else None]:
            if base:
                candidate = os.path.join(base, image_path.replace("/", os.sep))
                if os.path.exists(candidate):
                    abs_path = candidate
                    break
        # Fallback: treat image_path as relative to ABS_PROJECTS_DIR parent
        if abs_path is None:
            candidate = os.path.join(os.path.dirname(config.ABS_PROJECTS_DIR), image_path.replace("/", os.sep))
            if os.path.exists(candidate):
                abs_path = candidate

        if abs_path and os.path.isfile(abs_path):
            try:
                os.remove(abs_path)
                logger.info(f"Deleted image variation: {abs_path}")
            except Exception as e:
                logger.warning(f"Could not delete file {abs_path}: {e}")
        else:
            logger.warning(f"Image file not found on disk for deletion: {image_path}")

        # Persist updated shots.json
        project_dir = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return {"status": "success", "remaining": len(image_paths), "active_image_path": shot.get('image_path')}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image variation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image variation: {str(e)}"
        )


@router.post("/{shot_index}/select-video")
async def select_shot_video(project_id: str, shot_index: int, request: SelectVideoRequest):
    """Select a specific video as the active one for a shot"""
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]

        # Verify the requested path exists in video_paths
        video_paths = shot.get('video_paths', [])
        if request.video_path not in video_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video path not found in shot's video_paths"
            )

        # Update the active video_path
        shot['video_path'] = request.video_path

        # Save updated shots
        project_dir = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return {"status": "success", "video_path": request.video_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting video for shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select video: {str(e)}"
        )


@router.delete("/{shot_index}/videos")
async def delete_shot_video_variation(project_id: str, shot_index: int, video_path: str):
    """Delete a specific video variation from disk and from the shot record.

    Query param: video_path — the relative path of the video to delete.
    If the deleted video was the active one, the next available variation is promoted.
    """
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]
        video_paths: list = shot.get('video_paths', [])

        if video_path not in video_paths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video path not found in shot's video_paths"
            )

        # Remove from the list
        video_paths.remove(video_path)
        shot['video_paths'] = video_paths

        # If it was the active video, promote the first remaining variation (if any)
        if shot.get('video_path') == video_path:
            shot['video_path'] = video_paths[0] if video_paths else None
            shot['video_rendered'] = bool(video_paths)

        # Attempt to delete the physical file
        abs_path = None
        for base in [config.PROJECT_ROOT, config.ABS_OUTPUT_DIR if hasattr(config, 'ABS_OUTPUT_DIR') else None]:
            if base:
                candidate = os.path.join(base, video_path.replace("/", os.sep))
                if os.path.exists(candidate):
                    abs_path = candidate
                    break
        # Fallback: treat video_path as relative to ABS_PROJECTS_DIR parent
        if abs_path is None:
            candidate = os.path.join(os.path.dirname(config.ABS_PROJECTS_DIR), video_path.replace("/", os.sep))
            if os.path.exists(candidate):
                abs_path = candidate

        if abs_path and os.path.isfile(abs_path):
            try:
                os.remove(abs_path)
                logger.info(f"Deleted video variation: {abs_path}")
            except Exception as e:
                logger.warning(f"Could not delete file {abs_path}: {e}")
        else:
            logger.warning(f"Video file not found on disk for deletion: {video_path}")

        # Persist updated shots.json
        project_dir = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return {"status": "success", "remaining": len(video_paths), "active_video_path": shot.get('video_path')}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video variation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete video variation: {str(e)}"
        )


@router.post("/{shot_index}/upload-image")
async def upload_shot_image(project_id: str, shot_index: int, variant: str = None, file: UploadFile = File(...)):
    """Upload a custom image from disk for a shot (bypasses AI generation)"""
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]

        # Determine file extension (default to .png if none)
        original_filename = file.filename or "upload.png"
        ext = os.path.splitext(original_filename)[1].lower() or ".png"
        # Only allow image extensions
        allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {ext}. Allowed types: {', '.join(allowed_exts)}"
            )

        # Build target path using the same versioned naming convention as AI-generated images:
        # shot_001_001.png, shot_001_002.jpg, etc.
        # Scan all existing files for this shot index across all extensions so that
        # uploaded and AI-generated images share the same version counter.
        project_dir = os.path.join(config.ABS_PROJECTS_DIR, project_id)
        images_dir = os.path.join(project_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        version_re = re.compile(rf"shot_{shot_index:03d}_(\d+)\.[^.]+$")
        max_version = 0
        if os.path.isdir(images_dir):
            for fname in os.listdir(images_dir):
                m = version_re.match(fname)
                if m:
                    max_version = max(max_version, int(m.group(1)))
        next_version = max_version + 1

        filename = f"shot_{shot_index:03d}_{next_version:03d}{ext}"

        abs_dest = os.path.join(images_dir, filename)

        # Write uploaded bytes to disk
        contents = await file.read()
        with open(abs_dest, "wb") as f:
            f.write(contents)

        logger.info(f"Uploaded image for shot {shot_index} saved to {abs_dest}")

        # Build the relative path using the same logic as mark_image_generated
        # so the stored format is always consistent with AI-generated images.
        rel_path = project_service.project_manager._relativize_path(abs_dest)

        # Update the shot record
        shot['image_path'] = rel_path
        shot['image_generated'] = True
        
        # If this is an FLFI2V shot and a variant was specified, set the specific path
        if variant and shot.get('is_flfi2v'):
            if variant == 'then':
                shot['then_image_path'] = rel_path
                shot['then_image_generated'] = True
                logger.info(f"Set uploaded image as THEN image for shot {shot_index}")
            elif variant == 'now':
                shot['now_image_path'] = rel_path
                shot['now_image_generated'] = True
                logger.info(f"Set uploaded image as NOW image for shot {shot_index}")

        image_paths = shot.get('image_paths', [])
        if rel_path not in image_paths:
            image_paths.append(rel_path)
        shot['image_paths'] = image_paths

        # Persist to shots.json
        project_dir2 = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir2, "shots.json")
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return {"status": "success", "image_path": rel_path, "filename": filename}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image for shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.post("/{shot_index}/upload-video")
async def upload_shot_video(project_id: str, shot_index: int, variant: str = None, file: UploadFile = File(...)):
    """Upload a custom video from disk for a shot (bypasses AI generation)"""
    try:
        shots = await get_shots(project_id)

        if shot_index < 1 or shot_index > len(shots):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shot {shot_index} not found"
            )

        shot = shots[shot_index - 1]

        # Determine file extension (default to .mp4 if none)
        original_filename = file.filename or "upload.mp4"
        ext = os.path.splitext(original_filename)[1].lower() or ".mp4"
        # Only allow video extensions
        allowed_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {ext}. Allowed types: {', '.join(allowed_exts)}"
            )

        # Build target path using the same versioned naming convention as AI-generated videos:
        # shot_001_001.mp4, shot_001_002.mp4, etc.
        project_dir = os.path.join(config.ABS_PROJECTS_DIR, project_id)
        videos_dir = os.path.join(project_dir, "videos")
        os.makedirs(videos_dir, exist_ok=True)

        version_re = re.compile(rf"shot_{shot_index:03d}_(\d+)\.[^.]+$")
        max_version = 0
        if os.path.isdir(videos_dir):
            for fname in os.listdir(videos_dir):
                m = version_re.match(fname)
                if m:
                    max_version = max(max_version, int(m.group(1)))
        next_version = max_version + 1

        filename = f"shot_{shot_index:03d}_{next_version:03d}{ext}"

        abs_dest = os.path.join(videos_dir, filename)

        # Write uploaded bytes to disk
        contents = await file.read()
        with open(abs_dest, "wb") as f:
            f.write(contents)

        logger.info(f"Uploaded video for shot {shot_index} saved to {abs_dest}")

        # Build the relative path
        rel_path = project_service.project_manager._relativize_path(abs_dest)

        # Update the shot record
        shot['video_path'] = rel_path
        shot['video_rendered'] = True

        # If this is an FLFI2V shot and a variant was specified, set the specific path
        if variant and shot.get('is_flfi2v'):
            if variant == 'meeting':
                shot['meeting_video_path'] = rel_path
                shot['meeting_video_rendered'] = True
                logger.info(f"Set uploaded video as MEETING video for shot {shot_index}")
            elif variant == 'departure':
                shot['departure_video_path'] = rel_path
                shot['departure_video_rendered'] = True
                logger.info(f"Set uploaded video as DEPARTURE video for shot {shot_index}")

        video_paths = shot.get('video_paths', [])
        if rel_path not in video_paths:
            video_paths.append(rel_path)
        shot['video_paths'] = video_paths

        # Persist to shots.json
        project_dir2 = project_service.get_project_dir(project_id)
        shots_path = os.path.join(project_dir2, "shots.json")
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

        return {"status": "success", "video_path": rel_path, "filename": filename}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading video for shot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )


@router.post("/replan")
async def replan_shots(project_id: str, request: ReplanShotsRequest):
    """Re-plan shots from story"""
    try:
        shots = await generation_service.replan_shots(
            project_id,
            max_shots=request.max_shots,
            shots_agent=request.shots_agent
        )
        return {"status": "success", "shots": shots}
    except Exception as e:
        logger.error(f"Error replanning shots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replan shots: {str(e)}"
        )


@router.post("/cancel-generation")
async def cancel_generation(project_id: str):
    """Cancel all pending and running image/video generation for this project"""
    from core.comfy_client import cancel_all
    from web_ui.backend.websocket.manager import manager

    try:
        logger.info(f"Cancel generation requested for project {project_id}")
        result = cancel_all()
        generation_service.cancel_project(project_id)
        logger.info(f"ComfyUI cancel result: {result}")

        # Broadcast cancellation to frontend (use async since this handler is async)
        await manager.broadcast_to_project(project_id, {
            "type": "cancelled",
            "project_id": project_id
        })

        return {"status": "success", "cancelled": result}
    except Exception as e:
        logger.error(f"Error cancelling generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel generation: {str(e)}"
        )

@router.post("/{shot_index}/cancel-generation")
async def cancel_single_shot_generation(project_id: str, shot_index: int):
    """Cancel pending generation for a specific shot in this project"""
    from web_ui.backend.websocket.manager import manager

    try:
        logger.info(f"Cancel generation requested for project {project_id}, shot {shot_index}")
        
        # Mark the specific shot as cancelled so the backend loop skips it
        generation_service.cancel_single_shot(project_id, shot_index)

        # Broadcast cancellation for this specific shot to the frontend
        await manager.broadcast_to_project(project_id, {
            "type": "cancelled",
            "project_id": project_id,
            "shot_index": shot_index
        })

        return {"status": "success", "message": f"Shot {shot_index} generation cancelled"}
    except Exception as e:
        logger.error(f"Error cancelling single shot generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel single shot generation: {str(e)}"
        )

