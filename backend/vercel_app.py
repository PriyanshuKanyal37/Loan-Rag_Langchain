"""
Vercel-optimized entry point for FastAPI app.
Lazy-loads heavy dependencies to work within serverless constraints.
"""
import os
os.environ.setdefault("ENVIRONMENT", "production")

# Import the FastAPI app
from main import app

# Vercel requires the app to be named 'app' at module level
__all__ = ["app"]
