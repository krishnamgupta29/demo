# DENTRACE Level 8 — Test Report

> **DOCUMENT ID:** DOC-TST-008  
> **STATUS:** ALL TESTS PASSING (155/155)  
> **DATE:** 2026-10-22  
> **RUNTIME:** Python 3.11.9, pytest-9.1.1, FastAPI 0.146.0, ONNX Runtime 1.31.0, Pillow 13.0.0  

---

## 1. Executive Summary

Level 8 system hardening, security, privacy, and performance verification has been completed with **100% test pass rate**:
- **Total Tests Collected:** 155
- **Passed:** 155 (100%)
- **Failed:** 0
- **Errors:** 0
- **Execution Time:** 294.83 seconds (~4m 54s)

---

## 2. Test Breakdown by Domain & Module

| Test Module | Domain / Level | Tests | Status |
|---|---|---|---|
| `tests/test_api_studies.py` | Study ingestion, query & metadata API | 9 | ✅ PASS |
| `tests/test_database.py` | SQLite schema, foreign keys & connection pooling | 2 | ✅ PASS |
| `tests/test_dataset_integrity.py` | DENTEX / dataset manifest verification | 4 | ✅ PASS |
| `tests/test_environment.py` | Local host, Python 3.11 & disk budget checks | 3 | ✅ PASS |
| `tests/test_frontend_integration.py` | API client & Streamlit data contract | 13 | ✅ PASS |
| `tests/test_level_3_repair.py` | FDI assignment & polygon repair | 5 | ✅ PASS |
| `tests/test_level_4_clinical.py` | Clinical evidence engine & claim preflight | 16 | ✅ PASS |
| `tests/test_level_6_optimization.py` | Model benchmark, quantization & baseline | 14 | ✅ PASS |
| `tests/test_level_7_integration.py` | Full end-to-end integration & model selector | 13 | ✅ PASS |
| `tests/test_level_8_hardening.py` | Security, privacy, reliability & performance | 37 | ✅ PASS |
| `tests/test_model_inference.py` | ONNX runtime inference & bounding boxes | 16 | ✅ PASS |
| `tests/test_model_registry.py` | Provenance tracking & model metadata | 6 | ✅ PASS |
| `tests/test_segmentation_and_fdi.py` | Tooth segmentation & FDI resolution | 7 | ✅ PASS |
| `tests/test_storage_and_security.py` | Path traversal, sanitization & file management | 10 | ✅ PASS |
| **TOTAL** | | **155** | **✅ 100% PASS** |

---

## 3. Level 8 Hardening Test Suite Details (`test_level_8_hardening.py`)

### Security Suite (10/10 Passed)
- `SEC-01`: Security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: no-referrer`, `Content-Security-Policy`) present on all API responses.
- `SEC-02`: CORS origin list contains no wildcard (`*`), strictly restricted to localhost bindings.
- `SEC-03`: Path traversal tokens (`../`, `..\\`, absolute root prefixes) sanitized via `sanitize_filename()`.
- `SEC-04`: Oversized uploads exceeding 50 MB rejected at boundary with HTTP 413.
- `SEC-05`: Disallowed extensions (`.exe`, `.sh`, `.bat`) rejected at boundary with HTTP 400.
- `SEC-06`: SQL injection payloads in `study_id` path parameter handled safely via parameterized queries.
- `SEC-07`: Magic byte inspection verifies genuine image signatures (PNG, JPEG, BMP, TIFF, DICOM).
- `SEC-08`: Production model checkpoints verify SHA-256 integrity hashes against registry.
- `SEC-09`: Sensitive clinical endpoints include `Cache-Control: no-store, no-cache, must-revalidate`.
- `SEC-10`: Server socket binding strictly enforces `127.0.0.1` (never `0.0.0.0`).

### Privacy Suite (5/5 Passed)
- `PRI-01`: Internal exception stack traces stripped from audit event payloads.
- `PRI-02`: Preview raster filenames keyed by `study_id`, avoiding patient filename exposure.
- `PRI-03`: Zero temporary files leaked into system temp directories after radiograph upload.
- `PRI-04`: Hard delete cascades to radiograph storage files, preview rasters, and database records.
- `PRI-05`: Zero active file-based root log handlers capturing PHI to uncontrolled log files.

### Reliability Suite (9/9 Passed)
- `REL-01`: Corrupt image upload fails cleanly with database rollback and 0 partial records.
- `REL-02`: Duplicate identical uploads receive unique, distinct `study_id` values.
- `REL-03`: Clinician-confirmed findings are preserved across re-analysis runs.
- `REL-04`: Stale pending findings are purged during re-analysis (ensuring idempotency).
- `REL-05`: Requesting unavailable model returns structured error notification instead of crashing.
- `REL-06`: Database backup snapshots are verified valid and readable with complete table schemas.
- `REL-07`: Cascade deletion removes associated findings, radiographs, and audit records.
- `REL-08`: Analyzing non-existent `study_id` returns structured 404 error response.
- `REL-09`: Minimum-dimension images handled gracefully without runtime panic.

### Clinical Safety Suite (7/7 Passed)
- `CLS-01`: Unsupported model (`BoneLoss-PAN769`) explicitly returns `UNSUPPORTED_MISSING_LANDMARKS`.
- `CLS-02`: Endodontic findings generate hedged observational wording, never concluding "failure".
- `CLS-03`: Unresolved tooth coordinates maintain `None` FDI rather than guessing nearest tooth.
- `CLS-04`: Mandatory regulatory disclaimer injected into all error payloads.
- `CLS-05`: Claim preflight export blocked when mandatory teeth remain unconfirmed.
- `CLS-06`: Regulatory disclaimer verified in core system settings.
- `CLS-07`: Model availability states conform strictly to `ModelAvailabilityStatus` enum schema.

### Performance Suite (6/6 Passed)
- `PERF-01`: Health check endpoint latency < 500 ms (measured < 5 ms).
- `PERF-02`: Full study intake and validation < 2,000 ms (measured ~95 ms).
- `PERF-03`: Liodon screener ONNX inference verified (latency ~70 ms).
- `PERF-04`: DENTEX FP32 ONNX inference verified (latency ~103 ms).
- `PERF-05`: Claim pack PDF generation < 2,000 ms (measured ~90 ms).
- `PERF-06`: Deterministic narrative synthesis verified within local SLA.
