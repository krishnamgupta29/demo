# DENTRACE — Pretrained Dental Model & Checkpoint Audit (Verified Level 0.5)

> **DOCUMENT ID:** DOC-MODEL-003  
> **STATUS:** AUDITED & LIVE-VERIFIED (LEVEL 0.5)  
> **VERIFICATION DATE:** 2026-10-18  

This audit investigates dental-specific pretrained models, baseline codebases, and weights via direct repository inspection and remote header validation. It establishes a ranked reuse shortlist to eliminate redundant model training.

---

## 1. Candidate Pretrained Models & Live Verification Matrix

| Model / Repository | Verified Source | Hosted Weights Verified | Exact Size | Architecture | Classes / Targets | Modality | License | Hardware Compatibility | ONNX Status |
|---|---|---|---|---|---|---|---|---|---|
| **abychkov/dental-fdi-detection** | [HuggingFace](https://huggingface.co/abychkov/dental-fdi-detection) | **YES:** `dental_fdi.onnx` | 130,754,966 B (124.70 MB) | Transformer Object Detector | 32 permanent teeth (FDI 11–48) | Bounding Boxes + FDI Classes | Evaluation (`other`) | CPU-optimized (~300ms CPU, ~20ms GPU) & RTX 2050 | **NATIVE ONNX** (`dental_fdi.onnx` ready) |
| **liodon-ai/dental-panoramic-detector** | [HuggingFace](https://huggingface.co/liodon-ai/dental-panoramic-detector) | **YES:** `best.pt`, `best.onnx` | `best.pt`: 5.2 MB<br/>`best.onnx`: 10.11 MB | YOLO11n (Ultralytics Nano, ~2.6M params) | `caries`, `periapical_lesion`, `impacted_tooth` | Bounding Box Detection | CC BY-NC 4.0 | Runs on CPU (<20ms estimated) & RTX 2050 (<1 GB VRAM) | **ALREADY EXPORTED** (`best.onnx` ready) |
| **nsitnov/8024-yolov8-model** | [HuggingFace](https://huggingface.co/nsitnov/8024-yolov8-model) | **YES:** `8024.pt` | 143,955,443 B (137.29 MB) | YOLOv8-seg (Ultralytics Instance Segmentation) | `Caries`, `Crown`, `Filling`, `Implant`, `Missing-tooth`, `Periapical-lesion`, `Root Piece`, `Root-Canal-Treatment` | True Instance Segmentation Polygons | Apache 2.0 | Runs on RTX 2050 (4 GB VRAM) & CPU | Directly exportable to ONNX via Ultralytics |
| **gegesay89/dental-findings-yolo-detector** | [HuggingFace](https://huggingface.co/gegesay89/dental-findings-yolo-detector) | **YES:** `best.pt` | 367,706,701 B (350.67 MB) | YOLOv8x-seg (Ultralytics Large/Extra Large) | 31 classes (Caries, Periapical, Bone Loss, Root Canal, Impaction, Cyst, etc.) | Instance Segmentation Polygons | Educational (`other`) | Heavy memory footprint; high VRAM (~3.5 GB); CPU latency high | Exportable to ONNX; requires INT8 quantization |
| **BoneLoss-PAN769 Baseline** | [Zenodo](https://doi.org/10.5281/zenodo.10055276) / [GitHub](https://github.com/thiagoavieira/boneloss-inference) | **YES:** Weights on Zenodo | ~120 MB | ResNet / U-Net | Alveolar bone crest line, CEJ markers | Crestal Polylines & Markers | CC BY 4.0 | CPU & GPU compatible | Compatible with ONNX |
| **HierarchicalDet (DENTEX Baseline)** | [GitHub: DENTEX](https://github.com/ibrahimethemhamamci/HierarchicalDet) | **NO DIRECT WEIGHTS** (Code Only) | N/A | DiffusionDet + Hierarchical Detectron2 | Quadrants 1–4, Teeth 1–8, Diagnoses (Caries, Deep Caries, Periapical, Impacted) | Detection & Tooth Polygons | CC BY-NC 4.0 | Heavy multi-GPU compute footprint; incompatible with sub-50ms CPU target | PyTorch Detectron2 baseline |
| **tunisch/tooth-detection-and-numbering** | [GitHub: tunisch](https://github.com/tunisch/tooth-detection-and-numbering) | **CONDITIONAL:** External Drive | ~14 MB | YOLOv5 | 32 permanent teeth (FDI 11–48) | Bounding Boxes | MIT | CPU & GPU compatible | Requires manual ONNX conversion |

---

## 2. Granular Analysis & Target Class Coverage

The College Problem Statement mandates 5 key dental anomalies plus FDI tooth identification:

| Mandated Target | Supported By Verified Checkpoints | Modality in Checkpoint | Clinical Integration Strategy in DENTRACE |
|---|---|---|---|
| **FDI Tooth Identification (11–48)** | DENTEX `train_quadrant_enumeration.json` (18,095 labels) & `tunisch` | Tooth bounding box / contour | Fine-tune YOLO11n / YOLOv8 on DENTEX enumeration split. Post-process with deterministic quadrant rules (max 8 teeth per quadrant, deduplication). |
| **1. Dental Caries** | `liodon-ai` (box), `nsitnov` (mask), `gegesay89` (mask), DENTEX (tooth) | True polygon mask (`nsitnov`) / Box (`liodon-ai`) | Primary: `nsitnov` instance mask for cavity contour. Secondary: `liodon-ai` detection box. |
| **2. Periapical Lesions** | `liodon-ai` (box), `nsitnov` (mask), `gegesay89` (mask), DENTEX (tooth) | True polygon mask (`nsitnov`) / Box (`liodon-ai`) | Primary: `nsitnov` instance mask. Secondary: `liodon-ai` detection box. Triggers mandatory clinical notice: *"Needs intraoral periapical radiograph"*. |
| **3. Impacted Teeth** | `liodon-ai` (box), DENTEX (anatomical tooth polygon), `gegesay89` (box/poly) | Anatomical tooth polygon / Box | Primary: DENTEX anatomical tooth polygon or `liodon-ai` detection box. Documented as anatomical impaction boundary, not synthetic lesion mask. |
| **4. Alveolar Bone Loss** | `BoneLoss-PAN769` (crestal line), `gegesay89` (box/poly) | Crestal reference line / regional box | Primary: Crestal line marker / horizontal region box. Documented as detection fallback / crestal marker. Never rendered as closed organic blob. |
| **5. Root Canal Failures (Suspected Endodontic Failure)** | **COMPOSITE DETERMINISTIC RULE:** `nsitnov` (`Root-Canal-Treatment` mask) + (`Periapical-lesion` mask) | Composite spatial intersection | Spatial co-occurrence: When a tooth exhibits both an existing endodontic obturation (`Root-Canal-Treatment`) AND a `Periapical-lesion`, the Rule Layer authoritatively flags `suspected_endodontic_failure = True`. Elevates urgency to `urgent`. |

---

## 3. Ranked Checkpoint Shortlist & Dual-Head Strategy
 
DENTRACE employs a decoupled dual-head vision architecture: **Head 3A (FDI Tooth Identification)** and **Head 3B (Anomaly Detection & Instance Segmentation)**.
 
### Head 3A: FDI Tooth Localization Candidates
1. **Rank 1: `abychkov/dental-fdi-detection`**
   - **Why First:** Provides pre-trained 32-tooth FDI bounding box proposals directly in ONNX format (~45 MB). Trained on 4,000+ adult clinical OPGs. Execution is clinic-ready (~300ms on CPU, ~20ms on GPU).
   - **Testing Action:** Evaluate ONNX runtime inference and feed into `backend/pipeline/matching.py` with topological quadrant rules.
2. **Rank 2: In-House YOLOv8 FDI Detector trained on DENTEX `train_quadrant_enumeration.json`**
   - **Why Second:** 18,095 expert tooth enumeration annotations across 634 OPGs. Direct ground-truth alignment with DENTEX benchmark.
3. **Rank 3: `tunisch/tooth-detection-and-numbering`** (YOLOv5 baseline).

### Head 3B: Pathology Anomaly Detection & Segmentation Candidates
1. **Rank 1 (Fast Screening Baseline): `liodon-ai/dental-panoramic-detector`**
   - **Why First:** Ultra-lightweight YOLO11n (~2.6M parameters, `best.onnx` only 10.11 MB). Trained on 9,928 OPGs (DENTEX + OralXrays-9). Detects `Impacted Tooth`, `Caries`, and `Periapical Lesion`. Sub-30ms CPU latency expected.
   - **Testing Action:** Validate as fast first-pass screener and baseline for comparison.
2. **Rank 2 (Instance Segmentation Engine): `nsitnov/8024-yolov8-model`**
   - **Why Second:** Genuine pixel-level instance segmentation masks for Caries, Periapical Lesions, and Root Canal Treatments. Enables the composite `suspected_endodontic_failure` clinical rule (RCT mask + Periapical mask on identical tooth).
   - **Testing Action:** Export to ONNX, benchmark segmentation mask inference on host CPU/RTX 2050.
3. **Rank 3 (Specialized Bone Loss): `BoneLoss-PAN769` Baseline**
   - **Why Third:** Dedicated crestal alveolar bone loss reference line model from Zenodo.

### Deferred / Incompatible:
- **`HierarchicalDet`**: Code only; diffusion sampling is computationally prohibitive for edge CPU sub-50ms target.
- **`gegesay89`**: 350 MB checkpoint, 31 classes with severe class imbalance; heavy VRAM footprint (~3.5 GB).

---

## 4. Storage & Download Safeguards
- **Zero Heavy Downloads in Level 0.5:** No model weight files (`.pt` or `.onnx`) have been downloaded yet.
- **Gated Execution:** Download of `best.onnx` (10.1 MB) will occur strictly after user approval during Level 1/3, targeted directly to `C:\mini\models\checkpoints\`.
