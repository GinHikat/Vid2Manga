import os

class Settings:
    PROJECT_NAME: str = "Vid2Manga Backend"
    PROJECT_VERSION: str = "1.0.0"

    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    INPUT_DIR: str = os.path.join(BASE_DIR, "input")
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "output")

    CORS_ORIGINS: list = ["*"]

settings = Settings()

os.makedirs(settings.INPUT_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
