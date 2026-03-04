"""
Session service - Wrapper around SessionManager
"""
import sys
import os
from typing import List, Dict, Any, Optional

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from core.session_manager import SessionManager
from web_ui.backend.models.session import (
    SessionMetadata, SessionDetail, SessionListItem,
    CreateSessionRequest, UpdateSessionRequest
)
import json


class SessionService:
    """Service for session management operations"""

    def __init__(self, sessions_dir: str = None):
        # Default to configured sessions directory
        if sessions_dir is None:
            import config
            sessions_dir = getattr(config, 'ABS_SESSIONS_DIR', None)
            
            if sessions_dir is None:
                # Fallback if config not loaded properly
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
                sessions_dir = os.path.join(project_root, "output", "sessions")

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"SessionService initialized with sessions_dir: {sessions_dir}")
        logger.info(f"Directory exists: {os.path.exists(sessions_dir)}")
        print(f"[DEBUG] SessionService sessions_dir: {sessions_dir}")
        print(f"[DEBUG] Directory exists: {os.path.exists(sessions_dir)}")

        self.session_manager = SessionManager(sessions_dir)

    def list_sessions(self) -> List[SessionListItem]:
        """List all sessions"""
        sessions_data = self.session_manager.list_all_sessions()
        
        result = []
        for meta in sessions_data:
            session_id = meta.get("session_id")
            story = None
            if session_id:
                session_dir = self.session_manager.get_session_dir(session_id)
                story_path = os.path.join(session_dir, "story.json")
                if os.path.exists(story_path):
                    try:
                        with open(story_path, 'r', encoding='utf-8') as f:
                            story = json.load(f)
                    except Exception:
                        pass
            result.append(SessionListItem.from_metadata(meta, story))
            
        return result

    def get_session(self, session_id: str) -> SessionDetail:
        """Get session detail with story and shots"""
        meta = self.session_manager.load_session(session_id)

        # Load story if exists
        story = None
        session_dir = self.session_manager.get_session_dir(session_id)
        story_path = os.path.join(session_dir, "story.json")
        if os.path.exists(story_path):
            with open(story_path, 'r', encoding='utf-8') as f:
                story = json.load(f)

        # Load shots if exist
        shots = self.session_manager.get_shots(session_id)

        return SessionDetail.from_session_data(
            meta=meta,
            story=story,
            shots=shots
        )

    def create_session(self, request: CreateSessionRequest) -> SessionDetail:
        """Create a new session"""
        session_id, meta = self.session_manager.create_session(
            idea=request.idea,
            session_id=request.session_id,
            story_agent=request.story_agent,
            shots_agent=request.shots_agent,
            total_duration=request.total_duration
        )

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
                self.session_manager.save_shots(session_id, shots)

                # Create dummy story.json
                session_dir = self.session_manager.get_session_dir(session_id)
                story_path = os.path.join(session_dir, "story.json")
                
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
                self.session_manager._save_meta(session_id, meta)

            except Exception as e:
                # Log error but don't fail session creation completely?
                # Actually, it's better to log it and maybe the user can retry story generation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to process prompts file {request.prompts_file}: {e}")
                print(f"[ERROR] Failed to process prompts file: {e}")

        return SessionDetail.from_session_data(meta=meta)

    def update_session(self, session_id: str, request: UpdateSessionRequest) -> SessionMetadata:
        """Update session metadata"""
        meta = self.session_manager.load_session(session_id)

        if request.idea is not None:
            meta['idea'] = request.idea

        if request.story_agent is not None:
            meta['story_agent'] = request.story_agent

        if request.shots_agent is not None:
            meta['shots_agent'] = request.shots_agent

        if request.completed is not None:
            meta['completed'] = request.completed
            if request.completed:
                from datetime import datetime
                meta['completed_at'] = datetime.now().isoformat()

        self.session_manager._save_meta(session_id, meta)
        return SessionMetadata(**meta)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its files"""
        import shutil
        session_dir = self.session_manager.get_session_dir(session_id)

        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            return True
        return False

    def duplicate_session(self, session_id: str, new_session_id: Optional[str] = None) -> SessionDetail:
        """Duplicate a session"""
        import shutil
        from datetime import datetime

        old_session_dir = self.session_manager.get_session_dir(session_id)

        # Create new session
        meta = self.session_manager.load_session(session_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_session_id = new_session_id or f"session_{timestamp}"

        new_session_dir = self.session_manager.get_session_dir(new_session_id)
        shutil.copytree(old_session_dir, new_session_dir)

        # Update metadata
        new_meta = meta.copy()
        new_meta['session_id'] = new_session_id
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
        shots_path = os.path.join(new_session_dir, "shots.json")
        if os.path.exists(shots_path):
            with open(shots_path, 'r', encoding='utf-8') as f:
                shots = json.load(f)
            for shot in shots:
                shot['image_generated'] = False
                shot['video_rendered'] = False
            with open(shots_path, 'w', encoding='utf-8') as f:
                json.dump(shots, f, indent=2, ensure_ascii=False)

        self.session_manager._save_meta(new_session_id, new_meta)

        return self.get_session(new_session_id)

    def get_session_dir(self, session_id: str) -> str:
        """Get session directory path"""
        return self.session_manager.get_session_dir(session_id)

    def get_images_dir(self, session_id: str) -> str:
        """Get images directory for session"""
        return self.session_manager.get_images_dir(session_id)

    def get_videos_dir(self, session_id: str) -> str:
        """Get videos directory for session"""
        return self.session_manager.get_videos_dir(session_id)
