# DENTRACE — Phased Implementation Roadmap (Levels 1–10)

> **DOCUMENT ID:** DOC-ROAD-006  
> **STATUS:** BASELINED (LEVEL 0)  
> **DATE:** 2026-10-18  

This roadmap governs the incremental development of DENTRACE across 10 progressive levels. Progression from one level to the next requires satisfying all dependencies and passing all designated exit quality gates.

---

## Roadmap Overview

```
 [Level 0: Research & Architecture] ◄── CURRENT BASELINE
                │
                ▼
 [Level 1: Core Schemas & Mock Pipeline]
                │
                ▼
 [Level 2: Data Hygiene & Training Harness]
                │
                ▼
 [Level 3: ONNX INT8 CPU Inference Engine]
                │
                ▼
 [Level 4: Rule Layer & Faithful Ollama LLM]
                │
                ▼
 [Level 5: Clinical UI, Canvas & Odontogram]
                │
                ▼
 [Level 6: PDF Claim Pack & Signature Flow]
                │
                ▼
 [Level 7: Integration Testing & Privacy Hardening]
                │
                ▼
 [Level 8: CPU Benchmarking & Latency Profiling]
                │
                ▼
 [Level 9: Offline Packaging & Clinician Audit]
                │
                ▼
 [Level 10: Final Evaluation & Demonstration Pack]
```

---

## Detailed Level Specifications

### Level 0: Preparation, Technical Research & Architecture Specification (CURRENT)
- **Scope:** Environment audit, dataset licensing investigation, pretrained checkpoint audit, modular architecture design, and safety guidelines.
- **Dependencies:** None.
- **Exit Test:** Verified environment report, complete architectural deliverables in `docs/`, clean project structure, zero large downloads to D:, and explicit user approval gate.

---

### Level 1: Core Data Contracts, Pydantic Schemas & Mock End-to-End Pipeline
- **Scope:** Define immutable Pydantic v2 schemas (`AnalysisResult`, `ToothBox`, `PathologyFinding`, `PreAuthNarrative`, `ReportRequest`). Build realistic clinical mock inference pipeline so that full data flow, frontend, and API endpoints can be developed and demoed before heavy weights are loaded.
- **Dependencies:** Level 0 approval.
- **Exit Test:** Schema validation unit tests (`pytest tests/test_schemas.py`) and mock pipeline tests verifying FDI compliance and urgency assignments.

---

### Level 2: Data Preprocessing, Hygiene Pipeline & Training Harness
- **Scope:** Implement `data/download_and_prep.py` with 5-class filtering, patient-level train/val/test splitting BEFORE augmentation, perceptual MD5 hash deduplication, and FDI quadrant-aware horizontal flipping ($1x \leftrightarrow 2x$, $4x \leftrightarrow 3x$). Create reproducible Colab T4 training notebook.
- **Dependencies:** Level 1 completion.
- **Exit Test:** Disjoint split hygiene test verifying zero sample leakage across splits and FDI quadrant-swap verification test.

---

### Level 3: Real ONNX Export, INT8 Quantization & CPU Inference Engine
- **Scope:** Implement PyTorch to ONNX export (opset 17, `ir_version=10`) with dynamic and static calibration INT8 quantization. Build `backend/pipeline/onnx_inference.py` and `backend/pipeline/matching.py` with topological quadrant rules (max 8 teeth/quadrant, deduplication).
- **Dependencies:** Level 2 completion.
- **Exit Test:** ONNX model validity test (`onnx.checker`), INT8 quantization compression verification, and topological post-processing unit tests.

---

### Level 4: Deterministic Clinical Rule Engine, Ollama Client & Faithfulness Checker
- **Scope:** Authoritative deterministic clinical rule engine (`backend/rules/rule_engine.py`) detecting suspected endodontic failure (RCT + periapical lesion on same tooth), elevating urgency to `urgent`, assigning demo CDT codes, and emitting periapical radiograph hints. Connect local Ollama client with Pydantic JSON schema format constraint and bidirectional faithfulness validator.
- **Dependencies:** Level 3 completion.
- **Exit Test:** Rule engine unit tests, faithfulness checker tests catching hallucinated teeth/conditions, and deterministic fallback template tests.

---

### Level 5: Streamlit Clinical UI, Custom HTML5 Canvas Mask Viewer & FDI Odontogram
- **Scope:** Develop calm clinical Streamlit dashboard (`frontend/app.py`) following frontend design rules (paper `#F5F2EC`, ink `#222B2A`, forest green `#2F5D50`, clay `#B5573B`). Implement custom HTML5 canvas component for hover tooltips and tooth clicks. Implement interactive FDI odontogram grid.
- **Dependencies:** Level 4 completion.
- **Exit Test:** UI component rendering tests and headless component smoke test.

---

### Level 6: PDF Claim Pack Generator & Audit Trail
- **Scope:** Build two-page ReportLab clinical claim pack generator with mandatory disclaimer banner, patient/dentist/insurer metadata, embedded radiograph, itemized findings table with demo CDT codes, medical necessity narrative, and empty dentist physical signature line. Local SQLite audit ledger.
- **Dependencies:** Level 5 completion.
- **Exit Test:** PDF generation test verifying valid `%PDF-` binary, non-trivial file size ($>5\text{ KB}$), disclaimer presence, and signature block inclusion.

---

### Level 7: Comprehensive Integration Testing, Privacy Boundary Verification & Hardening
- **Scope:** Full integration test suite exercising FastAPI endpoints (`/health`, `/api/analyze`, `/api/narrative`, `/api/report`), image quality screening, privacy boundary enforcement (zero outbound cloud egress), and error handling for bad images, missing models, and offline Ollama.
- **Dependencies:** Level 6 completion.
- **Exit Test:** 100% pass across all pytest test suites; zero network egress verified.

---

### Level 8: CPU Latency Benchmarking & Performance Optimization
- **Scope:** Execute automated CPU benchmark harness (`benchmarks/benchmark.py`) measuring model-only and end-to-end latencies (p50, p95) for FP32 and INT8 ONNX models over 50 iterations on 640x640 inputs. Record true measured values in markdown table format without fake claims.
- **Dependencies:** Level 7 completion.
- **Exit Test:** Reproducible markdown table and `benchmark_results.json` matching true measurements.

---

### Level 9: Offline Packaging & Clinician Review Protocol
- **Scope:** Verify turnkey offline execution on Windows host. Document clinician-in-the-loop validation protocol, review checklist, and mock case evaluation scenarios.
- **Dependencies:** Level 8 completion.
- **Exit Test:** Clean execution test from cold-start without internet connection.

---

### Level 10: Final Documentation, Demonstration Assets & College Evaluation Readiness
- **Scope:** Finalize project report, code commentary, presentation slides, architecture diagrams, and demonstration video script tailored for college mini-project evaluation.
- **Dependencies:** Level 9 completion.
- **Exit Test:** Comprehensive project readiness audit and sign-off.
