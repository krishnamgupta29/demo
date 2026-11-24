# DENTRACE Level 4: Comprehensive QA & Security Test Report

**Document ID:** `DOC-TST-L4-006`  
**Date:** 2026-10-20  
**Test Runner:** `pytest 9.1.1` on Python 3.11.9 (Windows 11 x64)  
**Overall Result:** **78 / 78 TESTS PASSED (100% PASS RATE, 0 FAILURES, 0 REGRESSIONS)**  
**Notice:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. Test Suite Summary Table

| Test Module | Level Focus | Tests Run | Passed | Failed | Skipped | Pass Rate |
|---|---|:---:|:---:|:---:|:---:|:---:|
| `tests/test_environment.py` | Level 1: Python 3.11 & Localhost Binding | 3 | 3 | 0 | 0 | **100%** |
| `tests/test_storage_and_security.py` | Level 1: Sanitization, DICOM, Traversal | 11 | 11 | 0 | 0 | **100%** |
| `tests/test_database.py` | Level 1: SQLite WAL, Alembic, Migrations | 2 | 2 | 0 | 0 | **100%** |
| `tests/test_api_studies.py` | Level 1: Study Intake & REST API | 9 | 9 | 0 | 0 | **100%** |
| `tests/test_dataset_integrity.py` | Level 1: DENTEX ZIP CRC-32 & Polygons | 4 | 4 | 0 | 0 | **100%** |
| `tests/test_model_registry.py` | Level 1: Pretrained Candidate Registry | 6 | 6 | 0 | 0 | **100%** |
| `tests/test_model_inference.py` | Level 2: ONNX Runtime, FDI Proposals | 15 | 15 | 0 | 0 | **100%** |
| `tests/test_segmentation_and_fdi.py` | Level 3: Segmentation & Association | 7 | 7 | 0 | 0 | **100%** |
| `tests/test_level_3_repair.py` | Level 3: Audit Corrections & ONNX Parity | 5 | 5 | 0 | 0 | **100%** |
| `tests/test_level_4_clinical.py` | Level 4: Clinical Intelligence, Ollama, Pre-Auth | 16 | 16 | 0 | 0 | **100%** |
| **TOTAL REPOSITORY SUITE** | **Complete Project Levels 0 through 4** | **78** | **78** | **0** | **0** | **100%** |

---

## 2. Level 4 Specific Test Coverage Breakdown (`tests/test_level_4_clinical.py`)

| Test Name | Verification Focus | Result |
|---|---|:---:|
| `test_clinical_evidence_concept_separation` | Strict Pydantic separation of AI findings, clinician facts, and payer requirements | **PASSED** |
| `test_immutable_disclaimer_tamper_resistance` | Freezing of regulatory disclaimers against tampering or deletion | **PASSED** |
| `test_missing_evidence_detective_endodontic_checklist` | Detective flags pulp vitality, percussion, and IOPA for root canal claims | **PASSED** |
| `test_uncertain_tooth_blocks_preflight` | Flagged uncertain FDI numbers block export with `BLOCKED_BY_UNCONFIRMED_TOOTH` | **PASSED** |
| `test_contradiction_vital_tooth_endodontics` | Endodontic therapy on responsive vital tooth without caries raises contradiction | **PASSED** |
| `test_contradiction_rejected_finding_procedure` | Procedure requested for explicitly rejected finding triggers contradiction block | **PASSED** |
| `test_cdt_catalog_versioning_and_metadata` | ADA CDT catalog includes version `2026-Academic-Demo` and licensing notices | **PASSED** |
| `test_cdt_code_consistency_validation` | Validates molar vs premolar endodontic anatomy and impaction surgery consistency | **PASSED** |
| `test_faithfulness_checker_detects_hallucinated_tooth` | Statements citing ungrounded tooth numbers (e.g. Tooth #25) are flagged | **PASSED** |
| `test_faithfulness_checker_enforces_uncertainty_for_ai_findings` | Statements presenting unconfirmed AI findings as definite facts are flagged | **PASSED** |
| `test_prompt_injection_boundary_defense` | Prompt injection payloads in clinical notes are isolated in untrusted tags | **PASSED** |
| `test_deterministic_narrative_generator_fallback` | Deterministic template generates all 10 clinical sections with full citations | **PASSED** |
| `test_local_pdf_generation_and_disclaimer_stamping` | ReportLab produces valid PDF ($\ge 5\text{ KB}$) with disclaimers and signature line | **PASSED** |
| `test_api_clinical_endpoints` | Full REST integration: evidence retrieval, review, exam, procedure, readiness, draft, PDF | **PASSED** |
| `test_real_local_ollama_qwen_inference` | Real forward pass against local Ollama daemon (`127.0.0.1:11434`) using `qwen2.5:3b` | **PASSED** |
| `test_zero_cloud_egress_and_localhost_only` | Verified zero external cloud endpoints; strictly bound to loopback | **PASSED** |

---

## 3. Separation of Synthetic vs. Real Testing

- **Synthetic Fixtures (`conftest.py` & synthetic functions):** Used for reproducible unit tests, regression suites, edge case checks, boundary violation tests, and adversarial prompt injection checks without nondeterministic network or LLM latency.
- **Real Local Model Tests (`test_real_local_ollama_qwen_inference` & `benchmark_level_4_clinical.py`):** Directly invoke the live local Ollama daemon at `http://127.0.0.1:11434` with `qwen2.5:3b` weights, measuring real forward latency, real JSON parsing, and real token generation.

---

## 4. Execution Commands

To execute the entire test suite:
```powershell
.venv\Scripts\pytest.exe -v
```

To execute Level 4 tests exclusively:
```powershell
.venv\Scripts\pytest.exe tests/test_level_4_clinical.py -v
```
