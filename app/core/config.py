
import os
from pydantic_settings import BaseSettings
from pydantic import EmailStr # Keep for potential future use
from functools import lru_cache
from pathlib import Path

# Define the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent # This should point to yt_auto_vid_suite root

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    PROJECT_NAME: str = "YT AutoVid Suite"
    VERSION: str = "0.1.0"

    # Security
    SECRET_KEY: str

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = BASE_DIR / "logs"

    # Database
    DATABASE_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # API Keys (loaded but potentially validated later)
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    PEXELS_API_KEY: str | None = None

    # Directories for media handling (create if they don't exist)
    DOWNLOAD_DIR: Path = BASE_DIR / "downloads"
    RENDER_DIR: Path = BASE_DIR / "renders"
    MUSIC_LIBRARY_DIR: Path = BASE_DIR / "music_library" # Where user adds music

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = 'utf-8'
        # Make Pydantic case-insensitive for env vars if needed
        # case_sensitive = False

@lru_cache() # Cache the settings object
def get_settings() -> Settings:
    """Returns the settings instance, loading from .env file."""
    settings = Settings()

    # Ensure necessary directories exist
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    settings.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.RENDER_DIR.mkdir(parents=True, exist_ok=True)
    settings.MUSIC_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

    return settings

# Make settings easily accessible
settings = get_settings()
