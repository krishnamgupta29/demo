"""Configuration management for DENTRACE Clinical Decision Support Engine.

Enforces:
1. Strict localhost binding (127.0.0.1) for zero external cloud leakage.
2. Storage routing to C: drive exclusively.
3. Immutable clinical regulatory notice injection.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  """Application settings with environment variable override support."""

  model_config = SettingsConfigDict(
      env_file=".env",
      env_file_encoding="utf-8",
      extra="ignore",
  )

  # Application Identity
  APP_NAME: str = "DENTRACE Clinical Decision Support Engine"
  APP_VERSION: str = "0.1.0"
  ENVIRONMENT: str = "development"
  DEBUG: bool = False

  # Network & Binding Constraints (Zero Cloud Egress)
  HOST: str = "127.0.0.1"
  PORT: int = 8000

  # Storage Constraints (Strictly on C: drive)
  PROJECT_ROOT: Path = Path("C:/mini")
  DATA_DIR: Path = Path("C:/mini/data")
  STORAGE_DIR: Path = Path("C:/mini/data/storage")
  PREVIEW_DIR: Path = Path("C:/mini/data/previews")
  SQLITE_DB_PATH: Path = Path("C:/mini/data/dentrace.db")

  # Upload Constraints
  MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
  ALLOWED_EXTENSIONS: set[str] = {
      ".png",
      ".jpg",
      ".jpeg",
      ".bmp",
      ".tiff",
      ".tif",
      ".dcm",
  }
  ALLOWED_MIME_TYPES: set[str] = {
      "image/png",
      "image/jpeg",
      "image/bmp",
      "image/tiff",
      "application/dicom",
      "application/octet-stream",  # Fallback for DICOM
  }

  # Image Quality Constraints
  MIN_OPG_WIDTH: int = 900
  MIN_OPG_HEIGHT: int = 450
  MIN_OPG_ASPECT_RATIO: float = 1.35
  MAX_OPG_ASPECT_RATIO: float = 3.20

  # Mandatory Regulatory Disclaimer
  MANDATORY_DISCLAIMER: str = "Draft for dentist review. Not a diagnosis."


# Singleton instance
settings = Settings()

# Ensure required local directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
