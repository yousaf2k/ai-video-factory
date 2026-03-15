import os

files_to_delete = [
    r"c:\AI\ai_video_factory_v1\web_ui\backend\api\projects.py",
    r"c:\AI\ai_video_factory_v1\web_ui\backend\services\project_service.py",
    r"c:\AI\ai_video_factory_v1\web_ui\backend\models\project.py",
    r"c:\AI\ai_video_factory_v1\core\project_manager.py"
]

for path in files_to_delete:
    if os.path.exists(path):
        os.remove(path)
        print(f"Deleted {path}")
    else:
        print(f"Skipping {path} - not found")

# Also delete helper scripts I created if they still exist
helpers = [
    r"c:\AI\ai_video_factory_v1\core\create_project_manager.py",
    r"c:\AI\ai_video_factory_v1\core\create_project_service.py",
    r"c:\AI\ai_video_factory_v1\core\create_project_models_api.py",
    r"c:\AI\ai_video_factory_v1\core\update_shots_api.py",
    r"c:\AI\ai_video_factory_v1\core\update_backend_files.py",
    r"c:\AI\ai_video_factory_v1\core\update_manager.py",
    r"c:\AI\ai_video_factory_v1\core\update_remaining_backend.py",
    r"c:\AI\ai_video_factory_v1\core\fix_api_services.py"
]

for h in helpers:
    if os.path.exists(h):
        os.remove(h)
        print(f"Deleted helper {h}")

print("Cleanup complete")
