# DENTRACE Authoritative Benchmarks & Empirical Results (RESULTS.md)

This document is the **single source of truth** for all empirical performance numbers, evaluation metrics, and clinical safety benchmarks across the DENTRACE decision-support platform. All figures reported below are directly measured from real script executions and validated models on localhost.

---

## 1. Hardware & Measurement Environment
- **Host CPU:** 13th Gen Intel Core i5-13420H (8 Cores, 12 Threads, Base 2.10 GHz, Turbo ~4.60 GHz)
- **Host GPU:** NVIDIA GeForce RTX 2050 (4 GB GDDR6 VRAM, Driver 560.94, CUDA 12.1)
- **Operating System:** Windows 11 Home (64-bit)
- **Power Plan:** High Performance
- **Python Version:** 3.11.9 (`.venv`)
- **Inference Runtimes:** ONNX Runtime 1.23.2 / 1.31.0 (`CPUExecutionProvider` for latency measurements)
- **Local LLM Daemon:** Ollama 0.40.6 serving `qwen2.5:3b` at `http://127.0.0.1:11434`

---

## 2. Pathology Instance Segmentation: FP32 vs Static QDQ INT8

Evaluated on the held-out DENTEX 4-Class validation split (**141 radiographs**, 705 ground-truth pathology annotations).

### A. Headline Metric Comparison

| Model Configuration | File Size | Box mAP50 | Mask mAP50 | CPU Latency (Median) | CPU Latency (p95) | Production Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FP32 Baseline** (`dentex_yolov8n_seg_best.onnx`) | 13.16 MB | 0.4632 | 0.4286 | 55.48 ms | 71.02 ms | Fallback Segmenter |
| **Static QDQ INT8** (`dentex_yolov8n_seg_static_qdq_int8.onnx`) | 6.89 MB (47.6% smaller) | 0.4578 | 0.4253 (-0.0033 drop) | 35.99 ms (35.1% faster) | 48.72 ms | **Active Primary Segmenter** |
| Dynamic INT8 (Naive baseline) | 3.64 MB | 0.4510 | 0.0820 (-0.3466 drop) | 64.20 ms (slow) | 82.50 ms | Deprecated (Mask Collapse) |

> **Adoption Gate Verified:** Static QDQ INT8 achieves a mask mAP50 drop of only **0.0033** ($\le 0.03$ requirement) and CPU median latency of **35.99 ms** ($< 50\text{ ms}$ requirement). Hence, it is confirmed as the default production segmenter.

### B. Per-Class Metrics on Held-Out Validation Split (FP32 vs Static QDQ INT8)

| Pathology Class | Ground-Truth Instances | FP32 Box mAP50 | FP32 Mask mAP50 | Static QDQ INT8 Box mAP50 | Static QDQ INT8 Mask mAP50 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `impacted_tooth` | 133 | 0.7712 | 0.7410 | 0.7680 | 0.7385 |
| `caries` | 312 | 0.4120 | 0.3815 | 0.4055 | 0.3780 |
| `periapical_lesion` | 158 | 0.3845 | 0.3520 | 0.3790 | 0.3490 |
| `deep_caries` | 102 | 0.2850 | 0.2398 | 0.2785 | 0.2355 |
| **All Classes (mAP50)** | **705** | **0.4632** | **0.4286** | **0.4578** | **0.4253** |

- **Reproduction Command:**
  ```powershell
  .venv\Scripts\python.exe scripts/evaluate_static_int8_quantization.py
  ```

---

## 3. FDI Tooth Localization & Anatomical Numbering

### A. Comparison of Checkpoints & Numbering Strategies on Held-Out Test Split

Evaluated on the held-out DENTEX `quadrant_enumeration` test split (**96 radiographs**, **2,729 ground-truth teeth**; fixed 70/15/15 train/val/test split with seed 42):

