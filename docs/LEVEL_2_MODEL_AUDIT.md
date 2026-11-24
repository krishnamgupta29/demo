# DENTRACE — Level 2 Pretrained Model Integration & Verification Audit

> **DOCUMENT ID:** DOC-LVL2-AUDIT-001  
> **STAGE:** LEVEL 2 (COMPLETED)  
> **DATE:** 2026-10-19  
> **LEGAL NOTICE:** Draft for dentist review. Not a diagnosis.  

---

## 1. Executive Summary & Checkpoint Acquisition

Under Level 2 directives, external dental-specific model candidates were investigated and submitted for user authorization prior to download. Two verified checkpoints were approved and downloaded directly into `C:\mini\models\checkpoints\`:

1. **`liodon-ai/dental-panoramic-detector` (`best.onnx`)** — Primary Pathology Anomaly Screener.
2. **`abychkov/dental-fdi-detection` (`dental_fdi.onnx`)** — 32-Tooth FDI Localization Model.

Both checkpoints were verified via cryptographic SHA-256 digests and validated in local offline ONNX Runtime sessions.

---

## 2. Cryptographic Integrity & Source Verification

| Parameter | Primary Pathology Screener (`best.onnx`) | FDI Localization Detector (`dental_fdi.onnx`) |
|---|---|---|
| **Repository** | `liodon-ai/dental-panoramic-detector` | `abychkov/dental-fdi-detection` |
| **Download Source** | [HuggingFace Hub](https://huggingface.co/liodon-ai/dental-panoramic-detector/resolve/main/best.onnx) | [HuggingFace Hub](https://huggingface.co/abychkov/dental-fdi-detection/resolve/main/dental_fdi.onnx) |
| **Local Storage Path** | `C:\mini\models\checkpoints\best.onnx` | `C:\mini\models\checkpoints\dental_fdi.onnx` |
| **Exact File Size** | 10,605,711 bytes (10.11 MB) | 130,754,966 bytes (124.70 MB) |
| **SHA-256 Digest** | `4cee38b54203634d895ed30a8910f5d7c4cefe22b18f9116b5561d9dd6e83a71` | `426ddf210f339669f069bf41e0a4f225c72c4667ffb7f71c310112cfd7481f8a` |
| **License** | Creative Commons Attribution-NonCommercial 4.0 (`CC BY-NC 4.0`) | Proprietary Non-Commercial / Evaluation (`other`) |
| **Commercial Clinical Use** | Strictly Prohibited (Academic / Educational Only) | Strictly Prohibited (Research / Evaluation Only) |
| **Local Offline Status** | 100% offline localhost execution; zero cloud egress | 100% offline localhost execution; zero cloud egress |

---

## 3. Architecture & Tensor Contracts

### A. Primary Screener: `liodon-panoramic-screener` (`best.onnx`)
- **Producer / Library:** Ultralytics YOLO11n (`version 8.4.81`), export task: `detect`.
- **Parameter Count:** ~2.6 million parameters.
- **Quantization:** Standard FP32 ONNX graph.
- **Input Tensor Contract:**
  - Name: `images`
  - Shape: `[1, 3, 640, 640]` float32
  - Range: `[0.0, 1.0]` normalized (divided by 255.0)
  - Color Channel: RGB
  - Letterbox: Aspect-ratio preserving bilinear resize with grey padding `(114, 114, 114)`
- **Output Tensor Contract:**
  - Name: `output0`
  - Shape: `[1, 7, 8400]` float32
  - Channel 0: `cx` (center X in 640x640 space)
  - Channel 1: `cy` (center Y in 640x640 space)
  - Channel 2: `w` (box width)
  - Channel 3: `h` (box height)
  - Channel 4: `caries` confidence score
  - Channel 5: `periapical_lesion` confidence score
  - Channel 6: `impacted_tooth` confidence score
- **Output Classes (3):**
  - Index 0: `caries` (includes primary and deep caries)
  - Index 1: `periapical_lesion` (apical periodontitis / radiolucency)
  - Index 2: `impacted_tooth` (impacted and unerupted third molars)
- **Geometry Type:** Bounding Box (`bbox`). *Notice: Model does not produce instance segmentation masks; never represented as a pixel mask.*
- **Recommended Postprocessing:**
  - Confidence threshold: 0.25 (screening baseline) / 0.45 (conservative clinical review)
  - NMS IoU threshold: 0.35 (class-aware NMS)

### B. Tooth Localization: `abychkov-fdi-detection` (`dental_fdi.onnx`)
- **Architecture:** RT-DETR (Real-Time Detection Transformer).
- **Quantization:** Standard FP32 ONNX graph.
- **Input Tensor Contract:**
  - Name: `images`
  - Shape: `['batch', 3, 'height', 'width']` float32 (dynamic, evaluated at 640x640)
- **Output Tensor Contract:**
  - Name: `output0`
  - Shape: `[1, 300, 36]` float32 (300 object queries)
  - Values 0–3: `[cx, cy, w, h]` normalized in `[0.0, 1.0]`
  - Values 4–35: 32 tooth classification logits/probabilities
- **Numbering Convention:** Standard World Dental Federation (FDI) 2-digit system (11–48).
- **Documented Topological Limitation:**
  - The model author explicitly notes in `README.md` and `NOTICE` that the published ONNX weights represent the raw proposal stage. The author's proprietary "Anatomical consistency engine" is closed-source.
  - Raw unconstrained argmax mapping across classes 0..31 exhibits duplicate spatial proposals between bilateral quadrants.
  - **Engineering Decision:** DENTRACE rejects forced integer tooth numbering when ambiguous. Proposals are localized with patient-side anatomical orientation (Patient Right / Left, Maxilla / Mandible) and flagged as `uncertain_tooth = True` pending deterministic topological graph validation.

---

## 4. Training Data Provenance & Leakage Audit

A rigorous provenance audit was conducted to evaluate overlap between pretrained model training sources and benchmark datasets:

1. **`liodon-ai/dental-panoramic-detector` Training Corpus:**
   - Pretrained on 9,928 panoramic radiographs combining the **DENTEX Challenge Dataset** and **OralXrays-9** (CVPR 2025).
   - Validated by the author on 46 DENTEX validation images.
   - **Audit Finding:** Because the candidate model incorporated DENTEX images during its training phase, evaluations performed on DENTEX images cannot be classified as zero-shot independent clinical validation.
   - **Formal Designation:** All benchmarks in Level 2 are labeled as **Exploratory Pretrained Reproducibility Baselines**.

2. **`abychkov/dental-fdi-detection` Training Corpus:**
   - Pretrained on 4,000+ adult panoramic radiographs (18+ years) curated from independent clinical sources.
   - Zero intentional overlap with DENTEX enumeration splits.

---

## 5. Candidate Checkpoints Not Downloaded

| Candidate | Host / Format | Size | Decision / Rationale |
|---|---|---|---|
| `nsitnov/8024-yolov8-model` | HuggingFace (`8024.pt`) | 137.29 MB | Only PyTorch `.pt` hosted; no pre-exported ONNX weights. Deferred to maintain lightweight local ONNX runtime footprint. |
| `gegesay89/dental-findings-yolo-detector` | HuggingFace (`best.pt`) | 350.67 MB | Excessive VRAM footprint (~3.5 GB); 31 unbalanced classes; no native ONNX. |
| `HierarchicalDet` | GitHub (Code only) | N/A | Diffusion sampling requires multi-GPU cluster compute, incompatible with edge CPU target. |
| `BoneLoss-PAN769` | Zenodo / GitHub | ~120 MB | ResNet crestline model deferred to Level 3 specialized periodontal analysis. |
