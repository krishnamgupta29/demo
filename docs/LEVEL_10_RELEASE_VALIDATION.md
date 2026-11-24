# DENTRACE Level 10: Windows Desktop Release Validation & Deployment Audit

> **AUDIT AUTHORITY:** Windows Release Validation & Deployment Lead  
> **DATE:** October 22, 2026  
> **TARGET ARTIFACT:** `C:\mini\dist\DENTRACE-v0.1.0-win64.zip` (446.59 MB)  
> **DIGEST (SHA-256):** `6670007bfc86fe9deeab1b27123634377953735d9158a2d352c42d8265d3d475`

---

## 1. Release Package Self-Containment Audit

To uphold scientific honesty, the release bundle is audited across four distinct dependency tiers:

### Tier A: Fully Included in Release Archive (`DENTRACE-v0.1.0-win64.zip`)
- **Application Logic**:
  - FastAPI backend (`backend/`)
  - Streamlit clinical workstation (`frontend/`)
  - Deterministic clinical rules & CDT coding (`backend/clinical/`)
  - Ingestion & DICOM anonymizer (`backend/storage/`)
- **Neural Vision Models**:
  - `models/checkpoints/dentex_yolov8n_seg_best.onnx` (13.16 MB)
  - `models/checkpoints/dentex_yolov8n_seg_best_int8.onnx` (3.64 MB)
  - `models/checkpoints/dental_fdi.onnx` (124.70 MB)
  - `models/checkpoints/8024.onnx` (273.91 MB)
  - `models/checkpoints/best.onnx` (10.11 MB)
  - Associated INT8 checkpoints
- **Configuration & Schemas**:
  - `config/model_manifest.json`
  - `config/cdt_demo.json`
  - `config/class_mapping.json`
  - `config/settings.json`
- **Database Infrastructure**:
  - `alembic/` schema migrations and `alembic.ini`
- **Launchers & Supervisors**:
  - `launch_dentrace.bat` (Windows Batch launcher)
  - `launch_dentrace.ps1` (PowerShell supervisor)
  - `scripts/launcher/launcher.py` (Process lifecycle manager)
- **Integrity Manifests**:
  - `SHA256SUMS.txt` (Per-file cryptographic hashes)

### Tier B: Requires Separate Installation on Target Host
- **Python Runtime**: Requires Python 3.11.9 (64-bit) installed on the Windows host. Python binaries are **not** embedded in the ZIP.
- **Python Packages**: The release includes pinned `requirements.txt`. Host environment must have required wheels pre-installed (`fastapi`, `uvicorn`, `streamlit`, `onnxruntime`, `torch`, `ultralytics`, `reportlab`, `pydicom`, `pydantic`, `sqlalchemy`, etc.).
- **Ollama Engine**: Required for natural-language clinical narrative synthesis (downloaded from ollama.ai).

### Tier C: Components Requiring User-Supplied Licensed Weights
- **Ollama Language Model**: `qwen2.5:3b` model weights must be pulled via `ollama pull qwen2.5:3b` or transferred via local GGUF artifact.

### Tier D: Optional Components with Graceful Fallback
- **Ollama Natural-Language Service**: If Ollama daemon is offline or uninstalled, DENTRACE automatically reverts to `DeterministicNarrativeGenerator`. Radiograph segmentation, FDI tooth numbering, and pre-auth CDT code assignment operate with 100% functionality.
- **NVIDIA CUDA GPU Hardware**: If NVIDIA RTX 2050 (or compatible GPU) is absent, ONNX Runtime automatically falls back to `CPUExecutionProvider`.

> [!IMPORTANT]
> **CRITICAL RELEASE INTEGRITY DISCLOSURE**:  
> An offline runtime operating with previously cached Python environment dependencies is **fundamentally different** from an all-inclusive installer on a clean, vanilla computer without Python. True clean-machine deployment requires providing a pre-built embedded Python bundle or running `pip install -r requirements.txt` prior to disconnecting network access.

---

## 2. Inno Setup Compiler (`iscc.exe`) Status

- **Host Inspection**: Probing for `ISCC.exe` on the host machine returned: `Command not found`.
- **Script Status**: `scripts/installer/dentrace_setup.iss` was generated with valid Inno Setup directives, configured for x64 architecture, desktop shortcuts, and `%LOCALAPPDATA%\DENTRACE\data` storage isolation.
- **Audit Verdict**: **Installer compilation remains PENDING.** The official release deliverable is the verified portable ZIP package `dist/DENTRACE-v0.1.0-win64.zip`. No claims of a compiled `DENTRACE-v0.1.0-Setup.exe` binary are made.

---

## 3. Real Portable Package Installation Test

### 3.1 Test Methodology
1. Extracted `C:\mini\dist\DENTRACE-v0.1.0-win64.zip` into an isolated directory:
   `C:\dentrace_isolated_test\DENTRACE-v0.1.0-win64\`
2. Configured isolated runtime environment pointing to a temporary test database:
   `DENTRACE_DATA_DIR=C:\dentrace_isolated_test\temp_data`
3. Executed end-to-end clinical workflow:
   - Supervised launch via `launcher.py`
   - Single-instance lock creation
   - Port 8000 and 8501 binding
   - Model loading (`dental_fdi.onnx`, `dentex_yolov8n_seg_best.onnx`)
   - DICOM upload & 18-tag anonymization
   - Instance segmentation and FDI tooth assignment
   - Pre-auth claim narrative generation
   - ReportLab PDF export
   - Application shutdown and restart persistence check

### 3.2 Environmental Boundary Limitation
- Testing was performed in an isolated directory structure on the Windows 11 development host.
- A clean, isolated Virtual Machine (VM) or separate physical computer was not provisioned in this environment.
- Python packages and CUDA drivers from the host machine were utilized by the portable launcher.
