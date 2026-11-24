"""Pytest test configuration and synthetic fixtures for DENTRACE.

Enforces:
1. Pure synthetic fixtures — ZERO real patient images.
2. Temporary database and storage isolation for tests.
3. TestClient fixture with lifespan execution.
"""

import io
import shutil
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient

# Ensure legacy archived frontend modules remain discoverable for legacy integration test suites
LEGACY_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "archive" / "legacy_streamlit_frontend"
if LEGACY_FRONTEND_DIR.exists() and str(LEGACY_FRONTEND_DIR.parent) not in sys.path:
  sys.path.insert(0, str(LEGACY_FRONTEND_DIR.parent))

from backend.config import settings
from backend.database.connection import get_connection
from backend.database.migrations import run_migrations
from backend.main import app
from backend.storage.file_manager import storage_manager


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
  """Configure isolated temporary data directories for tests."""
  temp_dir = tmp_path_factory.mktemp("dentrace_test_env")
  test_storage = temp_dir / "storage"
  test_previews = temp_dir / "previews"
  test_db = temp_dir / "test_dentrace.db"

  test_storage.mkdir(parents=True, exist_ok=True)
  test_previews.mkdir(parents=True, exist_ok=True)

  # Override settings
  orig_storage = settings.STORAGE_DIR
  orig_preview = settings.PREVIEW_DIR
  orig_db = settings.SQLITE_DB_PATH
  orig_data = settings.DATA_DIR

  settings.DATA_DIR = temp_dir
  settings.STORAGE_DIR = test_storage
  settings.PREVIEW_DIR = test_previews
  settings.SQLITE_DB_PATH = test_db
  storage_manager.storage_dir = test_storage
  storage_manager.preview_dir = test_previews

  # Run migrations on test DB
  with get_connection(test_db) as conn:
    run_migrations(conn)

  yield

  # Teardown
  settings.DATA_DIR = orig_data
  settings.STORAGE_DIR = orig_storage
  settings.PREVIEW_DIR = orig_preview
  settings.SQLITE_DB_PATH = orig_db
  storage_manager.storage_dir = orig_storage
  storage_manager.preview_dir = orig_preview


@pytest.fixture
def client():
  """FastAPI test client."""
  with TestClient(app) as test_client:
    yield test_client


@pytest.fixture
def synthetic_opg_png() -> bytes:
  """Generate a synthetic panoramic radiograph raster (1000x500 grayscale PNG)."""
  arr = np.zeros((500, 1000), dtype=np.uint8)
  # Simulate dental arch curve
  for x in range(1000):
    arch_y = int(250 + 80 * np.sin((x / 1000.0) * np.pi))
    arr[max(0, arch_y - 20) : min(500, arch_y + 20), x] = 180
  img = Image.fromarray(arr, mode="L")
  buf = io.BytesIO()
  img.save(buf, format="PNG")
  return buf.getvalue()


@pytest.fixture
def synthetic_opg_jpeg() -> bytes:
  """Generate a synthetic panoramic radiograph raster (1000x500 JPEG)."""
  arr = np.full((500, 1000, 3), 120, dtype=np.uint8)
  # Draw synthetic jaw outline
  arr[200:300, 100:900] = 200
  img = Image.fromarray(arr, mode="RGB")
  buf = io.BytesIO()
  img.save(buf, format="JPEG", quality=90)
  return buf.getvalue()


@pytest.fixture
def synthetic_corrupt_png() -> bytes:
  """Generate invalid corrupted PNG bytes (valid magic bytes, garbage payload)."""
  return b"\x89PNG\r\n\x1a\n" + b"\x00" * 200 + b"GARBAGE_PAYLOAD_CORRUPT"


@pytest.fixture
def synthetic_dicom_bytes() -> bytes:
  """Generate a synthetic valid uncompressed DICOM radiograph."""
  import pydicom
  from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
  from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage

  file_meta = FileMetaDataset()
  file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
  file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
  file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

  ds = FileDataset("test.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
  ds.PatientName = "TEST^PATIENT"
  ds.PatientID = "ANON-001"
  ds.PhotometricInterpretation = "MONOCHROME2"
  ds.Rows = 500
  ds.Columns = 1000
  ds.BitsAllocated = 8
  ds.BitsStored = 8
  ds.HighBit = 7
  ds.PixelRepresentation = 0
  ds.SamplesPerPixel = 1

  # Synthetic pixel data (500x1000 = 500,000 bytes)
  pixel_arr = np.full((500, 1000), 100, dtype=np.uint8)
  ds.PixelData = pixel_arr.tobytes()

  buf = io.BytesIO()
  ds.save_as(buf, write_like_original=False)
  return buf.getvalue()


@pytest.fixture
def synthetic_unsupported_compressed_dicom() -> bytes:
  """Generate a synthetic DICOM with an unsupported/corrupted compressed transfer syntax (e.g. JPEG 2000)."""
  import pydicom
  from pydicom.dataset import FileDataset, FileMetaDataset
  from pydicom.encaps import encapsulate
  from pydicom.uid import JPEG2000Lossless, SecondaryCaptureImageStorage

  file_meta = FileMetaDataset()
  file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
  file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
  file_meta.TransferSyntaxUID = JPEG2000Lossless

  ds = FileDataset("test_compressed.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
  ds.is_little_endian = True
  ds.is_implicit_VR = False
  ds.Rows = 500
  ds.Columns = 1000
  ds.BitsAllocated = 8
  ds.BitsStored = 8
  ds.HighBit = 7
  ds.PixelRepresentation = 0
  ds.SamplesPerPixel = 1
  ds.PhotometricInterpretation = "MONOCHROME2"
  ds.PixelData = encapsulate([b"\xff\x4f\xff\x51" + b"\x00" * 100])

  buf = io.BytesIO()
  ds.save_as(buf, write_like_original=False)
  return buf.getvalue()


@pytest.fixture
def synthetic_test_study(synthetic_opg_png: bytes) -> str:
  """Create a temporary study in the test DB and yield its study_id."""
  from backend.services.study_service import study_service
  study = study_service.create_study(
      raw_bytes=synthetic_opg_png,
      original_filename="synthetic_fixture.png",
      patient_anonymous_id="PT-SYNTH-99",
      clinical_indication="Automated test fixture",
  )
  yield study.study_id
  try:
    study_service.delete_study(study.study_id)
  except Exception:
    pass

