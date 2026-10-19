"""Test suite verifying Python environment integrity and required dependencies."""

import sys
import pytest


def test_python_version_is_3_11():
  """Enforce Python 3.11 runtime environment."""
  major, minor = sys.version_info.major, sys.version_info.minor
  assert major == 3, f"Expected Python major version 3, got {major}"
  assert minor == 11, f"Expected Python minor version 11, got {minor}"


def test_core_dependencies_importable():
  """Verify all mandatory Level 1 dependencies can be imported successfully."""
  import fastapi
  import uvicorn
  import pydantic
  import sqlalchemy
  import alembic
  import pydicom
  import PIL
  import numpy
  import pytest
  import httpx
  import onnxruntime

  assert fastapi.__version__ is not None
  assert uvicorn.__version__ is not None
  assert pydantic.__version__ is not None
  assert sqlalchemy.__version__ is not None
  assert alembic.__version__ is not None
  assert pydicom.__version__ is not None
  assert PIL.__version__ is not None
  assert numpy.__version__ is not None
  assert pytest.__version__ is not None
  assert httpx.__version__ is not None
  assert onnxruntime.__version__ is not None


def test_settings_localhost_binding():
  """Enforce strict localhost binding and security defaults."""
  from backend.config import settings

  assert settings.HOST == "127.0.0.1"
  assert settings.MANDATORY_DISCLAIMER == "Draft for dentist review. Not a diagnosis."
  assert "C:" in str(settings.PROJECT_ROOT)
