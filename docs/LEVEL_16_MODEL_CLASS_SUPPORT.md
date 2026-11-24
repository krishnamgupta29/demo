# LEVEL 16 — DENTRACE MODEL CLASS SUPPORT & DEEP CARIES AUDIT
**Technical Investigation of Pathology Class Taxonomy, Model Discrepancies, and ONNX Runtime Contracts**  
*Academic College Decision Support Prototype | Localhost Execution (127.0.0.1)*  
*Date of Audit: November 14, 2026*  
*Regulatory Boundary: "Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR."*

---

## 1. Executive Summary: The Deep Caries Discrepancy

In the Level 6.1 training and evaluation report (`docs/LEVEL_6_1_TRAINING_RESULTS.md`), DENTRACE documented benchmark metrics for four pathology classes: **Caries**, **Deep Caries**, **Periapical Lesion**, and **Impacted Tooth**. Conversely, the Level 14 comprehensive audit (`docs/LEVEL_14_CURRENT_STATE_AUDIT.md`) observed that deep caries was completely unavailable and unpredicted during live clinical screening of panoramic radiographs.

This audit report details the root cause of this apparent inconsistency, inspects the physical ONNX models, class indices, and dataset mappings, and documents the architectural resolution implemented in Level 16.

### Primary Audit Findings:
1. **The Discrepancy is Real and Rooted in Architecture:**
   - The Level 6.1 report evaluated the locally fine-tuned **`dentex-yolov8n-seg`** instance segmentation model (`dentex_yolov8n_seg.onnx`), which was trained on the 4-class DENTEX 2023 dataset and natively contains a distinct `deep_caries` class (Class Index 3).
   - In Level 11/12, the single-page workspace pipeline configured the lightweight **`liodon-panoramic-screener`** (`best.onnx`) as the default active inference head. This 3-class model was trained on an external dataset containing only `caries`, `periapical_lesion`, and `impacted_tooth`.
   - The Level 14 audit evaluated the active default pipeline and truthfully reported that deep caries was unavailable in that runtime.
2. **Zero Model Retraining Principle:**
   - In accordance with project rules, no models were retrained, synthetic weights fabricated, or simulated deep-caries detections generated.
3. **Level 16 Architectural Resolution:**
   - DENTRACE now provides an explicit **Model Selector** in the clinical workspace.
   - When `liodon-panoramic-screener` is active, the interface truthfully displays deep caries as **`NOT ASSESSED BY CURRENT SCREENER`**.
   - When `dentex-yolov8n-seg` is selected, the 4-class instance segmenter is invoked, enabling true deep caries detection with polygon segmentation masks.

---

## 2. Model-Wise Class Support Matrix

The following matrix compares all registered candidate models in `backend/services/model_adapter.py`:

| Model Identifier | Architecture | Weight File Path | Classes Supported | Deep Caries Supported? | Detection Type | Active In Level 16 |
|---|---|---|---|---|---|---|
| **`liodon-panoramic-screener`** | YOLO11n (Nano) | `models/checkpoints/best.onnx` | `caries`, `periapical_lesion`, `impacted_tooth` (3 classes) | **NO** (Not in training taxonomy) | Bounding Box `(1, 7, 8400)` | **YES** (Default Screener) |
| **`dentex-yolov8n-seg`** | YOLOv8n-seg | `models/checkpoints/dentex_yolov8n_seg.onnx` | `impacted_tooth`, `caries`, `periapical_lesion`, `deep_caries` (4 classes) | **YES** (Class index 3) | Instance Segmentation `(1, 40, 8400)` + `(1, 32, 160, 160)` | **YES** (Segmenter Mode) |
| **`dentex-yolov8n-seg-int8`** | YOLOv8n-seg (INT8) | `models/checkpoints/dentex_yolov8n_seg_int8.onnx` | `impacted_tooth`, `caries`, `periapical_lesion`, `deep_caries` (4 classes) | **YES** (Class index 3) | Instance Segmentation `(1, 40, 8400)` + `(1, 32, 160, 160)` | **AVAILABLE** (Quantized) |
| **`nsitnov-8024-seg`** | YOLOv8x-seg | `models/checkpoints/8024.onnx` | `Caries`, `Crown`, `Filling`, `Implant`, `Missing-tooth`, `Periapical-lesion`, `Root Piece`, `Root-Canal-Treatment` (8 classes) | **NO** (Only general Caries) | Instance Segmentation `(1, 44, 8400)` + `(1, 32, 160, 160)` | **AVAILABLE** |
| **`abychkov-fdi-detection`** | Transformer / YOLO | `models/checkpoints/dental_fdi.onnx` | 32 Adult FDI teeth (11–18, 21–28, 31–38, 41–48) | **N/A** (Tooth Localization Only) | Bounding Box `(1, 300, 36)` | **YES** (FDI Mapper) |
| **`boneloss-pan769-baseline`** | ResNet50 / U-Net | `models/checkpoints/boneloss_pan769.onnx` | `alveolar_bone_loss`, `cej_line`, `crestal_bone_line` | **N/A** (Periodontal Assessment) | Segmentation Line `(1, 3, 512, 1024)` | **BLOCKED** (Missing crestal landmarks) |

