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
from core import json_atomic
import config


# Get logger for project management
logger = get_logger(__name__)


class ProjectManager:
    # Single lock guarding all JSON read-modify-write transactions of one
    # project (shots.json, meta, story.json) so multi-file updates stay atomic.
    PROJECT_LOCK_NAME = ".project_lock"

    def __init__(self, projects_dir=None):
        if projects_dir is None:
            # Import here to avoid circular dependencies
            import config
            self.projects_dir = getattr(config, 'ABS_PROJECTS_DIR', "output/projects")
        else:
            self.projects_dir = projects_dir

        os.makedirs(self.projects_dir, exist_ok=True)

    def _project_lock_path(self, project_id: str) -> str:
        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        return os.path.join(project_dir, self.PROJECT_LOCK_NAME)

    @contextlib.contextmanager
    def lock_project(self, project_id: str, timeout: int = 30):
        """
        File-based lock to prevent concurrent read-modify-write collisions on a
        project's JSON files. Re-entrant within a process/thread and safe
        across processes (atomic directory creation, stale-lock recovery).
        """
        with json_atomic.file_lock(self._project_lock_path(project_id), timeout=timeout):
            yield

    def update_shots_safely(self, project_id: str, modify_func):
        """
        Atomically loads, modifies, and saves shots.json with explicit file locking.

        The shot list is always re-read from disk inside the lock — never taken
        from an in-memory snapshot — so concurrent writers cannot overwrite
        each other's updates.

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

    def update_story_safely(self, project_id: str, modify_func):
        """
        Atomically loads, modifies, and saves story.json with explicit file locking.

        The story is always re-read from disk inside the lock, so writers that
        ran to completion while this generation was in flight (e.g. a parallel
        character-image completion) are never overwritten by a stale snapshot.

        Args:
            project_id: The ID of the project.
            modify_func: A callable that accepts the parsed story dict and updates it in-place.

        Returns:
            The updated story dict, or None if story.json is missing/corrupt.
        """
        story_path = os.path.join(self.get_project_dir(project_id), "story.json")
        with self.lock_project(project_id):
            if not os.path.exists(story_path):
                logger.warning(f"Story file not found for locked update: {story_path}")
                return None
            story = json_atomic.read_json(story_path, default=None)
            if story is None:
                logger.error(f"Malformed story.json for project: {project_id}")
                return None
            modify_func(story)
            json_atomic.atomic_write_json(story_path, story, indent=4)
            return story

    def sync_character_asset_refs(self, project_id: str) -> int:
        """
        Attach each character's reference image to that character's shots as a
        project-media asset reference (reference_asset_ids), so image generation
        consumes asset references directly instead of matching characters by
        name against shot prompts at generation time.

        Only standard (non-FLFI2V) shots are touched — FLFI2V shots resolve
        then/now references from the character separately. Refs the sync
        attached earlier are tracked per shot (synced_character_asset_refs) and
        replaced on the next sync, so regenerating a character image swaps the
        attached ref instead of accumulating old versions. Refs the user
        attached manually are never touched. The character ref is appended
        after user refs (order = priority, first is primary). Idempotent.

        Returns the number of shots updated.
        """
        story = self.get_story(project_id)
        characters = (story or {}).get('characters') or []
        if not characters:
            return 0

        # Character name -> asset ref for its reference image
        name_to_ref = {}
        all_names = set()
        for char in characters:
            name = (char.get('name') or '').strip()
            if not name:
                continue
            all_names.add(name)
            ref_path = char.get('character_reference_image_path')
            if not ref_path:
                continue
            asset_ref = self._project_media_asset_ref(project_id, self.relativize_path(ref_path))
            if asset_ref:
                name_to_ref[name] = asset_ref
        if not all_names:
            return 0

        updated = 0

        def modify(shots):
            nonlocal updated
            for shot in shots:
                if shot.get('is_flfi2v'):
                    continue
                name = (shot.get('character_name') or '').strip()
                if name not in all_names:
                    continue
                asset_ref = name_to_ref.get(name)
                original_refs = shot.get('reference_asset_ids') or []
                synced = shot.get('synced_character_asset_refs') or []
                refs = [r for r in original_refs if r not in synced]
                if asset_ref and asset_ref not in refs:
                    refs.append(asset_ref)
                if refs == original_refs:
                    continue
                shot['reference_asset_ids'] = refs
                shot['synced_character_asset_refs'] = [asset_ref] if asset_ref else []
                updated += 1

        self.update_shots_safely(project_id, modify)
        if updated:
            logger.info(f"Attached character asset references to {updated} shot(s) in project {project_id}")
        return updated

    @staticmethod
    def _project_media_asset_ref(project_id: str, rel_path: str):
        """Convert 'output/projects/{pid}/{media_dir}/{filename}' into the
        'p/{pid}/{media_dir}/{filename}' asset reference, or None when the path
        is not project media in an image directory."""
        p = (rel_path or '').replace('\\', '/')
        prefix = f"output/projects/{project_id}/"
        if not p.startswith(prefix):
            return None
        rest = p[len(prefix):]
        media_dir, _, filename = rest.partition('/')
        if not filename or media_dir not in ("images", "references", "backgrounds"):
            return None
        return f"p/{project_id}/{rest}"

    def append_shot_media_paths(self, project_id: str, paths, shot_id: str = None,
                                shot_index: int = None, list_field: str = 'image_paths'):
        """
        Append media paths (image/video variations) to a shot's path list.

        The dedupe-and-append happens inside the lock against the FRESH list
        from disk, so concurrent generations adding variations to the same shot
        never drop each other's entries (unlike passing a full list captured
        earlier from a stale snapshot).
        """
        if not paths:
            return

        def modify_shot(shots):
            target_shot = self._find_shot(shots, shot_id, shot_index)
            if not target_shot:
                logger.warning(f"append_shot_media_paths: could not find shot ID={shot_id}, Index={shot_index}")
                return
            path_list = target_shot.get(list_field)
            if not isinstance(path_list, list):
                path_list = []
                target_shot[list_field] = path_list
            existing_abs = {config.resolve_path(p) for p in path_list if p}
            for p in paths:
                if not p:
                    continue
                abs_p = config.resolve_path(p)
                if abs_p not in existing_abs:
                    path_list.append(abs_p)
                    existing_abs.add(abs_p)

        self.update_shots_safely(project_id, modify_shot)

    @staticmethod
    def _find_shot(shots, shot_id=None, shot_index=None):
        """Locate a shot dict by ID (preferred), falling back to 1-based index. Returns None if not found."""
        if shot_id:
            for s in shots:
                if s.get('id') == shot_id:
                    return s
        if shot_index is not None:
            if 0 <= shot_index - 1 < len(shots):
                return shots[shot_index - 1]
        return None

    def update_shot_metadata(self, project_id: str, updates: dict, shot_id: str = None, shot_index: int = None):
        """
        Update metadata for a specific shot using ID (preferred) or index.
        Race-proof: shots.json AND the meta stats are updated under ONE lock,
        with the shot list re-read fresh from disk (never an in-memory snapshot).
        """
        with self.lock_project(project_id):
            shots = self._load_shots(project_id)
            target_shot = self._find_shot(shots, shot_id, shot_index)

            if target_shot:
                # Apply updates
                for key, value in updates.items():
                    target_shot[key] = value

                # Special handling for path lists (image_paths, video_paths)
                # Map specific path fields to their corresponding variation lists
                path_to_list_map = {
                    'image_path': 'image_paths',
                    'then_image_path': 'image_paths',
                    'now_image_path': 'image_paths',
                    'video_path': 'video_paths',
                    'meeting_video_path': 'video_paths',
                    'departure_video_path': 'video_paths'
                }

                for update_key, list_key in path_to_list_map.items():
                    if update_key in updates:
                        path = updates[update_key]
                        if path:
                            # Normalize path to absolute for reliable comparison
                            # (_load_shots ensures existing list items are also absolute)
                            abs_path = config.resolve_path(path)

                            if list_key not in target_shot:
                                target_shot[list_key] = []

                            # Check for existence using absolute path
                            if abs_path not in target_shot[list_key]:
                                target_shot[list_key].append(abs_path)
            else:
                logger.warning(f"Could not find shot to update: ID={shot_id}, Index={shot_index}")

            self._save_shots(project_id, shots)

            # Update metadata stats from the SAME transaction (fresh meta read)
            meta = self.load_project(project_id)
            if meta:
                try:
                    meta.setdefault('stats', {})
                    meta['stats']['images_generated'] = sum(1 for s in shots if s.get('image_generated', False))
                    meta['stats']['videos_rendered'] = sum(1 for s in shots if s.get('video_rendered', False))
                    self._save_meta(project_id, meta)
                except Exception as e:
                    logger.error(f"Failed to update metadata stats in locked block: {e}")
        return True  # Best effort

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

    def create_project(self, idea, project_id=None, story_agent="default", shots_agent="default", total_duration=None, aspect_ratio="16:9", prompt_mode="video"):
        """Create a new project

        Args:
            idea: The video idea/prompt
            project_id: Optional project ID. If not provided, generates timestamp-based ID
            story_agent: Story generation agent
            shots_agent: Shots prompt agent
            total_duration: Target video length in seconds
            aspect_ratio: Video aspect ratio ("16:9" or "9:16")
            prompt_mode: Default prompt style for video generation ("video" or "motion")
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
            'prompt_mode': prompt_mode,
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
        """Save story output (full replacement, written atomically)"""
        project_dir = os.path.join(self.projects_dir, project_id)
        story_path = os.path.join(project_dir, "story.json")

        logger.debug(f"Saving story to: {story_path}")
        json_atomic.atomic_write_json(story_path, json.loads(story_json) if isinstance(story_json, str) else story_json, indent=2)

        # Update metadata safely
        def modify_meta(meta):
            meta['steps']['story'] = True
        self.update_meta_safely(project_id, modify_meta)

    def save_shots(self, project_id, shots):
        """Save shot data (image prompts, motion prompts) and initialize status fields.

        Full-list replacement — intended for (re-)planning, not for recording
        generation results. Written atomically under the project lock so it can
        never interleave with a concurrent update_shots_safely transaction.
        """
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
                'duration': shot.get('duration'),
                'image_prompt': shot.get('image_prompt', ''),
                'motion_prompt': shot.get('motion_prompt', ''),
                'video_prompt': shot.get('video_prompt'),
                'prompt_type': shot.get('prompt_type'),
                'camera': shot.get('camera', ''),
                'narration': shot.get('narration'),
                'soundfx_prompt': shot.get('soundfx_prompt'),
                'soundfx_generated': shot.get('soundfx_generated', False),
                'soundfx_path': shot.get('soundfx_path'),
                'scene_id': shot.get('scene_id', 0),
                'batch_number': shot.get('batch_number', idx),
                'reference_asset_ids': shot.get('reference_asset_ids', []),
                'synced_character_asset_refs': shot.get('synced_character_asset_refs', []),
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

        # Save to shots.json (atomic, under the project lock) and refresh stats
        with self.lock_project(project_id):
            json_atomic.atomic_write_json(shots_path, shots_with_status)

            meta = self.load_project(project_id)
            if meta:
                meta['stats']['total_shots'] = len(shots)
                meta['steps']['shots'] = True
                self._save_meta(project_id, meta)

    def relativize_path(self, path):
        """Convert an absolute path to a relative path if it's within the project root or output dir"""
        if not path:
            return path
            
        # Normalize slashes first for consistent checking
        path = path.replace('\\', '/')
        
        # If it doesn't look like an absolute path (no drive letter or leading slash on non-windows)
        # and it's already starting with "output/", return as is
        if not os.path.isabs(path) and path.startswith('output/'):
            return path
            
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
        """Save project metadata (atomic)"""
        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)

        meta_path = os.path.join(project_dir, f"{project_id}_meta.json")
        json_atomic.atomic_write_json(meta_path, meta)

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

        json_atomic.atomic_write_json(shots_path, shots)

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
