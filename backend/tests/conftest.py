"""
Pytest configuration file.

This adds the parent directory to the Python path so tests can import the app module.
"""

import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