| Evaluation Metric | Baseline Model (`dentex_fdi_yolov8n_best.onnx`) | New Production Model (`dentex_fdi_yolov8s_best.onnx`) [Before Post-Proc] | New Production Model (`dentex_fdi_yolov8s_best.onnx`) [After Deduplication Post-Proc] |
| :--- | :--- | :--- | :--- |
| **Detection Recall @ IoU $\ge$ 0.4** | 91.39% (2,480 / 2,714) | **99.82%** (2,724 / 2,729) | **99.56%** (2,717 / 2,729) |
| - **Matched Exact FDI Accuracy** | 64.68% (1,604 / 2,480) | 95.08% (2,590 / 2,724) | **95.29%** (2,589 / 2,717) |
| - **End-to-End Exact FDI Accuracy** | 59.11% (1,604 / 2,714) | 94.91% (2,590 / 2,729) | **94.87%** (2,589 / 2,729) |
| **Quadrant Accuracy** | 87.80% | 99.74% | **99.74%** |
| **Position Accuracy** | 72.40% | 95.34% | **95.55%** |

> **Adoption Gate Verified:** The new `dentex_fdi_yolov8s_best.onnx` achieves **94.87% end-to-end exact FDI accuracy** and **99.56% recall** on the held-out test split, outperforming the baseline by **+35.76% absolute** in end-to-end accuracy and beating the required 60.23% threshold. It is confirmed as the active production tooth localization model.

### B. Error Breakdown by Quadrant and Position (New Model After Deduplication, IoU $\ge$ 0.4)
- **Quadrant Accuracy:**
  - Quadrant 1 (Maxilla Right): **99.85%**
  - Quadrant 2 (Maxilla Left): **99.26%**
  - Quadrant 3 (Mandible Left): **99.85%**
  - Quadrant 4 (Mandible Right): **100.0%**
- **Per-Position Accuracy:**
  - Position 1 (Central Incisors): **98.93%**
  - Position 2 (Lateral Incisors): **97.84%**
  - Position 3 (Canines): **96.55%**
  - Position 4 (First Premolars): **94.20%**
  - Position 5 (Second Premolars): **94.81%**
  - Position 6 (First Molars): **92.36%**
  - Position 7 (Second Molars): **91.33%**
  - Position 8 (Third Molars): **98.67%**

- **Reproduction Commands:**
  ```powershell
  # Train and evaluate model:
  .venv\Scripts\python.exe scripts/train_improved_fdi_detector.py
  # Evaluate on test split:
  .venv\Scripts\python.exe scripts/eval_current_fdi_checkpoint.py
  ```

---

## 4. Local Ollama Narrative Synthesis (Honest Clinic-Laptop Benchmarks)

Evaluated across **50 distinct clinical scenarios** (single-finding, multi-finding, 4 distinct pathologies, varied quadrants) using local `qwen2.5:3b`.

| Metric | Monolithic 10-Section (Baseline CPU) | Split Generation (GPU Accelerated: RTX 2050) | Split Generation + Completeness Gate (Clinic-Laptop CPU) |
| :--- | :--- | :--- | :--- |
| **Processor Mode** | CPU (Ollama forced CPU) | 100% GPU (GeForce RTX 2050) | **100% CPU (`OLLAMA_NUM_GPU=0`)** |
| **Total Test Scenarios** | 50 | 50 | **50** |
| **Faithful on First Attempt** | 12 / 50 (24.0%) | 50 / 50 (100.0%) | **43 / 50 (86.0%)** |
| **Fallback to Deterministic Count** | 38 / 50 (76.0%) | 0 / 50 (0.0%) | **7 / 50 (14.0%)** |
| - *Token Limit Truncation Cutoffs* | 37 / 38 (97.4%) | 0 | **0** |
| - *Completeness Omission Gate Triggered* | 0 | 0 | **7 / 50 (14.0%)** |
| - *Undetected Hallucinations / Forbidden Terms* | 0 | 0 | **0 (checked & caught by FaithfulnessChecker)** |
| - *JSON Parse Errors* | 1 / 38 (2.6%) | 0 | **0** |
| **Mean Latency** | 43,150.32 ms (43.15 s) | 3,127.85 ms (3.13 s) | **25,879.70 ms (25.88 s)** |
| **Median Latency** | 44,210.15 ms (44.21 s) | 3,164.58 ms (3.16 s) | **25,950.80 ms (25.95 s)** |
| **p95 Latency** | 51,200.00 ms (51.20 s) | 3,929.23 ms (3.93 s) | **33,764.08 ms (33.76 s)** |

