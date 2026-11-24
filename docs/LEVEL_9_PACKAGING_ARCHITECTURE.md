# DENTRACE Level 9: Windows Desktop Packaging & Architecture

## 1. Executive Summary & Design Principles

DENTRACE is engineered as an offline-first, local-first clinical decision-support workstation for dental panoramic radiograph (OPG) anomaly detection, anatomical FDI tooth assignment, and insurance claim pre-authorization drafting.

Level 9 transitions DENTRACE from a multi-terminal developer environment into a robust, unified, self-contained Windows desktop package targeting **Windows 11 x64**.

### Core Packaging Directives
1. **Zero Cloud Egress**: Zero network calls outside `127.0.0.1`. Strict offline functionality.
2. **Single-Instance Enforcement**: Mutual exclusion prevents conflicting SQLite locks, overlapping port bindings (8000/8501), and GPU VRAM resource exhaustion.
3. **Clean Process Lifecycle**: Robust process supervision with zero orphaned background processes upon termination.
4. **Separation of Code and Data**: Application binaries and read-only model assets remain strictly separated from user-writable clinical databases and DICOM caches (`%LOCALAPPDATA%\DENTRACE\data`).
5. **Local Access Security**: Ephemeral token authorization (`X-DENTRACE-TOKEN`) prevents unauthenticated local processes or browser tabs from executing uninspected clinical endpoints.
6. **Regulatory Compliance Notice**: *"Draft for dentist review. Not a diagnosis."* Hardcoded into launcher banners, application headers, UI footers, and PDF exports.

---

## 2. Desktop Packaging Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                 WINDOWS 11 x64                                  |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                  LAUNCHER LAYER (Supervisor Process)                    |   |
|   |   - launch_dentrace.bat / launch_dentrace.ps1                           |   |
|   |   - scripts/launcher/launcher.py                                        |   |
|   |   * Single-instance lock (.dentrace.lock)                               |   |
|   |   * Port availability checks (8000, 8501)                               |   |
|   |   * Hardware detection (NVIDIA RTX 2050 CUDA vs CPU fallback)           |   |
|   |   * Local LLM service probe (Ollama 127.0.0.1:11434 qwen2.5:3b)         |   |
|   |   * SQLite WAL & schema preflight check                                 |   |
|   |   * Ephemeral session token generation (X-DENTRACE-TOKEN)               |   |
|   +-------------------+---------------------------------+-------------------+   |
|                       |                                 |                       |
|        Forks & Monitors Child 1                  Forks & Monitors Child 2       |
|                       |                                 |                       |
|   +-------------------v-----------------+   +-----------v-------------------+   |
|   |      FastAPI Backend (Uvicorn)      |   |  Streamlit Clinical Interface |   |
|   |      127.0.0.1:8000                 |   |  127.0.0.1:8501               |   |
|   |                                     |   |                               |   |
|   | - Token Auth Middleware             |   | - User Clinical Workstation   |   |
|   | - DICOM Ingestion (Anonymized)      |   | - Interactive Odontogram      |   |
|   | - YOLOv8n-Seg (DENTEX weights)      |   | - Real-time Polygon Overlay   |   |
|   | - Pretrained FDI Numbering          |   | - Pre-auth Draft Editor       |   |
|   | - Deterministic Clinical Rules      |   | - Local PDF Export Trigger    |   |
|   | - Ollama Client (Pydantic Schema)   |   | - Session Token Injection     |   |
|   +-------------------+-----------------+   +-----------+-------------------+   |
|                       |                                 |                       |
|                       +----------------+----------------+                       |
|                                        |                                        |
|   +------------------------------------v------------------------------------+   |
|   |                         STORAGE & DATA LAYER                            |   |
|   |                                                                         |   |
|   |   Program / Release Root (Read-Only):                                   |   |
|   |   - models/ (YOLOv8n-Seg, FDI ONNX, sha256 verified)                    |   |
|   |   - config/ (model_manifest.json, default configurations)               |   |
|   |                                                                         |   |
|   |   User-Writable Data Directory (%LOCALAPPDATA%\DENTRACE\data):          |   |
|   |   - dentrace.db (SQLite with Write-Ahead Logging WAL)                   |   |
|   |   - dicom_store/ (Anonymized studies & extracted diagnostic frames)     |   |
|   |   - exports/ (Generated pre-authorization clinical reports)             |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```

---

## 3. Component Breakdown & Runtime Management

### 3.1 Single-Instance Control
To prevent concurrent instances corrupting SQLite database state or binding conflicts on ports 8000 and 8501:
- A lock file `.dentrace.lock` is created in the runtime data directory.
- The lock file records the launcher's Process ID (PID) and timestamp.
- On startup, the launcher inspects the lock. If an active process holds the lock, launch is aborted with a user-friendly diagnostic alert.
- Upon normal shutdown, interrupt (Ctrl+C), or unexpected termination, the lock file is automatically released.

### 3.2 Preflight Validation Pipeline
Before initiating application services, the launcher performs 5 automated health gates:
1. **Port Verification**: Confirms ports 8000 and 8501 are not in use.
2. **Database Schema & Migration**: Runs SQLite connection check, enables Write-Ahead Logging (`PRAGMA journal_mode=WAL`), and verifies table integrity.
3. **Model Weights Verification**: Validates presence and SHA-256 integrity of critical model files against `config/model_manifest.json`:
   - `models/dentex_yolov8n_seg_best.pt`
   - `models/dentex_yolov8n_seg_best.onnx`
   - `models/fdi_detector_best.onnx`
4. **Hardware Acceleration Probe**:
   - Checks for NVIDIA CUDA runtime and RTX 2050 availability via PyTorch `torch.cuda.is_available()`.
   - Verifies ONNX Runtime execution provider hierarchy (`CUDAExecutionProvider` prioritized, falling back gracefully to `CPUExecutionProvider`).
5. **Local LLM Health Check**:
   - Pings Ollama at `http://127.0.0.1:11434/api/tags`.
   - Checks presence of `qwen2.5:3b`.
   - If Ollama is offline, reports advisory warning that clinical narrative generation will operate in deterministic template-fallback mode without halting radiological analysis.

