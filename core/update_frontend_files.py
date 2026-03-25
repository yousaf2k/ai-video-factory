import os

# List of files containing /api/projects that need to be updated
files_to_update = [
    r"c:\AI\ai_video_factory_v1\web_ui\frontend\src\services\api.ts",
    r"c:\AI\ai_video_factory_v1\web_ui\frontend\src\lib\utils.ts",
    r"c:\AI\ai_video_factory_v1\web_ui\frontend\src\components\scenes\SceneCard.tsx",
    r"c:\AI\ai_video_factory_v1\web_ui\frontend\src\components\scenes\SceneBackgroundManager.tsx",
    r"c:\AI\ai_video_factory_v1\web_ui\frontend\src\components\queue\QueueItem.tsx",
    r"c:\AI\ai_video_factory_v1\web_ui\frontend\src\components\characters\CharacterReferenceUpload.tsx"
]

for path in files_to_update:
    if not os.path.exists(path):
        print(f"Skipping {path} - not found")
        continue

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Special handling for utils.ts
    if "utils.ts" in path:
        content = content.replace("output/projects/", "output/projects/")
        content = content.replace("/api/projects/", "/api/projects/")
    else:
        # Standard replacement
        content = content.replace("/api/projects", "/api/projects")

    # Optional: rename variables from projectId to projectId to match new style if preferred
    # But it is not strictly required if keeping variables for JS code is acceptable
    # For better compatibility with existing JS hooks we might leave variable names alone, OR do it correctly.
    # Frontend variables might not have changed in frontend hooks yet.
    # Let's DO rename variables IF they are obvious like `${projectId}` to `${projectId}`
    # Wait, if I do that, I must also update ALL components using that hook.
    # The safest is just to leave variable names in JS/TS as `projectId` for now to avoid cascading breaks,
    # OR if I'm confident, update them.
    # Given the user says "change the word project... in api urls", keeping variable as `projectId` in code but URL as `/api/projects/${projectId}` is FINE and works perfectly.
    # Let's just update the URL string literals first to be safe, which is what actually hits the backend.

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated {path}")