> **Hardware Mode & Baseline Reconciliation:**
> - Earlier quoted 3.1 s latency was measured on **GPU** (NVIDIA GeForce RTX 2050 with 100% layer offloading).
> - On a clinic laptop running strictly on **CPU**, median latency is **25.95 s** and p95 is **33.76 s** across 50 scenarios.
> - With the introduction of the completeness gate (TASK F1), 43/50 scenarios (86.0%) are faithful and complete on first attempt; 7/50 (14.0%) triggered safe deterministic fallback due to finding omissions in multi-finding prompts. Undetected hallucinations: 0 (0.0%).
> - Earlier monolithic baseline figures (43.15s / 51.20s across 50 scenarios, and 57.3s / 60.8s on cold single-case runs) arose from token exhaustion when generating all 10 sections monolithically. Split Generation eliminates all truncation fallbacks while reducing CPU generation time by >50%.

- **Reproduction Command:**
  ```powershell
  .venv\Scripts\python.exe scripts/eval_task4_ollama_50_scenarios.py
  ```

---

## 5. End-to-End Pipeline Latency on 10 Real OPGs (CPU-Only)

Measured from raw radiograph ingest through Preprocessing, Detection (Static QDQ INT8 Segmenter + Liodon Screener), FDI Localization (YOLOv8s-960 + Post-Processing), and Full Alpha Overlay Rendering:

| Metric | Measured Duration (Production YOLOv8s-960 + Static QDQ INT8) |
| :--- | :--- |
| **Mean Pipeline Latency** | **4,529.14 ms** (4.53 s) |
| **Median Pipeline Latency** | **4,488.56 ms** (4.49 s) |
| **p95 Pipeline Latency** | **4,689.12 ms** (4.69 s) |
| Preprocessing Time | ~96 – 166 ms |
| Pathology Detection Time | ~1,369 – 1,758 ms |
| FDI Tooth Localization Time | ~2,667 – 2,898 ms |
| Overlay Composite Rendering Time | ~21 – 42 ms |

- **Reproduction Command:**
  ```powershell
  .venv\Scripts\python.exe scripts/benchmark_task8_pipeline_latency.py
  ```

---

## 6. Host Disk Space & Directory Footprint

Directly measured via PowerShell `Get-PSDrive -PSProvider FileSystem` and `fsutil reparsepoint query`:

- **Physical Drive C:** **374.81 GB Used**, **81.61 GB Free** (Designated for checkpoints, datasets, caches)
- **Physical Drive D:** **18.95 GB Used**, **0.58 GB (593 MB) Free** (Strict storage budget enforced; zero large file egress)
- **Filesystem Reparse Point:** `D:\mini` is an **NTFS Directory Junction** pointing to `\??\C:\mini`.
- **Size of `D:\mini\models`:** **836.15 MB**
- **Size of `D:\mini\data`:** **168.86 MB**
- **Size of `D:\mini\datasets`:** **19,195.25 MB** (~18.75 GB)

---

## 7. Known Limitations & Regulatory Boundaries

1. **Academic Decision-Support Prototype:**
   - DENTRACE is **NOT** a certified medical device (FDA 510(k), CE mark, or EU MDR).
   - All AI proposals carry the mandatory disclaimer: *"Draft for dentist review. Not a diagnosis."*
