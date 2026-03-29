"""
Shots API endpoints
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, BackgroundTasks
import sys
import os
import json
import logging
import uuid
import re
import shutil
import time
import config

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from web_ui.backend.models.shot import (
    UpdateShotsRequest, UpdateShotRequest, RegenerateImageRequest,
    RegenerateVideoRequest, BatchRegenerateRequest, ReplanShotsRequest,
    SelectImageRequest, SelectVideoRequest, RemoveWatermarkRequest,
    RegenerateSoundFXRequest
)
from web_ui.backend.services.project_service import ProjectService
from web_ui.backend.services.generation_service import get_generation_service
from web_ui.backend.models.queue import GenerationType

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


async def _resolve_shot(project_id: str, shot_id_or_index: str):
    """Helper to resolve a shot by ID or 1-based index"""
    shots = await get_shots(project_id)
    
    # Try as numeric index first (1-based)
    if shot_id_or_index.isdigit():
        idx = int(shot_id_or_index)
        if 1 <= idx <= len(shots):
            return shots[idx - 1], idx
            
    # Try as stable UUID
    for i, shot in enumerate(shots):
        if shot.get('id') == shot_id_or_index:
            return shot, i + 1
            
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Shot '{shot_id_or_index}' not found in project {project_id}"
    )


@router.get("/{shot_id_or_index}")
async def get_shot(project_id: str, shot_id_or_index: str):
    """Get a single shot by index or ID"""
    shot, _ = await _resolve_shot(project_id, shot_id_or_index)
    return shot


@router.put("")
async def update_shots(project_id: str, request: UpdateShotsRequest):
    """Update shots (reorder, edit prompts)"""
    try:
        shots_dicts = request.shots

        # Ensure all incoming shots have an ID
        for shot in shots_dicts:
            if 'id' not in shot or not shot.get('id'):
                shot['id'] = str(uuid.uuid4())[:8]

        # Update shots.json and perform safe renaming of associated media
        project_dir = os.path.join(config.ABS_PROJECTS_DIR, project_id)
        shots_path = os.path.join(project_dir, "shots.json")
        images_dir = os.path.join(project_dir, "images")
        videos_dir = os.path.join(project_dir, "videos")

        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)

        tmp_id = str(uuid.uuid4())[:8]
        prefix_re = re.compile(r"^(shot_)(\d+)(_.*)$")

        def get_new_filename(current_filename: str, new_index: int) -> str:
            if not current_filename:
                return current_filename
            match = prefix_re.match(current_filename)
            if match:
                return f"{match.group(1)}{new_index:03d}{match.group(3)}"
            return current_filename

        rename_operations = []

        for shot in shots_dicts:
            true_index = shot['index']

            # Media fields to check for renaming
            media_fields = [
                ('image_path', images_dir),
                ('video_path', videos_dir),
                ('then_image_path', images_dir),
                ('now_image_path', images_dir),
                ('meeting_video_path', videos_dir),
                ('departure_video_path', videos_dir)
            ]

            for field, m_dir in media_fields:
                path = shot.get(field)
                if path:
                    basename = os.path.basename(path)
                    match = prefix_re.match(basename)
                    if match and int(match.group(2)) != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"
                        rename_operations.append((
                            os.path.join(m_dir, basename),
                            os.path.join(m_dir, tmp_basename),
                            os.path.join(m_dir, new_basename)
                        ))
                        shot[field] = os.path.join("output", "projects", project_id, os.path.basename(m_dir), new_basename).replace('\\', '/')

            # Handle lists (image_paths, video_paths)
            for list_key, m_dir in [('image_paths', images_dir), ('video_paths', videos_dir)]:
                paths = shot.get(list_key, [])
                new_paths = []
                for p in paths:
                    basename = os.path.basename(p)
                    match = prefix_re.match(basename)
                    if match and int(match.group(2)) != true_index:
                        new_basename = get_new_filename(basename, true_index)
                        tmp_basename = f"{new_basename}.tmp-{tmp_id}"
                        rename_operations.append((
                            os.path.join(m_dir, basename),
                            os.path.join(m_dir, tmp_basename),
                            os.path.join(m_dir, new_basename)
                        ))
                        new_paths.append(os.path.join("output", "projects", project_id, os.path.basename(m_dir), new_basename).replace('\\', '/'))
                    else:
                        new_paths.append(p)
                shot[list_key] = new_paths

        # Execute renames
        for src, tmp, dst in rename_operations:
            if os.path.exists(src):
                try: shutil.move(src, tmp)
                except: pass
        for src, tmp, dst in rename_operations:
            if os.path.exists(tmp):
                try:
                    if os.path.exists(dst): os.remove(dst)
                    shutil.move(tmp, dst)
                except: pass

        # Atomic update
        def modify_func(current_shots):
            return shots_dicts
        project_service.project_manager.update_shots_safely(project_id, modify_func)

        return {"status": "success", "count": len(shots_dicts)}
    except Exception as e:
        logger.error(f"Error updating shots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{shot_id_or_index}")
async def update_shot(project_id: str, shot_id_or_index: str, request: UpdateShotRequest):
    """Update a single shot's prompts"""
    try:
        shot_data, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        
        def modify_shot(shots):
            shot = shots[shot_index - 1]
            for field in ['image_prompt', 'motion_prompt', 'camera', 'narration', 'scene_id', 
                         'then_image_prompt', 'now_image_prompt', 'meeting_video_prompt', 'departure_video_prompt']:
                val = getattr(request, field, None)
                if val is not None:
                    shot[field] = val
                    
        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating shot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/remove-watermark")
