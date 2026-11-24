# DENTRACE Level 9: Release Test Report & Validation Summary

## 1. Executive Summary

- **Product Name**: DENTRACE
- **Version**: 0.1.0 (Windows Desktop Release)
- **Target OS**: Windows 11 x64 (Build 22000+)
- **Execution Date**: October 22, 2026
- **Test Framework**: Pytest 9.1.1, Python 3.11.9
- **Overall Status**: **PASSED (155/155 tests, 100% success rate)**
- **Total Test Execution Time**: 220.45 seconds (03:40 min)
- **Safety Directive**: Hardcoded clinical disclaimer verified: *"Draft for dentist review. Not a diagnosis."*

---

## 2. Automated Test Suite Breakdown

| Test Module | Scope / Functionality Tested | Tests | Passed | Failed | Status |
|:---|:---|:---:|:---:|:---:|:---:|
| `tests/test_api_studies.py` | FastAPI study endpoints, DICOM upload, study metadata queries | 9 | 9 | 0 | PASSED |
| `tests/test_database.py` | SQLite schema initialization, table structures, relationships | 2 | 2 | 0 | PASSED |
| `tests/test_dataset_integrity.py` | Raw dataset inventories, annotation formats, split verification | 4 | 4 | 0 | PASSED |
| `tests/test_environment.py` | Python 3.11.9 runtime, dependency versions, GPU availability | 3 | 3 | 0 | PASSED |
| `tests/test_frontend_integration.py` | Streamlit component rendering, state handling, navigation | 13 | 13 | 0 | PASSED |
| `tests/test_level_3_repair.py` | Mask validation, polygon extraction, polygon-box distinction | 5 | 5 | 0 | PASSED |
| `tests/test_level_4_clinical.py` | Deterministic clinical rules, CDT/ADA code mapping, pre-auth | 16 | 16 | 0 | PASSED |
| `tests/test_level_6_optimization.py` | Quantization benchmarks, ONNX parity, FDI assignment logic | 14 | 14 | 0 | PASSED |
| `tests/test_level_7_integration.py` | End-to-end multi-stage pipeline, fallback mechanisms | 13 | 13 | 0 | PASSED |
| `tests/test_level_8_hardening.py` | DICOM de-identification, token security, rate limiting, DB locks | 37 | 37 | 0 | PASSED |
| `tests/test_model_inference.py` | PyTorch and ONNX inference execution, input tensors, output masks | 16 | 16 | 0 | PASSED |
| `tests/test_model_registry.py` | Model manifest validation, SHA-256 hash checks, file presence | 6 | 6 | 0 | PASSED |
| `tests/test_segmentation_and_fdi.py` | Combined tooth detection and pathological lesion segmentation | 7 | 7 | 0 | PASSED |
| `tests/test_storage_and_security.py` | User data isolation, path traversal prevention, file manager | 10 | 10 | 0 | PASSED |
| **TOTAL** | **Full Regression & Hardening Suite** | **155** | **155** | **0** | **100% PASSED** |

---

## 3. Level 9 Packaging & Launcher Validation

### 3.1 Packaging Automation Audit
- **Builder**: `scripts/build_release.py` executed without errors.
- **Staging Output**: `dist/DENTRACE-v0.1.0-win64/` (~450 MB uncompressed).
- **Package Archive**: `dist/DENTRACE-v0.1.0-win64.zip` (446.59 MB compressed).
- **Checksum Verification**: `dist/SHA256SUMS.txt` verified against package file hash.
- **Exclusion Filters Verified**:
  - Zero `__pycache__` or `.pyc` files staged.
  - Zero test files (`tests/`) or pytest caches staged.
  - Zero unanonymized patient data files staged.
  - Zero raw training datasets staged.

### 3.2 Launcher & Lifecycle Audit
- **Supervisor**: `scripts/launcher/launcher.py`, `launch_dentrace.bat`, `launch_dentrace.ps1`.
- **Single-Instance Mutex**: Verified. Running concurrent launches correctly detects `.dentrace.lock` and halts with warning.
- **Port Conflict Detection**: Verified. Confirms 8000 and 8501 are free before spawning servers.
- **Hardware & LLM Probing**:
  - NVIDIA RTX 2050 GPU detected; CUDA execution provider verified.
  - Ollama ping verified with graceful fallback if offline.
- **Zero-Orphan Process Termination**: Verified. On console close or `Ctrl+C`, the launcher terminates child process trees completely via `taskkill /F /T /PID`.

### 3.3 Security & Privacy Validation
- **Local API Security**: Ephemeral `X-DENTRACE-TOKEN` verified. Requests lacking token receive `401 Unauthorized`.
- **DICOM Privacy**: 18 standard PHI tags sanitized + vendor private groups purged + burned-in text detection active.
- **Storage Isolation**: Clinical data strictly written to user profile directory (`%LOCALAPPDATA%\DENTRACE\data`), requiring zero administrative write privileges.