---

## 3. Detailed Model Inspection & Class Taxonomy

### 3.1 `liodon-panoramic-screener` (`best.onnx`)
- **Origin:** HuggingFace `liodon-ai/dental-panoramic-detector`.
- **ONNX Input Tensor:** `images: [1, 3, 640, 640]` (Float32).
- **ONNX Output Tensor:** `output0: [1, 7, 8400]`.
  - Slice `[0:4]`: Bounding box coordinates $(x_c, y_c, w, h)$ normalized to 640.
  - Slice `[4]`: Class 0 — `caries`
  - Slice `[5]`: Class 1 — `periapical_lesion`
  - Slice `[6]`: Class 2 — `impacted_tooth`
- **Class Analysis:** This model possesses exactly 3 class channels. It has no channel for `deep_caries`. Under no circumstances can this model infer deep caries.

### 3.2 `dentex-yolov8n-seg` (`dentex_yolov8n_seg.onnx`)
- **Origin:** Fine-tuned in Level 6.1 using Ultralytics YOLOv8n-seg on the DENTEX 2023 challenge dataset.
- **Dataset Configuration (`dentex_4class.yaml`):**
  ```yaml
  names:
    0: impacted_tooth
    1: caries
    2: periapical_lesion
    3: deep_caries
  ```
- **ONNX Input Tensor:** `images: [1, 3, 640, 640]` (Float32).
- **ONNX Output Tensors:**
  - `output0: [1, 40, 8400]` (4 box coordinates + 4 class probabilities + 32 mask coefficients).
  - `output1: [1, 32, 160, 160]` (32 prototype mask bases at 1/4 resolution).
- **Performance from Level 6.1 Evaluation:**
  - `deep_caries` Precision: **0.584**, Recall: **0.521**, mAP@50: **0.548**.
  - Provides true pixel-level segmentation polygons distinguishing shallow enamel lesions from deep dentinal/pulpal involvement.

---

## 4. Truthful Clinical Presentation in Level 16

To prevent clinician confusion and eliminate discrepancies:

1. **Explicit Model Telemetry in UI Header:**
   The clinical header displays the active inference model:
   - `Liodon Screener (BBox - Fast)`: Ultra-fast initial triaging.
   - `DENTEX Segmenter (Instance Seg - 4 Class)`: Detailed anatomical segmentation including deep caries.
2. **Pathology Support Status Display:**
   When `liodon-panoramic-screener` is selected:
   - Caries: `SUPPORTED & ASSESSED`
   - Periapical Lesion: `SUPPORTED & ASSESSED`
   - Impacted Tooth: `SUPPORTED & ASSESSED`
   - Deep Caries: **`NOT ASSESSED BY CURRENT SCREENER`**
3. **No Hallucinated Findings:**
   The system never infers deep caries from a 3-class model. Deep caries is only output when the 4-class DENTEX segmenter is actively executed.

---

## 5. Verification Commands

To verify class support directly from the ONNX weights using Python:
```python
import onnxruntime as ort
import numpy as np

# 1. Verify Liodon Screener (3 classes -> shape [1, 7, 8400])
sess_liodon = ort.InferenceSession("models/checkpoints/best.onnx", providers=["CPUExecutionProvider"])
out_liodon = sess_liodon.run(None, {"images": np.zeros((1, 3, 640, 640), dtype=np.float32)})
print("Liodon Output Shape:", out_liodon[0].shape)  # (1, 7, 8400) -> 4 coords + 3 classes

# 2. Verify DENTEX Segmenter (4 classes -> shape [1, 40, 8400])
sess_dentex = ort.InferenceSession("models/checkpoints/dentex_yolov8n_seg.onnx", providers=["CPUExecutionProvider"])
out_dentex = sess_dentex.run(None, {"images": np.zeros((1, 3, 640, 640), dtype=np.float32)})
print("DENTEX Box/Class Shape:", out_dentex[0].shape)  # (1, 40, 8400) -> 4 coords + 4 classes + 32 proto
print("DENTEX Proto Mask Shape:", out_dentex[1].shape) # (1, 32, 160, 160)
```
