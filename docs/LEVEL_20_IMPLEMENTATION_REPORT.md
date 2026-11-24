# LEVEL 20 — DENTRACE OPG WORKFLOW, FDI NUMBERING & 3D SYNCHRONIZATION IMPLEMENTATION REPORT

> **DOCUMENT ID:** DOC-L20-IMPL-001  
> **STATUS:** COMPLETE & VERIFIED — 14/14 TEST SUITE PASSING — E2E BROWSER VALIDATED  
> **DATE:** 2026-11-21  
> **CLINICAL NOTICE:** "Draft for dentist review. Not a diagnosis. Not a certified medical device."

---

## 1. Executive Summary

Level 20 resolves critical workflow and presentation defects observed during real clinical radiograph intake:
1. **Unintended IOPA Mode on Panoramic Radiographs:** Uploaded Panoramic OPG images (specifically portrait-orientation photographs of panoramic scans with aspect ratio $\approx 0.75$) were incorrectly classified as Intraoral Periapical (`intraoral_periapical`), triggering modality safety locks that blocked AI screener inference and presented an irrelevant 4-tooth focus strip.
2. **Arbitrary Default Tooth Selection:** The 3D dental arch and tooth anatomy viewer hardcoded default selections to FDI #16 (or displayed FDI #12), falsely suggesting pre-existing pathology or tooth focus when no finding or tooth had been selected by the clinician.
3. **Misleading "0 Anomalies" Representation:** The findings dossier displayed *"No anomalies detected in this panoramic scan"* even when AI analysis had never run or was blocked due to modality gating.
4. **Modality State Inconsistency:** Switching modality from IOPA/unknown to Panoramic OPG did not allow a fresh inference request or clear stale modality blocker states.

Through systematic backend and frontend refactoring, all issues have been resolved, verified via 14 automated unit/integration tests in `tests/test_level_20_opg_workflow.py` (100% pass rate), and confirmed via live headless browser execution against `http://127.0.0.1:5173/`.

---

## 2. Root Cause Analysis

### 2.1 The Aspect Ratio Auto-Classification Flaw
In Level 18/19, an automated heuristic was introduced in `backend/services/study_service.py` (`create_study`):
```python
# PREVIOUS FLAWED HEURISTIC:
if metadata.aspect_ratio <= 1.4:
    persisted_modality = "intraoral_periapical"
elif metadata.aspect_ratio >= 1.6:
    persisted_modality = "panoramic_opg"
else:
    persisted_modality = "unknown"
```
When clinicians uploaded smartphone photographs or portrait scans of panoramic radiographs (e.g., $1200 \times 1600$, aspect ratio $0.75$), this heuristic automatically flagged the radiograph as `intraoral_periapical`. 

