# LEVEL 11 MIGRATION PLAN: STREAMLIT TO REACT ARCHITECTURE
**Project:** DENTRACE Clinical Decision Support Engine  
**Target:** Complete Streamlit Replacement & Premium React/Vite/TypeScript Frontend  
**Date:** November 2026  
**Status:** Approved for Execution  
**Regulatory Boundary:** *"Draft for dentist review. Not a diagnosis."*  

---

## 1. Existing Architecture Analysis

### Current Application Topology
```
                     +----------------------------------+
                     |  Single-Instance Launcher        |
                     |  (scripts/launcher/launcher.py)  |
                     +-----------------+----------------+
                                       |
                   +-------------------+-------------------+
                   | (Subprocess 1)                        | (Subprocess 2)
                   v                                       v
      +------------------------+             +--------------------------+
      | FastAPI Backend Engine | < - - - - - | Streamlit Frontend (8501)|
      | Port 8000 (127.0.0.1)  |  HTTP loop  | (frontend/app.py)        |
      | - REST API v1          |             | - 7 multi-page views     |
      | - SQLite DB + Alembic  |             | - Streamlit components   |
      | - Storage Manager      |             | - WebGL HTML iframe      |
      | - ONNX Models / PyTorch|             +--------------------------+
      | - Ollama Client (11434)|
      | - ReportLab PDF Export |
      +------------------------+
```

### Limitations of Current Streamlit Architecture
1. **Execution Model Overhead:** Every user interaction causes a full Python script re-run of the view file unless wrapped in complex `st.session_state` conditionals.
2. **Visual & Interaction Constraints:** Streamlit injects rigid DOM wrappers, automated iframe sandboxes, and default styling resets that conflict with custom medical imaging workstations.
3. **Dual-Process Burden:** Running both Uvicorn and Streamlit increases memory overhead and introduces IPC latency over HTTP loopback.
4. **3D WebGL Sandboxing:** The Three.js dental arch was forced into a static iframe component (`components.html()`), preventing reactive bidirectional state bindings (e.g., clicking a tooth in 3D directly triggering React state updates without a postMessage iframe hack).

---

## 2. Existing API Contracts (FastAPI Backend)

The FastAPI backend exposes 14 RESTful endpoints under `/api/v1` and health routes at `/`:

