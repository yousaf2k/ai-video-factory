"""Unit tests for project_service media-duration probing (editor timeline fix)."""
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from web_ui.backend.services import project_service as ps


class _StubService:
    """Just enough of ProjectService for _attach_media_durations."""

    def __init__(self, project_dir):
        self.project_manager = type("PM", (), {"get_project_dir": lambda self, pid: project_dir})()


class TestResolveProjectMediaPath(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.project_dir = tempfile.mkdtemp(prefix="aivf_dur_test_")
        self.videos_dir = os.path.join(self.project_dir, "videos")
        os.makedirs(self.videos_dir, exist_ok=True)
        self.video = os.path.join(self.videos_dir, "shot_001_001.mp4")
        with open(self.video, "wb") as f:
            f.write(b"\x00\x00\x00\x18ftypisom")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def test_none_path(self):
        self.assertIsNone(ps._resolve_project_media_path(self.project_dir, None))
        self.assertIsNone(ps._resolve_project_media_path(self.project_dir, ""))

    def test_full_output_projects_path(self):
        stored = "output/projects/project_x/videos/shot_001_001.mp4"
        resolved = ps._resolve_project_media_path(self.project_dir, stored)
        self.assertEqual(os.path.normcase(resolved or ""), os.path.normcase(self.video))

    def test_bare_filename(self):
        resolved = ps._resolve_project_media_path(self.project_dir, "shot_001_001.mp4")
        self.assertEqual(os.path.normcase(resolved or ""), os.path.normcase(self.video))

    def test_missing_file(self):
        self.assertIsNone(
            ps._resolve_project_media_path(self.project_dir, "output/projects/project_x/videos/nope.mp4")
        )


class TestProbeMediaDuration(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="aivf_probe_test_")
        ps._media_duration_cache.clear()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        ps._media_duration_cache.clear()

    def test_missing_file_returns_none(self):
        self.assertIsNone(ps._probe_media_duration(os.path.join(self.tmp, "nope.mp4")))

    def test_non_media_file_returns_none(self):
        path = os.path.join(self.tmp, "junk.mp4")
        with open(path, "wb") as f:
            f.write(b"not a video")
        self.assertIsNone(ps._probe_media_duration(path))

    def test_real_video_duration(self):
        """Requires ffmpeg in PATH; skipped when unavailable."""
        import shutil
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not available")
        path = os.path.join(self.tmp, "tiny.mp4")
        import subprocess
        subprocess.run(
            ["ffmpeg", "-v", "quiet", "-f", "lavfi", "-i", "testsrc=duration=0.5:size=64x64:rate=10",
             "-y", path],
            check=True, capture_output=True, timeout=60,
        )
        duration = ps._probe_media_duration(path)
        self.assertIsNotNone(duration)
        self.assertAlmostEqual(duration, 0.5, delta=0.2)
        # Second call served from cache (same value)
        self.assertEqual(ps._probe_media_duration(path), duration)


class TestAttachMediaDurations(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.project_dir = tempfile.mkdtemp(prefix="aivf_attach_test_")
        ps._media_duration_cache.clear()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.project_dir, ignore_errors=True)
        ps._media_duration_cache.clear()

    def test_fields_set_and_none_for_missing(self):
        shots = [
            {"index": 1, "video_path": "output/projects/p1/videos/a.mp4"},
            {"index": 2, "video_path": None},
            {"index": 3, "is_flfi2v": True,
             "meeting_video_path": "output/projects/p1/videos/m.mp4",
             "departure_video_path": "output/projects/p1/videos/d.mp4"},
        ]
        durations = {
            os.path.normcase(os.path.join(self.project_dir, "videos", "a.mp4")): 5.167,
            os.path.normcase(os.path.join(self.project_dir, "videos", "m.mp4")): 4.0,
            # d.mp4 deliberately missing -> None
        }

        def fake_probe(path):
            return durations.get(os.path.normcase(path)) if path else None

        with patch.object(ps, "_probe_media_duration", side_effect=fake_probe):
            with patch.object(ps, "_resolve_project_media_path",
                              side_effect=lambda pdir, p: (
                                  None if not p else os.path.join(pdir, "videos", os.path.basename(p))
                              )):
                ps.ProjectService._attach_media_durations(_StubService(self.project_dir), "p1", shots)

        self.assertEqual(shots[0]["video_duration"], 5.167)
        self.assertIsNone(shots[1]["video_duration"])
        self.assertEqual(shots[2]["meeting_video_duration"], 4.0)
        self.assertIsNone(shots[2]["departure_video_duration"])

    def test_empty_shots_noop(self):
        ps.ProjectService._attach_media_durations(_StubService(self.project_dir), "p1", [])
        ps.ProjectService._attach_media_durations(_StubService(self.project_dir), "p1", None)


if __name__ == "__main__":
    unittest.main()
