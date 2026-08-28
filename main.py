"""
Helix Finance AI — Application Entry Point
==========================================
Run locally:
    uvicorn apps.main:app --reload --host 0.0.0.0 --port 8000

Or via this script:
    python main.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "apps.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
