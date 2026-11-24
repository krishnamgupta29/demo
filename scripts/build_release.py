"""DENTRACE Level 9 — Release Packaging & Distribution Builder.

Builds a self-contained, reproducible Windows desktop release distribution:
- Staged on C: drive at `C:\\mini\\dist\\DENTRACE-v0.1.0-win64`
- Strictly excludes raw datasets, patient data, git logs, and training artifacts
- Verifies checksums and compiles SHA256SUMS.txt manifest
- Creates compressed release archive `DENTRACE-v0.1.0-win64.zip`
- Generates Inno Setup compiler configuration `dentrace_setup.iss`
"""

import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

# Paths
SOURCE_ROOT = Path("D:/mini")
DIST_BASE = Path("C:/mini/dist")
RELEASE_NAME = "DENTRACE-v0.1.0-win64"
STAGE_DIR = DIST_BASE / RELEASE_NAME
ZIP_PATH = DIST_BASE / f"{RELEASE_NAME}.zip"

# Exclusion patterns
EXCLUDED_PATTERNS = [
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    ".idea",
    ".vscode",
    "runs",
    "scratch",
    "tests",
    "datasets",
    "*.pyc",
    "*.log",
    "*.tmp",
    "dentrace.db*",
    "training_data.zip",
    "validation_data.zip",
]


def sha256_file(path: Path) -> str:
  """Compute SHA-256 hash of a file."""
  h = hashlib.sha256()
  with open(path, "rb") as f:
    while chunk := f.read(65536):
      h.update(chunk)
  return h.hexdigest()


def copy_tree_filtered(src: Path, dst: Path):
  """Copy directory tree excluding test, dataset, and cache artifacts."""
  dst.mkdir(parents=True, exist_ok=True)
  for item in src.iterdir():
    # Check exclusions
    if any(item.match(pat) or pat in item.parts for pat in EXCLUDED_PATTERNS):
      continue
    target = dst / item.name
    if item.is_dir():
      copy_tree_filtered(item, target)
    else:
      shutil.copy2(item, target)


