# DENTRACE Level 9: Installer Build & Distribution Specification

## 1. Overview & Build Automation

The DENTRACE release engineering pipeline automates the generation of standalone Windows 11 x64 distribution packages. The release pipeline produces two deliverables:
1. **Portable Desktop Release (`DENTRACE-v0.1.0-win64.zip`)**: A self-contained directory with one-click batch (`launch_dentrace.bat`) and PowerShell (`launch_dentrace.ps1`) launchers.
2. **Inno Setup Windows Installer (`dentrace_setup.iss`)**: A script generating an enterprise-standard Windows installer (`DENTRACE-v0.1.0-Setup.exe`) that configures Start Menu shortcuts, desktop icons, and standard Windows uninstallation.

---

## 2. Release Packaging Script (`scripts/build_release.py`)

The release packaging workflow is triggered via:
```powershell
python scripts/build_release.py --version 0.1.0
```

### Staging Rules and Clean Isolation
The script stages application assets from the source tree into `dist/DENTRACE-v0.1.0-win64` applying strict exclusion filters:
- **Excluded Patterns**:
  - `__pycache__`, `*.pyc`, `*.pyo`, `*.pyd`
  - `.pytest_cache`, `.coverage`, `tests/`
  - `.git`, `.github`, `.gitignore`, `.gitattributes`
  - `data/` (runtime patient databases, DICOM stores, and lock files are strictly isolated from the install payload)
  - `datasets/` (raw training datasets like DENTEX and Tufts are excluded to conserve distribution size)
  - `.env`, temporary logs, and developer IDE files
- **Included Assets**:
  - `backend/`: FastAPI application, inference orchestrator, rule engines, DICOM parsers.
  - `frontend/`: Streamlit workstation, interactive odontogram, evidence viewers.
  - `models/`: DENTEX YOLOv8n-Seg checkpoint (`.pt`), quantized ONNX model (`.onnx`), and FDI detector (`.onnx`).
  - `config/`: Application settings, clinical ontology, and `model_manifest.json`.
  - `scripts/launcher/`: Native process supervisor and preflight checker.
  - Launch scripts: `launch_dentrace.bat` and `launch_dentrace.ps1`.
  - Documentation: Clinical safety guidelines, user manual, and architectural specifications.

---

## 3. Cryptographic Verification (`SHA256SUMS.txt`)

Every packaged release generates a cryptographic manifest containing SHA-256 digests for all distributed files.

### Verification Command
Administrators and clinical IT reviewers can verify package integrity prior to deployment:
```powershell
# PowerShell verification
Get-FileHash -Algorithm SHA256 dist\DENTRACE-v0.1.0-win64.zip
```
The resulting checksum matches the entry recorded in `dist/SHA256SUMS.txt`.

---

## 4. Inno Setup Compiler Configuration (`scripts/installer/dentrace_setup.iss`)

The Inno Setup script compiles a Windows installer targeting 64-bit Windows architectures:

### Key Installer Attributes:
- **Application Name**: DENTRACE Dental Decision-Support Workstation
- **Version**: 0.1.0
- **Publisher**: Academic Decision-Support System / Clinical Engineering
- **Default Installation Path**: `{autopf}\DENTRACE` (Program Files 64-bit)
- **Data Path**: `{localappdata}\DENTRACE\data` (ensuring non-administrator execution without permission errors)
- **Privileges Required**: `lowest` (standard user installable) or `admin` (system-wide deployment)
- **Shortcuts Created**:
  - Desktop Icon: "DENTRACE Dental Workstation" pointing to `launch_dentrace.bat`
  - Start Menu Folder: "DENTRACE" containing application launch and uninstaller links
- **Post-Install Action**: Optional checkbox to launch DENTRACE immediately upon setup completion.

---

## 5. Build Artifact Audit

| Deliverable | Path | Approx. Size | Status |
|:---|:---|:---:|:---:|
| Staging Directory | `dist/DENTRACE-v0.1.0-win64/` | ~450 MB | Verified |
| Compressed Release Archive | `dist/DENTRACE-v0.1.0-win64.zip` | ~446 MB | Verified |
| Cryptographic Manifest | `dist/SHA256SUMS.txt` | 2 KB | Verified |
| Inno Setup Script | `scripts/installer/dentrace_setup.iss` | 3 KB | Verified |
| Production Launcher | `launch_dentrace.bat` | 1 KB | Verified |
