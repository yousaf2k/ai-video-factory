"""
Project service - Wrapper around ProjectManager
"""
import sys
import os
from typing import List, Dict, Any, Optional

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from core.project_manager import ProjectManager
from web_ui.backend.models.project import (
    ProjectMetadata, ProjectDetail, ProjectListItem,
    CreateProjectRequest, UpdateProjectRequest
)
import json


class ProjectService:
    """Service for project management operations"""

    def __init__(self, projects_dir: str = None):
        # Default to configured projects directory
        if projects_dir is None:
            import config
            projects_dir = getattr(config, 'ABS_PROJECTS_DIR', None)
            
            if projects_dir is None:
                # Fallback if config not loaded properly
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
                projects_dir = os.path.join(project_root, "output", "projects")

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"ProjectService initialized with projects_dir: {projects_dir}")
        logger.info(f"Directory exists: {os.path.exists(projects_dir)}")
        print(f"[DEBUG] ProjectService projects_dir: {projects_dir}")
        print(f"[DEBUG] Directory exists: {os.path.exists(projects_dir)}")

        self.project_manager = ProjectManager(projects_dir)

    def list_projects(self) -> List[ProjectListItem]:
        """List all projects"""
        projects_data = self.project_manager.list_all_projects()
        
        result = []
        for meta in projects_data:
            project_id = meta.get("project_id")
            story = None
            if project_id:
                project_dir = self.project_manager.get_project_dir(project_id)
                story_path = os.path.join(project_dir, "story.json")
                if os.path.exists(story_path):
                    try:
                        with open(story_path, 'r', encoding='utf-8') as f:
                            story = json.load(f)
                    except Exception:
                        pass
            result.append(ProjectListItem.from_metadata(meta, story))
            
        return result

    def get_project(self, project_id: str) -> ProjectDetail:
        """Get project detail with story and shots"""
        meta = self.project_manager.load_project(project_id)

        # Load story if exists
        story = None
        project_dir = self.project_manager.get_project_dir(project_id)
        story_path = os.path.join(project_dir, "story.json")
        if os.path.exists(story_path):
            with open(story_path, 'r', encoding='utf-8') as f:
                story = json.load(f)

        # Load shots if exist
        shots = self.project_manager.get_shots(project_id)

        return ProjectDetail.from_project_data(
            meta=meta,
            story=story,
            shots=shots
        )

    def create_project(self, request: CreateProjectRequest) -> ProjectDetail:
        """Create a new project"""
        project_id, meta = self.project_manager.create_project(
            idea=request.idea,
            project_id=request.project_id,
            story_agent=request.story_agent,
            shots_agent=request.shots_agent,
            total_duration=request.total_duration,
            aspect_ratio=request.aspect_ratio
        )

        # Detect if this is a ThenVsNow project
        is_then_vs_now = request.story_agent == "then_vs_now"

        if is_then_vs_now:
            # Use special story generation flow for ThenVsNow
            from core.story_engine import build_story_then_vs_now
            import logging
            logger = logging.getLogger(__name__)

            try:
                logger.info(f"Creating ThenVsNow project for movie: {request.idea}")
                print(f"[INFO] Creating ThenVsNow project for movie: {request.idea}")

                # Generate story with shots directly
                story_json = build_story_then_vs_now(
                    movie_name=request.idea,
                    target_length=request.total_duration,
                    aspect_ratio=request.aspect_ratio
                )
                story = json.loads(story_json)

                # Extract shots from story (already generated)
                shots = story.pop('shots', [])

                # Save story.json
                project_dir = self.project_manager.get_project_dir(project_id)
                story_path = os.path.join(project_dir, "story.json")
                with open(story_path, 'w', encoding='utf-8') as f:
                    json.dump(story, f, indent=2, ensure_ascii=False)

                # Save shots.json directly (bypass shot planner)
                shots_path = os.path.join(project_dir, "shots.json")
                with open(shots_path, 'w', encoding='utf-8') as f:
                    json.dump(shots, f, indent=2, ensure_ascii=False)

                # Update metadata with story info
                meta['idea'] = story.get('title', request.idea)
                if 'total_duration' in story:
                    meta['total_duration'] = story['total_duration']

                # Mark steps as complete
                meta['steps']['story'] = True
                meta['steps']['scene_graph'] = True
                meta['steps']['shots'] = True

                # Update stats
                meta['stats']['total_shots'] = len(shots)

                # Save updated metadata
                self.project_manager._save_meta(project_id, meta)

                logger.info(f"ThenVsNow project created with {len(shots)} shots")
                print(f"[INFO] ThenVsNow project created with {len(shots)} shots")

            except Exception as e:
                logger.error(f"Failed to create ThenVsNow story: {e}")
                print(f"[ERROR] Failed to create ThenVsNow story: {e}")
                import traceback
                traceback.print_exc()
                # Continue with empty project

        # Handle prompts file if provided
        if request.prompts_file:
            try:
                from core.prompts_parser import parse_prompts_file, prompts_to_shots, validate_and_fix_prompts
                import config

                # Resolve path
                resolved_prompts_file = config.resolve_path(request.prompts_file)

                # Parse and create shots
                prompts_data, overall_title = parse_prompts_file(resolved_prompts_file)
                prompts_data = validate_and_fix_prompts(prompts_data)
                shots = prompts_to_shots(prompts_data)

                # Update idea if overall_title found
                if overall_title:
                    meta['idea'] = overall_title

                # Mark steps as complete
                meta['steps']['story'] = True
                meta['steps']['scene_graph'] = True
                meta['steps']['shots'] = True
                meta['prompts_file'] = resolved_prompts_file

                # Calculate duration based on number of prompts (5 sec per prompt)
                calculated_duration = len(shots) * 5
                meta['total_duration'] = calculated_duration

                # Save shots
                self.project_manager.save_shots(project_id, shots)

                # Create dummy story.json
                project_dir = self.project_manager.get_project_dir(project_id)
                story_path = os.path.join(project_dir, "story.json")
                
                dummy_story = {
                    "title": overall_title or request.idea,
                    "style": "imported from prompts file",
                    "scenes": [
                        {
                            "index": 1,
                            "location": "N/A",
                            "characters": "N/A",
                            "action": "Imported from prompts file",
                            "emotion": "N/A",
                            "scene_duration": calculated_duration
                        }
                    ],
                    "total_duration": calculated_duration
                }
                
                with open(story_path, 'w', encoding='utf-8') as f:
                    json.dump(dummy_story, f, indent=2, ensure_ascii=False)

                # Save updated metadata
                self.project_manager._save_meta(project_id, meta)

            except Exception as e:
                # Log error but don't fail project creation completely?
                # Actually, it's better to log it and maybe the user can retry story generation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to process prompts file {request.prompts_file}: {e}")
                print(f"[ERROR] Failed to process prompts file: {e}")

        return ProjectDetail.from_project_data(meta=meta)

    def update_project(self, project_id: str, request: UpdateProjectRequest) -> ProjectMetadata:
        """Update project metadata"""
        meta = self.project_manager.load_project(project_id)

        if request.idea is not None:
            meta['idea'] = request.idea

        if request.story_agent is not None:
            meta['story_agent'] = request.story_agent

        if request.shots_agent is not None:
            meta['shots_agent'] = request.shots_agent

        if request.aspect_ratio is not None:
            meta['aspect_ratio'] = request.aspect_ratio

        if request.completed is not None:
            meta['completed'] = request.completed
            if request.completed:
                from datetime import datetime
                meta['completed_at'] = datetime.now().isoformat()

        self.project_manager._save_meta(project_id, meta)
        return ProjectMetadata(**meta)

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its files"""
        import shutil
        project_dir = self.project_manager.get_project_dir(project_id)

        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
            return True
        return False

    def duplicate_project(self, project_id: str, new_project_id: Optional[str] = None) -> ProjectDetail:
        """Duplicate a project"""
        import shutil
        from datetime import datetime

        old_project_dir = self.project_manager.get_project_dir(project_id)

        # Create new project
        meta = self.project_manager.load_project(project_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_project_id = new_project_id or f"project_{timestamp}"

        new_project_dir = self.project_manager.get_project_dir(new_project_id)
        shutil.copytree(old_project_dir, new_project_dir)

        # Update metadata
        new_meta = meta.copy()
        new_meta['project_id'] = new_project_id
        new_meta['timestamp'] = timestamp
        new_meta['started_at'] = datetime.now().isoformat()
        new_meta['completed'] = False
        new_meta['completed_at'] = None
        new_meta['steps'] = {
            'story': False,
            'scene_graph': False,
            'shots': False,
            'images': False,
            'videos': False,
            'narration': False
        }
        new_meta['stats'] = {
            'total_shots': 0,
            'images_generated': 0,
            'videos_rendered': 0,
            'narration_generated': False
        }

        # Reset shot status in shots.json
        shots_path = os.path.join(new_project_dir, "shots.json")
        if os.path.exists(shots_path):
            with open(shots_path, 'r', encoding='utf-8') as f:
                shots = json.load(f)
            for shot in shots:
                shot['image_generated'] = False
                shot['video_rendered'] = False
            with open(shots_path, 'w', encoding='utf-8') as f:
                json.dump(shots, f, indent=2, ensure_ascii=False)

        self.project_manager._save_meta(new_project_id, new_meta)

        return self.get_project(new_project_id)

    def get_project_dir(self, project_id: str) -> str:
        """Get project directory path"""
        return self.project_manager.get_project_dir(project_id)

    def get_images_dir(self, project_id: str) -> str:
        """Get images directory for project"""
        return self.project_manager.get_images_dir(project_id)

    def get_videos_dir(self, project_id: str) -> str:
        """Get videos directory for project"""
        return self.project_manager.get_videos_dir(project_id)