| Endpoint | Method | Input Contract | Output Contract | Frontend Consumer |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | None | `{status, app, version, timestamp, disclaimer}` | Global Heartbeat Badge, System Settings |
| `/api/v1/readiness` | `GET` | None | `{status, checks: {database, storage, disk_free_gb, available_models}}` | System Settings, Status Bar |
| `/api/v1/models` | `GET` | None | `{total, models: [{model_id, is_available, task, ...}]}` | Overview, Workstation Model Selector, Settings |
| `/api/v1/models/{id}/status` | `GET` | `model_id: str` | `{model_id, is_available, weights_hash_sha256, provenance}` | Model Registry Table |
| `/api/v1/studies` | `GET` | `limit: int`, `offset: int`, `include_archived: bool` | `{total, count, limit, offset, studies: [StudyResponse]}` | Overview (Recent Cases), Study Switcher |
| `/api/v1/studies/upload` | `POST` | `multipart/form-data`: `file`, `patient_anonymous_id`, `clinical_indication` | `StudyResponse` (UUID, metadata, preview path) | Upload Workspace |
| `/api/v1/studies/{id}` | `GET` | `study_id: str` | `StudyDetail` (full metadata, findings, quality, reviews) | Workstation, FDI Explorer, Evidence, Pre-Auth |
| `/api/v1/studies/{id}/preview` | `GET` | `study_id: str` | Image bytes (`image/png`) | Radiograph Viewport Canvas |
| `/api/v1/studies/{id}` | `DELETE` | `study_id: str`, `hard_delete: bool` | `204 No Content` | Case Management |
| `/api/v1/studies/{id}/analyze` | `POST` | `payload: {conf_threshold, iou_threshold, model_id}` | `AnalysisResponse` (detections, polygons, FDI, latency) | Workstation Run Screener Action |
| `/api/v1/clinical/studies/{id}/evidence` | `GET` | `study_id: str` | `ClinicalEvidencePackage` (AI findings, confirmed facts) | Clinical Evidence View, FDI Explorer |
| `/api/v1/clinical/studies/{id}/findings/{f_id}/review` | `POST` | `ClinicianReviewRequest` (decision, reviewer, fdi, notes) | `DentistFindingConfirmation` | Workstation Review Form, Evidence View |
| `/api/v1/clinical/studies/{id}/examination` | `POST` | `ClinicalExaminationRequest` (fdi, vitality, percussion, etc.) | `ClinicalExaminationRecord` | Evidence View (Chairside Exam) |
| `/api/v1/clinical/studies/{id}/symptoms` | `POST` | `PatientSymptomRequest` (symptom, fdi, duration, severity) | `PatientSymptomRecord` | Evidence View (Intake Symptoms) |
| `/api/v1/clinical/studies/{id}/procedure` | `POST` | `ProcedureSelectionRequest` (procedure, rationale, cdt) | `RequestedProcedureRecord` | Pre-Auth Studio (Procedure Selector) |
| `/api/v1/clinical/studies/{id}/readiness` | `POST/GET` | `study_id: str` | `EvidenceReadinessReport` (complete, missing, warnings) | Pre-Auth Studio Preflight Card |
| `/api/v1/clinical/studies/{id}/audit-trail` | `GET` | `study_id: str` | `list[AuditTrailEntry]` | Audit Ledger Modal / Evidence View |
| `/api/v1/insurance/studies/{id}/draft` | `POST` | `force_regenerate: bool`, `model_tag: str` | `{draft: InsurancePreAuthDraft, performance_metrics}` | Pre-Auth Studio Narrative Generator |
| `/api/v1/insurance/studies/{id}/draft` | `GET` | `study_id: str` | `InsurancePreAuthDraft` (10 clinical narrative sections) | Pre-Auth Studio Editor |
| `/api/v1/insurance/studies/{id}/draft` | `PUT` | `PreAuthDraftUpdateRequest` (updated sections, dentist info) | `InsurancePreAuthDraft` | Pre-Auth Studio Save Revisions |
| `/api/v1/insurance/studies/{id}/claim-pack/pdf` | `GET` | `study_id: str` | PDF binary stream (`application/pdf`) | Pre-Auth Studio PDF Preview & Download |
| `/api/v1/insurance/cdt-catalog` | `GET` | None | `list[CDTCodeEntry]` | Pre-Auth Studio CDT Explorer |

---

## 3. Existing Frontend Features (To Migrate with Full Parity)

1. **Global Features:**
   - Single-page application shell with deep linking and route parameters.
   - Distinctive brand identity (DENTRACE monogram, Swiss typography, mineral palette).
   - Sticky mandatory clinical boundary: *"Draft for dentist review. Not a diagnosis."*
   - Active study context switcher and telemetry status indicators.
   - Keyboard navigation shortcuts (`1-7` for view switching, `F` for zoom-fit, `Esc` for modal dismissal).

2. **Screen A: Overview:**
   - Academic clinical mission hero and system vitals telemetry.
   - Interactive 3D dental arch widget showing permanent dentition reference.
   - Recent studies dossier table with real acquisition timestamps, case IDs, and actions (Open in Workstation, Export, Inspect).
   - Fast case launcher / file drop-zone shortcut.

3. **Screen B: Upload Workspace:**
   - Drag-and-drop file ingestion zone supporting PNG, JPEG, and DICOM formats.
   - Client-side image dimensions, aspect ratio, file size, and color space preflight inspection.
   - Anonymous patient ID generator (`ANON-XXXXX`) and clinical indication text input.
   - Real upload progress bar with direct transition to Diagnostic Workstation upon completion.

4. **Screen C: Diagnostic Workstation:**
   - 70/30 asymmetric high-priority radiographic viewport.
   - Pan and zoom canvas with mouse wheel, drag-to-pan, 1:1 pixel view, and zoom-to-fit controls.
   - Interactive detection layers: toggle bounding boxes, polygon masks, finding labels, and confidence tags.
   - Real-time screener trigger invoking backend ONNX models (`liodon-panoramic-screener`, `dentex-yolov8n-seg`).
   - Finding inspector sidebar: card listing of anomalies with Okabe-Ito clinical color coding, tooth FDI assignment, confidence scores, and bounding box hover sync.
   - Clinician attestation form: Accept / Reject / Correct finding with dentist name, license, and audit trail record.

