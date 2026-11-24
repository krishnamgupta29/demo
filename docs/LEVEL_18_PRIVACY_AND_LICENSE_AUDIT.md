# LEVEL 18 — Privacy & License Compliance Audit

**Document ID:** DENTRACE-L18-PRIVACY  
**Author:** AI Systems Engineer  
**Date:** November 16, 2026  
**Status:** 100% Compliant  

---

## 1. Zero Cloud Egress Boundary

DENTRACE enforces strict local-first execution across all functional layers:
- **FastAPI Backend:** Bound strictly to `127.0.0.1:8000`. No external listening sockets.
- **Inference Engines:** ONNX Runtime executing on local CPU (`CPUExecutionProvider`) or local GPU (`CUDAExecutionProvider`). Zero external model API endpoints.
- **Local LLM Engine:** Ollama running locally at `127.0.0.1:11434`.
- **Database:** Local SQLite database at `C:\mini\data\dentrace.db`.
- **Network Verification:** Zero outbound telemetry, crash reporting, or external API pings.

---

## 2. De-identification & Burned-In Metadata Defense

### Pixel Data Safeguard
- Radiographs uploaded from mobile cameras or PACS exports frequently have patient demographics (Name, MRN, Date of Birth, Clinic) printed in black/white borders along the top or bottom 10% of the image.
- `backend/storage/file_manager.py` inspects DICOM tags and alerts clinicians when `BurnedInAnnotation == YES`.
- For standard photographic uploads (JPEG/PNG), DENTRACE maintains an authentic, unadulterated clinical master copy while providing presentation mode de-identification warnings.
- All EXIF metadata, camera serial numbers, and GPS coordinates are stripped upon intake.

---

## 3. Open-Source Software & Model License Audit

| Asset / Component | Source | License | Compliance Assertion |
|---|---|---|---|
| **Liodon Panoramic Screener** | Ultralytics YOLO11n ONNX | AGPL-3.0 / Research Use | Local execution within college research scope. |
| **DENTEX YOLOv8 Seg** | MICCAI 2023 DENTEX Challenge | Academic / Research License | Academic college decision-support system strictly. |
| **3D Dental Arch Meshes** | OrganUI / BodyParts3D | CC BY-SA 2.1 JP | Attributed in UI footer and documentation. |
| **ReportLab Engine** | ReportLab Open Source | BSD License | Clean commercial/open-source permissive compliance. |
| **Three.js** | Mr.doob / Three.js | MIT License | Permissive compliance. |
| **Lucide Icons** | Lucide Contributors | ISC License | Permissive compliance. |
| **React / Vite** | Meta / Vite Team | MIT License | Permissive compliance. |

---

## 4. Statutory & Regulatory Boundaries
- **Mandatory Notice:** `"Draft for dentist review. Not a diagnosis."` is permanently burned into all UI views and exported PDF claim packs.
- **Regulatory Status:** DENTRACE is an academic college decision-support research engine. It is not an FDA-cleared, CE-marked, or MDR-certified medical device. It does not provide autonomous clinical diagnosis or automated insurance approvals.
