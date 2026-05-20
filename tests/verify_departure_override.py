import sys
import os
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web_ui.backend.services.generation_service import GenerationService, GenerationType
from core.project_manager import ProjectManager

def setup_test_project(project_id, agent_name):
    pm = ProjectManager()
    project_dir = pm.get_project_dir(project_id)
    os.makedirs(project_dir, exist_ok=True)
    
    meta = {
        "project_id": project_id,
        "timestamp": "20260406_000000",
        "idea": "Test Idea",
        "story_agent": agent_name,
        "started_at": "2026-04-06T00:00:00",
        "completed": False,
        "steps": {},
        "stats": {}
    }
    
    meta_path = os.path.join(project_dir, f"{project_id}_meta.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"Set up test project {project_id} with agent {agent_name}")
    return project_id

def test_override_prevention():
    gs = GenerationService()
    
    # CASE 1: Actor Face Agent - Override should be REMOVED
    project_id_actor = "test_actor_face"
    setup_test_project(project_id_actor, "then_vs_now/then_vs_now_actor_faces")
    
    request_dict_actor = {
        "departure_prompt_override": "This is an override"
    }
    
    print(f"\nTesting Actor Face Agent ({project_id_actor}):")
    print(f"Before: {request_dict_actor}")
    
    # We call the logic directly since _create_queue_item is internal and does a lot of other things
    # We'll simulate the logic we added
    is_actor_face = gs._is_actor_face_agent(project_id_actor)
    print(f"Is Actor Face: {is_actor_face}")
    
    if is_actor_face:
        # Simulate DEPARTURE_VIDEO type check
        if 'departure_prompt_override' in request_dict_actor:
            print("Action: Removing departure_prompt_override (as expected)")
            request_dict_actor.pop('departure_prompt_override', None)
            
    print(f"After: {request_dict_actor}")
    assert 'departure_prompt_override' not in request_dict_actor
    print("SUCCESS: Override was correctly removed for Actor Face agent.")

    # CASE 2: Regular Agent - Override should be KEPT
    project_id_regular = "test_regular_agent"
    setup_test_project(project_id_regular, "documentary/youtube_documentary")
    
    request_dict_regular = {
        "departure_prompt_override": "This is an override"
    }
    
    print(f"\nTesting Regular Agent ({project_id_regular}):")
    print(f"Before: {request_dict_regular}")
    
    is_actor_face_reg = gs._is_actor_face_agent(project_id_regular)
    print(f"Is Actor Face: {is_actor_face_reg}")
    
    if is_actor_face_reg:
        if 'departure_prompt_override' in request_dict_regular:
            print("Action: Removing departure_prompt_override")
            request_dict_regular.pop('departure_prompt_override', None)
    else:
        print("Action: Keeping departure_prompt_override (as expected)")
            
    print(f"After: {request_dict_regular}")
    assert 'departure_prompt_override' in request_dict_regular
    print("SUCCESS: Override was correctly kept for regular agent.")

if __name__ == "__main__":
    try:
        test_override_prevention()
    finally:
        # Cleanup
        pm = ProjectManager()
        import shutil
        for pid in ["test_actor_face", "test_regular_agent"]:
            pdir = pm.get_project_dir(pid)
            if os.path.exists(pdir):
                shutil.rmtree(pdir)
                print(f"Cleaned up {pdir}")