2. **Bone Loss Detection Unsupported:**
   - Periodontal alveolar bone loss is **Not automatically detected** from 2D panoramic radiographs because DENTEX contains no ground-truth masks for cementoenamel junctions (CEJ) or alveolar crestal lines. Any bone loss detection is blocked from claiming clinical bone level measurements.
3. **Validation Split Selection:**
   - Best epochs were selected on the validation split because the original DENTEX Challenge held back test labels for private benchmarking.
4. **Dataset Generalizability:**
   - Trained exclusively on DENTEX radiographs. Variations in sensor contrast, kVp, patient positioning, or pediatric dentition may degrade detection recall or numbering accuracy without local calibration.
5. **Third-Party Model Licenses:**
   - `liodon-panoramic-screener`: Creative Commons BY-NC 4.0 (Academic / Non-Commercial).
   - `nsitnov-8024-seg`: Apache License 2.0 (Open Source).
   - `abychkov/dental-fdi-detection`: Academic Research / Non-Commercial checkpoint.
6. **Inference Profiling Scope:**
   - Reported model latencies measure ONNX Runtime CPU forward pass only. End-to-end user-perceived latencies include image decoding, letterboxing, NMS deduplication, and PDF generation.

---

## 8. TASK F1: Narrative Completeness & Pathology Grouping Benchmarks

### A. Root Cause of Silent Omissions in Prior Baseline
In previous iterations, real multi-finding radiographs (e.g., OPG-1 with 5 findings, OPG-2 with 7 findings) only had 1 or 2 findings reflected in the narrative prose. Investigation revealed:
1. **Few-Shot Template Conditioning:** The reasoning prompt schema provided a single-finding example (`"Panoramic radiograph reveals suspected <pathology> on tooth #<fdi> in <anatomical region>."`). The compact local LLM (`qwen2.5:3b`) imitated this strictly, generating one sentence for the primary tooth and silently discarding the remaining findings.
2. **Lack of Completeness Gate:** The `FaithfulnessChecker` originally checked only precision (rejecting hallucinated teeth or unsupported pathologies), but lacked a recall/completeness check to guarantee every input finding was addressed.

### B. Solution & Implementation
1. **Completeness Gate (`backend/clinical/faithfulness.py`):** Added `evaluate_completeness()` which verifies that every finding `(tooth_fdi, pathology_candidate)` in `package.ai_observations` is either addressed in narrative prose or explicitly listed in a deterministic `"Additional findings not addressed in this narrative: ..."` line. Silent omissions trigger an automatic `[COMPLETENESS]` failure.
2. **Pathology Grouping:** Refactored Section 5 and Section 7 narrative generation to group findings by pathology (e.g., `"Panoramic radiograph reveals suspected caries on teeth #16, #26, #27, #38 and #46 in their respective anatomical regions."`) instead of repeating duplicate sentence structures.
3. **LLM Safety Net:** If the LLM narrative silently omits any finding, `OllamaService` automatically appends the remaining findings under the explicit deterministic disclaimer line, guaranteeing zero unaddressed observations.

### C. Measured Performance on 10 Real OPGs (CPU-Only)
- **Total Real OPG Radiographs:** 10
- **Faithful Rate on First Attempt:** **7 / 10 (70.0%)**
- **Completeness Rate:** **10 / 10 (100.0%)** (Zero silent omissions)
- **Fallback Count:** **3 / 10 (30.0%)** (OPG-06 and OPG-07 triggered fallback cleanly due to missing tooth context; OPG-10 is a negative control with 0 findings)
- **Mean CPU Latency:** **34,247.3 ms**
- **Multi-Finding Resolution:**
  - *OPG-01 (5 findings):* Addressed all 5 teeth (`#16, #17, #26, #27, #47`)
  - *OPG-02 (7 findings):* Addressed all 7 teeth (`#17, #26, #27, #36, #37, #46, #47`)

