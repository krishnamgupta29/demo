# DENTRACE Level 6 — Comprehensive AI Model Comparison Matrix

**Document ID:** DENTRACE-L6-COMP-001  
**Status:** COMPLETE & AUDITED  
**Date:** October 2026  
**Registry Version:** 1.0.0  

---

## 1. Overview & Evaluation Framework

In Level 6, DENTRACE audited, optimized, and integrated 8 candidate AI models across four distinct clinical computer vision tasks:
1. **FDI Permanent Tooth Localization & Enumeration (ISO 3950)**
2. **Whole-Tooth Anomaly Detection & Screening**
3. **Multi-Class Instance Segmentation (Whole-Tooth & Restorative Polygons)**
4. **Alveolar Bone Loss & Periodontal Staging Analysis**

All candidates operate strictly offline under zero-cloud-egress directives (`127.0.0.1:8000`).

---

## 2. Master Model Comparison Matrix

| Model Identifier | Clinical Task Domain | Model Architecture | Supported Classes | Input Shape | Checkpoint Size | Availability Status | License | Mean CPU Latency |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|
| `abychkov-fdi-detection` | FDI Tooth Localization | RT-DETR / Transformer | 32 permanent teeth (11–48) | (1, 3, 640, 640) | 114.5 MB | **AVAILABLE** | Open Community / Educational | ~450 ms |
| `liodon-panoramic-screener` | Pathology Screener | YOLO11n (Ultralytics) | `caries`, `periapical_lesion`, `impacted_tooth` | (1, 3, 640, 640) | 10.11 MB | **AVAILABLE** | CC BY-NC 4.0 | 312.4 ms |
| `liodon-panoramic-screener-int8` | Pathology Screener (Quantized) | YOLO11n Dynamic INT8 | `caries`, `periapical_lesion`, `impacted_tooth` | (1, 3, 640, 640) | **2.87 MB** | **AVAILABLE** | CC BY-NC 4.0 | 489.2 ms |
| `dentex-yolov8n-seg` | 4-Class Tooth Segmentation | YOLOv8n-seg (Fine-tuned) | `impacted_tooth`, `caries`, `periapical_lesion`, `deep_caries` | (1, 3, 640, 640) | 6.74 MB (pt) / 12.67 MB (onnx) | **AVAILABLE** | CC BY-NC 4.0 | 360.8 ms (pt) / 874.9 ms (onnx) |
| `dentex-yolov8n-seg-int8` | 4-Class Tooth Segmentation (Quantized) | YOLOv8n-seg Dynamic INT8 | `impacted_tooth`, `caries`, `periapical_lesion`, `deep_caries` | (1, 3, 640, 640) | **3.52 MB** | **AVAILABLE** | CC BY-NC 4.0 | 1,370.2 ms |
| `nsitnov-8024-seg` | Restorations & Endodontics | YOLOv8x-seg (Ultralytics) | 8 classes (Caries, Crown, Filling, Implant, Missing-tooth, Periapical-lesion, Root Piece, Root-Canal-Treatment) | (1, 3, 640, 640) | 137.0 MB (pt) / 273.9 MB (onnx) | **AVAILABLE** | Apache 2.0 | 1,842.3 ms |
| `nsitnov-dental-segmentation` | Segmentation Baseline (Uninstalled Fixture) | YOLOv8-seg | 8 classes | (1, 3, 640, 640) | N/A | **MODEL_UNAVAILABLE** (Truthful missing weights test) | Apache 2.0 | N/A |
| `boneloss-pan769-baseline` | Periodontal Bone Loss | ResNet50 / U-Net | Alveolar bone loss, CEJ line, Crestal bone line | (1, 3, 512, 1024) | N/A | **BLOCKED (UNSUPPORTED_MISSING_LANDMARKS)** | Academic Research Only | N/A |

---

## 3. Detailed Model Analysis

### 1. `abychkov-fdi-detection`
- **Strengths:** High sensitivity for tooth crown proposals across all 4 quadrants.
- **Weaknesses:** Raw output is permutation-invariant; requires the `CalibratedFDISolver` for anatomical arch sequence alignment.
- **Role:** Upstream tooth proposal extractor.

### 2. `liodon-panoramic-screener` & `liodon-panoramic-screener-int8`
- **Strengths:** Ultra-fast detection screening (312 ms FP32, 2.87 MB INT8).
- **Weaknesses:** Rectangular bounding-box proposals only; cannot provide pixel-level boundaries.
- **Role:** Fast first-pass screening and triaging.

### 3. `dentex-yolov8n-seg` & `dentex-yolov8n-seg-int8`
- **Strengths:** Fine-tuned specifically on the 3,529 authoritative DENTEX annotations. Outputs true polygon masks tracing whole abnormal tooth envelopes.
- **Weaknesses:** Polygons represent whole tooth boundaries rather than micro-margin cavity preps.
- **Role:** Primary 4-class instance segmenter for caries, deep caries, periapical lesions, and impacted teeth.

### 4. `nsitnov-8024-seg`
- **Strengths:** Excellent differentiation of restorative gutta-percha (`Root-Canal-Treatment`) from radiolucent apical osteolysis (`Periapical-lesion`).
- **Weaknesses:** Large model size (273.9 MB FP32 ONNX; 70.1 MB INT8); higher CPU inference latency (~1.8–2.4 s).
- **Role:** Endodontic and restorative verification engine; powers the composite root-canal failure alert.

### 5. `boneloss-pan769-baseline`
- **Status:** Explicitly blocked (`UNSUPPORTED_MISSING_LANDMARKS`).
- **Clinical Rationale:** Alveolar crest height and PBL % cannot be reliably determined from whole-tooth abnormal condition contours without CEJ and crest line landmarks. Falsifying bone loss is strictly prohibited.
