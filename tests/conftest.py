"""
pytest configuration and shared fixtures
"""
import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Shared fixtures for tests can be added here

def temp_output_dir(tmp_path):
    """Fixture providing temporary output directory for tests"""
    return tmp_path