5. **Screen D: FDI Tooth Explorer:**
   - Synchronized dual-mode dental representation: 3D interactive arch alongside 2D adult odontogram.
   - 32 permanent teeth categorized by 4 quadrants (Q1 Maxillary Right, Q2 Maxillary Left, Q3 Mandibular Left, Q4 Mandibular Right).
   - Selected tooth detailed dossier: anatomical classification, historical findings, vitality status, and quick attestation actions.
   - Camera presets: Full Arch, Maxilla (Upper), Mandible (Lower), Frontal Anterior.

6. **Screen E: Clinical Evidence:**
   - Strict factual separation: AI Candidate Observations vs. Clinician-Confirmed Findings.
   - Chairside examination inputs (pulp vitality, percussion sensitivity, probing depth, visual cavitation).
   - Patient intake symptoms recorder (chief complaint, pain duration, severity scale).
   - Chronological audit ledger with cryptographic SHA-256 verification and immutable event records.

7. **Screen F: Insurance Pre-Authorization Studio:**
   - Deterministic evidence readiness preflight report (identifying missing required documentation).
   - CDT code catalog explorer and procedure recommendation selector.
   - Evidence-grounded 10-section narrative draft generator (Ollama local LLM with deterministic clinical fallback).
   - Full in-place narrative editor allowing clinician revisions.
   - ReportLab PDF export with live browser preview and download capability.

8. **Screen G: System Settings:**
   - Real backend health metrics, database connectivity, and local storage usage.
   - Hardware detection: NVIDIA RTX 2050 GPU status, CUDA availability, and host CPU specs.
   - Local Ollama status probe (`127.0.0.1:11434`).
   - Cryptographic model registry inspector with SHA-256 weight hashes and provenance verification.
   - Zero-cloud-egress compliance audit verification.

---

## 4. Backend Dependencies & Static Serving Integration

The backend will be preserved without altering its inference algorithms, clinical logic, or database schemas:
1. **Static Files Mount:** In `backend/main.py`, mount the built React assets (`web/dist`) to serve the single-page application at `/`.
2. **SPA Routing Fallback:** For non-API routes (`not path.startswith("/api")`), return `web/dist/index.html` so client-side React Router handles URLs seamlessly.
3. **CORS Hardening:** React served directly from FastAPI over port 8000 eliminates cross-origin issues completely, while retaining loopback restriction to `127.0.0.1`.
4. **Single-Port Desktop Architecture:** The Windows launcher (`scripts/launcher/launcher.py`) only needs to start FastAPI on `127.0.0.1:8000`. The browser opens directly to `http://127.0.0.1:8000`, eliminating port 8501 and reducing system memory consumption.

---

## 5. Migration Strategy

```
Phase 1: Project Setup & Build Environment
  ├── Create `web/` directory with Vite + React + TypeScript
  ├── Create NTFS Directory Junction: `web/node_modules` -> `C:\Users\krish\AppData\Local\dentrace_build\web_node_modules`
  ├── Install dependencies (react, react-dom, react-router-dom, three, @types/three, motion, lucide-react, vite)
  └── Configure offline font bundle and global Swiss-editorial design tokens (CSS Modules/Variables)

Phase 2: Core Infrastructure & API Layer
  ├── Strongly typed API client (`src/api/client.ts`) matching FastAPI schemas
  ├── State management hooks (`useStudy`, `useHealth`, `useEvidence`)
  └── Shell layout: Header, Navigation Bar, Clinical Disclaimer Banner, Heartbeat Badge

Phase 3: 3D Dental Arch Engine
  ├── Port Three.js procedural tooth geometry (32 anatomically differentiated teeth)
  ├── Implement OrbitControls, raycasting hover/selection, and camera presets
  └── Ensure disclaimer: "Reference 3D Model • Not Patient Scan"

Phase 4: Rebuild 7 Application Views
  ├── View 1: Overview (`/overview`)
  ├── View 2: Upload Workspace (`/upload`)
  ├── View 3: Diagnostic Workstation (`/workstation`) with radiograph pan/zoom canvas
  ├── View 4: FDI Tooth Explorer (`/fdi`) with 3D/2D sync
  ├── View 5: Clinical Evidence (`/evidence`)
  ├── View 6: Pre-Authorization Studio (`/preauth`)
  └── View 7: System Settings (`/settings`)

Phase 5: Backend Static Mount & Launcher Integration
  ├── Build production bundle (`npm run build` -> `web/dist`)
  ├── Update `backend/main.py` to serve `web/dist` with SPA fallback
  ├── Update `scripts/launcher/launcher.py` to launch single FastAPI process on 8000
  └── Verify launcher preflight, health checks, and browser launch

Phase 6: Multi-Tier Verification & Testing
  ├── Run backend 155-test suite
  ├── Run frontend functional and Playwright tests
  ├── Capture 5-resolution screenshots (1920x1080, 1440x900, 1366x768, 1024x768, 768x1024)
  └── Document PS compliance exception for Streamlit -> React migration
```

