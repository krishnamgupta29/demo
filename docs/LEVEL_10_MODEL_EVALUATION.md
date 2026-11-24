# DENTRACE Level 10: Model Evaluation & Scientific Benchmark Audit

> **AUDIT AUTHORITY:** Medical Computer Vision & Scientific Quality Auditor  
> **DATE:** October 22, 2026  
> **EVALUATION TARGETS:** DENTEX YOLOv8n-Seg, Anatomical FDI Locator, Quantized ONNX Engines

---

## 1. Dataset Provenance & Split Integrity

The primary vision models were trained and evaluated on the **DENTEX 2023 Challenge Dataset**:
- **Source**: Miccai DENTEX 2023 (Panoramic Dental X-rays)
- **Total Radiographs**: 705 training images, 141 validation images (strictly isolated 80/20 train/val split)
- **Pathology Annotations**: 3,529 polygon instance masks
  - Caries: 2,189 instances
  - Deep Caries: 578 instances
  - Impacted Tooth: 604 instances
  - Periapical Lesions: 158 instances
- **Pretrained Transfer Source**: Official Ultralytics `yolov8n-seg.pt` (COCO pretraining, 411/417 layers transferred)
- **Data Leakage Check**: Zero image overlap between train and validation splits. Verified via SHA-256 hash inspection.

---

## 2. Neural Segmentation Performance Metrics (Epoch 25 Best Model)

Evaluated on the isolated DENTEX validation split (141 images, 689 pathological instances):

### 2.1 Overall Performance Summary

| Task | Precision | Recall | mAP50 | mAP50-95 | Best Epoch |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Bounding Box Detection** | 0.5172 | 0.5435 | **0.4816** | 0.2972 | 25 / 30 |
| **Instance Mask Segmentation** | 0.4697 | 0.5099 | **0.4460** | 0.2732 | 25 / 30 |

### 2.2 Class-Wise Performance Breakdown

| Class | Instances (Val) | Box mAP50 | Mask mAP50 | Clinical Reliability Assessment |
|:---|:---:|:---:|:---:|:---|
| **Impacted Tooth** | 120 | **0.864** | **0.867** | **High Reliability**: Distinct anatomical third molar boundaries. |
| **Deep Caries** | 115 | **0.440** | **0.430** | **Moderate Reliability**: Severe cavitation clearly visible; vitality check required. |
| **Caries** | 402 | **0.317** | **0.317** | **Moderate Reliability**: Enamel/dentin radiolucency; subtle interproximal lesions challenging on 2D OPG. |
| **Periapical Lesion** | 52 | **0.284** | **0.171** | **Low Sensitivity / Highest Clinical Risk**: Diffuse borders and small training sample (158 train instances). **Mandatory chairside dentist confirmation required.** |
| **Aggregate Mean (All)** | 689 | **0.476** | **0.446** | — |

---

## 3. Scientific Discrepancy Analysis

### 3.1 Periapical Lesion Underperformance Analysis
- **Root Cause 1: Class Imbalance**: Periapical lesions comprise only 4.5% of total annotations (158 in train, 52 in val).
- **Root Cause 2: 2D Radiographic Limitations**: Unlike distinct impacted crowns or cavitated tooth crowns, periapical lesions present as diffuse, poorly circumscribed periapical radiolucencies in trabecular bone, frequently obscured by the maxillary sinus floor, nasal fossa, or mandibular canal.
- **Clinical Policy**: DENTRACE explicitly acknowledges this lower detection sensitivity (mAP50=0.284) and prohibits autonomous apical diagnoses.

### 3.2 FDI Numbering Solver Evolution
- **Level 3 Baseline**: 74.55% exact tooth accuracy.
- **Level 6.1 Calibrated Solver**: **76.07% exact tooth accuracy** (76.55% precision on non-abstained teeth) with 98.63% quadrant accuracy across 4,224 teeth (150 OPGs).
- **Improvements Applied**: Crown width prior scaling (`MAXILLA_WIDTH_FACTORS`, `MANDIBLE_WIDTH_FACTORS`), calibrated pitch gap threshold ($1.35$), midline ratio ($1.10$), and strict quadrant limit ($N \le 8$) abstention.
- **Remaining Error Mode**: Severely crowded anterior dentition or congenitally missing premolars produce quadrant shifting. Clinician edit controls on the interactive odontogram provide the mandatory human correction mechanism.

---

## 4. Latency, Compression & Quantization Benchmark

Evaluated on host machine hardware:
- **CPU**: Intel Core i5-13420H (4 performance cores + 4 efficiency cores, 16 threads)
- **GPU**: NVIDIA GeForce RTX 2050 (4 GB GDDR6 VRAM, Driver 592.82, CUDA 13.1)

| Engine / Model | Format | File Size | Compression Ratio | Device / Provider | Latency (p50) | Latency (p95) | Production Status |
|:---|:---:|:---:|:---:|:---|:---:|:---:|:---:|
| PyTorch FP32 (`dentex_yolov8n_seg_best.pt`) | PyTorch | 6.44 MB | 1.0x | RTX 2050 (CUDA) | 14.2 ms | 19.8 ms | Training / Dev |
| ONNX FP32 (`dentex_yolov8n_seg_best.onnx`) | ONNX | 13.2 MB | 1.0x | RTX 2050 (CUDA) | **18.2 ms** | 24.5 ms | **Production GPU** |
| ONNX FP32 (`dentex_yolov8n_seg_best.onnx`) | ONNX | 13.2 MB | 1.0x | Intel i5 (CPU) | **113.8 ms** | 515.2 ms | **Production CPU** |
| ONNX Dynamic INT8 (`best_int8_dyn.onnx`) | ONNX | 3.52 MB | **3.6x** | Intel i5 (CPU) | 1,528.0 ms | 1,840.0 ms | Available (Archival) |

### Rejection of INT8 Dynamic Quantization for Real-Time CPU Inference
While Dynamic INT8 achieved 3.6x disk compression, real-time CPU latency increased by **13.4x** (from 113.8 ms to 1,528.0 ms). On x86 architectures, the per-layer runtime overhead of dynamically converting activations between INT8 and FP32 outweighs the memory bandwidth savings of lightweight (3.2M parameter) networks. Therefore, **ONNX FP32** is deployed as the production default.

---

## 5. Independent Clinical Validation Disclosure

- **Internal Development Split**: All reported vision metrics were computed on the held-out DENTEX challenge validation split.
- **No External Multi-Center Validation**: DENTRACE has **not** undergone prospective multi-center clinical trials across diverse OPG scanner manufacturers (e.g., Planmeca, Carestream, KaVo, Sirona).
- **Academic Scope**: These benchmarks demonstrate technical proof-of-concept for an academic capstone, not clinical diagnostic equivalence.
