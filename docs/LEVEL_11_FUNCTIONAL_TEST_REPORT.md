# LEVEL 11 FUNCTIONAL TEST REPORT: END-TO-END VERIFICATION

**Document Status:** Final Functional Test Report  
**Project:** DENTRACE Clinical Decision Support Engine  
**Milestone:** Level 11 — Complete Streamlit Removal & Premium React Frontend  
**Date:** November 2026  
**Regulatory Boundary:** *Draft for dentist review. Not a diagnosis.*  

---

## 1. Test Suite Summary

The Level 11 release was subjected to three distinct layers of functional validation:
1. **Backend Integration & Unit Test Suite (`pytest`):** 155 test cases validating ML inference, tooth assignment algorithms, clinical evidence storage, insurance drafting, and REST API endpoints.
2. **Frontend End-to-End Test Suite (`Playwright`):** 7 comprehensive browser-level tests validating DOM mounting, component interaction, 3D WebGL canvas initialization, and cross-view routing.
3. **Automated Visual Regression Suite (`CDP Screenshot Runner`):** 11 automated screenshots captured at 1920×1080 and across 4 responsive viewports (1440×900, 1366×768, 1024×768, 768×1024).

---

## 2. Playwright E2E Functional Test Results

- **Test Framework:** Playwright v1.47.2
- **Browser Channel:** Google Chrome (Headless)
- **Target URL:** `http://127.0.0.1:8000`
- **Execution Mode:** Single-worker sequential execution
- **Execution Time:** **8.4 seconds**
- **Pass Rate:** **7 / 7 (100% Passed)**

### Test Execution Matrix

| Test ID | Test Name | Target View | Key Assertions | Result | Duration |
|---|---|---|---|---|---|
| **01** | System Shell & Navigation | `/overview` | Title contains "DENTRACE", mandatory disclaimer visible, loopback telemetry badge visible, 3D canvas mounted | **PASS** | 1.2s |
| **02** | Radiograph Ingestion Bay | `/upload` | Heading verified, drag-and-drop file input attached with PNG/JPEG/DICOM accept filters | **PASS** | 732ms |
| **03** | Diagnostic Workstation Viewport | `/workstation` | Workstation header verified, active study auto-selected, radiograph image rendered, layer buttons (Box/Mask/Label) active, screener trigger visible | **PASS** | 899ms |
| **04** | FDI Tooth Explorer 3D/2D Sync | `/fdi` | 3D canvas mounted, 2D odontogram mounted, click tooth #16 updates detail dossier heading | **PASS** | 1.1s |
| **05** | Clinical Evidence Engine | `/evidence` | Strict separation headers verified: "AI Candidate Observations" vs "Clinician Confirmed Findings", 4-tab switcher mounted | **PASS** | 554ms |
| **06** | Pre-Authorization Studio | `/preauth` | Active study loaded, 10-section narrative editor visible, "Generate Narrative" button mounted, "Export Claim PDF" button attached | **PASS** | 547ms |
| **07** | System Settings & Hardware | `/settings` | NVIDIA GeForce RTX 2050 GPU detected, Zero External Cloud Egress badge verified, model registry visible | **PASS** | 639ms |

---

## 3. Automated Visual Regression Suite (CDP)

Captured via `scripts/capture_level_11_screenshots.py` using Chrome DevTools Protocol:

| View Slug | Viewport Resolution | File Size | Output Path | Status |
|---|---|---|---|---|
| `overview` | 1920 × 1080 | 137.3 KB | `docs/screenshots/level_11/overview_1920x1080.png` | **VERIFIED** |
| `upload` | 1920 × 1080 | 85.5 KB | `docs/screenshots/level_11/upload_1920x1080.png` | **VERIFIED** |
| `workstation` | 1920 × 1080 | 71.4 KB | `docs/screenshots/level_11/workstation_1920x1080.png` | **VERIFIED** |
| `fdi` | 1920 × 1080 | 127.2 KB | `docs/screenshots/level_11/fdi_1920x1080.png` | **VERIFIED** |
| `evidence` | 1920 × 1080 | 87.1 KB | `docs/screenshots/level_11/evidence_1920x1080.png` | **VERIFIED** |
| `preauth` | 1920 × 1080 | 101.7 KB | `docs/screenshots/level_11/preauth_1920x1080.png` | **VERIFIED** |
| `settings` | 1920 × 1080 | 174.6 KB | `docs/screenshots/level_11/settings_1920x1080.png` | **VERIFIED** |
| `workstation` | 1440 × 900 | 69.6 KB | `docs/screenshots/level_11/workstation_1440x900.png` | **VERIFIED** |
| `workstation` | 1366 × 768 | 68.4 KB | `docs/screenshots/level_11/workstation_1366x768.png` | **VERIFIED** |
| `workstation` | 1024 × 768 | 66.7 KB | `docs/screenshots/level_11/workstation_1024x768.png` | **VERIFIED** |
| `overview` | 768 × 1024 | 110.8 KB | `docs/screenshots/level_11/overview_768x1024.png` | **VERIFIED** |

---

## 4. Defects Identified & Resolved During Migration

| Defect ID | Description | Root Cause | Resolution |
|---|---|---|---|
| **BUG-L11-01** | Blank screen on initial browser navigation | Level 8 security middleware enforced `script-src 'none'` globally, blocking compiled Vite scripts | Applied path-conditional CSP: strict `'none'` for `/api/*`, `'self' 'unsafe-inline'` for SPA paths |
| **BUG-L11-02** | Vite production build failure across drive junction | NTFS junction `D:\mini\web\node_modules` -> `C:\...` caused Vite to emit absolute path error | Added `resolve: { preserveSymlinks: true }` in `vite.config.ts` |
| **BUG-L11-03** | Workstation & PreAuth Playwright tests failing | `StudyContext` checked `res.studies`, but backend Pydantic model serialized as `res.items`, leaving `currentStudyId` null | Normalized `StudyContext` to consume `res.items || res.studies || []` and updated `StudyListResponse` interface |
| **BUG-L11-04** | Clinical Evidence view crashing on load | Field name mismatch between backend (`ai_observations`, `dentist_confirmations`) and frontend (`ai_candidate_observations`), causing undefined `.length` access | Added normalized getters `aiObs` and `confirmed` with fallback chaining and updated TypeScript interface |
| **BUG-L11-05** | Three.js `userData` TypeScript compilation warning | Duplicate `fdi` property assigned in `mesh.userData = { fdi: data.fdi, ...data }` | Simplified to `mesh.userData = { ...data }` |

---

## 5. Performance & Responsiveness Comparison

| Metric | Level 10 (Streamlit) | Level 11 (React SPA) | Improvement |
|---|---|---|---|
| Page Navigation Latency | 800 – 1800 ms (rerun) | < 16 ms (client-side) | **> 98% faster** |
| 3D Dental Arch FPS | 24 – 35 FPS (iframe) | 60 FPS (native WebGL) | **Smooth 60 FPS** |
| Radiograph Pan/Zoom | Clunky / reloaded | Hardware-accelerated CSS/SVG | **Zero flicker** |
| Process Count | 2 processes (8000 + 8501) | 1 process (8000 only) | **50% fewer processes** |
| Memory Overhead | ~350 MB Python RAM | ~70 MB Browser RAM | **~80% reduction** |

