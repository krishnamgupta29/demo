# DENTRACE Level 7 — End-to-End System Integration & Reliability Report

> **DOCUMENT ID:** DOC-INT-007  
> **STATUS:** LEVEL 7 COMPLETE & VERIFIED  
> **DATE:** 2026-10-22  
> **REGULATORY DIRECTIVE:** *"Draft for dentist review. Not a diagnosis. Academic college decision-support prototype."*

---

## 1. Executive Summary & Purpose

Level 7 solidifies the complete end-to-end operational lifecycle of **DENTRACE** (Dental Radiograph OPG Anomaly Detection & Insurance Claim Pre-Authorization Decision-Support System). 

Prior levels established isolated subsystem milestones:
- Level 1: Core REST backend, SQLite/Alembic ORM, file storage & DICOM intake.
- Level 2: ONNX Runtime CPU inference runtime, initial baseline evaluation.
- Level 3: DENTEX abnormal-tooth dataset preparation, topological FDI tooth numbering, IoP association engine.
- Level 4: Deterministic Clinical Evidence Engine, Missing Evidence Detective, local Ollama narrative drafting, local ReportLab PDF claim pack generation.
- Level 5: Curie-Nordic Streamlit Workstation, HTML5 canvas pan/zoom viewer, 32-tooth interactive odontogram.
- Level 6 & 6.1: DENTEX YOLOv8n-seg transfer training (best epoch 25, 0.476 Box mAP50 / 0.446 Mask mAP50), anatomical FDI calibration (76.07% exact accuracy), FP32 vs Dynamic INT8 CPU quantization benchmarks.

**Level 7 achieves complete operational integration**, validating the entire study path from upload through model inference, FDI tooth enumeration, clinician review, structured evidence validation, offline LLM synthesis, and watermarked PDF export without data loss, coordinate drift, or cloud leakage.

---

## 2. Integrated Study Lifecycle

```
[1. Radiograph Intake] (Web Upload / DICOM Sanitization / 1200x600 - 4.02 ms)
          │
          ▼
[2. Quality Preflight] (Aspect ratio, Resolution, Blur score, Content check)
          │
          ▼
[3. Image Preprocessing] (Letterbox 640x640, Aspect Ratio Preservation - 25.09 ms)
          │
          ▼
[4. Multi-Model Vision Inference]
   ├── Head 3A: abychkov RT-DETR (32-Tooth Proposal Localizer)
   ├── Head 3B: Fine-Tuned DENTEX YOLOv8n-seg (4-Class Abnormal Tooth Contours)
   └── Head 3B (Screener): liodon YOLO11n ONNX (Fast 70.73 ms Screener)
          │
          ▼
[5. Anatomical Tooth Enumeration] (`CalibratedFDISolver` - 1.00 ms, 76.07% Exact, 98.63% Quad)
          │
          ▼
[6. Geometry Association] (`ToothPathologyAssociator` IoP ≥ 0.40 - 0.13 ms)
          │
          ▼
[7. SQLite Transaction] (Findings persisted, Stale pending findings cleared idempotently)
          │
          ▼
[8. Clinician Review & Attestation] (Dentist Confirms / Corrects FDI / Rejects with license)
          │
          ▼
[9. Deterministic Clinical Evidence Engine] (Missing Evidence Detective, Contradiction Interception)
          │
          ▼
[10. Local Narrative Drafting]
   ├── Offline Local Ollama (`qwen2.5:3b`, Pydantic JSON schema - ~9.78 s)
   └── Deterministic Clinical Template Fallback (0.95 s, 100% Offline Guaranteed)
          │
          ▼
[11. Clinician Revision Studio] (Editable draft sections, non-overwriting protections)
          │
          ▼
[12. Local ReportLab PDF Export] (Two-pass canvas, "DRAFT — NOT FOR SUBMISSION" watermark, 90.39 ms)
```

---

## 3. End-to-End Pipeline Reliability & State Coherence

| Architectural Attribute | Implementation Mechanism | Verification Result |
|---|---|---|
| **Study ID Consistency** | Globally unique `CASE-[UUID8]` propagated across storage, database, inference runs, audit trail, and PDF | Verified across all test cases |
| **Coordinate Mapping** | `LetterboxMetadata` preserves scale, pad_x, pad_y; coordinates inverted 1:1 back to original image space | Zero coordinate drift between raw image, model input, and canvas overlay |
| **Idempotent Reanalysis** | Pending model proposals cleared (`DELETE FROM findings WHERE study_id=? AND review_status='pending'`) while clinician-confirmed records are preserved | 0 duplicate or orphaned findings upon repeated analysis |
| **Zero Cloud Egress** | All HTTP and Ollama calls bound strictly to `127.0.0.1:8000` and `127.0.0.1:11434`; network sockets non-routable | 100% offline verified |
| **Database Cascades** | Study deletion (`hard_delete=True`) removes radiograph files, preview cache, findings, draft, and audit records cleanly | Zero disk leakage or dangling SQLite rows |

---

## 4. Acceptance Summary

- **Total Integration Scenarios Tested:** 10 / 10 passed (Scenarios A through J)
- **Security & Reliability Scenarios:** 3 / 3 passed (Corrupted uploads, zero egress, PDF watermark)
- **Automated Test Suite Pass Rate:** **118 / 118 tests passed (100% pass rate)**
- **Level 7 Gate Status:** **COMPLETE & VERIFIED**