async def remove_shot_watermark(project_id: str, shot_id_or_index: str, request: RemoveWatermarkRequest):
    """Remove watermark from the currently active image or video of this shot"""
    from core.geminiweb_subprocess import _remove_watermark
    try:
        shot, _ = await _resolve_shot(project_id, shot_id_or_index)
        
        media_type = request.type
        variant = request.variant

        file_path = None
        if media_type == 'image':
            if variant == 'then': file_path = shot.get('then_image_path') or shot.get('image_path')
            elif variant == 'now': file_path = shot.get('now_image_path') or shot.get('image_path')
            else: file_path = shot.get('image_path')
        elif media_type == 'video':
            if variant == 'meeting': file_path = shot.get('meeting_video_path') or shot.get('video_path')
            elif variant == 'departure': file_path = shot.get('departure_video_path') or shot.get('video_path')
            else: file_path = shot.get('video_path')

        if not file_path:
            raise HTTPException(status_code=400, detail="Shot has no such media")

        abs_file_path = config.resolve_path(file_path)
        if not os.path.exists(abs_file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        _remove_watermark(abs_file_path, media_type=media_type)
        return {"status": "success"}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error removing watermark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-regenerate")
async def batch_regenerate(project_id: str, request: BatchRegenerateRequest, background_tasks: BackgroundTasks):
    """Queue multiple shots for regeneration"""
    try:
        background_tasks.add_task(generation_service.run_batch_generation, project_id, request)
        count = len(request.shot_ids or request.shot_indices or [])
        return {"status": "queued", "shot_count": count}
    except Exception as e:
        logger.error(f"Error queuing batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/regenerate-image")
async def regenerate_single_shot_image(project_id: str, shot_id_or_index: str, request: RegenerateImageRequest):
    """Queue image generation for a single shot"""
    try:
        await _resolve_shot(project_id, shot_id_or_index)
        result = generation_service.add_single_shot_to_queue(project_id, shot_id_or_index, GenerationType.IMAGE, request)
        return {"status": "queued", "item_count": len(result)}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/regenerate-video")
async def regenerate_single_shot_video(project_id: str, shot_id_or_index: str, request: RegenerateVideoRequest):
    """Queue video generation for a single shot"""
    try:
        await _resolve_shot(project_id, shot_id_or_index)
        result = generation_service.add_single_shot_to_queue(project_id, shot_id_or_index, GenerationType.VIDEO, request)
        return {"status": "queued", "item_count": len(result)}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/regenerate-soundfx")
async def regenerate_single_shot_soundfx(project_id: str, shot_id_or_index: str, request: RegenerateSoundFXRequest):
    """Queue sound effects generation for a single shot"""
    try:
        await _resolve_shot(project_id, shot_id_or_index)
        result = generation_service.add_single_shot_to_queue(project_id, shot_id_or_index, GenerationType.SOUNDFX, request)
        return {"status": "queued", "item_count": len(result)}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/select-image")
async def select_shot_image(project_id: str, shot_id_or_index: str, request: SelectImageRequest):
    """Select a specific image as the active one"""
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        def modify_shot(shots):
            target = shots[shot_index - 1]
            variant = request.variant
            if not variant:
                if '_then_' in request.image_path: variant = 'then'
                elif '_now_' in request.image_path: variant = 'now'
            
            if variant == 'then' and target.get('is_flfi2v'):
                target['then_image_path'] = request.image_path
                target['then_image_generated'] = True
            elif variant == 'now' and target.get('is_flfi2v'):
                target['now_image_path'] = request.image_path
                target['now_image_generated'] = True
            else:
                target['image_path'] = request.image_path
        
        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{shot_id_or_index}/images")
async def delete_shot_image_variation(project_id: str, shot_id_or_index: str, image_path: str):
    """Delete a specific image variation"""
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        def modify_shot(shots):
            target = shots[shot_index - 1]
            paths = target.get('image_paths', [])
            if image_path in paths: paths.remove(image_path)
            if target.get('image_path') == image_path:
                target['image_path'] = paths[0] if paths else None
                target['image_generated'] = bool(paths)
            if target.get('then_image_path') == image_path:
                target['then_image_path'] = None
                target['then_image_generated'] = False
            if target.get('now_image_path') == image_path:
                target['now_image_path'] = None
                target['now_image_generated'] = False

        abs_path = config.resolve_path(image_path)
        if os.path.exists(abs_path): os.remove(abs_path)
        
        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/select-video")
async def select_shot_video(project_id: str, shot_id_or_index: str, request: SelectVideoRequest):
    """Select a specific video as active"""
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        def modify_shot(shots):
            target = shots[shot_index - 1]
            variant = request.variant
            if not variant:
                if '_meeting_' in request.video_path: variant = 'meeting'
                elif '_departure_' in request.video_path: variant = 'departure'
            
            if variant == 'meeting' and target.get('is_flfi2v'):
                target['meeting_video_path'] = request.video_path
                target['meeting_video_rendered'] = True
            elif variant == 'departure' and target.get('is_flfi2v'):
                target['departure_video_path'] = request.video_path
                target['departure_video_rendered'] = True
            else:
                target['video_path'] = request.video_path
        
        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{shot_id_or_index}/videos")
async def delete_shot_video_variation(project_id: str, shot_id_or_index: str, video_path: str):
    """Delete a specific video variation"""
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        def modify_shot(shots):
            target = shots[shot_index - 1]
            paths = target.get('video_paths', [])
            if video_path in paths: paths.remove(video_path)
            if target.get('video_path') == video_path:
                target['video_path'] = paths[0] if paths else None
                target['video_rendered'] = bool(paths)
            if target.get('meeting_video_path') == video_path:
                target['meeting_video_path'] = None
                target['meeting_video_rendered'] = False
            if target.get('departure_video_path') == video_path:
                target['departure_video_path'] = None
                target['departure_video_rendered'] = False

        abs_path = config.resolve_path(video_path)
        if os.path.exists(abs_path): os.remove(abs_path)
        
        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/upload-image")
async def upload_shot_image(project_id: str, shot_id_or_index: str, variant: str = None, file: UploadFile = File(...)):
    """Upload a custom image"""
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        ext = os.path.splitext(file.filename or "")[1] or ".png"
        filename = f"upload_{shot_id_or_index}_{variant or 'default'}_{int(time.time())}{ext}"
        project_dir = project_service.get_project_dir(project_id)
        images_dir = os.path.join(project_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        abs_dest = os.path.join(images_dir, filename)
        
        contents = await file.read()
        with open(abs_dest, "wb") as f: f.write(contents)
        rel_path = project_service.project_manager._relativize_path(abs_dest)
        
        def modify_shot(shots):
            target = shots[shot_index - 1]
            if variant == 'then':
                target['then_image_path'] = rel_path
                target['then_image_generated'] = True
            elif variant == 'now':
                target['now_image_path'] = rel_path
                target['now_image_generated'] = True
            else:
                target['image_path'] = rel_path
                target['image_generated'] = True
            paths = target.get('image_paths', [])
            if rel_path not in paths: paths.append(rel_path)
            target['image_paths'] = paths

        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success", "image_path": rel_path}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/upload-video")
async def upload_shot_video(project_id: str, shot_id_or_index: str, variant: str = None, file: UploadFile = File(...)):
    """Upload a custom video"""
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        ext = os.path.splitext(file.filename or "")[1] or ".mp4"
        filename = f"upload_{shot_id_or_index}_{variant or 'default'}_{int(time.time())}{ext}"
        project_dir = project_service.get_project_dir(project_id)
        videos_dir = os.path.join(project_dir, "videos")
        os.makedirs(videos_dir, exist_ok=True)
        abs_dest = os.path.join(videos_dir, filename)
        
        contents = await file.read()
        with open(abs_dest, "wb") as f: f.write(contents)
        rel_path = project_service.project_manager._relativize_path(abs_dest)
        
        def modify_shot(shots):
            target = shots[shot_index - 1]
            if variant == 'meeting':
                target['meeting_video_path'] = rel_path
                target['meeting_video_rendered'] = True
            elif variant == 'departure':
                target['departure_video_path'] = rel_path
                target['departure_video_rendered'] = True
            else:
                target['video_path'] = rel_path
                target['video_rendered'] = True
            paths = target.get('video_paths', [])
            if rel_path not in paths: paths.append(rel_path)
            target['video_paths'] = paths

        project_service.project_manager.update_shots_safely(project_id, modify_shot)
        return {"status": "success", "video_path": rel_path}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replan")
async def replan_shots(project_id: str, request: ReplanShotsRequest):
    """Re-plan shots from story"""
    try:
        shots = await generation_service.replan_shots(project_id, max_shots=request.max_shots, shots_agent=request.shots_agent)
        return {"status": "success", "shots": shots}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel-generation")
async def cancel_generation(project_id: str):
    """Cancel all generations"""
    from core.comfy_client import cancel_all
    from web_ui.backend.websocket.manager import manager
    try:
        result = cancel_all()
        generation_service.cancel_project(project_id)
        await manager.broadcast_to_project(project_id, {"type": "cancelled", "project_id": project_id})
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{shot_id_or_index}/cancel")
async def cancel_single_shot_generation(project_id: str, shot_id_or_index: str):
    """Cancel generation for a single shot"""
    from web_ui.backend.websocket.manager import manager
    try:
        shot, shot_index = await _resolve_shot(project_id, shot_id_or_index)
        generation_service.cancel_single_shot(project_id, shot_index)
        await manager.broadcast_to_project(project_id, {
            "type": "shot_cancelled",
            "shot_index": shot_index,
            "shot_id": shot.get('id')
        })
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
