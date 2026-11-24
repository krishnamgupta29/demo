# DENTRACE User Troubleshooting & Diagnostic Guide

## 1. Quick Diagnostic Checklist

If you encounter issues launching or running DENTRACE, follow this sequential diagnostic checklist:

1. **Check the Launcher Console**: Review error messages printed in the terminal window before it closes.
2. **Verify Python Environment**: Ensure Python 3.11.9 is active (`python --version`).
3. **Verify Ports**: Check if ports 8000 or 8501 are held by lingering processes.
4. **Check Lock File**: Inspect if an old `.dentrace.lock` file exists in `%LOCALAPPDATA%\DENTRACE\data`.

---

## 2. Common Issues & Solutions

### Issue 1: "Port 8000 or 8501 is already in use"
- **Symptom**: The launcher halts during preflight with:
  `ERROR: Port 8000 (Backend) is currently occupied by another process.`
- **Cause**: A prior instance did not shut down cleanly, or another local web service is using the port.
- **Resolution**:
  1. Open Windows PowerShell as Administrator.
  2. Find the Process ID (PID) holding the port:
     ```powershell
     netstat -ano | findstr :8000
     netstat -ano | findstr :8501
     ```
  3. Terminate the blocking process (replace `<PID>` with the actual process ID):
     ```powershell
     taskkill /F /PID <PID>
     ```
  4. Re-run `launch_dentrace.bat`.

---

### Issue 2: "Another instance of DENTRACE is already running"
- **Symptom**: Launcher alerts:
  `ERROR: DENTRACE is already running under PID [xxxx]. Only one instance permitted.`
- **Cause**: DENTRACE enforces single-instance mutual exclusion via `.dentrace.lock`. If the computer crashed or was forcefully rebooted while DENTRACE was open, a stale lock file may remain.
- **Resolution**:
  1. Open Windows Task Manager and verify no `python.exe` process with the reported PID is active.
  2. If no process is running, safely delete the stale lock file:
     - Default location: `%LOCALAPPDATA%\DENTRACE\data\.dentrace.lock`
     - Fallback location: `C:\mini\data\.dentrace.lock`
  3. Re-run `launch_dentrace.bat`.

---

### Issue 3: "Ollama not reachable at http://127.0.0.1:11434"
- **Symptom**: Launcher displays an advisory notice:
  `[ADVISORY] Ollama service not detected at 127.0.0.1:11434. Running in template fallback mode.`
- **Explanation**: Dental image segmentation and FDI tooth numbering continue to function with 100% precision. Only the natural-language pre-authorization narrative switches to a deterministic clinical template.
- **Resolution**:
  1. Ensure Ollama is running in the Windows system tray.
  2. If stopped, start it in PowerShell:
     ```powershell
     ollama serve
     ```
  3. Verify the model is pulled:
     ```powershell
     ollama list
     # If qwen2.5:3b is missing:
     ollama pull qwen2.5:3b
     ```

---

### Issue 4: "GPU Acceleration Not Detected / Slow Inference"
- **Symptom**: Scans take 1.5 - 2.5 seconds to process instead of sub-second inference.
- **Cause**: PyTorch / ONNX Runtime defaulted to `CPUExecutionProvider` because NVIDIA CUDA drivers were not detected.
- **Resolution**:
  1. Verify GPU driver status in PowerShell:
     ```powershell
     nvidia-smi
     ```
  2. If `nvidia-smi` works, verify PyTorch CUDA binding:
     ```powershell
     python -c "import torch; print('CUDA available:', torch.cuda.is_available(), 'Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
     ```
  3. Update NVIDIA drivers to the latest Game Ready or Studio Driver supporting CUDA 12.x.

---

### Issue 5: "401 Unauthorized: Missing or Invalid Token"
- **Symptom**: Calling API endpoints directly or via custom scripts yields `{"detail": "Unauthorized: Missing or invalid X-DENTRACE-TOKEN"}`.
- **Cause**: Security hardening restricts API mutations to authenticated local sessions.
- **Resolution**:
  - Always access the system through the Streamlit graphical workstation (`http://127.0.0.1:8501`), which automatically attaches the session token.
  - If using custom scripts or cURL, pass the header `-H "X-DENTRACE-TOKEN: <token>"` using the token printed in the launcher console.
