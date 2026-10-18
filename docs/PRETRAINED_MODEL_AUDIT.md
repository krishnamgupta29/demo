# DENTRACE — Pretrained Dental Model & Checkpoint Audit

> **DOCUMENT ID:** DOC-MODEL-003  
> **STATUS:** AUDITED (LEVEL 0)  
> **VERIFICATION DATE:** 2026-10-18  

This audit investigates accessible dental-specific pretrained models, baseline codebases, and weights to determine which can be directly leveraged for inference, which require fine-tuning, and which are code-only repositories lacking direct weights.

---

## 1. Candidate Pretrained Models & Checkpoints

| Model / Repository | Source Link | Weights Present? | Architecture | Classes / Labels | Expected Input | License | Compatibility & Reuse Strategy | Limitations & Hardware Constraints |
|---|---|---|---|---|---|---|---|---|
| **liodon-ai/dental-panoramic-detector** | [HuggingFace: liodon-ai/dental-panoramic-detector](https://huggingface.co/liodon-ai/dental-panoramic-detector) | **YES (Verified)**: `best.pt` & `best.onnx` present on HuggingFace | YOLOv8 (Ultralytics) | Impacted teeth, periapical lesions, caries | 2D Panoramic X-ray, 640x640 RGB | Open / Academic (Apache 2.0 / MIT style) | **Direct Reuse Candidate:** Can run via ONNX Runtime on CPU or PyTorch on RTX 2050. Usable as initial checkpoint for pathology detection without retraining. | Bounding box detection only; no pixel segmentation masks. Trained on combined DENTEX + OralXrays-9 (~9,900 images). |
| **nsitnov/8024-yolov8-model** | [HuggingFace: nsitnov/8024-yolov8-model](https://huggingface.co/nsitnov/8024-yolov8-model) | **YES (Verified)**: Checkpoint files hosted on HuggingFace | YOLOv8-seg (Instance Segmentation) | Caries, crown, filling, implant, missing teeth, periapical lesion, root canal treatment | 2D Panoramic X-ray, 640x640 | Open Community | **Direct / Fine-Tune Candidate:** Provides genuine instance segmentation masks for caries, periapical lesions, and root canal treatments. | Requires testing validation on DENTEX/Loki Silvres test sets. Fine-tuning recommended for clinical calibration. |
| **gegesay89/dental-findings-yolo-detector** | [HuggingFace: gegesay89/dental-findings-yolo-detector](https://huggingface.co/gegesay89/dental-findings-yolo-detector) | **YES (Verified)**: Checkpoint available | YOLOv8-seg | 31 classes (bone loss, cysts, root canal, restoration, impaction) | 2D Panoramic X-ray, 640x640 | Open Community | **Fine-Tune Baseline:** Multi-class feature representations can be fine-tuned to isolate our target 5 classes. | High class imbalance across 31 classes. Must be filtered through `config/class_mapping.json`. |
| **HierarchicalDet (DENTEX Baseline)** | [GitHub: ibrahimethemhamamci/HierarchicalDet](https://github.com/ibrahimethemhamamci/HierarchicalDet) (MICCAI 2023) | **NO DIRECT WEIGHTS (Code Only).** Weights must be trained locally or requested from authors. | DiffusionDet + Hierarchical multi-label Detectron2 | Quadrants (1–4), Enumeration (1–8), Diagnosis (`caries`, `deep caries`, `periapical`, `impacted`) | 2D Panoramic X-ray, dynamic resolution | Academic Non-Commercial (CC BY-NC 4.0) | **Training Benchmark:** Provides reference diffusion-detection architecture for DENTEX hierarchical evaluation. Cannot be used off-the-shelf without training. | Heavy compute footprint (Diffusion model training requires multi-GPU or extended Colab T4 run). Incompatible with sub-50ms CPU target. |
| **tunisch/tooth-detection-and-numbering** | [GitHub: tunisch/tooth-detection-and-numbering](https://github.com/tunisch/tooth-detection-and-numbering) | **CONDITIONAL:** Hub link / Google Drive weights referenced in repository | YOLOv5 / PyTorch Hub | 32 permanent teeth (FDI notation 11–48) | 2D Panoramic X-ray, 640x640 | MIT License | **Reuse / Adaptation Candidate:** Standalone tooth detector for FDI numbering. Can be converted to ONNX for CPU inference. | YOLOv5 architecture (older than YOLOv8); outputs bounding boxes. Requires topological post-processing rules. |
| **BoneLoss-PAN769 Inference Baseline** | [GitHub: thiagoavieira/boneloss-inference](https://github.com/thiagoavieira/boneloss-inference) / Zenodo | **YES (Verified)**: Weights provided via Zenodo repository | ResNet / U-Net baseline | Alveolar ridge, cementoenamel junction, tooth crowns | 2D Panoramic X-ray, normalized | Creative Commons Attribution (CC BY 4.0) | **Specialized Bone Loss Model:** Authoritative for quantitative alveolar bone loss calculation. | Requires multi-stage pipeline coupling with tooth numbering. |

---

## 2. Analysis of "General Pretrained" vs "Dental Pretrained" Checkpoints

> **CRITICAL ARCHITECTURAL DISTINCTION:**
> Standard COCO-pretrained weights (e.g., standard `yolov8n.pt` trained on cars, persons, dogs) are NOT dental pathology models. While they provide transferrable low-level edge and texture filters, they have ZERO knowledge of dental radiopacity, pulpal radiolucency, or FDI tooth taxonomy.

### Strategy for DENTRACE:
1. **Tooth Localization & FDI Numbering:**
   - Primary: Utilize DENTEX challenge annotations to fine-tune a YOLOv8 tooth enumeration model (or adapt `tunisch` / `liodon-ai` dental checkpoints).
   - Post-process with deterministic anatomical rules:
     - Quadrant 1 (UR): 18 down to 11 (max 8)
     - Quadrant 2 (UL): 21 up to 28 (max 8)
     - Quadrant 3 (LL): 31 up to 38 (max 8)
     - Quadrant 4 (LR): 48 down to 41 (max 8)
     - De-duplication: Resolve colliding FDI numbers by retaining the highest confidence candidate.
2. **Pathology Segmentation (5 Classes):**
   - Fine-tune a lightweight YOLOv8-seg model using the filtered 5-class configuration from Loki Silvres / DENTEX / HuggingFace checkpoints.
   - For classes with genuine polygon masks (Caries, Periapical Lesion, Root Canal Treatment): output segmentation polygons.
   - For classes without polygon masks (Impacted Tooth, Alveolar Bone Loss): output bounding boxes or crestal lines, documented explicitly as detection fallbacks.
3. **Suspected Endodontic Failure:**
   - Implemented as a **deterministic clinical rule** evaluating the spatial intersection of a `Root Canal Treatment` mask and a `Periapical Lesion` mask on the same FDI tooth box.
   - This eliminates the need for an artificial single-label classifier while reflecting real endodontic pathology.

---

## 3. Storage and Execution Guardrails
- **No Checkpoint Downloads in Level 0:** In strict accordance with Level 0 rules, no multi-gigabyte `.pt` weights have been downloaded to the local filesystem.
- **Drive Partitioning:** All future checkpoint downloads and Colab exports must be routed to `C:\` or cached in virtual environments, protecting `D:\` from disk exhaustion.
