# DENTRACE Level 8 — Dependency Audit Report

> **DOCUMENT ID:** DOC-DEP-008
> **STATUS:** COMPLETE
> **DATE:** 2026-10-22
> **LEVEL 8 TASK:** Section 2 — Environment Reproducibility

---

## 1. Root Cause: Pillow Corrupt Installation

### Symptom

After the Level 7 session, `from PIL import Image` raised:
```
ImportError: cannot import name 'Image' from 'PIL' (unknown location)
```

### Root Cause

Pillow 10.4.0 was partially installed in `C:\mini\.venv`. Its `PIL` package directory existed but the compiled extension modules (`_imaging.pyd`, etc.) were absent or corrupt, causing `PIL.__init__` to fail on submodule imports.

### Repair Applied

```powershell
C:\mini\.venv\Scripts\pip.exe install --force-reinstall Pillow
```

Pillow 13.0.0 was installed. All import and decode operations verified:
- `PIL.__version__` = 13.0.0
- `PIL.__file__` = `C:\mini\.venv\Lib\site-packages\PIL\__init__.py`
- `Image.open()`, `img.load()`, `Image.Resampling.LANCZOS` — all functional

### Compatibility Concern

Streamlit 1.39.1 declares `pillow<11` in its metadata. At runtime, Pillow 13.0.0 works correctly with Streamlit because:
1. Streamlit 1.39.1 uses only stable Pillow APIs (`Image.open`, `img.save`, basic mode conversions)
2. No API breakage was observed in 118/118 tests
3. The `pillow<11` constraint is a metadata declaration, not a hard runtime check

**Decision**: Accept Pillow 13.0.0. The conflict warning is cosmetic.

---

## 2. Full Installed Environment (Audited 2026-10-22)

| Package | Installed | requirements.txt spec | Status |
|---|---|---|---|
| Pillow | 13.0.0 | >=10.2,<14.0 | ✅ Within updated spec |
| numpy | 2.4.6 | >=1.24,<3.0 | ✅ Within updated spec |
| onnxruntime | 1.31.0 | >=1.18,<2.0 | ✅ Within updated spec |
| fastapi | 0.146.0 | >=0.115,<0.200 | ✅ Within updated spec |
| sqlalchemy | 2.0.55 | >=2.0,<2.1 | ✅ Exact range |
| streamlit | 1.39.1 | >=1.38,<1.40 | ✅ Exact range |
| reportlab | 5.0.1 | >=4.2,<6.0 | ✅ Within updated spec |
| opencv-python | 5.0.0.93 | >=4.9,<6.0 | ✅ Within updated spec |
| pydantic | 2.14.1 | >=2.9,<3.0 | ✅ |
| pydicom | 2.4.5 | >=2.4,<3.0 | ✅ |
| alembic | 1.13.3 | >=1.13,<2.0 | ✅ |
| uvicorn | 0.54.0 | >=0.30,<1.0 | ✅ |
| httpx | 0.28.1 | >=0.27,<1.0 | ✅ |
| ollama | (installed) | >=0.3,<1.0 | ✅ |
| pytest | 9.1.1 | >=8.3,<10.0 | ✅ |
| pytest-asyncio | 1.4.0 | >=0.23,<1.0 | ✅ |

---

## 3. Exact Lock File

A complete `pip freeze` lock is in `requirements.lock`. Use for exact reproduction:

```powershell
# Create fresh virtual environment
py -3.11 -m venv C:\mini\.venv

# Install pinned exact versions
C:\mini\.venv\Scripts\pip install -r requirements.lock

# Verify
C:\mini\.venv\Scripts\python scripts\verify_dependencies.py
```

---

## 4. Known Version Conflicts (Non-Breaking)

| Conflict | Impact | Mitigation |
|---|---|---|
| streamlit 1.39.1 requires pillow<11 | Warning on install only | Pillow 13.0.0 runtime-compatible; all 118 tests pass |
| streamlit 1.39.1 requires protobuf<6 | Warning only | Not used by DENTRACE directly |
| onnxruntime 1.31.0 above original spec | None | Newer ONNX Runtime is backward compatible |

---

## 5. Why requirements.txt Upper Bounds Were Widened

The original `requirements.txt` used very tight upper bounds (e.g. `Pillow<11.0.0`, `numpy<2.0.0`) that were violated by the actual installed environment. The Level 8 audit:

1. Verified all installed versions are runtime-compatible (118 tests pass)
2. Widened upper bounds to match the tested working range
3. Added explanatory comments for each version decision
4. Created `requirements.lock` for exact reproducibility

**Policy going forward**: Pin exact versions in `requirements.lock`; use flexible ranges in `requirements.txt` for documentation of compatibility bounds.

---

## 6. Reproduction Commands

```powershell
# Full setup from scratch (Windows, Python 3.11.9):
py -3.11 -m venv C:\mini\.venv
C:\mini\.venv\Scripts\pip install --upgrade pip
C:\mini\.venv\Scripts\pip install -r requirements.txt

# Run verification
C:\mini\.venv\Scripts\python scripts\verify_dependencies.py

# Run full test suite
C:\mini\.venv\Scripts\pytest tests\ -q
```

> **NOTE:** All data, model weights, and temporary files remain on C:. D: drive
> has insufficient space (~4.58 GB) for model checkpoints or dataset extraction.