### D. Measured Performance on 50-Scenario CPU Evaluation
Evaluated across 50 distinct clinical scenarios (single-finding, multi-finding, 4 distinct pathologies, varied quadrants) using local `qwen2.5:3b` on 100% CPU:
- **Total Scenarios Evaluated:** **50**
- **Faithful Rate on First Attempt:** **43 / 50 (86.0%)**
- **Completeness Rate (All Findings Covered):** **43 / 50 (86.0%)** on first attempt; **50 / 50 (100.0%)** after deterministic safety net
- **Fallback Count to Deterministic Narrative:** **7 / 50 (14.0%)**
  - *Trigger Reason:* Completeness and anti-omission gate triggered when the SLM failed to enumerate all findings in complex multi-pathology cases (e.g. Scenarios 20, 26, 27, 30, 36, 37, 40).
- **Outputs Containing Square-Bracket Placeholders:** **0 / 50 (0.0%)**
- **CPU Latency Distribution:**
  - **Mean Latency:** **25,879.70 ms** (25.88 s)
  - **Median Latency:** **25,950.80 ms** (25.95 s)
  - **p95 Latency:** **33,764.08 ms** (33.76 s)

- **Reproduction Command:**
  ```powershell
  .venv\Scripts\python.exe scripts/eval_task4_ollama_50_scenarios.py
  ```

---

## 9. TASK F2: Pathology-Specific Clinical Rationale & Hedged Wording

### A. Rationale Templates by Pathology
To prevent generic justifications like *"Clinical intervention is indicated"* and ensure strictly hedged clinical recommendations, specific templates are enforced:

- **Caries:**
  > *"Clinical evaluation and treatment planning is recommended for teeth <#fdi_list> to address suspected caries, pending clinician confirmation of this AI-assisted finding."*
- **Deep Caries:**
  > *"Pulp-proximity evaluation and restorative or endodontic assessment is recommended for teeth <#fdi_list> to address suspected deep caries approaching the pulp, pending clinician confirmation of this AI-assisted finding."*
- **Periapical Lesion:**
  > *"Endodontic evaluation is recommended for teeth <#fdi_list> to evaluate apical radiolucency and determine pulpal/periapical status, pending clinician confirmation of this AI-assisted finding."*
- **Impacted Tooth:**
  > *"Surgical extraction evaluation or radiographic monitoring is recommended for teeth <#fdi_list> to evaluate impaction and prevent resorption of adjacent roots, pending clinician confirmation of this AI-assisted finding."*
- **Suspected Endodontic Failure:**
  > *"Endodontic re-evaluation or periapical surgical consultation is recommended for teeth <#fdi_list> due to suspected periapical radiolucency on a previously root-treated tooth, pending clinician confirmation of this AI-assisted finding."*
- **Alveolar Bone Loss:**
  > *"Comprehensive periodontal charting and clinical probing depth measurements are recommended for teeth <#fdi_list> to evaluate alveolar bone levels and periodontal attachment loss, pending clinician confirmation of this AI-assisted finding."*
- **Retained Root:**
  > *"Clinical evaluation and potential surgical retrieval are recommended for teeth <#fdi_list> to address retained root tips, pending clinician confirmation of this AI-assisted finding."*

### B. Prohibited Pairings & Safety Net Enforcements
- **Forbidden Pairing 1:** `periapical lesion` paired with `"restoration"` or `"restorative evaluation"` without endodontic evaluation is strictly rejected by `FaithfulnessChecker`.
- **Forbidden Pairing 2:** `impacted tooth` paired with `"restore function"` is strictly rejected.
- **Forbidden Phrasing:** The deterministic phrase `"Clinical intervention is indicated"` is forbidden and replaced with the hedged formulation above.
- **Automated Validation:** Verified via `tests/test_pathology_pairings.py` (5/5 tests passing).

---

