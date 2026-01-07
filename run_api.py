#!/usr/bin/env python3
"""Local development server for ARGUS API"""

import sys
from pathlib import Path

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
