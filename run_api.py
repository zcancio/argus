#!/usr/bin/env python3
"""Local development server for ARGUS API"""

import sys
from pathlib import Path

# Debug: show which Python is being used
print(f"[DEBUG] Python executable: {sys.executable}")
print(f"[DEBUG] Python version: {sys.version}")

# Check if openai is available
try:
    import openai
    print(f"[DEBUG] OpenAI package found: {openai.__file__}")
except ImportError as e:
    print(f"[DEBUG] OpenAI package NOT found: {e}")

# Add project root to Python path so imports work like on Vercel
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.index:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api"],
    )
