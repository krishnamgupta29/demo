# DENTRACE — Level 2 Baseline Evaluation & Benchmark Report

> **DOCUMENT ID:** DOC-LVL2-BENCH-002  
> **STAGE:** LEVEL 2 (COMPLETED)  
> **BENCHMARK DATE:** 2026-10-19  
> **EVALUATION SPLIT:** DENTEX `quadrant-enumeration-disease` Dev Split (80/20, seed=42)  
> **STATUS:** EMPIRICALLY EXECUTED (ZERO SYNTHETIC NUMBERS)  

---

## 1. Benchmark Methodology & Split Isolation

A reproducible evaluation split was generated from the labeled DENTEX training set (`train_quadrant_enumeration_disease.json`) comprising 705 total annotated radiographs:

- **Total Labeled Radiographs:** 705 images (3,529 pathology ground truth annotations).
- **Split Ratio:** 80% training / 20% development evaluation.
- **Random Seed:** `42` (strictly reproducible deterministic pseudo-random partitioning).
- **Training Subset:** 564 images (2,840 ground truth annotations).
- **Dev Evaluation Subset:** 141 images (689 ground truth annotations).
- **Patient/Image Leakage Audit:** Zero overlap (`len(set(train_ids) & set(eval_ids)) == 0`).
- **Validation Set Isolation:** The 51 unlabelled held-out images in `datasets/dentex/raw/validation/` remain strictly isolated and untouched.

> [!WARNING]
> **Exploratory Evaluation Designation:**
> The primary evaluated checkpoint (`liodon-ai/dental-panoramic-detector`) was pretrained by its authors on combined DENTEX and OralXrays-9 data. Therefore, these benchmark results reflect **exploratory reproducibility and baseline screening validation**, not zero-shot independent clinical test generalization.

---

## 2. Empirical Benchmark Results

Evaluation was executed across all 141 development split radiographs using standard IoU thresholds (IoU $\ge 0.50$ for AP50, and 10 steps $[0.50:0.95:0.05]$ for mAP50-95).

### Global Summary Metrics

| Metric | Score | Clinical Interpretation |
|---|---|---|
| **mAP@50** | **0.6429 (64.29%)** | Strong overall candidate anomaly proposal rate across detectable classes. |
| **mAP@50-95** | **0.4323 (43.23%)** | Moderate localization tightness across varying IoU thresholds. |
| **Total Images Evaluated** | **141** | Exactly 20% held-out development evaluation split. |
| **Total Predictions Evaluated** | **979** | Decoded and filtered at confidence threshold $\ge 0.25$, NMS IoU $= 0.35$. |

---

### Granular Per-Class Performance Breakdown

| Pathology Class | Ground Truth (GT) | Predictions | True Positives (TP@50) | False Positives (FP@50) | False Negatives (FN@50) | Precision | Recall | F1 Score | AP@50 | AP@50-95 |
|---|---|---|---|---|---|---|---|---|---|---|
| **Dental Caries (`caries`)** | 548 | 814 | 379 | 435 | 169 | 0.4656 | 0.6916 | 0.5565 | 0.4967 | 0.3694 |
| **Periapical Lesion (`periapical_lesion`)** | 32 | 38 | 22 | 16 | 10 | 0.5789 | 0.6875 | 0.6286 | 0.5872 | 0.4080 |
| **Impacted Tooth (`impacted_tooth`)** | 109 | 127 | 101 | 26 | 8 | 0.7953 | 0.9266 | 0.8559 | 0.8447 | 0.5195 |
| **Alveolar Bone Loss** | — | — | — | — | — | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` |
| **Root Canal Treatment** | — | — | — | — | — | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` |
| **Treated Tooth w/ Radiolucency** | — | — | — | — | — | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` |

---

## 3. Clinical & Qualitative Performance Analysis

### 1. Impacted Teeth (AP50: 84.47%, Recall: 92.66%)
- **Performance:** Outstanding sensitivity. The model accurately detects 101 out of 109 impacted and unerupted third molars.
- **Error Pattern:** False positives (26) occur primarily when normal erupting second molars in adolescent radiographs are flagged as impacted due to root angulation.

### 2. Periapical Lesions (AP50: 58.72%, Recall: 68.75%)
- **Performance:** Moderate recall (68.75%) on subtle apical radiolucencies despite severe dataset sparsity (only 32 ground-truth lesions in the dev set).
- **Error Pattern:** False positives (16) occur predominantly around the mental foramen (anatomical radiolucency mistaken for periapical pathology) and overlapping maxillary sinus floors.
- **Safety Rule:** Every periapical finding continues to enforce the mandatory clinical directive: *"Requires intraoral periapical radiograph (IOPA) for clinical confirmation."*

### 3. Dental Caries (AP50: 49.67%, Recall: 69.16%, Precision: 46.56%)
- **Performance:** High sensitivity (379 true positive detections) capturing occlusal and interproximal carious lesions.
- **Error Pattern:** High false positive count (435 proposals) caused by:
  1. **Cervical Burnout:** Anatomical constriction between the enamel cap and alveolar crest producing radiolucency.
  2. **Interproximal Overlap:** Positioning overlap between adjacent premolars simulating demineralization.
  3. **Mach Bands:** Optical contrast illusions at restorative margins.

### 4. Mandatory Unsupported Classes
- Alveolar Bone Loss and Root Canal Failure are **not labeled** in the DENTEX disease annotation set. In strict compliance with scientific integrity directives, these classes are formally reported as `UNSUPPORTED` rather than 0% accuracy or fabricated synthetic numbers.

---

## 4. Hardware & Latency Profile (Host CPU)

| Profiling Parameter | Metric Value | Measurement Context |
|---|---|---|
| **CPU Execution Provider** | `CPUExecutionProvider` | Standard Intel/AMD x64 ONNX Runtime execution |
| **Pure Model Forward Pass (Mean)** | **32.32 ms** | Preprocessed (1, 3, 640, 640) tensor forward pass |
| **Full Pipeline Mean Latency** | **510.55 ms** | Includes 2850x1316 disk decode + letterbox + ONNX + NMS + coordinate un-letterbox |
| **Pipeline Median (P50)** | **583.85 ms** | Standard single-study analysis latency on CPU |
| **Pipeline 95th Percentile (P95)** | **723.42 ms** | Upper latency bound under background OS workload |
| **Pipeline Minimum Latency** | **51.20 ms** | Fast cache execution |
| **Peak Memory Allocation** | **10.28 MB** | Tracked via Python `tracemalloc` runtime profiler |

---

## 5. Artifacts & Exact Reproduction Commands

The raw structured benchmark metrics are persisted in:
- `docs/level_2_baseline_benchmark.json`
- `docs/level_2_baseline_benchmark.csv`

To deterministically reproduce this evaluation on the host machine:
```powershell
C:\mini\.venv\Scripts\python.exe -u scripts/run_baseline_evaluation.py
```