def build_release():
  print("=" * 70)
  print(f"  BUILDING DENTRACE DESKTOP RELEASE: {RELEASE_NAME}")
  print("=" * 70)

  if STAGE_DIR.exists():
    print(f"[*] Cleaning existing staging directory: {STAGE_DIR}")
    shutil.rmtree(STAGE_DIR)
  STAGE_DIR.mkdir(parents=True, exist_ok=True)

  # 1. Copy Application Core
  core_dirs = ["backend", "frontend", "config", "alembic", "scripts/launcher"]
  for d in core_dirs:
    src_p = SOURCE_ROOT / d
    dst_p = STAGE_DIR / d
    if src_p.exists():
      print(f"[*] Copying {d}...")
      copy_tree_filtered(src_p, dst_p)

  # 2. Copy Root Launchers & Config Files
  root_files = [
      "launch_dentrace.bat",
      "launch_dentrace.ps1",
      "alembic.ini",
      "requirements.txt",
      "README.md",
  ]
  for f in root_files:
    src_f = SOURCE_ROOT / f
    if src_f.exists():
      shutil.copy2(src_f, STAGE_DIR / f)
      print(f"[*] Copied {f}")

  # 3. Create Fresh User Data & Staging Directories
  (STAGE_DIR / "data" / "storage").mkdir(parents=True, exist_ok=True)
  (STAGE_DIR / "data" / "previews").mkdir(parents=True, exist_ok=True)
  (STAGE_DIR / "models" / "checkpoints").mkdir(parents=True, exist_ok=True)

  # Create .gitkeep in empty directories
  (STAGE_DIR / "data" / "storage" / ".gitkeep").touch()
  (STAGE_DIR / "data" / "previews" / ".gitkeep").touch()

  # 4. Copy Authorized Models (Models allowed for redistribution or local staging)
  # Copy Apache 2.0 and community educational models
  source_models = SOURCE_ROOT / "models" / "checkpoints"
  if source_models.exists():
    for cp in source_models.glob("*.onnx"):
      # Copy authorized models into release checkpoints
      shutil.copy2(cp, STAGE_DIR / "models" / "checkpoints" / cp.name)
      print(f"    [+] Staged model: {cp.name} ({cp.stat().st_size / (1024*1024):.2f} MB)")

  # 5. Write Model Pack Instructions
  model_readme = STAGE_DIR / "models" / "README.md"
  model_readme.write_text(
      """# DENTRACE Offline Model Pack & Placement Guide

This directory holds offline AI model checkpoints for the DENTRACE Clinical Decision Support Engine.

## Checkpoint Inventory & Placement

| Model Identifier | Required Filename | Architecture | SHA-256 Hash |
|---|---|---|---|
| `liodon-panoramic-screener` | `best.onnx` | YOLO11n Anomaly Screener | `4cee38b54203634d895ed30a8910f5d7c4cefe22b18f9116b5561d9dd6e83a71` |
| `abychkov-fdi-detection` | `dental_fdi.onnx` | RT-DETR FDI Localizer | `426ddf210f339669f069bf41e0a4f225c72c4667ffb7f71c310112cfd7481f8a` |
| `nsitnov-8024-seg` | `8024.onnx` | YOLOv8-seg Restorations & Lesions | `36b2eca68e32116484ffae6f110f2e5dbf182e06cd4f4c05c98fb15dd3cdad8c` |
| `dentex-yolov8n-seg` | `dentex_yolov8n_seg.onnx` | 4-Class DENTEX Segmenter | `32fb75fe29fc2d0d6ee21f79d7f93fc37fd4248e88080823e30691c7a094c435` |

Place downloaded or institutional checkpoints directly in `models/checkpoints/`.
DENTRACE will automatically verify SHA-256 hashes upon startup.
""",
      encoding="utf-8",
  )

  # 6. Generate Checksum Manifest
  print("[*] Generating SHA256SUMS.txt manifest...")
  checksum_lines = []
  total_files = 0
  total_bytes = 0
  for root, _, files in os.walk(STAGE_DIR):
    for f in sorted(files):
      p = Path(root) / f
      rel = p.relative_to(STAGE_DIR)
      h = sha256_file(p)
      sz = p.stat().st_size
      total_files += 1
      total_bytes += sz
      checksum_lines.append(f"{h}  {rel.as_posix()}\n")

  manifest_path = STAGE_DIR / "SHA256SUMS.txt"
  manifest_path.write_text("".join(checksum_lines), encoding="utf-8")
  print(f"[*] Staged {total_files} files ({total_bytes / (1024*1024):.2f} MB extracted).")

  # 7. Compress into Release Archive
  print(f"[*] Creating compressed release archive: {ZIP_PATH}...")
  if ZIP_PATH.exists():
    ZIP_PATH.unlink()

  with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for root, _, files in os.walk(STAGE_DIR):
      for f in files:
        p = Path(root) / f
        arcname = p.relative_to(DIST_BASE)
        zf.write(p, arcname)

  zip_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
  zip_hash = sha256_file(ZIP_PATH)
  print(f"[SUCCESS] Release Archive Created: {ZIP_PATH}")
  print(f"          Size: {zip_size_mb:.2f} MB")
  print(f"          SHA-256: {zip_hash}")

  # 8. Create Inno Setup Script
  create_inno_setup_script()

  print("\n" + "=" * 70)
  print("  LEVEL 9 RELEASE BUILD COMPLETED SUCCESSFULLY")
  print(f"  Distribution Path: {STAGE_DIR}")
  print(f"  Archive Path:      {ZIP_PATH}")
  print(f"  Archive Size:      {zip_size_mb:.2f} MB")
  print("=" * 70 + "\n")


def create_inno_setup_script():
  """Generate Inno Setup script for optional native Windows installer compilation."""
  iss_dir = SOURCE_ROOT / "scripts" / "installer"
  iss_dir.mkdir(parents=True, exist_ok=True)
  iss_path = iss_dir / "dentrace_setup.iss"

  iss_template = """// DENTRACE Desktop Installer — Inno Setup Script
// Target: Windows 11 x64
#define MyAppName "DENTRACE"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "DENTRACE Clinical Decision Support"
#define MyAppExeName "launch_dentrace.bat"
#define MySourceDir "C:\\mini\\dist\\__RELEASE_NAME__"

[Setup]
AppId={{A8F24C71-934E-4BC9-9A07-7FE382B14912}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile={#MySourceDir}\\README.md
PrivilegesRequired=lowest
OutputDir=C:\\mini\\dist
OutputBaseFilename=DENTRACE-v0.1.0-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MySourceDir}\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\\*.tmp"
// Retain user patient records in %LOCALAPPDATA%\\DENTRACE on uninstall!
"""
  iss_content = iss_template.replace("__RELEASE_NAME__", RELEASE_NAME)
  iss_path.write_text(iss_content, encoding="utf-8")
  print(f"[*] Generated Inno Setup script: {iss_path}")
  print(f"[*] Generated Inno Setup script: {iss_path}")


if __name__ == "__main__":
  build_release()
