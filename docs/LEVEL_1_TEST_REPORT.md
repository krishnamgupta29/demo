# DENTRACE — Level 1 Verification & Test Execution Report

> **DOCUMENT ID:** DOC-TEST-013  
> **STATUS:** LEVEL 1 QA PASSED (100% PASS RATE)  
> **DATE:** 2026-10-19  
> **WORKSPACE:** `C:\mini` (Drive C:)  
> **ENVIRONMENT:** Windows 11 x64 | Python 3.11.9 (`C:\mini\.venv`) | SQLite 3.45.3  

---

## 1. Executive Summary

Level 1 establishes the core foundation and data integration layer for DENTRACE. All objectives specified in the Level 1 problem statement have been implemented, forensic audited, and verified via automated test suites:

- **Environment & Runtime:** Dedicated virtual environment at `C:\mini\.venv` (Python 3.11.9) with reproducible pinned dependencies.
- **DENTEX Dataset Extraction:** Safely extracted 3,606 files from `training_data.zip` (13.71 GB) and 51 files from `validation_data.zip` (0.19 GB) to `C:\mini\datasets\dentex\raw\`. Forensic inspection confirmed 100% polygon coverage (3,529 disease polygons, 18,095 tooth contour polygons; average 12 vertices/polygon). Held-out validation split kept isolated.
- **FastAPI Backend Core:** Fully functional REST backend under `/api/v1` bound strictly to `127.0.0.1:8000` with privacy-safe request logging, structured error envelopes, and zero external telemetry.
- **Database & Persistence:** SQLite with WAL mode, foreign key cascade deletions, SQLAlchemy 2.0 ORM models, and dual migration management (Alembic + runtime migration manager).
- **Secure Image Intake & DICOM:** Magic byte inspection, corruption rejection, path traversal defense, oversized payload rejection, DICOM transfer syntax validation, patient PHI sanitization, and web preview raster generation.
- **Model Registry Foundation:** Standardized adapter and registry interface for 4 dental AI candidates. Uninstalled checkpoints truthfully report `MODEL_UNAVAILABLE`; zero fabricated predictions or confidence scores.
- **Automated Tests:** 33 automated unit and integration tests executed using synthetic fixtures. **33 passed, 0 failed (100% pass rate).**

---

## 2. Dataset Extraction & Forensic Manifest Audit

### Extraction Summary
- **Source Archives:** `C:\mini\training_data.zip` (10.18 GB) and `C:\mini\validation_data.zip` (142.59 MB)
- **Destination:** `C:\mini\datasets\dentex\raw/` (Excluded from git via `.gitignore`)
- **Extraction Protection:** Zip-Slip path traversal defense, symlink rejection, byte-size integrity checks, resumable extraction.

| Split / Archive | Total Archive Members | Extracted Files | Skipped Directories | Extracted Bytes | Extracted GB | Status |
|---|---|---|---|---|---|---|
| `validation_data.zip` | 55 | 51 | 4 | 201,044,945 | 0.19 GB | **VERIFIED & ISOLATED** |
| `training_data.zip` | 3,615 | 3,606 | 9 | 14,725,611,903 | 13.71 GB | **VERIFIED & PARSED** |

### Annotation Hierarchy & Polygon Geometry
Forensic inspection of the extracted COCO-style JSON annotation files confirmed:

1. **`quadrant/train_quadrant.json`**:
   - 693 images | 2,772 annotations | 0 orphan annotations
   - 2,772 / 2,772 bounding boxes & polygon segmentations (100%)
   - Class distribution: `cat_0`: 693, `cat_1`: 693, `cat_2`: 693, `cat_3`: 693

2. **`quadrant_enumeration/train_quadrant_enumeration.json`**:
   - 634 images | 18,095 annotations | 0 orphan annotations
   - 18,095 / 18,095 polygon instance segmentations (100%)
   - Vertex statistics: min = 3, max = 63, avg = 11.6 vertices/polygon
   - Class distribution: teeth 1 to 8 across all 4 quadrants (1,504 to 2,508 per tooth class)

3. **`quadrant-enumeration-disease/train_quadrant_enumeration_disease.json`**:
   - 705 images | 3,529 annotations | 0 orphan annotations
   - 3,529 / 3,529 bounding boxes & polygon segmentations (100%)
   - Vertex statistics: min = 4, max = 34, avg = 12.0 vertices/polygon
   - Class distribution:
     - `disease_0` (Impacted Tooth): 604 annotations
     - `disease_1` (Caries): 2,189 annotations
     - `disease_2` (Periapical Lesion): 158 annotations
     - `disease_3` (Deep Caries): 578 annotations

---

## 3. Database Schema & Persistence Audit

Dual migration support was implemented and verified:
1. **Alembic Revisions:** Initial schema generated at `alembic/versions/ec4d280c3836_initial_schema.py` and upgraded to head.
2. **Runtime SQLite Migration Manager:** Self-healing migrations executed on application lifespan startup.

### Relational Tables
| Table | Description | Primary Key | Foreign Keys & Cascades |
|---|---|---|---|
| `studies` | Core study record and patient metadata | `study_id` (VARCHAR 64) | None |
| `radiographs` | Original image metadata, hashes, quality metrics | `study_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE |
| `teeth` | Tooth localizations with FDI numbering (11–48) | `tooth_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE |
| `findings` | Pathologies with geometries, model attribution, review status | `finding_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE |
| `model_runs` | Model execution provenance and performance tracking | `run_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE |
| `confirmations` | Clinician review decisions and signature attestations | `confirmation_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE (UNIQUE) |
| `insurance_drafts` | Pre-auth narrative drafts and CDT code sets | `draft_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE (UNIQUE) |
| `audit_events` | Append-only ledger of all intake and clinical events | `event_id` (VARCHAR 64) | `studies.study_id` ON DELETE CASCADE |
| `schema_migrations`| Migration tracking table | `version` (INTEGER) | None |

---

## 4. FastAPI Backend Endpoint Inventory

All endpoints operate under `/api/v1` and are bound strictly to `127.0.0.1:8000`:

| Method | Endpoint | Description | Status Code | Error Codes |
|---|---|---|---|---|
| `GET` | `/api/v1/health` (also `/health`) | Liveness probe with mandatory disclaimer | `200 OK` | — |
| `GET` | `/api/v1/readiness` (also `/readiness`) | Evaluates DB connectivity, storage writeability, free disk space | `200 OK` | `503 Service Unavailable` |
| `POST` | `/api/v1/studies` (also `/studies/upload`) | Ingests radiograph bytes, sanitizes, assesses quality, records study | `201 Created` | `400 Bad Request`, `413 Payload Too Large`, `422 Unprocessable` |
| `GET` | `/api/v1/studies` | Paginated listing of ingested studies | `200 OK` | — |
| `GET` | `/api/v1/studies/{study_id}` | Retrieves full study detail with findings, teeth, and review | `200 OK` | `404 Not Found` |
| `GET` | `/api/v1/studies/{study_id}/preview` | Returns web preview raster (`image/png`) | `200 OK` | `404 Not Found` |
| `DELETE`| `/api/v1/studies/{study_id}` | Soft-archives or hard-deletes study and associated disk files | `204 No Content` | `404 Not Found` |
| `GET` | `/api/v1/models` | Lists all candidate models with truthful availability status | `200 OK` | — |
| `GET` | `/api/v1/models/{model_id}/status` | Retrieves specific model provenance and SHA-256 hash | `200 OK` | `404 Not Found` |

---

## 5. Pretrained Model Registry & Benchmarking

The model registry tracks 4 candidate dental AI models:

| Model Identifier | Architecture | Task Domain | Checked Path | Registry Status |
|---|---|---|---|---|
| `abychkov-fdi-detection` | Transformer Object Detector | FDI Tooth Localization (11–48) | `models/checkpoints/dental_fdi_detection.onnx` | `MODEL_UNAVAILABLE` |
| `liodon-panoramic-screener` | YOLO11n (Ultralytics Nano) | Pathology Anomaly Screener | `models/checkpoints/best.onnx` | `MODEL_UNAVAILABLE` |
| `nsitnov-dental-segmentation` | YOLOv8-seg | Instance Segmentation | `models/checkpoints/8024_seg.onnx` | `MODEL_UNAVAILABLE` |
| `boneloss-pan769-baseline` | ResNet50 / U-Net | Alveolar Crest Line Detector | `models/checkpoints/boneloss_pan769.onnx` | `MODEL_UNAVAILABLE` |

- **Strict Non-Fabrication:** Uninstalled models return `status="MODEL_UNAVAILABLE"`, `outputs=None`, and an explanatory notice. Zero fake confidences or predictions are manufactured.
- **Local Benchmarking Suite:** `scripts/benchmark_models.py` truthfully reports model absence and records results in `docs/model_benchmark_results.json`.

---

## 6. Automated Test Results (33 Passed / 0 Failed)

The automated test suite was executed using `.venv\Scripts\pytest.exe -v` across 6 test modules:

```
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0 -- C:\mini\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\mini
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, asyncio-1.4.0
collecting ... collected 33 items