### 2.2 Cascading Failures
1. **Inference Rejection:** `analyze_study()` correctly enforced the Level 18 modality safety boundary, rejecting panoramic model execution on `intraoral_periapical` images with `status="modality_unsupported"`.
2. **Silent Swallowing:** The frontend `handleFileUpload` caught the notice silently, leaving the study in `ingested` status with zero findings.
3. **Misleading Findings Dossier:** `SinglePageExperience.tsx` rendered *"No anomalies detected in this panoramic scan"*, misleading the clinician into believing a clean scan was diagnosed.
4. **Irrelevant 4-Tooth Strip:** The UI entered IOPA mode, rendering a 4-tooth focus strip (#14, #15, #16, #17) across the top of a full panoramic radiograph.
5. **Default 3D State:** `selectedFdi` was initialized to `16` in `SinglePageExperience.tsx`, `DentalArchGLTF.tsx`, `DentalArch3D.tsx`, and `ToothCutaway3D.tsx`, resulting in unprompted molar highlighting.

---

## 3. Engineering & Architectural Fixes

### 3.1 Backend Modality Ingestion & Safety Guard (`backend/services/study_service.py`)
- **Safe Ratio Thresholding:** Changed the heuristic so that only clear panoramic aspect ratios ($\ge 1.5$) are auto-assigned `panoramic_opg`. Any image with ratio $< 1.5$ (including square and portrait scans) is tagged as `unknown`.
- **Zero Silent Guessing:** The application NEVER silently assumes an image is IOPA. If the aspect ratio is ambiguous, the study is recorded as `unknown`, requiring explicit clinician confirmation before AI models can execute.
- **State Reset on Modality Update:** In `update_study_modality()`, when a study is updated to `panoramic_opg`, any stale findings are purged, and the study status is reset to `ingested` if not already `analyzed`, allowing fresh inference execution.

### 3.2 Frontend Neutral State & Default Removal
- `SinglePageExperience.tsx`: `selectedFdi` initialized to `null` (was `16`). `handleReset()` resets `selectedFdi` to `null`.
- `DentalArchGLTF.tsx`, `DentalArch3D.tsx`, `ToothCutaway3D.tsx`: `selectedFdi` defaults changed from `16` to `null`.
- When `selectedFdi === null`, the 3D model badge displays: *"Select a tooth or finding to inspect"* and the cutaway viewer displays *"Educational Reference Anatomy — Select a tooth or finding to view anatomical tissue correlation"*.

### 3.3 Truthful Inference States in Findings Dossier
The findings empty-state container now distinguishes four clinical realities:
1. `currentStudy.status === 'analyzed'`: *"Analysis completed — 0 anomalies detected under current screener threshold."*
2. `modality === 'unknown'`: *"Analysis not performed — Radiograph modality is unconfirmed. Please confirm modality above."*
3. `modality === 'intraoral_periapical' || modality === 'bitewing'`: *"Automated analysis unavailable for limited-field radiographs. Use manual annotation on X-ray."*
4. Otherwise: *"Analysis not performed — Click below to execute panoramic anomaly screener."* with an interactive `"Run Panoramic AI Analysis"` trigger button.

### 3.4 Modality Confirmation Banner
When a radiograph is loaded with `modality === 'unknown'`, a prominent high-contrast yellow alert banner appears above the radiograph canvas with one-click actions:
- `[Confirm Panoramic (OPG)]` -> Updates database to `panoramic_opg` and automatically triggers the neural screener.
- `[Confirm IOPA]` -> Updates database to `intraoral_periapical` and switches to the 4-tooth limited-field focus strip.

---

## 4. Test & Verification Matrix

Automated test suite `tests/test_level_20_opg_workflow.py` executed with 100% success rate:

| Test ID | Test Name | Invariant Verified | Outcome |
|---|---|---|---|
| T20-01 | `test_opg_study_auto_selects_correct_modality_when_panoramic_ratio` | Aspect ratio $\ge 1.5$ assigns `panoramic_opg` | **PASSED** |
| T20-02 | `test_portrait_or_square_study_defaults_to_unknown_never_silently_iopa` | Portrait ($0.75$) defaults to `unknown`, never IOPA | **PASSED** |
| T20-03 | `test_opg_modality_persists_after_reload` | Modality survives SQLite round-trip | **PASSED** |
| T20-04 | `test_opg_inference_actually_executes` | Real ONNX screener runs on OPG without fake fallbacks | **PASSED** |
| T20-05 | `test_opg_findings_saved_and_retrieved` | Findings persisted with bounding boxes and status | **PASSED** |
| T20-06 | `test_iopa_and_bitewing_remain_protected` | Panoramic models refuse execution on IOPA/bitewing | **PASSED** |
| T20-07 | `test_unknown_modality_blocks_ai_inference` | `unknown` modality strictly blocks inference | **PASSED** |
| T20-08 | `test_switching_from_iopa_to_opg_permits_fresh_analysis` | Modality update permits fresh inference | **PASSED** |
| T20-09 | `test_explicit_user_modality_overrides_heuristic` | Explicit user selection takes precedence | **PASSED** |
| T20-10 | `test_model_switching_idempotency` | Switching models executes cleanly | **PASSED** |
| T20-11 | `test_manual_annotations_distinct_from_ai_findings` | AI (`FND-`) vs Manual (`ANN-`) separation maintained | **PASSED** |
| T20-12 | `test_aspect_ratio_threshold_boundary` | Exact $1.50$ vs $1.49$ threshold behavior | **PASSED** |
| T20-13 | `test_pdf_export_with_opg_study` | Valid multi-page ReportLab PDF export ($>10$ KB) | **PASSED** |
| T20-14 | `test_regulatory_disclaimer_presence` | Mandatory clinical disclaimer assertion | **PASSED** |

---

## 5. End-to-End Browser Verification Evidence

Headless browser automation verified all visual and interactive requirements at `http://127.0.0.1:5173/`:
- **Initial State:** Badge shows *"Select a tooth or finding to inspect"*; no tooth pre-selected.
- **OPG Mode:** Verified case `CASE-D49166F1` loads with `Panoramic Radiograph (OPG)` header, IOPA strip hidden, and 4 neural detections rendered.
- **3D Synchronization:** Selecting finding `FDI #35 · Caries (47%)` synchronously updates the 2D bounding reticle, the 3D dental arch highlight, and the 3D cutaway mesh.
- **Clinical Claim Pack Studio:** Pre-Authorization modal renders live 3D canvas snapshot, CDT demonstrative billing codes, editable clinical justification narrative, and successfully downloads `DENTRACE_CASE-D49166F1_ClinicalReport.pdf`.