---

## 6. Potential Risks & Mitigation

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Disk Space Exhaustion on D:** | Build failure or corruption | Route `web/node_modules` via NTFS Directory Junction to `C:\Users\krish\AppData\Local\dentrace_build\`, where 88 GB is free. |
| **Asset CDN Leaks (Cloud Egress)** | Breach of Zero Cloud Egress rule | All dependencies, Three.js runtime, Lucide icons, and web fonts are 100% locally bundled. Zero external CDNs or network fetches. |
| **Canvas Pan/Zoom Performance** | Sluggish radiograph exploration | Use hardware-accelerated CSS transforms (`transform: translate3d(...) scale(...)`) with high-resolution canvas overlays. |
| **Inference Regression** | Model failures | Zero modifications to ML inference models, FDI calibration, or Ollama service. React client consumes identical REST endpoints. |
| **Streamlit PS Requirement Deviation** | Academic project evaluation risk | Document transparently in `docs/LEVEL_11_PS_COMPLIANCE_UPDATE.md` with explicit justification (clinical usability, performance, and responsive WebGL integration). |

---

## 7. Files That Will Be Modified or Created

### New React Application (`web/`)
- `web/package.json`, `web/tsconfig.json`, `web/vite.config.ts`, `web/index.html`
- `web/src/main.tsx`, `web/src/App.tsx`, `web/src/routes.tsx`
- `web/src/styles/tokens.css`, `web/src/styles/global.css`
- `web/src/api/client.ts`, `web/src/api/types.ts`
- `web/src/components/layout/Shell.tsx`, `Header.tsx`, `Nav.tsx`, `Disclaimer.tsx`
- `web/src/components/3d/DentalArch3D.tsx`, `web/src/components/3d/toothGeometry.ts`
- `web/src/components/canvas/RadiographCanvas.tsx`
- `web/src/components/odontogram/Odontogram2D.tsx`
- `web/src/views/OverviewView.tsx`
- `web/src/views/UploadView.tsx`
- `web/src/views/WorkstationView.tsx`
- `web/src/views/FdiExplorerView.tsx`
- `web/src/views/ClinicalEvidenceView.tsx`
- `web/src/views/PreAuthStudioView.tsx`
- `web/src/views/SystemSettingsView.tsx`

### Backend Modifications
- `backend/main.py`: Add static files mount for `web/dist` with SPA fallback.

### Launcher & Packaging Modifications
- `scripts/launcher/launcher.py`: Remove Streamlit subprocess launch; point browser to `http://127.0.0.1:8000`.
- `launch_dentrace.bat` / `launch_dentrace.ps1`: Update documentation and health probes.

### Documentation Deliverables
- `docs/LEVEL_11_MIGRATION_PLAN.md` (this document)
- `docs/LEVEL_11_ARCHITECTURE.md`
- `docs/LEVEL_11_IMPLEMENTATION_REPORT.md`
- `docs/LEVEL_11_FUNCTIONAL_TEST_REPORT.md`
- `docs/LEVEL_11_VISUAL_REVIEW.md`
- `docs/LEVEL_11_PS_COMPLIANCE_UPDATE.md`