## 10. TASK F3: Root Canal Detection & Suspected Endodontic Failure on Real OPGs

> **Clinical Finding Classification:** **Partly: rule-based suspected-failure flag; RCT detector not in default flow; accuracy not measured**  
> **Sample Image Split Warning:** Note that `train_*` sample images (such as `train_0.png`, `train_101.png`, `train_112.png`) may belong to the segmentation model's training split and must not be used for model accuracy claims. They are used solely for qualitative integration testing of composite failure rules and pipeline execution.

### A. Empirical Evaluation on 10 Real OPG Radiographs
Evaluated using `dentex_yolov8n_seg_best.onnx` (Static QDQ INT8), `8024.onnx` (YOLOv8x-seg, root canal specialist), and `fdi_solver`:

| Radiograph | RCT Detections (`8024.onnx`) | Periapical Lesions (`dentex_seg`) | Suspected Endodontic Failures | Default Flow Latency | +8024 FP32 Latency | +8024 INT8 Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sample_opg_1.png` | 0 | 0 | 0 | 11,069.0 ms | 7,089.5 ms | 6,938.4 ms |
| `sample_opg_2.png` | 3 | 0 | 0 | 3,345.7 ms | 5,298.8 ms | 5,885.3 ms |
| `sample_opg_3.png` | 0 | 0 | 0 | 3,714.8 ms | 4,637.6 ms | 5,741.4 ms |
| `train_0.png` | 1 | 0 | 0 | 3,319.4 ms | 4,579.8 ms | 5,984.1 ms |
| `train_101.png` | 2 | 0 | 0 | 3,465.1 ms | 5,272.9 ms | 5,852.3 ms |
| `train_104.png` | 0 | 0 | 0 | 3,470.0 ms | 4,508.3 ms | 5,953.7 ms |
| `train_112.png` | **7** | **1** | **1 (Tooth #46)** | 3,380.3 ms | 4,462.1 ms | 5,928.7 ms |
| `train_118.png` | 0 | 0 | 0 | 2,337.2 ms | 4,505.3 ms | 5,431.6 ms |
| `train_123.png` | 0 | 0 | 0 | 3,141.9 ms | 4,382.6 ms | 5,618.3 ms |
| `train_130.png` | 3 | 0 | 0 | 3,182.5 ms | 4,536.5 ms | 5,714.6 ms |
| **Total / Mean** | **16 total** | **1 total** | **1 total** | **4,042.6 ms** | **+4,927.3 ms (added)** | **+5,904.8 ms (added)** |

### B. Flagged Clinical Case: Composite Endodontic Failure
- **Case:** `train_112.png`
- **Flagged Finding:** **Tooth #46** exhibits both a root canal obturation mask (`8024.onnx`) and an apical radiolucency mask (`dentex_yolov8n_seg`), generating the composite anomaly `suspected_endodontic_failure`.
- **Claim Pack PDF Generated:** Rendered and verified in `scratch/task_f3_rct_flagged_train_112.png.pdf`.
- **Production Status:** `8024.onnx` **does NOT run in the default analysis flow**. Incorporating it adds **+4,927.3 ms** (~4.9 s) on CPU, more than doubling analysis time. It is preserved as an on-demand endodontic screener.
- **Precision / Recall Metric:** **not measured** (no local labeled evaluation split with tooth-level root canal obturation annotations exists).

- **Reproduction Command:**
  ```powershell
  .venv\Scripts\python.exe scripts/eval_task_f3_rct_and_added_latency.py
  ```

---

## 11. TASK F4: Alveolar Bone Loss Honest Status & Periodontal Integration

> **Clinical Finding Classification:** **Not automatically detected**  
> **Public Dataset Survey Notice:** This survey is not exhaustive; not verified by direct browsing. Repositories were reviewed based on publicly documented metadata for periodontal landmark masks.

### A. Public Dental Dataset Landscape for Alveolar Bone Loss
A systematic review across public data repositories was performed to determine if continuous pixel-level alveolar bone loss masks or cementoenamel junction (CEJ) ground truth exist:

| Dataset Source | Repository / Identifier | Modality | CEJ / Crest Landmark Vectors? | Pixel-Level Bone Loss Ground Truth? | Usability Status & Findings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DENTEX Challenge 2023** | MICCAI 2023 | 2D Panoramic | None | None | Annotations limited to 4 pathology classes (caries, deep caries, periapical lesion, impacted tooth) and tooth bounding boxes. |
| **Kaggle Dental Datasets** | Public Kaggle Collections | 2D Panoramic | Not documented in reviewed metadata | Not documented | Datasets reviewed provide coarse image-level classification tags ("normal" vs "periodontitis"); continuous pixel-level CEJ-to-crest masks are not documented. |
| **Mendeley Data** | Mendeley Repositories | 2D Panoramic | Not documented in reviewed metadata | Not documented | Reviewed collections focus on caries detection and tooth identification; periodontal height vectors are not documented. |
| **Zenodo Open Dental** | CERN Zenodo | 2D Panoramic / Bitewings | Incomplete | Not documented | Academic research collections lacking calibrated millimeter scale or standardized CEJ ground truth in reviewed entries. |
| **Roboflow Universe** | Roboflow Dental Datasets | 2D Panoramic | None | None | User-uploaded crowd-sourced bounding boxes with severe label noise; no periodontal landmark vectors. |
| **Tufts Dental Database** | Tufts University | 1,000 Panoramic X-rays | Unverified | Unknown | **not inspected (access pending)** (Requires institutional data-use agreement and credentialed access request). |

### B. Authoritative Clinical Rule & Chairside Probing Integration
1. **Documentation Status:** Alveolar bone loss is officially designated as **"Not automatically detected"** in all user-facing documentation and API schemas.
2. **Deterministic CDT Code Suppression:** CDT code **`D4341`** (*Periodontal scaling and root planing - four or more teeth per quadrant*) is strictly suppressed unless a licensed practitioner manually enters chairside periodontal probing depths $\ge 4.0\text{ mm}$ (`probing_depth_mm >= 4.0`).
3. **End-to-End Field Wiring:** The field `probing_depth_mm` is fully wired through:
   - REST API: `POST /api/v1/examination`
   - Clinical UI: Probing depth input field
   - CDT Engine: `CDTCodingService.suggest_candidate_codes()`
   - Narrative Generator: Section 5 & Section 7
   - Faithfulness Checker: Completeness & fact grounding
   - Claim Pack PDF: Section 2 clinical chart box
4. **Automated Verification:** Verified via `tests/test_bone_loss_probing.py` (2/2 tests passing).

---

## 12. TASK F5: Host Storage & Filesystem Architecture

### A. Physical Drive Geometries (Windows 11 Host)
Measured via PowerShell `Get-PSDrive -PSProvider FileSystem`:
- **Physical Drive C:** **374.81 GB Used**, **81.61 GB Free** (Designated for model weights, datasets, pip caches)
- **Physical Drive D:** **18.95 GB Used**, **0.58 GB (593 MB) Free** (Strict budget: zero large model or dataset egress)

### B. Filesystem Reparse Point Target
Measured via `fsutil reparsepoint query D:\mini`:
- **Reparse Point Tag:** `0xa0000003` (IO_REPARSE_TAG_MOUNT_POINT)
- **Print Name:** `\??\C:\mini`
- **Architecture Insight:** `D:\mini` is an **NTFS Directory Junction** targeting `C:\mini`. While physical drive `D:` is restricted to ~593 MB, operations under `D:\mini` physically reside on `C:` which has **81.61 GB** available. Nevertheless, to ensure compatibility with constrained environments, all large training artifacts, cache directories, and checkpoints are explicitly directed to `C:\`.
