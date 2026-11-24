# LEVEL 19 — DEDICATED INTRAORAL PERIAPICAL (IOPA) AI MODEL FEASIBILITY STUDY

**Domain:** Dental Machine Learning & Computer Vision  
**Target Hardware:** NVIDIA GeForce RTX 2050 (4 GB VRAM) / Offline Localhost Execution  
**Policy:** Never train on single patient demonstration images; require independent open-access benchmarks.

---

## 1. Candidate Public Datasets for IOPA & Bitewing Radiographs

| Dataset Name | Source / Institution | Modality | Image Count | Annotations | Pathology Classes | License | VRAM Feasibility (4 GB) |
|:---|:---|:---:|:---:|:---|:---|:---:|:---:|
| **Tufts Dental Database** | Tufts University | Panoramic + Periapical | ~1,000 | Bounding Boxes + Radiopaque tags | Caries, Periapical Lesions, Teeth | Research / Non-commercial | Feasible ($B \le 8$, YOLO11n) |
| **Mendeley Periapical Caries** | Open Science Platform | Periapical (IOPA) | ~1,500 | Pixel Masks / BBoxes | Dental Caries, Restorations | CC BY 4.0 | Feasible ($B \le 8$, YOLOv8n-seg) |
| **Bitewing Radiograph Caries** | University of Campinas | Bitewing | ~500 | Expert Consensus BBoxes | Interproximal Caries, Enamel Breakdown | CC BY-NC 4.0 | Feasible ($B \le 8$, ONNX INT8) |

---

## 2. Technical Feasibility & Training Constraints

### 2.1 Hardware Directives
- **Host Machine:** Laptop NVIDIA RTX 2050 with 4 GB VRAM limit.
- **Disk Space Constraint:** `C:\` has ~150 GB free, while `D:\` has < 5 GB free. Any future training datasets must be staged exclusively under `C:\datasets\iopa`.
- **Model Architecture Recommendation:** YOLO11-Nano (`yolo11n.pt`) or YOLOv8-Nano Segmentation (`yolov8n-seg.pt`) quantized to INT8 with ONNX Runtime execution on DirectML / CPUExecutionProvider.

### 2.2 Clinical Safety Decision
Until a candidate model trained on 1,000+ consensus-labeled periapical images is integrated, validated, and quantified for sensitivity and specificity:
- Automated IOPA inference remains **DISABLED**.
- The application surfaces the notice: `"Automated IOPA analysis is not currently available. Panoramic models are disabled for periapical safety."`
- The clinician is empowered to utilize manual region annotations and the 4-tooth focus strip for documentation and insurance reporting.
