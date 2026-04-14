import os

class Settings:
    """Application settings and basic path configurations."""
    PROJECT_NAME: str = "Vid2Manga Backend"
    PROJECT_VERSION: str = "1.0.0"

    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    INPUT_DIR: str = os.path.join(BASE_DIR, "input")
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "output")

    CORS_ORIGINS: list = ["*"]

settings = Settings()

# Ensure required directories exist
for directory in [settings.INPUT_DIR, settings.OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)
