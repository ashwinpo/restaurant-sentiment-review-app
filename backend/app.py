import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routes import api_router
from dotenv import load_dotenv

load_dotenv()


app = FastAPI(
    title="Bloomin Brands Review App",
    description="A review validation application for LLM-generated sentiment analysis",
    version="1.0.0",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug endpoint to check frontend build status (before mounting static files)
build_dir = Path(__file__).parent.parent / "frontend" / "dist"

@app.get("/api/debug/frontend")
async def debug_frontend():
    """Debug endpoint to check frontend build status"""
    build_exists = build_dir.exists()
    assets = []
    if build_exists:
        try:
            assets = [str(f.relative_to(build_dir)) for f in build_dir.rglob("*") if f.is_file()]
        except Exception as e:
            assets = [f"Error listing files: {str(e)}"]
    
    return {
        "build_dir": str(build_dir),
        "build_dir_exists": build_exists,
        "assets": assets[:20]  # Limit to first 20 files
    }

# Include API router
app.include_router(api_router)

# Mount static files (frontend dist) - this should come AFTER API routes
if build_dir.exists():
    app.mount("/", StaticFiles(directory=build_dir, html=True), name="static")
else:
    import logging
    logging.warning("Frontend build not found: %s", build_dir)

@app.get("/")
async def root():
    """Root endpoint - will be overridden by static files when frontend is built"""
    return {
        "app": "Bloomin Brands Review App",
        "message": "Backend is running! Frontend build not found.",
        "docs": "/docs"
    }
