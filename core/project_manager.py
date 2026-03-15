"""
Project Manager - Tracks progress and enables crash recovery
Saves all outputs (story, shots, images) and tracks completion status
"""
import json
import os
from datetime import datetime
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
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)

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

        # Update metadata
        meta = self.load_project(project_id)
        meta['steps']['story'] = True
        self._save_meta(project_id, meta)

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

        # Update metadata - only store stats, not the shots array
        meta = self.load_project(project_id)
        meta['stats']['total_shots'] = len(shots)
        meta['steps']['shots'] = True
        self._save_meta(project_id, meta)

    def _relativize_path(self, path):
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

    def mark_image_generated(self, project_id, shot_index, image_path):
        """Mark that an image has been generated for a shot"""
        # Load shots from shots.json
        shots = self._load_shots(project_id)

        if 0 <= shot_index - 1 < len(shots):
            # Convert to relative path if absolute and inside project root
            normalized_path = self._relativize_path(image_path)

            shots[shot_index - 1]['image_generated'] = True
            shots[shot_index - 1]['image_path'] = normalized_path

            # Also add to image_paths array if not already there
            if normalized_path not in shots[shot_index - 1].get('image_paths', []):
                if 'image_paths' not in shots[shot_index - 1]:
                    shots[shot_index - 1]['image_paths'] = []
                shots[shot_index - 1]['image_paths'].append(normalized_path)

            # Update stats
            images_generated = sum(1 for s in shots if s.get('image_generated', False))

            # Save updated shots.json
            self._save_shots(project_id, shots)

            # Update metadata stats
            meta = self.load_project(project_id)
            meta['stats']['images_generated'] = images_generated
            self._save_meta(project_id, meta)

    def mark_video_rendered(self, project_id, shot_index, video_path=None):
        """
        Mark that a video has been rendered for a shot

        Args:
            project_id: Project identifier
            shot_index: Shot number (1-based)
            video_path: Optional path to the video file (will verify existence)
        """
        import os

        # Verify video file exists before marking as rendered
        if video_path and not os.path.exists(video_path):
            print(f"[WARN] mark_video_rendered: Video file doesn't exist: {video_path}")
            print(f"[WARN] Shot {shot_index} will NOT be marked as rendered")
            return

        # Load shots from shots.json
        shots = self._load_shots(project_id)

        if 0 <= shot_index - 1 < len(shots):
            shots[shot_index - 1]['video_rendered'] = True
            if video_path:
                # Convert to relative path if absolute and inside project root
                normalized_path = self._relativize_path(video_path)
                
                shots[shot_index - 1]['video_path'] = normalized_path

                # Also add to video_paths array if not already there
                if normalized_path not in shots[shot_index - 1].get('video_paths', []):
                    if 'video_paths' not in shots[shot_index - 1]:
                        shots[shot_index - 1]['video_paths'] = []
                    shots[shot_index - 1]['video_paths'].append(normalized_path)

            # Update stats
            videos_rendered = sum(1 for s in shots if s.get('video_rendered', False))

            # Save updated shots.json
            self._save_shots(project_id, shots)

            # Update metadata stats
            meta = self.load_project(project_id)
            meta['stats']['videos_rendered'] = videos_rendered
            self._save_meta(project_id, meta)

    def mark_step_complete(self, project_id, step_name):
        """Mark a pipeline step as complete"""
        logger.debug(f"Marking step complete: {project_id} - {step_name}")
        meta = self.load_project(project_id)
        meta['steps'][step_name] = True
        self._save_meta(project_id, meta)

    def mark_project_complete(self, project_id):
        """Mark the entire project as complete"""
        meta = self.load_project(project_id)
        meta['completed'] = True
        meta['completed_at'] = datetime.now().isoformat()
        self._save_meta(project_id, meta)

    def mark_then_image_generated(self, project_id, shot_index, image_path):
        """Mark THEN image as generated for FLFI2V shot"""
        shots = self._load_shots(project_id)

        if 0 <= shot_index - 1 < len(shots):
            normalized_path = self._relativize_path(image_path)

            shots[shot_index - 1]['then_image_generated'] = True
            shots[shot_index - 1]['then_image_path'] = normalized_path

            # Save updated shots.json
            self._save_shots(project_id, shots)

    def mark_now_image_generated(self, project_id, shot_index, image_path):
        """Mark NOW image as generated for FLFI2V shot"""
        shots = self._load_shots(project_id)

        if 0 <= shot_index - 1 < len(shots):
            normalized_path = self._relativize_path(image_path)

            shots[shot_index - 1]['now_image_generated'] = True
            shots[shot_index - 1]['now_image_path'] = normalized_path

            # Save updated shots.json
            self._save_shots(project_id, shots)

    def mark_meeting_video_rendered(self, project_id, shot_index, video_path):
        """Mark meeting video as rendered for FLFI2V shot"""
        import os

        # Verify video file exists before marking as rendered
        if video_path and not os.path.exists(video_path):
            print(f"[WARN] mark_meeting_video_rendered: Video file doesn't exist: {video_path}")
            return

        shots = self._load_shots(project_id)

        if 0 <= shot_index - 1 < len(shots):
            normalized_path = self._relativize_path(video_path)

            shots[shot_index - 1]['meeting_video_rendered'] = True
            shots[shot_index - 1]['meeting_video_path'] = normalized_path

            # Also add to video_paths array if not already there
            if normalized_path not in shots[shot_index - 1].get('video_paths', []):
                if 'video_paths' not in shots[shot_index - 1]:
                    shots[shot_index - 1]['video_paths'] = []
                shots[shot_index - 1]['video_paths'].append(normalized_path)

            # Save updated shots.json
            self._save_shots(project_id, shots)

    def mark_departure_video_rendered(self, project_id, shot_index, video_path):
        """Mark departure video as rendered for FLFI2V shot"""
        import os

        # Verify video file exists before marking as rendered
        if video_path and not os.path.exists(video_path):
            print(f"[WARN] mark_departure_video_rendered: Video file doesn't exist: {video_path}")
            return

        shots = self._load_shots(project_id)

        if 0 <= shot_index - 1 < len(shots):
            normalized_path = self._relativize_path(video_path)

            shots[shot_index - 1]['departure_video_rendered'] = True
            shots[shot_index - 1]['departure_video_path'] = normalized_path

            # Also add to video_paths array if not already there
            if normalized_path not in shots[shot_index - 1].get('video_paths', []):
                if 'video_paths' not in shots[shot_index - 1]:
                    shots[shot_index - 1]['video_paths'] = []
                shots[shot_index - 1]['video_paths'].append(normalized_path)

            # Save updated shots.json
            self._save_shots(project_id, shots)

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

        with open(shots_path, 'r', encoding='utf-8') as f:
            shots = json.load(f)
            
        # Resolve paths to absolute at runtime
        for shot in shots:
            if 'image_path' in shot and shot['image_path']:
                shot['image_path'] = config.resolve_path(shot['image_path'])
            if 'image_paths' in shot and shot['image_paths']:
                shot['image_paths'] = [config.resolve_path(p) for p in shot['image_paths']]
            if 'video_path' in shot and shot['video_path']:
                shot['video_path'] = config.resolve_path(shot['video_path'])
                
        return shots

    def _save_shots(self, project_id, shots):
        """Save shots to shots.json, ensuring paths are relative"""
        project_dir = self.get_project_dir(project_id)
        shots_path = os.path.join(project_dir, "shots.json")

        # Ensure all paths are relative before saving
        for shot in shots:
            if 'image_path' in shot:
                shot['image_path'] = self._relativize_path(shot.get('image_path'))
            if 'image_paths' in shot:
                shot['image_paths'] = [self._relativize_path(p) for p in shot.get('image_paths', [])]
            if 'video_path' in shot:
                shot['video_path'] = self._relativize_path(shot.get('video_path'))

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
