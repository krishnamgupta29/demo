"""Configuration management for DENTRACE Clinical Decision Support Engine.

Enforces:
1. Strict localhost binding (127.0.0.1) for zero external cloud leakage.
2. Storage routing to C: drive exclusively.
3. Immutable clinical regulatory notice injection.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_data_dir() -> Path:
  """Resolve user-writable application data directory for DENTRACE.

  Precedence:
  1. DENTRACE_DATA_DIR environment variable
  2. If DENTRACE_DEV_MODE == "1" (default) and (PROJECT_ROOT / "data") exists: use project data dir
  3. %LOCALAPPDATA%/DENTRACE/data
  4. Fallback to PROJECT_ROOT / "data"
  """
  if "DENTRACE_DATA_DIR" in os.environ:
    return Path(os.environ["DENTRACE_DATA_DIR"])
  
  detected_root = Path(__file__).resolve().parents[1]
  if os.environ.get("DENTRACE_DEV_MODE", "1") == "1" and (detected_root / "data").exists():
    return detected_root / "data"
  local_app_data = os.environ.get("LOCALAPPDATA")
  if local_app_data:
    return Path(local_app_data) / "DENTRACE" / "data"
  return detected_root / "data"


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

  # Storage Constraints (User-writable directory, strictly on C: drive)
  PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
  DATA_DIR: Path = Field(default_factory=get_default_data_dir)
  STORAGE_DIR: Path = Field(default_factory=lambda: get_default_data_dir() / "storage")
  PREVIEW_DIR: Path = Field(default_factory=lambda: get_default_data_dir() / "previews")
  SQLITE_DB_PATH: Path = Field(default_factory=lambda: get_default_data_dir() / "dentrace.db")

  # Local Access Control (Level 9 Single-User Token)
  LOCAL_API_KEY: Optional[str] = Field(
      default_factory=lambda: os.environ.get("DENTRACE_API_KEY") or os.environ.get("DENTRACE_LOCAL_TOKEN"),
      description="Ephemeral local single-user access token. If set, required on clinical endpoints.",
  )

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
