#!/usr/bin/env python
"""
Test runner script - run all tests
"""
import sys
import subprocess

def main():
    """Run tests using pytest"""
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/",
        "-v", "--tb=short"
    ])
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
