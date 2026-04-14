import os
import sys

# Add App/backend to sys.path to resolve core and schemas imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "App", "backend"))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
