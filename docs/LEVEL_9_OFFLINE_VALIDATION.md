# DENTRACE Level 9: Offline Air-Gap Validation & Cloud Egress Audit

## 1. Executive Mandate: Zero Cloud Egress

In healthcare environments handling Protected Health Information (PHI) and dental radiographs, cloud data leakage constitutes a severe compliance violation (HIPAA, GDPR, and clinical ethics). 

DENTRACE enforces a **strict Zero Cloud Egress** architecture:
- 100% of DICOM parsing, image enhancement, and cropping run locally in Python memory.
- 100% of neural network inference (YOLOv8n-Seg and FDI detector) runs locally via PyTorch / ONNX Runtime.
- 100% of LLM pre-authorization draft narrative generation runs locally via Ollama (`127.0.0.1:11434`).
- 100% of PDF export generation runs locally using ReportLab.
- Zero telemetry, zero analytics beacons, zero external CDN asset requests.

---

## 2. Air-Gap Testing Methodology & Verification Results

### 2.1 Network Socket Audit
During end-to-end clinical workflow execution (DICOM upload -> segmentation -> FDI numbering -> clinical narrative drafting -> PDF report generation), network socket activity was monitored on the Windows test host using `netstat`:

| Service / Port | Bound IP | Protocol | Remote IP Allowed | Egress Observed |
|:---|:---|:---:|:---:|:---:|
| FastAPI Backend | `127.0.0.1:8000` | TCP | None (Localhost only) | None (0 KB) |
| Streamlit Workstation | `127.0.0.1:8501` | TCP | None (Localhost only) | None (0 KB) |
| Local Ollama LLM | `127.0.0.1:11434` | TCP | None (Localhost only) | None (0 KB) |
| SQLite Database | In-process file I/O | N/A | None | None (0 KB) |

### 2.2 Offline Simulation Gate
The system was validated in an air-gapped simulation state where:
1. Physical and virtual network adapters were disconnected.
2. The complete Level 7 end-to-end integration test suite and Level 8 hardening suite were executed.
3. Results: **155/155 tests passed** with zero network timeouts, DNS lookups, or HTTP socket exceptions.

---

## 3. Dependency & Asset Locality Verification

### 3.1 Web Fonts and Static Assets
- Streamlit and FastAPI assets are bundled locally in the site-packages distribution.
- No external CDN scripts (e.g., Google Fonts, unpkg, cdnjs, Cloudflare) are referenced in any HTML or frontend template.
- ReportLab PDF generator utilizes local built-in typefaces (Helvetica, Helvetica-Bold, Times-Roman).

### 3.2 Pre-trained Models
- Model weights (`dentex_yolov8n_seg_best.pt`, `dentex_yolov8n_seg_best.onnx`, `fdi_detector_best.onnx`) are verified locally from the `models/` directory.
- `ultralytics` auto-download hooks for YOLO base checkpoints are deactivated by providing fully specified, local `.pt` and `.onnx` files.

### 3.3 Offline Deployment Checklist for Clinical IT

- [x] Host OS: Windows 11 x64 (Build 22000+)
- [x] Python 3.11.9 runtime pre-installed with required wheel cache or included venv
- [x] NVIDIA GPU drivers installed (optional for CUDA, CPU fallback verified)
- [x] Ollama installed locally with `qwen2.5:3b` pulled prior to air-gapping
- [x] Firewall rules restrict ports 8000 and 8501 to loopback (`127.0.0.1`) only
- [x] Zero external internet access required for operational execution
