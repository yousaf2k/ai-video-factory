#!/usr/bin/env python3
"""
Fix script to update all shots in a ThenVsNow project to use scene_id=0.
This allows departure videos to properly transition between characters.
"""
import os
import sys
import json
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from core.project_manager import ProjectManager
from web_ui.backend.models.story import ProjectType


def fix_project_scene_ids(project_id: str, dry_run: bool = True):
    """Fix scene_ids for all shots in a ThenVsNow project."""
    project_manager = ProjectManager()

    print(f"\n{'='*70}")
    print(f"Fixing Scene IDs for ThenVsNow Project")
    print(f"Project: {project_id}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will save changes)'}")
    print(f"{'='*70}\n")

    # Load project data
    story = project_manager.get_story(project_id)
    shots = project_manager.get_shots(project_id)

    if not story or not shots:
        print(f"ERROR: Could not load project data")
        return False

    # Check if this is a ThenVsNow project
    project_type = story.get('project_type', 1)
    if project_type != ProjectType.THEN_VS_NOW:
        print(f"WARNING: This is not a ThenVsNow project (project_type={project_type})")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return False

    print(f"Total shots: {len(shots)}")

    # Check which shots need fixing
    shots_to_fix = []
    for shot in shots:
        if shot.get('scene_id') != 0:
            shots_to_fix.append(shot)

    if not shots_to_fix:
        print("\nNo shots need fixing - all already have scene_id=0")
        return True

    print(f"Shots to fix: {len(shots_to_fix)}")
    print(f"\nCurrent scene_id distribution:")
    scene_counts = {}
    for shot in shots:
        scene_id = shot.get('scene_id', 'N/A')
        scene_counts[scene_id] = scene_counts.get(scene_id, 0) + 1

    for scene_id, count in sorted(scene_counts.items()):
        print(f"  scene_id {scene_id}: {count} shots")

    print(f"\nShots that will be updated:")
    for shot in shots_to_fix:
        print(f"  Shot {shot.get('index')}: scene_id {shot.get('scene_id')} -> 0")

    if dry_run:
        print(f"\nDRY RUN: No changes made. Use --live to apply changes.")
        return True

    # Confirm before making changes
    print(f"\n{'='*70}")
    response = input("Apply these changes? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled")
        return False

    # Apply fixes
    for shot in shots_to_fix:
        shot['scene_id'] = 0
        # Ensure is_flfi2v is preserved (or set to True for ThenVsNow projects)
        if shot.get('is_flfi2v') is None:
            shot['is_flfi2v'] = True

    # Save changes
    project_manager.save_shots(project_id, shots)
    print(f"\nSaved updated shots to shots.json")

    print(f"\n{'='*70}")
    print("SUCCESS: All shots now have scene_id=0")
    print("Departure videos will now properly transition between characters")
    print(f"{'='*70}\n")

    return True


def list_projects():
    """List all projects with their scene_id distribution."""
    from web_ui.backend.services.project_service import ProjectService

    project_service = ProjectService()
    projects_list = project_service.list_projects()

    print(f"\n{'='*70}")
    print("All Projects")
    print(f"{'='*70}\n")

    for project_info in projects_list:
        project_id = getattr(project_info, 'project_id', None)
        story = getattr(project_info, 'story', {})

        if not project_id:
            continue

        if isinstance(story, dict):
            project_type = story.get('project_type', 1)
            title = story.get('title', 'Unknown')

            # Check if ThenVsNow
            if project_type == ProjectType.THEN_VS_NOW:
                # Load shots to check scene distribution
                project_manager = ProjectManager()
                try:
                    shots = project_manager.get_shots(project_id)
                    if shots:
                        scene_ids = [s.get('scene_id', '?') for s in shots[:10]]
                        scenes_str = ', '.join(map(str, scene_ids))
                        if len(shots) > 10:
                            scenes_str += f", ... ({len(shots)} total)"

                        print(f"{project_id}")
                        print(f"  Title: {title}")
                        print(f"  Shots: {len(shots)}")
                        print(f"  Scene IDs (first 10): {scenes_str}")

                        # Check if needs fixing
                        unique_scenes = len(set(s.get('scene_id', -1) for s in shots))
                        if unique_scenes > 1:
                            print(f"  Status: NEEDS FIX ({unique_scenes} different scene_ids)")
                        else:
                            print(f"  Status: OK")
                        print()
                except Exception as e:
                    print(f"{project_id}: Error loading shots - {e}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Fix scene_ids for ThenVsNow projects"
    )
    parser.add_argument("--project", help="Project ID to fix")
    parser.add_argument("--live", action="store_true", help="Actually save changes (default is dry-run)")
    parser.add_argument("--list", action="store_true", help="List all projects and their scene_id status")

    args = parser.parse_args()

    if args.list:
        list_projects()
    elif args.project:
        fix_project_scene_ids(args.project, dry_run=not args.live)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
