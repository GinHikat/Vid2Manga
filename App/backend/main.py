from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.config import settings
from api.v1.api import router as api_router
import uvicorn
import sys
import os

if settings.BASE_DIR not in sys.path:
    sys.path.append(settings.BASE_DIR)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the output directory to serve files (StaticFiles)
app.mount("/output", StaticFiles(directory=settings.OUTPUT_DIR), name="output")

# Include the router
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)