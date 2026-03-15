"""
Projects API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import os

from web_ui.backend.models.project import (
    ProjectListItem, ProjectDetail, CreateProjectRequest,
    UpdateProjectRequest, DuplicateProjectRequest
)
from pydantic import BaseModel

class GenerateThumbnailRequest(BaseModel):
    aspect_ratio: str = "16:9"
    force: bool = False
    image_mode: Optional[str] = None
    image_workflow: Optional[str] = None
    seed: Optional[int] = None

from web_ui.backend.services.project_service import ProjectService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])

# Initialize project service
project_service = ProjectService()


@router.get("", response_model=List[ProjectListItem])
async def list_projects():
    """List all projects"""
    logger.info("list_projects endpoint called")
    try:
        projects = project_service.list_projects()
        logger.info(f"Returning {len(projects)} projects")
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        return project_service.create_project(request)
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str):
    """Get project details"""
    try:
        return project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put("/{project_id}", response_model=ProjectDetail)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update project metadata"""
    try:
        project_service.update_project(project_id, request)
        return project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str):
    """Delete a project"""
    try:
        success = project_service.delete_project(project_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.post("/{project_id}/duplicate", response_model=ProjectDetail)
async def duplicate_project(project_id: str, request: DuplicateProjectRequest = None):
    """Duplicate a project"""
    try:
        new_project_id = request.new_project_id if request else None
        return project_service.duplicate_project(project_id, new_project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    except Exception as e:
        logger.error(f"Error duplicating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate project: {str(e)}"
        )


@router.get("/{project_id}/images/{filename}", response_class=FileResponse)
async def get_project_image(project_id: str, filename: str):
    """Serve a project image file directly"""
    try:
        images_dir = project_service.get_images_dir(project_id)
        image_path = os.path.join(images_dir, filename)
        
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image {filename} not found for project {project_id}"
            )
            
        return FileResponse(image_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filename} for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve image: {str(e)}"
        )


@router.get("/{project_id}/videos/{filename}", response_class=FileResponse)
async def get_project_video(project_id: str, filename: str):
    """Serve a project video file directly"""
    try:
        videos_dir = project_service.get_videos_dir(project_id)
        video_path = os.path.join(videos_dir, filename)
        
        if not os.path.exists(video_path) or not os.path.isfile(video_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video {filename} not found for project {project_id}"
            )
            
        return FileResponse(video_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving video {filename} for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve video: {str(e)}"
        )


@router.post("/{project_id}/thumbnail")
async def generate_thumbnail(project_id: str, request: GenerateThumbnailRequest):
    """Generate a thumbnail for the project"""
    try:
        from web_ui.backend.services.generation_service import get_generation_service
        gen_service = get_generation_service()
        
        image_path = await gen_service.generate_thumbnail(
            project_id, 
            aspect_ratio=request.aspect_ratio, 
            force=request.force,
            image_mode=request.image_mode,
            image_workflow=request.image_workflow,
            seed=request.seed
        )
        
        filename = os.path.basename(image_path)
        thumbnail_url = f"/api/projects/{project_id}/images/{filename}"
        
        return {"status": "success", "thumbnail_url": thumbnail_url}
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thumbnail: {str(e)}"
        )

