# DENTRACE Level 6.1 — Test Report

**Generated:** 2026-10-21 21:34
**Status:** PASS

## Summary

| Result | Count |
|--------|-------|
| ✅ Passed | 0 |
| ❌ Failed | 0 |
| ⚠️ Errors | 0 |

## Test Output

```
============================= test session starts =============================
collected 105 items

tests\test_api_studies.py .........                                      [  8%]
tests\test_database.py ..                                                [ 10%]
tests\test_dataset_integrity.py ....                                     [ 14%]
tests\test_environment.py ...                                            [ 17%]
tests\test_frontend_integration.py .............                         [ 29%]
tests\test_level_3_repair.py .....                                       [ 34%]
tests\test_level_4_clinical.py ................                          [ 49%]
tests\test_level_6_optimization.py ..............                        [ 62%]
tests\test_model_inference.py ................                           [ 78%]
tests\test_model_registry.py ......                                      [ 83%]
tests\test_segmentation_and_fdi.py .......                               [ 90%]
tests\test_storage_and_security.py ..........                            [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\mini\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 105 passed, 1 warning in 874.15s (0:14:34) ==================

```
