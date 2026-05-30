import os
import sys

# Get the absolute paths of the root directory and the backend service directory
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "App", "backend")

# Ensure uvicorn runs can resolve both root-level modules and backend-specific imports
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import the FastAPI application from App.backend.main
from App.backend.main import app

if __name__ == "__main__":
    import uvicorn
    # Bind to the PORT environment variable injected dynamically by Render/Vercel
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
