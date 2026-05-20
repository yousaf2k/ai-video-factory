"""
Editor-specific API endpoints for asset management, timeline persistence, and video export
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import os
import json
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/editor", tags=["editor"])

from web_ui.backend.services.export_service import ExportService
export_service = ExportService()


@router.post("/upload/{project_id}")
async def upload_editor_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_type: str = Form(...),  # 'video', 'audio', 'image'
):
    """Upload a custom asset to the project"""
    try:
        from web_ui.backend.services.project_service import ProjectService
        project_service = ProjectService()

        # Validate file type
        allowed_extensions = {
            'video': ['.mp4', '.mov', '.avi', '.webm'],
            'audio': ['.mp3', '.wav', '.aac', '.ogg'],
            'image': ['.png', '.jpg', '.jpeg', '.webp', '.gif']
        }

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions.get(asset_type, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for {asset_type}: {file_ext}"
            )

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Determine target directory
        if asset_type == 'image':
            target_dir = project_service.get_images_dir(project_id)
        elif asset_type == 'video':
            target_dir = project_service.get_videos_dir(project_id)
        elif asset_type == 'audio':
            # Create audio directory in project
            project_dir = project_service.get_project_dir(project_id)
            target_dir = os.path.join(project_dir, "audio")
            os.makedirs(target_dir, exist_ok=True)
        else:
            raise HTTPException(status_code=400, detail="Invalid asset type")

        # Save file
        file_path = os.path.join(target_dir, unique_filename)
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Uploaded {asset_type} asset: {file.filename} -> {unique_filename}")

        return {
            "status": "success",
            "asset_url": f"/api/projects/{project_id}/{asset_type}s/{unique_filename}",
            "filename": unique_filename,
            "original_name": file.filename,
            "asset_type": asset_type
        }

    except Exception as e:
        logger.error(f"Error uploading asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/{project_id}")
async def list_project_assets(project_id: str):
    """List all assets in a project"""
    try:
        from web_ui.backend.services.project_service import ProjectService
        project_service = ProjectService()

        assets = {
            'images': [],
            'videos': [],
            'audio': []
        }

        # Scan images
        images_dir = project_service.get_images_dir(project_id)
        if os.path.exists(images_dir):
            assets['images'] = [
                f for f in os.listdir(images_dir)
                if os.path.isfile(os.path.join(images_dir, f))
            ]

        # Scan videos
        videos_dir = project_service.get_videos_dir(project_id)
        if os.path.exists(videos_dir):
            assets['videos'] = [
                f for f in os.listdir(videos_dir)
                if os.path.isfile(os.path.join(videos_dir, f))
            ]

        # Scan audio
        project_dir = project_service.get_project_dir(project_id)
        audio_dir = os.path.join(project_dir, "audio")
        if os.path.exists(audio_dir):
            assets['audio'] = [
                f for f in os.listdir(audio_dir)
                if os.path.isfile(os.path.join(audio_dir, f))
            ]

        return assets

    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/timeline/{project_id}/save")
async def save_timeline(project_id: str, timeline_data: dict):
    """Save timeline JSON to project directory"""
    try:
        from web_ui.backend.services.project_service import ProjectService

        project_service = ProjectService()
        project_dir = project_service.get_project_dir(project_id)

        # Create editor directory if it doesn't exist
        editor_dir = os.path.join(project_dir, "editor")
        os.makedirs(editor_dir, exist_ok=True)

        # Save timeline.json
        timeline_path = os.path.join(editor_dir, "timeline.json")
        with open(timeline_path, 'w', encoding='utf-8') as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved timeline for project {project_id}")

        return {
            "status": "success",
            "timeline_path": f"/api/projects/{project_id}/editor/timeline.json"
        }

    except Exception as e:
        logger.error(f"Error saving timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/{project_id}/load")
async def load_timeline(project_id: str):
    """Load timeline JSON from project directory"""
    try:
        from web_ui.backend.services.project_service import ProjectService

        project_service = ProjectService()
        project_dir = project_service.get_project_dir(project_id)
        timeline_path = os.path.join(project_dir, "editor", "timeline.json")

        if not os.path.exists(timeline_path):
            return {"status": "not_found", "timeline": None}

        with open(timeline_path, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)

        logger.info(f"Loaded timeline for project {project_id}")

        return {
            "status": "success",
            "timeline": timeline_data
        }

    except Exception as e:
        logger.error(f"Error loading timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/{project_id}/list")
async def list_timelines(project_id: str):
    """List all saved timeline versions for a project"""
    try:
        from web_ui.backend.services.project_service import ProjectService
        import glob

        project_service = ProjectService()
        project_dir = project_service.get_project_dir(project_id)
        editor_dir = os.path.join(project_dir, "editor")

        if not os.path.exists(editor_dir):
            return {"timelines": []}

        # Find all timeline_*.json files
        timeline_files = glob.glob(os.path.join(editor_dir, "timeline_*.json"))

        timelines = []
        for timeline_file in timeline_files:
            filename = os.path.basename(timeline_file)
            # Extract timestamp from filename
            timestamp = filename.replace("timeline_", "").replace(".json", "")
            timelines.append({
                "filename": filename,
                "timestamp": timestamp,
                "url": f"/api/projects/{project_id}/editor/{filename}"
            })

        # Sort by timestamp descending (newest first)
        timelines.sort(key=lambda x: x['timestamp'], reverse=True)

        return {"timelines": timelines}

    except Exception as e:
        logger.error(f"Error listing timelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def editor_health():
    """Check FFmpeg availability and disk space"""
    import shutil
    import subprocess

    # Check FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'],
                      capture_output=True,
                      check=True,
                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        ffmpeg_status = "available"
    except:
        ffmpeg_status = "unavailable"

    # Check disk space
    disk_usage = shutil.disk_usage(".")
    free_space_gb = disk_usage.free / (1024**3)

    return {
        "ffmpeg": ffmpeg_status,
        "disk_space_gb": round(free_space_gb, 2),
        "exports_dir": "output/exports"
    }


@router.post("/export/{project_id}")
async def export_video(project_id: str, request: dict):
    """Export timeline as video using FFmpeg"""
    try:
        import asyncio

        # Extract timeline and settings from request
        timeline_data = request.get('timeline', {})
        settings = request.get('settings', {
            'resolution': '1280x720',
            'fps': 30,
            'codec': 'libx264',
            'bitrate': '5M',
            'audio_bitrate': '192k',
            'format': 'mp4'
        })

        # Start export process (async)
        export_id = await export_service.start_export(
            project_id,
            timeline_data,
            settings
        )

        logger.info(f"Started export {export_id} for project {project_id}")

        return {
            "status": "started",
            "export_id": export_id,
            "message": "Video export started"
        }

    except Exception as e:
        logger.error(f"Error starting export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{project_id}/status/{export_id}")
async def get_export_status(project_id: str, export_id: str):
    """Get the status of an ongoing export"""
    try:
        status = export_service.get_export_status(export_id)

        return status

    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{project_id}/download/{export_id}")
async def download_export(project_id: str, export_id: str):
    """Download the exported video"""
    try:
        from fastapi.responses import FileResponse

        video_path = export_service.get_export_path(export_id)

        if not video_path or not os.path.exists(video_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export {export_id} not found or not ready"
            )

        return FileResponse(
            video_path,
            media_type='video/mp4',
            filename=f"{project_id}_export.mp4"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        raise HTTPException(status_code=500, detail=str(e))
