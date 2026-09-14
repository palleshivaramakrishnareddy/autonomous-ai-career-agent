import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import the FastAPI instance
from backend.app.main import app

# Export for Vercel
# Vercel's Python runtime detects 'app' in api/index.py
