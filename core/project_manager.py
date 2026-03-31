"""
Project Manager - Tracks progress and enables crash recovery
Saves all outputs (story, shots, images) and tracks completion status
"""
import json
import os
import time
from datetime import datetime
import contextlib
from core.logger_config import get_logger
import config


# Get logger for project management
logger = get_logger(__name__)


class ProjectManager:
    def __init__(self, projects_dir=None):
        if projects_dir is None:
            # Import here to avoid circular dependencies
            import config
            self.projects_dir = getattr(config, 'ABS_PROJECTS_DIR', "output/projects")
        else:
            self.projects_dir = projects_dir
            
        os.makedirs(self.projects_dir, exist_ok=True)

    @contextlib.contextmanager
    def lock_project(self, project_id: str, timeout: int = 15):
        """
        File-based lock to prevent concurrent read-modify-write collisions on shots.json.
        Uses atomic directory creation (supported across Windows and POSIX).
        """
        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        lock_dir = os.path.join(project_dir, ".shots_lock")
        
        start_time = time.time()
        acquired = False
        
        while time.time() - start_time < timeout:
            try:
                os.mkdir(lock_dir)
                acquired = True
                break
            except FileExistsError:
                # Check if the lock is stale (e.g., from a crash)
                try:
                    # If lock is older than 60 seconds, remove it as stale safety
                    mtime = os.path.getmtime(lock_dir)
                    if time.time() - mtime > 60:
                        logger.warning(f"Removing stale project lock for {project_id}")
                        os.rmdir(lock_dir)
                        continue
                except:
                    pass
                time.sleep(0.1)
                
        if not acquired:
            logger.error(f"Timed out acquiring lock for project: {project_id}")
            raise TimeoutError(f"Could not acquire project lock for {project_id} after {timeout} seconds.")
            
        try:
            yield
        finally:
            try:
                os.rmdir(lock_dir)
            except Exception as e:
                logger.warning(f"Failed to release project lock for {project_id}: {e}")

    def update_shots_safely(self, project_id: str, modify_func):
        """
        Atomically loads, modifies, and saves shots.json with explicit file locking.
        
        Args:
            project_id: The ID of the project.
            modify_func: A callable that accepts a list of shot dictionaries or None and updates in-place.
        """
        with self.lock_project(project_id):
            shots = self._load_shots(project_id)
            modify_func(shots)
            self._save_shots(project_id, shots)
            return shots

    def update_meta_safely(self, project_id: str, modify_func):
        """
        Atomically loads, modifies, and saves project metadata with explicit file locking.
        
        Args:
            project_id: The ID of the project.
            modify_func: A callable that accepts a metadata dictionary and updates it in-place.
        """
        with self.lock_project(project_id):
            meta = self.load_project(project_id)
            if not meta:
                logger.warning(f"Metadata not found for project: {project_id}")
                return None
            modify_func(meta)
            self._save_meta(project_id, meta)
            return meta

    def update_shot_metadata(self, project_id: str, updates: dict, shot_id: str = None, shot_index: int = None):
        """
        Update metadata for a specific shot using ID (preferred) or index.
        Thread-safe and race-condition proof via update_shots_safely.
        """
        def modify_shot(shots):
            target_shot = None
            
            # 1. Try to find by ID
            if shot_id:
                for s in shots:
                    if s.get('id') == shot_id:
                        target_shot = s
                        break
            
            # 2. Skip fallback if ID was provided but not found (safety)
            # 3. Try to find by index if no ID or ID not found
            if not target_shot and shot_index is not None:
                if 0 <= shot_index - 1 < len(shots):
                    target_shot = shots[shot_index - 1]
                    
            if target_shot:
                # Apply updates
                for key, value in updates.items():
                    target_shot[key] = value
                
                # Special handling for path lists (image_paths, video_paths)
                if 'image_path' in updates:
                    path = updates['image_path']
                    if 'image_paths' not in target_shot:
                        target_shot['image_paths'] = []
                    if path and path not in target_shot['image_paths']:
                        target_shot['image_paths'].append(path)
                
                if 'video_path' in updates:
                    path = updates['video_path']
                    if 'video_paths' not in target_shot:
                        target_shot['video_paths'] = []
                    if path and path not in target_shot['video_paths']:
                        target_shot['video_paths'].append(path)
            else:
                logger.warning(f"Could not find shot to update: ID={shot_id}, Index={shot_index}")
                return  # Move to next step if no shot for stats update

        # Update shots.json atomically
        updated_shots = self.update_shots_safely(project_id, modify_shot)
        
        # Update metadata stats (total counts) - do it SAFELY using update_meta_safely
        def modify_meta(meta):
            try:
                images_generated = sum(1 for s in updated_shots if s.get('image_generated', False))
                videos_rendered = sum(1 for s in updated_shots if s.get('video_rendered', False))
                
                meta['stats']['images_generated'] = images_generated
                meta['stats']['videos_rendered'] = videos_rendered
            except Exception as e:
                logger.error(f"Failed to update metadata stats in locked block: {e}")
                
        self.update_meta_safely(project_id, modify_meta)
        return True # Best effort

    def get_latest_project(self):
        """Get the most recent incomplete project, or None if all complete"""
        projects = []

        for item in os.listdir(self.projects_dir):
            item_path = os.path.join(self.projects_dir, item)

            # Check if it's a directory (project folder) and not a backup
            if os.path.isdir(item_path) and "_backup_" not in item:
                meta_file = f"{item}_meta.json"
                meta_path = os.path.join(item_path, meta_file)

                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            projects.append({
                                'file': meta_file,
                                'meta': meta,
                                'timestamp': meta.get('timestamp', ''),
                                'completed': meta.get('completed', False)
                            })
                    except:
                        pass

        if not projects:
            return None

        # Sort by timestamp descending, get most recent
        projects.sort(key=lambda x: x['timestamp'], reverse=True)
        latest = projects[0]

        # Only return if incomplete
        if not latest['completed']:
            return latest['meta']
        return None

    def create_project(self, idea, project_id=None, story_agent="default", shots_agent="default", total_duration=None, aspect_ratio="16:9"):
        """Create a new project

        Args:
            idea: The video idea/prompt
            project_id: Optional project ID. If not provided, generates timestamp-based ID
            story_agent: Story generation agent
            shots_agent: Shots prompt agent
            total_duration: Target video length in seconds
            aspect_ratio: Video aspect ratio ("16:9" or "9:16")
        """
        if project_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_id = f"project_{timestamp}"
        else:
            # Extract timestamp from project_id for consistency
            timestamp = project_id.replace("project_", "")

        logger.info(f"Creating new project: {project_id}")
        logger.debug(f"  Idea: {idea[:100]}...")

        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)

        meta = {
            'project_id': project_id,
            'timestamp': timestamp,
            'idea': idea,
            'story_agent': story_agent,
            'shots_agent': shots_agent,
            'total_duration': total_duration,
            'aspect_ratio': aspect_ratio,
            'started_at': datetime.now().isoformat(),
            'completed': False,
            'steps': {
                'story': False,
                'scene_graph': False,
                'shots': False,
                'images': False,
                'videos': False,
                'narration': False
            },
            'stats': {
                'total_shots': 0,
                'images_generated': 0,
                'videos_rendered': 0,
                'narration_generated': False
            }
        }

        self._save_meta(project_id, meta)
        logger.info(f"Project created: {project_id}")
        return project_id, meta

    def load_project(self, project_id):
        """Load an existing project"""
        logger.debug(f"Loading project: {project_id}")
        meta_path = os.path.join(self.projects_dir, project_id, f"{project_id}_meta.json")
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            logger.error(f"Failed to load project meta from {meta_path}: {e}")
            return {}

    def get_project(self, project_id):
        """Get project metadata (alias for load_project)"""
        return self.load_project(project_id)

    def save_story(self, project_id, story_json):
        """Save story output"""
        project_dir = os.path.join(self.projects_dir, project_id)
        story_path = os.path.join(project_dir, "story.json")

        logger.debug(f"Saving story to: {story_path}")
        with open(story_path, 'w', encoding='utf-8') as f:
            f.write(story_json)

        # Update metadata safely
        def modify_meta(meta):
            meta['steps']['story'] = True
        self.update_meta_safely(project_id, modify_meta)

    def save_shots(self, project_id, shots):
        """Save shot data (image prompts, motion prompts) and initialize status fields"""
        project_dir = os.path.join(self.projects_dir, project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        # Sort shots by batch_number, then preserve original order within each batch
        # If batch_number is not present, use the original index
        shots_with_batch = [(i, s) for i, s in enumerate(shots)]
        # Sort by batch_number first, then by original index to maintain order within batches
        shots_with_batch.sort(key=lambda x: (x[1].get('batch_number', x[0] + 1), x[0]))

        import uuid
        
        # Add status fields to each shot with reindexed values (1 to n)
        shots_with_status = []
        for idx, (original_idx, shot) in enumerate(shots_with_batch, start=1):
            shot_data = {
                'id': shot.get('id', str(uuid.uuid4())[:8]),
                'index': idx,
                'image_prompt': shot.get('image_prompt', ''),
                'motion_prompt': shot.get('motion_prompt', ''),
                'camera': shot.get('camera', ''),
                'scene_id': shot.get('scene_id', 0),
                'batch_number': shot.get('batch_number', idx),
                # Status fields
                'image_generated': shot.get('image_generated', False),
                'image_path': shot.get('image_path'),
                'image_paths': shot.get('image_paths', []),  # For multiple image variations
                'video_rendered': shot.get('video_rendered', False),
                'video_path': shot.get('video_path'),
                'video_paths': shot.get('video_paths', []),
                # FLFI2V fields - preserve if present
                'is_flfi2v': shot.get('is_flfi2v', False),
                'character_id': shot.get('character_id'),
                'then_image_prompt': shot.get('then_image_prompt'),
                'then_image_generated': shot.get('then_image_generated'),
                'then_image_path': shot.get('then_image_path'),
                'now_image_prompt': shot.get('now_image_prompt'),
                'now_image_generated': shot.get('now_image_generated'),
                'now_image_path': shot.get('now_image_path'),
                'meeting_video_prompt': shot.get('meeting_video_prompt'),
                'meeting_video_rendered': shot.get('meeting_video_rendered'),
                'meeting_video_path': shot.get('meeting_video_path'),
                'departure_video_prompt': shot.get('departure_video_prompt'),
                'departure_video_rendered': shot.get('departure_video_rendered'),
                'departure_video_path': shot.get('departure_video_path'),
            }
            shots_with_status.append(shot_data)

        # Log batch distribution for debugging
        batch_counts = {}
        for shot in shots_with_status:
            batch_num = shot.get('batch_number', 0)
            batch_counts[batch_num] = batch_counts.get(batch_num, 0) + 1
        logger.info(f"Shots sorted by batch_number: {batch_counts}")

        # Save to shots.json
        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots_with_status, f, indent=2, ensure_ascii=False)

        # Update metadata safely - only store stats, not the shots array
        def modify_meta(meta):
            meta['stats']['total_shots'] = len(shots)
            meta['steps']['shots'] = True
        self.update_meta_safely(project_id, modify_meta)

    def relativize_path(self, path):
        """Convert an absolute path to a relative path if it's within the project root or output dir"""
        if not path:
            return path
            
        # Normalize slashes
        path = path.replace('\\', '/')
        
        # 1. Check PROJECT_ROOT (Standard case)
        project_root = getattr(config, 'PROJECT_ROOT', None)
        if project_root:
            project_root_norm = project_root.replace('\\', '/')
            if path.lower().startswith(project_root_norm.lower()):
                try:
                    rel_path = os.path.relpath(path, project_root).replace('\\', '/')
                    return rel_path
                except Exception:
                    pass # Fall through to next check
            
        # 2. Check OUTPUT_DIR (Handle different drives)
        output_dir = getattr(config, 'OUTPUT_DIR', None)
        if output_dir and os.path.isabs(output_dir):
            output_parent = os.path.dirname(output_dir)
            output_parent_norm = output_parent.replace('\\', '/')
            if path.lower().startswith(output_parent_norm.lower()):
                try:
                    # Relativize to the parent of OUTPUT_DIR so it starts with "output/"
                    rel_path = os.path.relpath(path, output_parent).replace('\\', '/')
                    return rel_path
                except Exception:
                    pass
        
        return path

    def mark_image_generated(self, project_id, shot_index, image_path, shot_id=None):
        """Mark that an image has been generated for a shot"""
        normalized_path = self.relativize_path(image_path)
        updates = {
            'image_generated': True,
            'image_path': normalized_path
        }
        self.update_shot_metadata(project_id, updates, shot_id=shot_id, shot_index=shot_index)

    def mark_video_rendered(self, project_id, shot_index, video_path=None, shot_id=None):
        """
        Mark that a video has been rendered for a shot
        """
        import os
        # Verify video file exists before marking as rendered
        if video_path and not os.path.exists(video_path):
            logger.warning(f"mark_video_rendered: Video file doesn't exist: {video_path}")
            return

        normalized_path = self.relativize_path(video_path) if video_path else None
        updates = {
            'video_rendered': True
        }
        if normalized_path:
            updates['video_path'] = normalized_path
            
        self.update_shot_metadata(project_id, updates, shot_id=shot_id, shot_index=shot_index)

    def mark_step_complete(self, project_id, step_name):
        """Mark a pipeline step as complete"""
        logger.debug(f"Marking step complete: {project_id} - {step_name}")
        def modify_meta(meta):
            meta['steps'][step_name] = True
        self.update_meta_safely(project_id, modify_meta)

    def mark_project_complete(self, project_id):
        """Mark the entire project as complete"""
        def modify_meta(meta):
            meta['completed'] = True
            meta['completed_at'] = datetime.now().isoformat()
        self.update_meta_safely(project_id, modify_meta)

    def mark_then_image_generated(self, project_id, shot_index, image_path, shot_id=None):
        """Mark THEN image as generated for FLFI2V shot"""
        normalized_path = self.relativize_path(image_path)
        updates = {
            'then_image_generated': True,
            'then_image_path': normalized_path
        }
        self.update_shot_metadata(project_id, updates, shot_id=shot_id, shot_index=shot_index)

    def mark_now_image_generated(self, project_id, shot_index, image_path, shot_id=None):
        """Mark NOW image as generated for FLFI2V shot"""
        normalized_path = self.relativize_path(image_path)
        updates = {
            'now_image_generated': True,
            'now_image_path': normalized_path
        }
        self.update_shot_metadata(project_id, updates, shot_id=shot_id, shot_index=shot_index)

    def mark_meeting_video_rendered(self, project_id, shot_index, video_path, shot_id=None):
        """Mark meeting video as rendered for FLFI2V shot"""
        import os
        if video_path and not os.path.exists(video_path):
            logger.warning(f"mark_meeting_video_rendered: Video file doesn't exist: {video_path}")
            return

        normalized_path = self.relativize_path(video_path)
        updates = {
            'meeting_video_rendered': True,
            'meeting_video_path': normalized_path
        }
        self.update_shot_metadata(project_id, updates, shot_id=shot_id, shot_index=shot_index)

    def mark_departure_video_rendered(self, project_id, shot_index, video_path, shot_id=None):
        """Mark departure video as rendered for FLFI2V shot"""
        import os
        if video_path and not os.path.exists(video_path):
            logger.warning(f"mark_departure_video_rendered: Video file doesn't exist: {video_path}")
            return

        normalized_path = self.relativize_path(video_path)
        updates = {
            'departure_video_rendered': True,
            'departure_video_path': normalized_path
        }
        self.update_shot_metadata(project_id, updates, shot_id=shot_id, shot_index=shot_index)

    def get_project_dir(self, project_id):
        """Get the directory path for a project"""
        return os.path.join(self.projects_dir, project_id)

    def get_images_dir(self, project_id):
        """Get the images directory for a project"""
        return os.path.join(self.projects_dir, project_id, "images")

    def get_videos_dir(self, project_id):
        """Get the videos directory for a project"""
        return os.path.join(self.projects_dir, project_id, "videos")

    def get_narration_dir(self, project_id):
        """Get the narration directory for a project"""
        return os.path.join(self.projects_dir, project_id, "narration")

    def get_shots(self, project_id):
        """Get shots from shots.json"""
        return self._load_shots(project_id)

    def get_story(self, project_id):
        """Get story from story.json"""
        return self._load_story(project_id)

    def _load_story(self, project_id):
        """Load story from story.json"""
        project_dir = os.path.join(self.projects_dir, project_id)
        story_path = os.path.join(project_dir, "story.json")

        if os.path.exists(story_path):
            try:
                with open(story_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Malformed story.json in {project_id}: {e}")
                return {}
            except Exception as e:
                logger.error(f"Failed to load story from {story_path}: {e}")
                return None
        else:
            logger.warning(f"Story file not found: {story_path}")
            return None

    def _save_meta(self, project_id, meta):
        """Save project metadata"""
        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)

        meta_path = os.path.join(project_dir, f"{project_id}_meta.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def _update_shots_file(self, project_id, shots):
        """Update the shots.json file with current shot data"""
        # This method is kept for backward compatibility but now delegates to _save_shots
        self._save_shots(project_id, shots)

    def _load_shots(self, project_id):
        """Load shots from shots.json, resolving relative paths to absolute"""
        project_dir = self.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        if not os.path.exists(shots_path):
            return []

        try:
            with open(shots_path, 'r', encoding='utf-8') as f:
                shots = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Malformed shots.json in {project_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load shots from {shots_path}: {e}")
            return []
            
        # Resolve paths to absolute at runtime
        path_fields = ['image_path', 'video_path', 'then_image_path', 'now_image_path',
                       'meeting_video_path', 'departure_video_path']
        list_path_fields = ['image_paths', 'video_paths']
        for shot in shots:
            for field in path_fields:
                if field in shot and shot[field]:
                    shot[field] = config.resolve_path(shot[field])
            for field in list_path_fields:
                if field in shot and shot[field]:
                    shot[field] = [config.resolve_path(p) for p in shot[field]]
                
        return shots

    def _save_shots(self, project_id, shots):
        """Save shots to shots.json, ensuring paths are relative"""
        project_dir = self.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        # Ensure all paths are relative before saving
        path_fields = ['image_path', 'video_path', 'then_image_path', 'now_image_path',
                       'meeting_video_path', 'departure_video_path']
        list_path_fields = ['image_paths', 'video_paths']
        for shot in shots:
            for field in path_fields:
                if field in shot:
                    shot[field] = self.relativize_path(shot.get(field))
            for field in list_path_fields:
                if field in shot:
                    shot[field] = [self.relativize_path(p) for p in shot.get(field, [])]

        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

    def list_all_projects(self):
        """List all projects with their status"""
        projects = []

        for item in os.listdir(self.projects_dir):
            item_path = os.path.join(self.projects_dir, item)

            # Check if it's a directory (project folder) and not a backup
            if os.path.isdir(item_path) and "_backup_" not in item:
                meta_file = f"{item}_meta.json"
                meta_path = os.path.join(item_path, meta_file)

                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            projects.append(meta)
                    except:
                        pass

        projects.sort(key=lambda x: x['timestamp'], reverse=True)
        return projects

    def print_project_summary(self, project_id):
        """Print a summary of a project"""
        meta = self.load_project(project_id)
        if not meta:
            print(f"Project meta not found for {project_id}")
            return

        print("\n" + "="*60)
        print(f"SESSION: {project_id}")
        print("="*60)
        print(f"Idea: {meta.get('idea', 'N/A')[:100]}...")
        print(f"Started: {meta.get('started_at', 'N/A')}")
        print(f"Status: {'COMPLETE' if meta.get('completed') else 'IN PROGRESS'}")
        print(f"\nProgress:")
        print(f"  Total shots: {meta['stats']['total_shots']}")
        print(f"  Images generated: {meta['stats']['images_generated']}")
        print(f"  Videos rendered: {meta['stats']['videos_rendered']}")
        print(f"  Narration: {'[DONE]' if meta.get('steps', {}).get('narration', False) else '[TODO]'}")

        # Load shots from shots.json for details
        shots = self._load_shots(project_id)
        if shots:
            print(f"\nShot Details:")
            for shot in shots:
                status = "[DONE]" if shot.get('video_rendered', False) else ("[IMG]" if shot.get('image_generated', False) else "[TODO]")
                print(f"  {status} Shot {shot['index']}: {shot.get('image_prompt', '')[:50]}...")

        print("="*60 + "\n")
