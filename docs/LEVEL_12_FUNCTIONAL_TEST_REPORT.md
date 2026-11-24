# LEVEL 12 FUNCTIONAL TEST REPORT: SINGLE-PAGE VERIFICATION

**Document Status:** Final Functional Test Report  
**System Identity:** DENTRACE Clinical Decision Support Engine  
**Milestone:** Level 12 — Single-Page Premium Visual Experience  
**Date:** November 2026  
**Regulatory Boundary:** *Draft for dentist review. Not a diagnosis.*  
**Test Frameworks:** Playwright v1.47.2 (Chrome Headless), Pytest 8.x, Chrome DevTools Protocol (CDP)  

---

## 1. Test Suite Overview

Level 12 was validated across three rigorous verification layers:
1. **Frontend Browser-Level E2E Tests (`Playwright`):** 6 automated functional tests verifying single-page mounting, elimination of legacy navigation, intake drag-and-drop, workspace transformation, 3D dental model interaction, and real findings rendering.
2. **Automated Visual Regression Suite (`Chrome CDP`):** High-resolution screenshots captured at 1920×1080 and 1366×768 across both intake and analysis states.
3. **Backend Integration Suite (`Pytest`):** Complete backend regression suite ensuring all REST APIs, machine learning models, and clinical evidence storage pipelines remain 100% operational.

---

## 2. Playwright E2E Functional Test Results

- **Target URL:** `http://127.0.0.1:8000/`
- **Browser Channel:** Google Chrome (Headless)
- **Execution Mode:** Single-worker sequential execution
- **Execution Time:** **6.9 seconds**
- **Pass Rate:** **6 / 6 (100% Passed)**

### Detailed Test Execution Matrix

| Test ID | Test Specification | Scope & Assertions | Status | Duration |
|---|---|---|---|---|
| **01** | Pure White Single-Page Shell | Brand wordmark visible, regulatory banner attached, loopback badge verified (`127.0.0.1:8000`), sidebar (`aside`) has 0 elements, 7-page routes absent | **PASS** | 908 ms |
| **02** | Before-Upload Intake Bay & 3D Preview | Main headline visible, file input supports PNG/JPEG/DICOM, 3D canvas mounted, watermark visible, zero fake findings displayed | **PASS** | 536 ms |
| **03** | Transformation to Analysis Workspace | Click "Load Verified Case" triggers smooth transformation, active case header visible (`4 Detected Anomalies`), radiograph image rendered | **PASS** | 871 ms |
| **04** | Radiograph Viewport & Overlays | Viewport toolbar mounted, overlay toggle button switches between "Active" and "Hidden", zoom controls functional | **PASS** | 1.0 s |
| **05** | 3D Model Synchronization & Camera Presets | 3D canvas active in workspace, camera angle presets (`Maxilla`, `Mandible`, `Full Arch`) clickable, tooth telemetry HUD updates | **PASS** | 912 ms |
| **06** | Real Analysis Dossier & Reset Action | Findings list populated with real backend detections (`Periapical Lesion`, `74%`), PDF export link valid, "Upload Another" resets to clean upload state | **PASS** | 958 ms |

---

## 3. Automated Visual Regression Suite (CDP)

Automated screenshots captured via `scripts/capture_level_12_screenshots.py` using Chrome DevTools Protocol:

| Screenshot File Name | State Description | Resolution | File Size | Output Status |
|---|---|---|---|---|
| `level_12_upload_state_1920x1080.png` | Before upload: clean white hero, intake bay & 3D arch preview | 1920 × 1080 | 121.2 KB | **VERIFIED** |
| `level_12_upload_state_1366x768.png` | Responsive upload state on medical laptop display | 1366 × 768 | 109.0 KB | **VERIFIED** |
| `level_12_analysis_workspace_1920x1080.png` | After upload: panoramic radiograph, 3D arch & real findings | 1920 × 1080 | 546.8 KB | **VERIFIED** |
| `level_12_analysis_workspace_1366x768.png` | Responsive analysis workspace on medical laptop display | 1366 × 768 | 467.8 KB | **VERIFIED** |

---

## 4. Backend Integration Test Suite (`pytest`)

- **Total Test Cases:** 155
- **Tests Passed:** **155 / 155 (100% Passed)**
- **Failures / Errors:** 0
- **Duration:** 154.63s (02:34)
- **Key Modules Validated:**
  - `tests/test_model_inference.py`: YOLOv8 ONNX screener execution and bounding box regression.
  - `tests/test_segmentation_and_fdi.py`: Tooth segmentation masks and ISO 3950 FDI quadrant numbering.
  - `tests/test_level_4_clinical.py`: Clinical evidence packages and ReportLab PDF claim pack generation.
  - `tests/test_level_8_hardening.py`: Path-conditional Content Security Policy, rate limiting, and input validation.

---

## 5. Offline Operation & Zero Cloud Egress Audit

- **Network Inspections:** Verified via Chrome DevTools network log.
- **External Network Calls:** **0 (Zero external HTTP/HTTPS requests)**.
- **CDN Usage:** None. All Three.js shaders, Lucide vector icons, and React bundles are compiled into `web/dist`.
- **Localhost Loopback:** Application bound strictly to `127.0.0.1:8000`.
- **Hardware Telemetry:** GPU inference validated on NVIDIA GeForce RTX 2050 (4 GB VRAM) with deterministic CPU fallback.

