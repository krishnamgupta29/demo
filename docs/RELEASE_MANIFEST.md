# DENTRACE Level 9: Official Release Manifest

## 1. Release Identification

- **Release Name**: DENTRACE Desktop Workstation
- **Version**: 0.1.0
- **Build Target**: Windows 11 x64 (AMD64)
- **Release Date**: October 22, 2026
- **Architecture**: Dual-Process (FastAPI Backend + Streamlit Clinical Interface)
- **Regulatory Status**: Academic Decision-Support System / College Capstone
- **Clinical Notice**: *"Draft for dentist review. Not a diagnosis."*

---

## 2. Release Package Deliverables

| Deliverable | File Path | Size | SHA-256 Digest |
|:---|:---|:---:|:---|
| Compressed Release Archive | `dist/DENTRACE-v0.1.0-win64.zip` | 446.59 MB | `f6ad8af386050996094c2d97465d6a6564b0ed8b7341ffa29903eb6cc63dd331` |
| Inno Setup Script | `scripts/installer/dentrace_setup.iss` | 3.1 KB | — |
| Primary Windows Launcher | `launch_dentrace.bat` | 1.4 KB | `4948ca154bbc15d7bc37bf700330824358e226145f4c6975a01e016cb6e04b76` |
| PowerShell Launcher | `launch_dentrace.ps1` | 1.6 KB | `3befbbd26da9e0debabf8da9d5145e94c01a9c2bd1b87a290f7fc83b2519411b` |
| Master Checksum File | `dist/SHA256SUMS.txt` | 8.5 KB | — |

---

## 3. Distributed Neural Model Artifacts

| Model Name | Role / Task | Framework | Location in Release | License / Redistribution |
|:---|:---|:---:|:---|:---|
| `dentex_yolov8n_seg_best.pt` | Lesion Segmentation | PyTorch (FP32) | `models/dentex_yolov8n_seg_best.pt` | Research / Bundled |
| `dentex_yolov8n_seg_best.onnx` | Lesion Segmentation | ONNX Runtime | `models/checkpoints/dentex_yolov8n_seg_best.onnx` | Research / Bundled |
| `dental_fdi.onnx` / `fdi_detector_best.onnx` | FDI 32-Tooth Detection | ONNX Runtime | `models/checkpoints/dental_fdi.onnx` | Research / Bundled |
| `qwen2.5:3b` | Clinical Pre-Auth Draft | Ollama (Local) | Local Ollama store (`127.0.0.1:11434`) | Qwen Research / Local |

---

## 4. Release Directory Hierarchy

```
DENTRACE-v0.1.0-win64/
├── launch_dentrace.bat             # One-click Windows batch launcher
├── launch_dentrace.ps1             # PowerShell launcher with detailed logs
├── requirements.txt                # Pinned dependencies
├── README.md                       # Release overview & user instructions
├── SHA256SUMS.txt                  # Cryptographic file hashes
├── alembic.ini                     # Database migration configuration
├── backend/                        # FastAPI services, ML engines, rules
├── frontend/                       # Streamlit workstation & components
├── config/                         # Model manifests & CDT ontology
│   ├── model_manifest.json
│   ├── class_mapping.json
│   ├── cdt_demo.json
│   └── settings.json
├── models/                         # Trained neural weights & checkpoints
│   └── checkpoints/
│       ├── dentex_yolov8n_seg_best.onnx
│       ├── dental_fdi.onnx
│       └── ...
├── scripts/                        # Launcher supervisor & setup scripts
│   └── launcher/
│       └── launcher.py
└── data/                           # Isolated directory templates
    ├── previews/
    └── storage/
```
