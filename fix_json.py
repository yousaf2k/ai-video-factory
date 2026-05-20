import config
filepath = config.resolve_path(os.path.join("projects", "project_20260323_091004", "shots.json"))

if not os.path.exists(filepath):
    print("File not found")
    exit(1)

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The file looks like:
# ...
#   }
# ]departure_video_rendered": null, ...
# ]

# Search without newline directly!
idx = content.find("]departure_video_rendered")
if idx == -1:
    # Try any variation: "]dep" or similar
    idx = content.find("]departure_")

if idx != -1:
    fixed_content = content[:idx+1]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    print(f"Fixed via exact index: {idx}")
else:
    # Generic backup: Find the ABSOLUTE FIRST `]` that is followed by anything that isn't space/newline/comma.
    # But this covers the exact case.
    print("Could not reliably fix JSON pattern.")
