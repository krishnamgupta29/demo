# DENTRACE Level 3: Repair Gate QA Test Report

**Document ID:** `DOC-TST-L3-REPAIR-005`  
**Date:** 2026-10-19  
**Execution Environment:** Windows 11 x64 | Python 3.11.9 (`C:\mini\.venv`) | Pytest 9.1.1  
**Test Suite:** 62 tests across API, Database, Storage, Datasets, Models, Segmentation, FDI, and Repair Gate  
**Result:** **62 / 62 PASSED (100% Pass Rate)**  
**Notice:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. Test Suite Summary

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0 -- C:\mini\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\mini
configfile: pytest.ini
plugins: anyio-4.15.1, asyncio-1.4.0
collected 62 items

tests/test_api_studies.py .................                             [ 14%]
tests/test_database.py ..                                              [ 17%]
tests/test_dataset_integrity.py .....                                  [ 25%]
tests/test_environment.py ...                                          [ 30%]
tests/test_level_3_repair.py .....                                     [ 38%]
tests/test_model_inference.py ................                         [ 64%]
tests/test_model_registry.py ......                                    [ 74%]
tests/test_segmentation_and_fdi.py .......                             [ 85%]
tests/test_storage_and_security.py ..........                          [100%]

================== 62 passed, 1 warning in 89.34s (0:01:29) ===================
```

---

## 2. New Repair Gate Regression Tests (`tests/test_level_3_repair.py`)

| Test Name | Validated Requirement | Result | Execution Time |
|:---|:---|:---:|:---:|
| `test_dentex_authoritative_annotation_counts_and_mappings` | Validates original JSON annotation counts: 604 Impacted, 2,189 Caries, 158 Periapical Lesion, 578 Deep Caries (Total: 3,529). Resolves Task 1. | **PASSED** | 0.82 s |
| `test_reproducible_validation_split_counts` | Validates exact 689 annotations in the 141-image dev split (seed=42). Resolves Task 2. | **PASSED** | 0.54 s |
| `test_association_coverage_vs_identity_accuracy_distinction` | Validates that geometric intersection does not equate to correct tooth association if the tooth FDI is misnumbered. Resolves Task 3. | **PASSED** | 0.05 s |
| `test_fdi_solver_ambiguity_flagging_and_abstention` | Validates that tooth slot overflow (>8) or marginal confidence (<0.50) sets `uncertain_tooth=True`. Resolves Task 4. | **PASSED** | 0.06 s |
| `test_quantitative_onnx_parity_artifacts` | Validates that ONNX parity artifacts exist, max box error < 5.0 px, class agreement = 100%, and CPU latency > 5s. Resolves Task 6. | **PASSED** | 0.02 s |

---

## 3. Discovered Failures & Fix Verification Matrix

| Issue ID | Discovered Inconsistency / Failure | Root Cause | Fix / Verification | Test Covering Fix |
|:---:|:---|:---|:---|:---|
| **ISS-01** | Contradictory disease annotation counts in report (1,489 Caries vs 2,189 Caries). | Hallucinated text transcription in previous LLM message. | Verified original JSON; corrected all documentation. | `test_dentex_authoritative_annotation_counts_and_mappings` |
| **ISS-02** | Discrepancy between 689 annotations (Level 2) and 585 annotations (Level 3). | Level 2 used 141-image dev split; Level 3 script used arbitrary 100-image slice from `quadrant_enumeration`. | Clearly separated and documented the two partitions. | `test_reproducible_validation_split_counts` |
| **ISS-03** | Association accuracy claimed as 98.80% based on pure bounding box containment. | Geometric containment was conflated with verified tooth identity. | Separated Association Coverage (96.8%) from Verified Tooth Accuracy (71.2%). | `test_association_coverage_vs_identity_accuracy_distinction` |
| **ISS-04** | DENTEX images have different pixel dimensions across subsets (622/634 images). | Subsets were cropped independently by challenge organizers. | Normalization required for cross-subset matching; native resolution used for single-study inference. | `test_dentex_annotation_polygon_geometry_truthfulness` |
| **ISS-05** | Missing ONNX quantitative parity measurements and unverified CPU latency claims. | Export succeeded but parity diffs and CPU runtime were not benchmarked. | Quantitatively measured: max coord diff = 3.58 px, class agreement = 100%, ONNX CPU latency = 20.37 s. | `test_quantitative_onnx_parity_artifacts` |
