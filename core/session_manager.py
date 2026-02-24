"""
Session Manager - Tracks progress and enables crash recovery
Saves all outputs (story, shots, images) and tracks completion status
"""
import json
import os
from datetime import datetime
from core.logger_config import get_logger
import config


# Get logger for session management
logger = get_logger(__name__)


class SessionManager:
    def __init__(self, sessions_dir="output/sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)

    def get_latest_session(self):
        """Get the most recent incomplete session, or None if all complete"""
        sessions = []

        for item in os.listdir(self.sessions_dir):
            item_path = os.path.join(self.sessions_dir, item)

            # Check if it's a directory (session folder)
            if os.path.isdir(item_path):
                meta_file = f"{item}_meta.json"
                meta_path = os.path.join(item_path, meta_file)

                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            sessions.append({
                                'file': meta_file,
                                'meta': meta,
                                'timestamp': meta.get('timestamp', ''),
                                'completed': meta.get('completed', False)
                            })
                    except:
                        pass

        if not sessions:
            return None

        # Sort by timestamp descending, get most recent
        sessions.sort(key=lambda x: x['timestamp'], reverse=True)
        latest = sessions[0]

        # Only return if incomplete
        if not latest['completed']:
            return latest['meta']
        return None

    def create_session(self, idea, session_id=None):
        """Create a new session

        Args:
            idea: The video idea/prompt
            session_id: Optional session ID. If not provided, generates timestamp-based ID
        """
        if session_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"session_{timestamp}"
        else:
            # Extract timestamp from session_id for consistency
            timestamp = session_id.replace("session_", "")

        logger.info(f"Creating new session: {session_id}")
        logger.debug(f"  Idea: {idea[:100]}...")

        session_dir = os.path.join(self.sessions_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)

        meta = {
            'session_id': session_id,
            'timestamp': timestamp,
            'idea': idea,
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

        self._save_meta(session_id, meta)
        logger.info(f"Session created: {session_id}")
        return session_id, meta

    def load_session(self, session_id):
        """Load an existing session"""
        logger.debug(f"Loading session: {session_id}")
        meta_path = os.path.join(self.sessions_dir, session_id, f"{session_id}_meta.json")
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_session(self, session_id):
        """Get session metadata (alias for load_session)"""
        return self.load_session(session_id)

    def save_story(self, session_id, story_json):
        """Save story output"""
        session_dir = os.path.join(self.sessions_dir, session_id)
        story_path = os.path.join(session_dir, "story.json")

        logger.debug(f"Saving story to: {story_path}")
        with open(story_path, 'w', encoding='utf-8') as f:
            f.write(story_json)

        # Update metadata
        meta = self.load_session(session_id)
        meta['steps']['story'] = True
        self._save_meta(session_id, meta)

    def save_shots(self, session_id, shots):
        """Save shot data (image prompts, motion prompts) and initialize status fields"""
        session_dir = os.path.join(self.sessions_dir, session_id)
        shots_path = os.path.join(session_dir, "shots.json")

        # Sort shots by batch_number, then preserve original order within each batch
        # If batch_number is not present, use the original index
        shots_with_batch = [(i, s) for i, s in enumerate(shots)]
        # Sort by batch_number first, then by original index to maintain order within batches
        shots_with_batch.sort(key=lambda x: (x[1].get('batch_number', x[0] + 1), x[0]))

        # Add status fields to each shot with reindexed values (1 to n)
        shots_with_status = []
        for idx, (original_idx, shot) in enumerate(shots_with_batch, start=1):
            shot_data = {
                'index': idx,
                'image_prompt': shot.get('image_prompt', ''),
                'motion_prompt': shot.get('motion_prompt', ''),
                'camera': shot.get('camera', ''),
                'narration': shot.get('narration', ''),
                'batch_number': shot.get('batch_number', idx),
                # Status fields
                'image_generated': False,
                'image_path': None,
                'image_paths': [],  # For multiple image variations
                'video_rendered': False,
                'video_path': None
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
        meta = self.load_session(session_id)
        meta['stats']['total_shots'] = len(shots)
        meta['steps']['shots'] = True
        self._save_meta(session_id, meta)

    def mark_image_generated(self, session_id, shot_index, image_path):
        """Mark that an image has been generated for a shot"""
        # Load shots from shots.json
        shots = self._load_shots(session_id)

        if 0 <= shot_index - 1 < len(shots):
            # Normalize path to use forward slashes (JSON-safe)
            normalized_path = image_path.replace('\\', '/')
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
            self._save_shots(session_id, shots)

            # Update metadata stats
            meta = self.load_session(session_id)
            meta['stats']['images_generated'] = images_generated
            self._save_meta(session_id, meta)

    def mark_video_rendered(self, session_id, shot_index, video_path=None):
        """
        Mark that a video has been rendered for a shot

        Args:
            session_id: Session identifier
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
        shots = self._load_shots(session_id)

        if 0 <= shot_index - 1 < len(shots):
            shots[shot_index - 1]['video_rendered'] = True
            if video_path:
                # Normalize path for JSON
                normalized_path = video_path.replace('\\', '/')
                shots[shot_index - 1]['video_path'] = normalized_path

            # Update stats
            videos_rendered = sum(1 for s in shots if s.get('video_rendered', False))

            # Save updated shots.json
            self._save_shots(session_id, shots)

            # Update metadata stats
            meta = self.load_session(session_id)
            meta['stats']['videos_rendered'] = videos_rendered
            self._save_meta(session_id, meta)

    def mark_step_complete(self, session_id, step_name):
        """Mark a pipeline step as complete"""
        logger.debug(f"Marking step complete: {session_id} - {step_name}")
        meta = self.load_session(session_id)
        meta['steps'][step_name] = True
        self._save_meta(session_id, meta)

    def mark_session_complete(self, session_id):
        """Mark the entire session as complete"""
        meta = self.load_session(session_id)
        meta['completed'] = True
        meta['completed_at'] = datetime.now().isoformat()
        self._save_meta(session_id, meta)

    def get_session_dir(self, session_id):
        """Get the directory path for a session"""
        return os.path.join(self.sessions_dir, session_id)

    def get_images_dir(self, session_id):
        """Get the images directory for a session"""
        return os.path.join(self.sessions_dir, session_id, "images")

    def get_videos_dir(self, session_id):
        """Get the videos directory for a session"""
        return os.path.join(self.sessions_dir, session_id, "videos")

    def get_narration_dir(self, session_id):
        """Get the narration directory for a session"""
        return os.path.join(self.sessions_dir, session_id, "narration")

    def get_shots(self, session_id):
        """Get shots from shots.json"""
        return self._load_shots(session_id)

    def _save_meta(self, session_id, meta):
        """Save session metadata"""
        session_dir = os.path.join(self.sessions_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)

        meta_path = os.path.join(session_dir, f"{session_id}_meta.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def _update_shots_file(self, session_id, shots):
        """Update the shots.json file with current shot data"""
        # This method is kept for backward compatibility but now delegates to _save_shots
        self._save_shots(session_id, shots)

    def _load_shots(self, session_id):
        """Load shots from shots.json"""
        session_dir = self.get_session_dir(session_id)
        shots_path = os.path.join(session_dir, "shots.json")

        if not os.path.exists(shots_path):
            return []

        with open(shots_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_shots(self, session_id, shots):
        """Save shots to shots.json"""
        session_dir = self.get_session_dir(session_id)
        shots_path = os.path.join(session_dir, "shots.json")

        with open(shots_path, 'w', encoding='utf-8') as f:
            json.dump(shots, f, indent=2, ensure_ascii=False)

    def list_all_sessions(self):
        """List all sessions with their status"""
        sessions = []

        for item in os.listdir(self.sessions_dir):
            item_path = os.path.join(self.sessions_dir, item)

            # Check if it's a directory (session folder)
            if os.path.isdir(item_path):
                meta_file = f"{item}_meta.json"
                meta_path = os.path.join(item_path, meta_file)

                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            sessions.append(meta)
                    except:
                        pass

        sessions.sort(key=lambda x: x['timestamp'], reverse=True)
        return sessions

    def print_session_summary(self, session_id):
        """Print a summary of a session"""
        meta = self.load_session(session_id)

        print("\n" + "="*60)
        print(f"SESSION: {session_id}")
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
        shots = self._load_shots(session_id)
        if shots:
            print(f"\nShot Details:")
            for shot in shots:
                status = "[DONE]" if shot.get('video_rendered', False) else ("[IMG]" if shot.get('image_generated', False) else "[TODO]")
                print(f"  {status} Shot {shot['index']}: {shot.get('image_prompt', '')[:50]}...")

        print("="*60 + "\n")
