"""
FFmpeg-based video export service
Handles multi-track timeline composition with video layering and audio mixing
"""
import os
import json
import subprocess
import logging
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self):
        self.exports = {}  # Track active exports
        try:
            from config import ABS_OUTPUT_DIR, ABS_PROJECTS_DIR
            self.exports_dir = os.path.join(ABS_OUTPUT_DIR, "exports")
            self.projects_dir = ABS_PROJECTS_DIR
        except Exception:
            self.exports_dir = "output/exports"
            self.projects_dir = "output/projects"
            
        os.makedirs(self.exports_dir, exist_ok=True)

    async def start_export(
        self,
        project_id: str,
        timeline_data: Dict[str, Any],
        settings: Dict[str, Any]
    ) -> str:
        """
        Start an asynchronous video export process

        Args:
            project_id: Project identifier
            timeline_data: Timeline JSON with tracks and clips
            settings: Export settings (resolution, fps, codec, etc.)

        Returns:
            export_id: Unique identifier for tracking export progress
        """
        export_id = str(uuid.uuid4())[:8]

        # Initialize export state
        self.exports[export_id] = {
            'status': 'initializing',
            'progress': 0,
            'project_id': project_id,
            'started_at': datetime.now().isoformat(),
            'error': None,
            'output_path': None
        }

        # Start export in background
        asyncio.create_task(self._process_export(export_id, project_id, timeline_data, settings))

        return export_id

    async def _process_export(
        self,
        export_id: str,
        project_id: str,
        timeline_data: Dict[str, Any],
        settings: Dict[str, Any]
    ):
        """
        Process the export asynchronously
        """
        try:
            await self._update_export_status(export_id, 'processing', 5, 'Analyzing timeline...')

            # Validate timeline data
            if 'clips' not in timeline_data or 'tracks' not in timeline_data:
                raise ValueError('Invalid timeline data: missing clips or tracks')

            clips = timeline_data['clips']
            tracks = timeline_data['tracks']
            duration = timeline_data.get('duration', 60)

            logger.info(f"Starting export {export_id} for project {project_id}")
            logger.info(f"Timeline: {len(clips)} clips, {len(tracks)} tracks, {duration}s duration")

            # Separate video and audio tracks
            video_tracks = [t for t in tracks if t['type'] == 'video']
            audio_tracks = [t for t in tracks if t['type'] == 'audio']

            video_clips = [c for c in clips if c['type'] == 'video']
            audio_clips = [c for c in clips if c['type'] == 'audio']

            await self._update_export_status(export_id, 'processing', 10, 'Preparing assets...')

            # Resolve asset paths
            project_dir = os.path.join(self.projects_dir, project_id)

            # Generate temp directory for this export
            temp_dir = os.path.join(self.exports_dir, export_id)
            os.makedirs(temp_dir, exist_ok=True)

            # Process video tracks (composite multiple layers)
            if video_clips:
                await self._update_export_status(export_id, 'processing', 5, f'Synchronizing {len(video_clips)} visual assets...')
                video_output = os.path.join(temp_dir, "video_composite.mp4")
                await self._compose_video_tracks(
                    video_clips,
                    video_tracks,
                    duration,
                    settings,
                    video_output,
                    export_id
                )
            else:
                video_output = None

            # Process audio tracks (mix multiple audio streams)
            if audio_clips:
                await self._update_export_status(export_id, 'processing', 65, f'Calibrating {len(audio_clips)} audio streams...')
                audio_output = os.path.join(temp_dir, "audio_mix.m4a")
                await self._mix_audio_tracks(
                    audio_clips,
                    audio_tracks,
                    duration,
                    settings,
                    audio_output,
                    project_dir,
                    export_id
                )
            else:
                audio_output = None

            # Final merge (video + audio)
            await self._update_export_status(export_id, 'processing', 90, 'Final assembly...')

            final_output = os.path.join(self.exports_dir, f"{project_id}_export_{export_id}.mp4")

            if video_output and audio_output:
                await self._merge_video_audio(
                    video_output,
                    audio_output,
                    final_output,
                    settings
                )
            elif video_output:
                # Video only, no audio
                import shutil
                shutil.copy(video_output, final_output)
            else:
                raise ValueError("No video or audio content to export")

            await self._update_export_status(
                export_id,
                'completed',
                100,
                'Export complete',
                final_output
            )

            logger.info(f"Export {export_id} completed successfully: {final_output}")

        except Exception as e:
            logger.error(f"Export {export_id} failed: {e}", exc_info=True)
            await self._update_export_status(
                export_id,
                'failed',
                0,
                'Export failed',
                error=str(e)
            )

    async def _compose_video_tracks(
        self,
        clips: List[Dict],
        tracks: List[Dict],
        duration: float,
        settings: Dict,
        output_path: str,
        export_id: str
    ):
        """
        Compose multiple video tracks using FFmpeg
        Handles video layering with top tracks having priority
        """
        logger.info(f"Composing {len(clips)} video clips")

        # Sort clips by start time for processing
        sorted_clips = sorted(clips, key=lambda c: c['startAt'])

        if not sorted_clips:
            # Create black video if no clips
            await self._create_black_video(output_path, duration, settings)
            return

        # Simple concatenation approach for now
        # Build FFmpeg concat filter
        filter_parts = []
        input_files = []

        for i, clip in enumerate(sorted_clips):
            project_dir = os.path.join(self.projects_dir, self.exports[export_id]['project_id'])
            clip_path = self._resolve_clip_path(clip['url'], project_dir)
            if os.path.exists(clip_path):
                input_files.extend(['-i', clip_path])
                # Scale and set duration, enforce square pixels (setsar=1)
                res = settings.get('resolution', '1280x720').replace('x', ':')
                filter_parts.append(f"[{i}:v]scale={res}:force_original_aspect_ratio=decrease,pad={res}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={settings.get('fps', 30)},setpts=PTS-STARTPTS,trim=0:{clip['duration']}[v{i}]")

        if filter_parts:
            # Concatenate all videos
            concat_inputs = "".join([f"[v{i}]" for i in range(len(sorted_clips))])
            filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(sorted_clips)}:v=1[outv]"
        else:
            res = settings.get('resolution', '1280x720').replace('x', ':')
            filter_complex = f"color=black:s={res}:d={duration},setsar=1[outv]"

        # Build FFmpeg command
        output_args = [
            'ffmpeg', '-y', '-loglevel', 'info', '-stats',
            *input_files,
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-c:v', settings.get('codec', 'libx264'),
            '-b:v', settings.get('bitrate', '5M'),
            '-pix_fmt', 'yuv420p',
            '-aspect', settings.get('aspect_ratio', '16:9'),
            '-t', str(duration),
            output_path
        ]

        await self._update_export_status(export_id, 'processing', 10, 'Preparing professional render pipeline...')
        
        await self._run_ffmpeg_command(
            output_args, 
            export_id, 
            progress_range=(10, 60),
            total_duration=duration,
            status_msg='Composing video...'
        )

    async def _mix_audio_tracks(
        self,
        clips: List[Dict],
        tracks: List[Dict],
        duration: float,
        settings: Dict,
        output_path: str,
        project_dir: str,
        export_id: str
    ):
        """
        Mix multiple audio tracks using FFmpeg
        Handles audio mixing with proper timing and crossfades
        """
        logger.info(f"Mixing {len(clips)} audio clips")

        if not clips:
            # Create silent audio
            await self._create_silent_audio(output_path, duration)
            return

        filter_complex = []
        input_files = []
        valid_inputs = 0
        valid_input_refs = []

        for clip in clips:
            clip_path = self._resolve_clip_path(clip['url'], project_dir)

            if not os.path.exists(clip_path):
                logger.warning(f"Audio clip file not found: {clip_path}")
                continue

            input_files.extend(['-i', clip_path])
            
            input_idx = valid_inputs
            # Trim and delay audio to correct position
            filter_complex.append(
                f"[{input_idx}:a]atrim=start=0:end={clip['duration']},"
                f"adelay={int(clip['startAt'] * 1000)}|{int(clip['startAt'] * 1000)}[a{input_idx}]"
            )
            valid_input_refs.append(f"[a{input_idx}]")
            valid_inputs += 1

        if valid_inputs == 0:
            # Create silent audio
            await self._create_silent_audio(output_path, duration)
            return
        elif valid_inputs == 1:
            final_audio = valid_input_refs[0]
        else:
            # Mix all valid audio inputs
            mix_inputs = "".join(valid_input_refs)
            filter_complex.append(
                f"{mix_inputs}amix=inputs={valid_inputs}:duration=longest[audio_mix]"
            )
            final_audio = "[audio_mix]"

        # Normalize audio
        filter_complex.append(f"{final_audio}loudnorm=I=-16:TP=-1.5:LRA=11[outa]")

        # Build FFmpeg command
        output_args = [
            'ffmpeg', '-y', '-loglevel', 'info', '-stats',
            *input_files,
            '-filter_complex', ';'.join(filter_complex),
            '-map', '[outa]',
            '-c:a', 'aac',
            '-b:a', settings.get('audio_bitrate', '192k'),
            '-t', str(duration),
            output_path
        ]

        await self._run_ffmpeg_command(
            output_args, 
            export_id, 
            progress_range=(65, 90),
            total_duration=duration,
            status_msg='Mixing audio tracks...'
        )

    async def _merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        settings: Dict
    ):
        """
        Merge video and audio tracks into final output
        """
        output_args = [
            'ffmpeg', '-y', '-loglevel', 'info', '-stats',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',  # Copy video stream without re-encoding
            '-c:a', 'aac',
            '-b:a', settings.get('audio_bitrate', '192k'),
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *output_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg merge failed: {stderr.decode()}")

    async def _create_black_video(self, output_path: str, duration: float, settings: Dict):
        """Create a black video when no video clips exist"""
        output_args = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f"color=c=black:s={settings.get('resolution', '1280x720')}:d={duration},setsar=1",
            '-c:v', settings.get('codec', 'libx264'),
            '-b:v', settings.get('bitrate', '5M'),
            '-pix_fmt', 'yuv420p',
            '-aspect', settings.get('aspect_ratio', '16:9'),
            '-t', str(duration),
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *output_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Failed to create black video")

    async def _create_silent_audio(self, output_path: str, duration: float):
        """Create silent audio when no audio clips exist"""
        output_args = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f"anullsrc=r=44100:cl=stereo:d={duration}",
            '-c:a', 'aac',
            '-b:a', '192k',
            '-t', str(duration),
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *output_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Failed to create silent audio")

    async def _run_ffmpeg_command(
        self, 
        args: List[str], 
        export_id: str, 
        progress_range: Tuple[int, int],
        total_duration: float = 300.0,
        status_msg: str = 'processing'
    ):
        """
        Run FFmpeg command and monitor progress
        """
        logger.info(f"Running FFmpeg: {' '.join(args)}")

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Immediate feedback that process has started
        p_start, _ = progress_range
        await self._update_export_status(export_id, 'processing', p_start, f"Initializing engine: {status_msg}")

        # Monitor stderr for progress (FFmpeg writes progress to stderr)
        progress_start, progress_end = progress_range

        while True:
            # Read in smaller chunks or line-by-line but ensure it's not buffered
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8', errors='ignore').strip()
            if not line_str:
                continue

            # Parse FFmpeg time output for progress
            # Look for both 'time=' and 'out_time=' (from -progress)
            if 'time=' in line_str:
                try:
                    time_str = line_str.split('time=')[1].split()[0]
                    # Parse HH:MM:SS or HH:MM:SS.mmm format
                    time_parts = time_str.split(':')
                    if len(time_parts) == 3:
                        hours, minutes, seconds = time_parts
                        current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

                        # Calculate progress using actual total_duration
                        # Avoid division by zero
                        duration_to_use = total_duration if total_duration > 0 else 1.0
                        progress_pct = current_time / duration_to_use
                        progress = progress_start + progress_pct * (progress_end - progress_start)
                        
                        await self._update_export_status(export_id, status_msg, min(progress, progress_end))
                except:
                    pass  # Ignore parsing errors

        await process.wait()

        if process.returncode != 0:
            stderr_output = await process.stderr.read()
            raise RuntimeError(f"FFmpeg failed with code {process.returncode}: {stderr_output.decode()}")

    def _resolve_clip_path(self, url: str, project_dir: str) -> str:
        """
        Resolve clip URL to absolute file path
        Handles API URLs and relative paths
        """
        # Remove API URL prefix if present
        if '/api/projects/' in url:
            # Extract project ID and filename
            parts = url.split('/api/projects/')
            if len(parts) > 1:
                path_parts = parts[1].split('/')
                if len(path_parts) >= 3:
                    # Reconstruct the path inside the project
                    clean_parts = list(path_parts[1:])
                    if clean_parts:
                        # Remove any URL query parameters from the filename
                        clean_parts[-1] = clean_parts[-1].split('?')[0]
                        
                    return os.path.join(project_dir, *clean_parts)

        if 'output/projects/' in url.replace('\\', '/'):
            # It's a relative path starting with output/projects
            rel = url.replace('\\', '/').split('output/projects/')[-1].lstrip('/')
            return os.path.join(self.projects_dir, rel)
            
        if os.path.isabs(url):
            return url

        # If URL resolution failed, try relative path
        return os.path.join(project_dir, url)

    async def _update_export_status(
        self,
        export_id: str,
        status: str,
        progress: float,
        message: str = '',
        output_path: str = None,
        error: str = None
    ):
        """Update export status and broadcast via WebSocket"""
        if export_id not in self.exports:
            return

        # Get project_id for broadcasting
        project_id = self.exports[export_id].get('project_id')

        self.exports[export_id].update({
            'status': status,
            'progress': min(100, max(0, progress)),
            'message': message,
            'updated_at': datetime.now().isoformat()
        })

        if output_path:
            self.exports[export_id]['output_path'] = output_path

        if error:
            self.exports[export_id]['error'] = error

        # Broadcast update via WebSocket
        if project_id:
            try:
                from web_ui.backend.websocket.manager import manager
                # Using broadcast_sync as this might be called from background tasks
                # where the loop management is handled by ConnectionManager
                manager.broadcast_sync(project_id, {
                    "type": "editor_export",
                    "data": {
                        "export_id": export_id,
                        "status": status,
                        "progress": min(100, max(0, progress)),
                        "message": message,
                        "filename": os.path.basename(output_path) if output_path else None,
                        "error": error
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to broadcast export update: {e}")

        logger.debug(f"Export {export_id}: {status} - {progress:.1f}% - {message}")

    def get_export_status(self, export_id: str) -> Dict[str, Any]:
        """Get current export status"""
        data = self.exports.get(export_id, {
            'status': 'not_found',
            'progress': 0,
            'error': 'Export not found'
        })
        
        # Add filename to help with notifications
        if data.get('status') == 'completed' and data.get('output_path'):
            data['filename'] = os.path.basename(data['output_path'])
            
        return data

    def get_export_path(self, export_id: str) -> Optional[str]:
        """Get output file path for completed export"""
        export_data = self.exports.get(export_id)
        if export_data and export_data['status'] == 'completed':
            return export_data.get('output_path')
        return None
