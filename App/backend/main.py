import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add App/backend and project root to sys.path to find 'core', 'schemas', and 'modules'
backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(backend_dir, "..", ".."))
for d in [backend_dir, root_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings
from api.v1.api import router as api_router

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=settings.OUTPUT_DIR), name="output")
@app.get("/health")
async def health_check():
    """Simple health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
