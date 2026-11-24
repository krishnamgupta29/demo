# DENTRACE — Level 2 Test Report & QA Attestation

> **DOCUMENT ID:** DOC-LVL2-TEST-004  
> **STAGE:** LEVEL 2 (COMPLETED)  
> **EXECUTION DATE:** 2026-10-19  
> **RESULT:** 50 / 50 TESTS PASSED (100% PASS RATE)  

---

## 1. Test Execution Summary

The complete automated test suite was executed in the official Python 3.11.9 virtual environment (`C:\mini\.venv`) using `pytest 9.1.1`.

| Metric | Result |
|---|---|
| **Total Test Items Collected** | 50 |
| **Total Tests Passed** | **50 (100.0%)** |
| **Total Tests Failed** | **0 (0.0%)** |
| **Total Tests Skipped** | 0 |
| **Execution Duration** | 28.88 seconds |
| **Platform** | Windows 11 x64, Python 3.11.9 |
| **Database State** | SQLite 3 (`data/dentrace.db`) via programmatic Alembic head migrations |

---

## 2. Granular Module Breakdown

| Test Suite Module | Target Component / Layer | Items | Passed | Failed | Status |
|---|---|---|---|---|---|
| `tests/test_api_studies.py` | FastAPI Ingest, Retrieval, Previews & REST Aliases | 9 | 9 | 0 | **PASSED** |
| `tests/test_database.py` | Alembic Migrations & Full SQLAlchemy 2.0 ORM Lifecycle | 2 | 2 | 0 | **PASSED** |
| `tests/test_dataset_integrity.py` | DENTEX Polygons, Tooth Enumeration & Split Isolation | 4 | 4 | 0 | **PASSED** |
| `tests/test_environment.py` | Python 3.11 Runtime, Core Dependencies & Localhost Settings | 3 | 3 | 0 | **PASSED** |
| `tests/test_model_registry.py` | Model Registry, Truthful Availability & Zero Fake Predictions | 6 | 6 | 0 | **PASSED** |
| `tests/test_storage_and_security.py` | Path Traversal Defense, Sanitization, Magic Bytes & DICOM | 10 | 10 | 0 | **PASSED** |
| `tests/test_model_inference.py` | **ONNX Runtime, Pre/Postprocessing, FDI Engine & API Analysis** | **16** | **16** | **0** | **PASSED** |
| **TOTAL** | **Full System Integration Test Suite** | **50** | **50** | **0** | **100% PASS** |

---

## 3. Specific Level 2 Test Validations

The 16 newly implemented Level 2 tests in `tests/test_model_inference.py` verify the following critical contracts:

1. `test_real_model_initialization`: Verifies physical `best.onnx` presence, SHA-256 hash match (`4cee38b54...`), and clean CPU provider initialization.
2. `test_onnx_session_execution`: Verifies forward pass execution on synthetic radiograph returning valid output tensors.
3. `test_input_preprocessing_letterbox`: Confirms aspect-ratio preservation, bilinear scaling, padding placement, and normalization to $[0.0, 1.0]$.
4. `test_output_decoding_and_nms`: Validates raw tensor parsing and class-aware NMS suppression of duplicate detections.
5. `test_coordinate_scaling_roundtrip`: Verifies unletterboxed coordinates map strictly within original image boundaries without out-of-bounds leakage.
6. `test_class_mapping`: Validates mapping of candidate string labels to authoritative `PathologyClass` enums.
7. `test_fdi_mapping_and_ambiguity`: Validates `FDINumberingEngine` returns proposals with correct patient orientation and `uncertain_tooth` flags without forced integer assignment.
8. `test_missing_checkpoint_handling`: Ensures uninstalled models return `MODEL_UNAVAILABLE` cleanly without crashes.
9. `test_corrupted_checkpoint_handling`: Confirms corrupted model weights are safely caught before session execution.
10. `test_invalid_image_handling`: Confirms preprocessor rejects 0x0 or corrupted inputs with informative domain errors.
11. `test_api_analysis_endpoint_real_model`: Validates `POST /api/v1/studies/{study_id}/analyze` executes real inference, persists findings, and includes required disclaimers.
12. `test_api_analysis_endpoint_unavailable_model`: Validates requesting an uninstalled model returns `model_unavailable` without 500 error.
13. `test_prediction_persistence`: Confirms analyzed findings and study status update to `analyzed` are persisted in SQLite and retrievable.
14. `test_repeated_inference_consistency`: Validates deterministic output across repeated runs on identical images.
15. `test_dataset_split_isolation`: Proves mathematical disjointness between train and dev evaluation splits (`train & eval == empty`).
16. `test_inference_latency_measurement`: Validates latency measurement reporting positive float under 1500 ms.

---

## 4. Exact Command to Reproduce

```powershell
C:\mini\.venv\Scripts\python.exe -m pytest tests -v
```
