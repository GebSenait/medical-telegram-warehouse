"""
Simple script to run the FastAPI server
Task-4: Convenience script for starting the API

Usage:
    python run_api.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info",
    )
