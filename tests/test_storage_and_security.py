"""Test suite verifying image intake, DICOM handling, path traversal defense, and security screening."""

import pytest
from backend.storage.file_manager import storage_manager, sanitize_filename, detect_mime_type


def test_sanitize_filename_strips_traversal():
  """Test filename sanitization against path traversal attempts."""
  assert sanitize_filename("../../etc/passwd.png") == "passwd.png"
  assert sanitize_filename("..\\..\\windows\\system32.jpg") == "system32.jpg"
  assert sanitize_filename(".hidden_image.png") == "file.hidden_image.png"
  assert sanitize_filename("safe_radiograph_123.png") == "safe_radiograph_123.png"


def test_save_valid_png(synthetic_opg_png):
  """Test saving a valid synthetic panoramic PNG radiograph."""
  metadata, quality = storage_manager.save_upload(
      study_id="TEST-PNG-01",
      raw_bytes=synthetic_opg_png,
      original_filename="opg_valid.png",
  )

  assert metadata.mime_type == "image/png"
  assert metadata.width_px == 1000
  assert metadata.height_px == 500
  assert metadata.aspect_ratio == 2.0
  assert quality.aspect_ratio_valid is True
  assert quality.resolution_valid is True
  assert quality.passed is True


def test_save_valid_jpeg(synthetic_opg_jpeg):
  """Test saving a valid synthetic panoramic JPEG radiograph."""
  metadata, quality = storage_manager.save_upload(
      study_id="TEST-JPG-01",
      raw_bytes=synthetic_opg_jpeg,
      original_filename="opg_valid.jpg",
  )

  assert metadata.mime_type == "image/jpeg"
  assert metadata.width_px == 1000
  assert metadata.height_px == 500
  assert quality.passed is True


def test_reject_corrupt_image(synthetic_corrupt_png):
  """Test rejection of corrupted image payload."""
  with pytest.raises(ValueError, match="Corrupted or invalid image data"):
    storage_manager.save_upload(
        study_id="TEST-CORRUPT",
        raw_bytes=synthetic_corrupt_png,
        original_filename="corrupt.png",
    )


def test_reject_empty_or_tiny_file():
  """Test rejection of empty or sub-100-byte file."""
  with pytest.raises(ValueError, match="under 100 bytes"):
    storage_manager.save_upload(
        study_id="TEST-EMPTY",
        raw_bytes=b"too short",
        original_filename="tiny.png",
    )


def test_reject_unsupported_file_type():
  """Test rejection of non-image file type."""
  with pytest.raises(ValueError, match="Unsupported or unrecognized"):
    storage_manager.save_upload(
        study_id="TEST-TXT",
        raw_bytes=b"This is a text file not an image" * 10,
        original_filename="notes.txt",
    )


def test_reject_oversized_file():
  """Test rejection of payload exceeding MAX_UPLOAD_SIZE_BYTES."""
  oversized_payload = b"\x00" * (51 * 1024 * 1024)  # 51 MB
  with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
    storage_manager.save_upload(
        study_id="TEST-OVERSIZED",
        raw_bytes=oversized_payload,
        original_filename="large.png",
    )


def test_reject_path_traversal():
  """Test rejection of filenames containing path traversal tokens."""
  with pytest.raises(ValueError, match="Path traversal detected"):
    storage_manager.save_upload(
        study_id="TEST-TRAVERSAL",
        raw_bytes=b"safe bytes" * 20,
        original_filename="../../etc/passwd.png",
    )


def test_dicom_ingestion_and_sanitization(synthetic_dicom_bytes):
  """Test valid DICOM ingestion, pixel extraction, and metadata sanitization."""
  metadata, quality = storage_manager.save_upload(
      study_id="TEST-DCM-01",
      raw_bytes=synthetic_dicom_bytes,
      original_filename="radiograph.dcm",
  )

  assert metadata.is_dicom is True
  assert metadata.metadata_sanitized is True
  assert metadata.width_px == 1000
  assert metadata.height_px == 500

  # Verify preview was generated as PNG without DICOM headers
  preview_path = storage_manager.get_preview_path(metadata.preview_rel_path)
  assert preview_path is not None
  assert preview_path.exists()
  assert preview_path.suffix == ".png"


def test_reject_unsupported_compressed_dicom(synthetic_unsupported_compressed_dicom):
  """Test that unsupported compressed DICOM transfer syntaxes fail with a clear error."""
  with pytest.raises(ValueError, match="(Unsupported compressed DICOM|Corrupted or unreadable)"):
    storage_manager.save_upload(
        study_id="TEST-DCM-COMPRESSED",
        raw_bytes=synthetic_unsupported_compressed_dicom,
        original_filename="compressed.dcm",
    )
