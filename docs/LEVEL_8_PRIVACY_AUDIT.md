# DENTRACE Level 8 — Privacy Audit Report

> **DOCUMENT ID:** DOC-PRI-008
> **STATUS:** COMPLETE
> **DATE:** 2026-10-22
> **REGULATORY NOTE:** This is an academic prototype. Privacy safeguards described are engineering measures, NOT formal HIPAA/GDPR compliance certifications.

---

## 1. Data Lifecycle Overview

```
[Upload] → [Storage] → [Database] → [Inference] → [Preview] → [Evidence] → [Ollama] → [PDF] → [Deletion]
```

| Stage | PHI Risk | Mitigation |
|---|---|---|
| Upload endpoint | Filename may contain patient name | `sanitize_filename()` strips all chars except alphanumeric/dash/underscore/dot |
| Storage file | Image may contain DICOM metadata | DICOM anonymization (11 PHI tags → "ANONYMIZED") before save |
| Preview raster | Strips EXIF, saves clean PNG | Preview re-encoded via Pillow (no metadata copy) |
| Database | `patient_anonymous_id` stored as provided | System defaults to `PT-[random hex]` if not supplied |
| Inference input | Preprocessed tensor only (no metadata) | ONNX Runtime processes float32 array, not raw file |
| Audit events | Structured JSON payload | Stack traces stripped; only hashes, status flags logged |
| Ollama request | Study evidence text (anonymized) | `127.0.0.1:11434` — zero external egress |
| PDF export | May include `patient_anonymous_id` and clinical notes | "DRAFT — NOT FOR SUBMISSION" watermark; clinician controls export |
| Hard delete | Files + DB rows removed | `storage_file.unlink()` + SQLite cascade deletes |

---

## 2. DICOM Metadata Anonymization

**Covered Tags (11 attributes):**

| Tag | Action |
|---|---|
| PatientName | → "ANONYMIZED" |
| PatientID | → "ANONYMIZED" |
| PatientBirthDate | → "ANONYMIZED" |
| PatientSex | → "ANONYMIZED" |
| PatientAge | → "ANONYMIZED" |
| PatientAddress | → "ANONYMIZED" |
| InstitutionName | → "ANONYMIZED" |
| ReferringPhysicianName | → "ANONYMIZED" |
| PhysiciansOfRecord | → "ANONYMIZED" |
| PerformingPhysicianName | → "ANONYMIZED" |
| OperatorName | → "ANONYMIZED" |

**Gap:** Additional DICOM tags (e.g., StudyDescription, ScheduledProcedureStepID) are not explicitly anonymized. For research images already de-identified by dataset providers (DENTEX challenge), this is acceptable. For clinical use, a full DICOM de-identification profile (PS3.15 Annex E) would be required.

---

## 3. Storage Naming Convention

| Item | Pattern | PHI Exposure |
|---|---|---|
| Storage file | `{study_id}_{sanitized_filename}` | Sanitized filename retains alphanumeric chars — potential for partial name retention |
| Preview file | `{study_id}_preview.png` | Study ID only — no patient-identifying information |
| Database row key | `CASE-{random 8 hex chars}` | No PHI |
| Anonymous patient ID | `PT-{random 6 hex chars}` (default) | No PHI |

**Residual Risk:** If a user uploads a file named `john_doe_scan.png`, the stored filename becomes `{study_id}_john_doe_scan.png`. The sanitizer preserves alphabetic characters. This is mitigated by:
1. Preview files never contain original filenames
2. Storage directory is local-only (not web-exposed)
3. Hard delete removes the file completely

---

## 4. Logging Analysis

| Logger | Level | PHI Risk | Status |
|---|---|---|---|
| `dentrace.api` (middleware) | INFO: `{method} {path}` only | Path may contain study_id (not PHI) | ✅ Safe |
| `dentrace.api` (errors) | ERROR: `type(exc).__name__` only | Exception type only, not message | ✅ Safe |
| Database migrations | INFO: migration count | No PHI | ✅ Safe |
| File handlers | None | N/A | ✅ No log files |

**Zero file-based logging** is confirmed. Console output is the only log sink.

---

## 5. Temporary File Audit

Verified: No `dentrace*` files created in system temp directory during upload processing. Image bytes are kept in-memory (`io.BytesIO`) throughout the pipeline. No intermediate temp files written.

---

## 6. Ollama Privacy Boundary

The narrative generation prompt sent to Ollama includes:
- Tooth FDI numbers (not PHI)
- Pathology class names (not PHI)  
- AI confidence scores (not PHI)
- Anonymized patient ID (e.g., `PT-3A2F11`)

The prompt does **not** include:
- Patient name
- Date of birth
- Address
- Radiograph image bytes

All Ollama traffic is bound to `127.0.0.1:11434`. Verified via settings and network binding analysis.

---

## 7. PDF Export Privacy

PDFs include:
- `patient_anonymous_id` (user-controlled anonymous code)
- `study_id` (random UUID-derived)
- Findings summary (AI observations with disclaimers)
- Procedure rationale (clinician-authored)

PDFs do **not** include:
- Patient real name (not collected)
- Date of birth
- Insurance member ID (not implemented)
- Radiograph image pixels (image crop not included in current implementation)

**Watermark:** Every PDF carries "DRAFT — NOT FOR SUBMISSION" and "Draft for dentist review. Not a diagnosis."

---

## 8. Data Deletion Verification

Hard delete behavior (tested REL-07):
1. `storage_file.unlink()` — removes raw radiograph
2. `preview_file.unlink()` — removes web preview
3. SQLite cascade: `findings`, `radiographs`, `audit_events`, `model_runs`, `teeth`, `confirmations`, `insurance_drafts` all removed via `CASCADE` foreign key constraint
4. Study row removed

Soft delete (default) archives (`archived=1`) the study row but does not remove files.

---

## 9. Academic Privacy Disclaimer

> **This system applies engineering privacy measures appropriate for an academic prototype working with pre-de-identified research datasets (DENTEX challenge).**
>
> **This is NOT formal HIPAA or GDPR compliance.** Formal compliance requires:
> - A formal HIPAA risk assessment by a qualified privacy officer
> - Business Associate Agreements if any PHI is processed
> - Data Processing Agreement (GDPR Article 28) for EU data
> - Formal DICOM de-identification profile (PS3.15 Annex E Application Level Confidentiality Profile)
>
> The DENTEX training dataset is published under CC BY-NC 4.0 by Grand Challenge and has been de-identified prior to release. This application does not process identifiable patient data in its current academic scope.
