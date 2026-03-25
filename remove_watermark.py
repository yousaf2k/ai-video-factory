"""
remove_watermark.py — Standalone Gemini watermark remover.

Usage:
    python remove_watermark.py <input_image> [output_image]

If no output_image is specified, the result is saved next to the input
with a _removed suffix (e.g. photo.png → photo_removed.png).
"""

import sys
import os
import shutil

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    # Determine output path
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_removed{ext}"

    # Copy original to output before modifying
    shutil.copy2(input_path, output_path)
    print(f"Processing: {input_path}")
    print(f"Output:     {output_path}")

    # Add project root to path so we can import the module
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)

    try:
        from core.geminiweb_subprocess import _remove_watermark
        _remove_watermark(output_path)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
