# DENTRACE User Installation & Setup Guide

## 1. System Requirements

### Hardware Requirements
- **Operating System**: Windows 11 x64 (Build 22000+) or Windows 10 x64 (Version 21H2+)
- **Processor**: Intel Core i5 (8th Gen+) or AMD Ryzen 5 (3000 series+)
- **System Memory (RAM)**: 8 GB minimum, 16 GB recommended
- **Graphics Card (GPU)**: NVIDIA GPU with 4 GB VRAM (e.g., GeForce RTX 2050, RTX 3050, GTX 1650). CPU fallback is automatically supported.
- **Disk Space**: At least 1.5 GB free storage on the system drive.

### Software Prerequisites
1. **Python 3.11.9**: Required for running the application environment.
2. **Ollama (Optional, for AI Clinical Narratives)**:
   - Download and install from [ollama.ai](https://ollama.ai)
   - In terminal/PowerShell, pull the clinical model:
     ```powershell
     ollama pull qwen2.5:3b
     ```
   *Note: If Ollama is not installed, DENTRACE automatically uses deterministic template-based narrative drafting.*

---

## 2. Installation Options

### Option A: Portable Desktop Release (Recommended for Clinical Trials)
1. Download `DENTRACE-v0.1.0-win64.zip` from your institution's release portal.
2. Extract the ZIP archive to your preferred directory (e.g., `C:\DENTRACE` or `D:\DENTRACE`).
3. Ensure the folder is writable by your Windows user account.
4. Double-click **`launch_dentrace.bat`** (or right-click `launch_dentrace.ps1` -> *Run with PowerShell*).

### Option B: Windows Installer Setup Wizard
1. Run `DENTRACE-v0.1.0-Setup.exe`.
2. Follow the standard Windows Setup wizard steps.
3. Choose destination directory (defaults to `C:\Program Files\DENTRACE` or `%LOCALAPPDATA%\Programs\DENTRACE`).
4. Select whether to create a Desktop icon and Start Menu shortcut.
5. Click **Install**.
6. Check **"Launch DENTRACE"** and click **Finish**.

---

## 3. First Launch & Clinical Workstation Operation

1. **Preflight Console**:
   When launched, a console window opens displaying system initialization:
   - Mutex lock verification (preventing multiple instances).
   - Port 8000 (FastAPI) and 8501 (Streamlit) availability checks.
   - GPU hardware probing (e.g., detecting NVIDIA GeForce RTX 2050 CUDA provider).
   - Local Ollama `qwen2.5:3b` connection check.
   - SQLite Write-Ahead Logging (WAL) database readiness check.
   - Generation of single-user session security token.
2. **Workstation Launch**:
   Once both services report healthy, your default browser automatically opens to:
   `http://127.0.0.1:8501`
3. **Workflow Quickstart**:
   - **Upload**: Upload a dental panoramic radiograph (OPG) in DICOM (`.dcm`), PNG, or JPG format.
   - **Inspect**: Review the real-time AI segmentation overlay (caries, deep caries, periapical lesions, impacted teeth) and FDI tooth numbering.
   - **Review Odontogram**: Inspect tooth-level observations and adjust tooth assignments if necessary.
   - **Generate Pre-Auth Draft**: Click to draft an insurance justification with CDT/ADA codes.
   - **Export PDF**: Click "Download Pre-Authorization Packet" to generate a tamper-evident clinical PDF with mandatory clinical disclaimers.

---

## 4. Closing the Application

- Simply press **`Ctrl + C`** in the launcher console window, or close the console window.
- The supervisor process traps the termination signal and immediately stops all child processes (Uvicorn backend and Streamlit server), ensuring no background processes remain in memory or hold GPU VRAM.
