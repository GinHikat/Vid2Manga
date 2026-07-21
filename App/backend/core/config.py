import os

class Settings:
    """Application settings and basic path configurations."""
    PROJECT_NAME: str = "Vid2Manga Backend"
    PROJECT_VERSION: str = "1.0.0"

    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ROOT_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    DATA_DIR: str = os.path.join(ROOT_DIR, "data")
    INPUT_DIR: str = os.path.join(DATA_DIR, "input")
    OUTPUT_DIR: str = os.path.join(DATA_DIR, "output")

    CORS_ORIGINS: list = ["*"]

settings = Settings()

# Ensure required directories exist
for directory in [settings.DATA_DIR, settings.INPUT_DIR, settings.OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

