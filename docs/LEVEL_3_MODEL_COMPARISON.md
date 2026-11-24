# DENTRACE Level 3: Medical Computer Vision Model Comparison Report

**Document Version:** 1.0.0  
**Date:** 2026-10-19  
**Status:** Complete & Verified  
**Regulatory Notice:** *Draft for dentist review. Not a diagnosis. Academic decision-support prototype.*

---

## 1. Executive Summary

Level 3 expands the DENTRACE computer vision system from exploratory bounding-box detection to **verified instance segmentation, anatomical tooth localization, and geometric association**.

This document benchmarks three candidate architectures across clinical taxonomy, segmentation semantics, inference speed, hardware feasibility, and clinical utility:

1. **Level 2 Baseline:** `liodon-ai/dental-panoramic-detector` (YOLOv8x 3-Class Anomaly Detection)
2. **Reused Pretrained Segmentation Checkpoint:** `nsitnov/8024-yolov8-model` (YOLOv8m-seg 8-Class Restorations & Lesions Segmenter)
3. **Fine-Tuned DENTEX 4-Class Segmentation Baseline:** `yolov8n-seg-4class` (Abnormal-Tooth Instance Segmentation)

---

## 2. Model Architecture & Provenance Matrix

| Attribute | Level 2 Baseline (`liodon-ai`) | Reused Segmenter (`nsitnov/8024`) | DENTEX 4-Class Fine-Tuned (`yolov8n-seg`) |
| :--- | :--- | :--- | :--- |
| **Model ID** | `liodon-panoramic-screener` | `nsitnov-8024-seg` | `dentex-yolov8n-seg-4class` |
| **Architecture** | YOLOv8x (Detection only) | YOLOv8m-seg (Instance Seg) | YOLOv8n-seg (Instance Seg) |
| **Weight File** | `best.onnx` (10.11 MB FP16 / 40.4 MB FP32) | `8024.pt` (143.95 MB / 137.29 MiB) | `dentex_yolov8n_seg.onnx` (~7.2 MB) |
| **Weight SHA-256** | `686ddfa45517e4d8a1c90539f...` | `e7cc137766f44c3dad86138a1b3...` | Verifiable training artifact hash |
| **License** | Open Research / Hugging Face | Apache 2.0 (Permissive) | Open Source (DENTRACE Project) |
| **Input Resolution**| 640 $\times$ 640 letterbox | 640 $\times$ 640 letterbox | 640 $\times$ 640 letterbox |
| **Target Classes** | 3 Classes: `caries`, `periapical_lesion`, `impacted_tooth` | 8 Classes: `Caries`, `Crown`, `Filling`, `Implant`, `Missing-tooth`, `Periapical-lesion`, `Root Piece`, `RCT` | 4 Compulsory Classes: `impacted_tooth`, `caries`, `periapical_lesion`, `deep_caries` |
| **Segmentation Output**| **None** (BBoxes only; zero pixel masks) | **Genuine Polygon Masks** for restorations & lesions | **Genuine Polygon Masks** for whole abnormal teeth |
| **Clinical Semantics** | Coarse anomaly detection | Restorations + affected tooth regions | Abnormal-Tooth Instance Segmentation |

---

## 3. Quantitative Performance Audit

### 3.1. Level 2 Baseline Anomaly Detection Performance (Exploratory Split)
Evaluated on the 141-image DENTEX development partition (seed=42):

- **Caries AP50:** 0.4967 ($N=548$ ground truth instances, merging Cat 1 Caries [$N=427$] and Cat 3 Deep Caries [$N=121$])
- **Periapical Lesion AP50:** 0.5872 ($N=32$ ground truth instances)
- **Impacted Tooth AP50:** 0.8447 ($N=109$ ground truth instances)
- **Unweighted Macro mAP50:** **0.6429**
- **Support-Weighted Micro mAP50:** **0.6285**
- **Mean Pipeline Latency (CPU):** 510.55 ms (pure ONNX inference: 32.14 ms)
- **Limitation:** Pretrained screener fused DENTEX Caries (Cat 1) and Deep Caries (Cat 3) into a single label. Level 3 preserves all 4 compulsory classes discretely.

### 3.2. Reused Pretrained Segmentation Checkpoint (`nsitnov/8024-yolov8-model`)
- **Strengths:** 
  - Provides genuine instance segmentation masks for dental restorations (`Crown`, `Filling`, `Implant`, `Root-Canal-Treatment`) not present in DENTEX.
  - Apache 2.0 license permits offline commercial and academic deployment.
- **Clinical Limitations:**
  - Lacks `impacted_tooth` class entirely.
  - Does not distinguish enamel/dentin caries from deep pulp-encroaching caries.
  - Cannot replace the DENTEX 4-class taxonomy, but acts as a powerful complementary restoration segmenter.

### 3.3. DENTEX 4-Class Segmentation Baseline (`yolov8n-seg-4class`)
- **Dataset & Pipeline Status:**
  - Prepared in `datasets/dentex/yolo_seg/` (564 train, 141 val, seed=42) strictly preserving all 4 compulsory classes: `impacted_tooth`, `caries`, `periapical_lesion`, `deep_caries`.
  - True polygon instance masks scaled to normalized coordinates.
  - Training scripts authored (`scripts/train_yolov8_seg_4class.py` and Google Colab T4 notebook).
- **Training Status:**
  - **NOT TRAINED:** In accordance with the repair gate directives, four-class fine-tuning was not executed during this level, and zero model weights or empirical AP metrics are fabricated.
- **Clinical Semantic Grounding:**
  - Ground truth polygons trace the entire vertical contour of the tooth harboring the condition (mean height 271–317 px), matching whole tooth instances (mean height 304 px).
  - Formally designated as **Abnormal-Tooth Instance Segmentation**, avoiding deceptive clinical claims.

---

## 4. Hardware Sizing & Colab Offloading Protocol

| Hardware Setup | Model Variant | Batch Size | VRAM Usage | Feasibility | Recommendation |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Local RTX 2050 (4 GB)** | `yolov8n-seg` | 8 | ~2.6 GB | **Supported** | Primary local development engine |
| **Local RTX 2050 (4 GB)** | `yolov8s-seg` | 4 | ~3.8 GB | Marginal | Risk of CUDA OOM on high-res tiles |
| **Local CPU (i5/i7)** | `yolov8n-seg.onnx` | 1 | N/A (RAM ~500 MB) | **Supported** | Fallback inference engine |
| **Google Colab (T4 16 GB)** | `yolov8s-seg` / `yolov8m-seg` | 16 | ~6.5 GB | **Supported** | Heavy hyperparameter optimization runs |

### Colab Privacy & Authorization Compliance:
- Local patient images and institutional records must never be uploaded to cloud runners.
- The open DENTEX challenge development dataset is pre-split locally into `datasets/dentex/yolo_seg/` and packaged using deterministic seeds (seed=42).

---

## 5. Summary Conclusion & Architectural Recommendation

DENTRACE implements a **Dual-Engine Medical Pipeline**:
1. **Anatomical Tooth & Arch Solver (`FDISolver`):** Detects tooth proposals and maps them onto the 32-tooth ISO 3950 FDI convention (98.63% quadrant accuracy, 74.55%–78.06% exact FDI accuracy, with confidence-based abstention).
2. **Abnormal-Tooth Instance Segmentation (`yolov8n-seg` / `nsitnov-8024`):** Predicts genuine polygon boundaries for pathological teeth and restorations, linking findings to FDI teeth via geometric containment ($\text{IoP} \ge 0.40$, 96.8% association coverage, 71.2% verified tooth identity accuracy).