tests/test_api_studies.py::test_health_endpoints PASSED                  [  3%]
tests/test_api_studies.py::test_readiness_endpoints PASSED               [  6%]
tests/test_api_studies.py::test_create_study_png PASSED                  [  9%]
tests/test_api_studies.py::test_create_study_rest_alias PASSED           [ 12%]
tests/test_api_studies.py::test_list_studies_pagination PASSED           [ 15%]
tests/test_api_studies.py::test_study_not_found PASSED                   [ 18%]
tests/test_api_studies.py::test_delete_study_hard PASSED                 [ 21%]
tests/test_api_studies.py::test_reject_unsupported_file_extension PASSED [ 24%]
tests/test_api_studies.py::test_reject_corrupt_upload_via_api PASSED     [ 27%]
tests/test_database.py::test_migrations_execute_cleanly PASSED           [ 30%]
tests/test_database.py::test_sqlalchemy_orm_full_lifecycle PASSED        [ 33%]
tests/test_dataset_integrity.py::test_dataset_inventory_exists_and_valid PASSED [ 36%]
tests/test_dataset_integrity.py::test_dentex_annotation_polygon_geometry_truthfulness PASSED [ 39%]
tests/test_dataset_integrity.py::test_tooth_enumeration_polygon_geometry PASSED [ 42%]
tests/test_dataset_integrity.py::test_validation_set_isolation PASSED    [ 45%]
tests/test_environment.py::test_python_version_is_3_11 PASSED            [ 48%]
tests/test_environment.py::test_core_dependencies_importable PASSED      [ 51%]
tests/test_environment.py::test_settings_localhost_binding PASSED        [ 54%]
tests/test_model_registry.py::test_model_registry_registered_candidates PASSED [ 57%]
tests/test_model_registry.py::test_uninstalled_models_report_model_unavailable PASSED [ 60%]
tests/test_model_registry.py::test_zero_fake_predictions PASSED          [ 63%]
tests/test_model_registry.py::test_model_endpoint_api PASSED             [ 66%]
tests/test_model_registry.py::test_specific_model_status_api PASSED      [ 69%]
tests/test_storage_and_security.py::test_sanitize_filename_strips_traversal PASSED [ 72%]
tests/test_storage_and_security.py::test_save_valid_png PASSED           [ 75%]
tests/test_storage_and_security.py::test_save_valid_jpeg PASSED          [ 78%]
tests/test_storage_and_security.py::test_reject_corrupt_image PASSED     [ 81%]
tests/test_storage_and_security.py::test_reject_empty_or_tiny_file PASSED [ 84%]
tests/test_storage_and_security.py::test_reject_unsupported_file_type PASSED [ 87%]
tests/test_storage_and_security.py::test_reject_oversized_file PASSED    [ 90%]
tests/test_storage_and_security.py::test_reject_path_traversal PASSED    [ 93%]
tests/test_storage_and_security.py::test_dicom_ingestion_and_sanitization PASSED [ 96%]
tests/test_storage_and_security.py::test_reject_unsupported_compressed_dicom PASSED [100%]

======================== 33 passed, 1 warning in 7.36s ========================
```

---

## 7. Commands to Run & Verify the Application

All commands run strictly on Windows PowerShell from `C:\mini`:

```powershell
# 1. Environment Setup & Dependency Installation
.\scripts\setup_env.ps1

# 2. Run Automated QA Test Suite (33 tests)
.\scripts\run_tests.ps1

# 3. Run Pretrained Model Benchmark Suite (Truthful Availability)
& "C:\mini\.venv\Scripts\python.exe" C:\mini\scripts\benchmark_models.py

# 4. Launch FastAPI Backend Development Server (127.0.0.1:8000)
.\scripts\start_backend.ps1
```

---

## 8. Level 1 Conclusion

Level 1 is **100% COMPLETE**. All criteria have been satisfied without gaps, compromises, or mock fabrication. Development is now gated and awaiting explicit user authorization before starting Level 2.
