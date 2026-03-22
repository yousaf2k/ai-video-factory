#!/usr/bin/env python3
"""
Restore is_flfi2v=True for all shots in ThenVsNow projects.
This fixes the issue where fix_scene_ids.py set is_flfi2v to None.
"""
import os
import sys
import json
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from core.project_manager import ProjectManager
from web_ui.backend.models.story import ProjectType


def fix_project_is_flfi2v(project_id: str, dry_run: bool = True):
    """Fix is_flfi2v field for all shots in a ThenVsNow project."""
    project_manager = ProjectManager()

    print(f"\n{'='*70}")
    print(f"Restoring is_flfi2v Field for ThenVsNow Project")
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
        is_flfi2v = shot.get('is_flfi2v')
        if is_flfi2v is None or is_flfi2v is False:
            shots_to_fix.append(shot)

    if not shots_to_fix:
        print("\nNo shots need fixing - all already have is_flfi2v=True")
        return True

    print(f"Shots to fix: {len(shots_to_fix)}")
    print(f"\nis_flfi2v distribution:")
    flfi2v_counts = {}
    for shot in shots:
        is_flfi2v = shot.get('is_flfi2v', 'None')
        flfi2v_counts[is_flfi2v] = flfi2v_counts.get(is_flfi2v, 0) + 1

    for value, count in sorted(flfi2v_counts.items()):
        print(f"  is_flfi2v={value}: {count} shots")

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
        shot['is_flfi2v'] = True

    # Save changes
    project_manager.save_shots(project_id, shots)
    print(f"\nSaved updated shots to shots.json")

    print(f"\n{'='*70}")
    print("SUCCESS: All shots now have is_flfi2v=True")
    print("Images will now be generated with correct FLFI2V naming")
    print(f"{'='*70}\n")

    return True


def list_projects():
    """List all projects with their is_flfi2v status."""
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
                # Load shots to check is_flfi2v
                project_manager = ProjectManager()
                try:
                    shots = project_manager.get_shots(project_id)
                    if shots:
                        flfi2v_counts = {}
                        for s in shots:
                            val = s.get('is_flfi2v', 'None')
                            flfi2v_counts[val] = flfi2v_counts.get(val, 0) + 1

                        counts_str = ', '.join(f'{k}={v}' for k, v in flfi2v_counts.items())

                        print(f"{project_id}")
                        print(f"  Title: {title}")
                        print(f"  Shots: {len(shots)}")
                        print(f"  is_flfi2v: {counts_str}")

                        # Check if needs fixing
                        needs_fix = any(s.get('is_flfi2v') is not True for s in shots)
                        if needs_fix:
                            print(f"  Status: NEEDS FIX")
                        else:
                            print(f"  Status: OK")
                        print()
                except Exception as e:
                    print(f"{project_id}: Error loading shots - {e}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Restore is_flfi2v=True for ThenVsNow projects"
    )
    parser.add_argument("--project", help="Project ID to fix")
    parser.add_argument("--live", action="store_true", help="Actually save changes (default is dry-run)")
    parser.add_argument("--list", action="store_true", help="List all projects and their is_flfi2v status")

    args = parser.parse_args()

    if args.list:
        list_projects()
    elif args.project:
        fix_project_is_flfi2v(args.project, dry_run=not args.live)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