### 3.3 Ephemeral Security Token Injection
To eliminate unauthenticated local access:
- The launcher generates a high-entropy cryptographically secure random session token (`secrets.token_urlsafe(32)`).
- The token is passed to the FastAPI backend via the environment variable `DENTRACE_LOCAL_TOKEN`.
- The FastAPI middleware validates `X-DENTRACE-TOKEN` on all mutative and analytical endpoints.
- The Streamlit frontend client (`api_client.py`) automatically embeds the token in all HTTP requests.

### 3.4 Process Supervision and Zero-Orphan Cleanup
Windows processes spawned by background wrappers frequently become orphaned when terminal windows or wrappers are closed. DENTRACE resolves this via:
- Spawning child processes using Python's `subprocess.Popen` with dedicated process group creation (`subprocess.CREATE_NEW_PROCESS_GROUP`).
- Trapping `SIGINT`, `SIGTERM`, and Windows break events.
- An `atexit` registered supervisor function that iterates active child PIDs and executes clean termination, followed by forceful process tree termination (`taskkill /F /T /PID <pid>`) if a process does not exit within 3 seconds.
- Guarantees 0 background Python or Uvicorn instances left consuming RAM or GPU VRAM.

---

## 4. Storage & Path Isolation

In compliance with Windows application development standards:
- **Application Binaries (`INSTALLDIR`)**: Read-only directory containing Python virtual environment, application source code, and verified neural model weights.
- **Application Data (`%LOCALAPPDATA%\DENTRACE\data`)**:
  - `dentrace.db`: Relational metadata, audit logs, tooth observations, pre-auth claims.
  - `dicom_store/`: Anonymized DICOM files and preprocessed PNG arrays.
  - `exports/`: Generated clinical pre-authorization claim PDF packages.
  - `.dentrace.lock`: Runtime single-instance mutex lock.
- **Fallback Resolution**: If `%LOCALAPPDATA%` is inaccessible, the system seamlessly falls back to `<app_root>\data`.
