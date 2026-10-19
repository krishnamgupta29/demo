# DENTRACE — DENTEX Dataset Readiness & Integrity Audit

> **DOCUMENT ID:** DOC-DATA-008  
> **STATUS:** AUDITED & STAGED (LEVEL 0.5)  
> **AUDIT DATE:** 2026-10-18  

This document provides a thorough forensic audit of the two local DENTEX challenge archives, detailing their exact file paths, byte sizes, archive structures, annotation hierarchies, integrity verification results, disk budget requirements, and proposed extraction destinations.

---

## 1. Discovered Archives & File Inventory

Both DENTEX challenge ZIP archives were located directly in the workspace root on the **C: drive**:

| Attribute | `training_data.zip` | `validation_data.zip` | Total / Combined |
|---|---|---|---|
| **Absolute Path** | `C:\mini\training_data.zip` | `C:\mini\validation_data.zip` | `C:\mini\` |
| **Exact File Size (Bytes)** | `10,927,391,529` bytes | `149,512,256` bytes | `11,076,903,785` bytes |
| **Compressed Size (GB / MB)** | **10.18 GB** (10,421.17 MB) | **0.14 GB** (142.59 MB) | **10.32 GB** |
| **Uncompressed Size (Bytes)** | `14,725,611,903` bytes | `201,044,945` bytes | `14,926,656,848` bytes |
| **Uncompressed Size (GB / MB)**| **13.71 GB** (14,043.44 MB) | **0.19 GB** (191.73 MB) | **13.90 GB** |
| **Total Archive Entries** | 3,615 files & folders | 55 files & folders | 3,670 entries |
| **Total Panoramic Images** | 3,603 OPG images | 51 OPG images | 3,654 images |
| **Total Annotation JSONs** | 3 COCO-style JSON files | 0 (Held-out evaluation set) | 3 JSON files |

---

## 2. Archive Structure & Subdirectory Breakdown

### A. Structure of `training_data.zip`
```
training_data.zip
└── training_data/
    ├── quadrant/
    │   ├── train_quadrant.json          (2,772 annotations across 693 images)
    │   └── xrays/                       (693 PNG radiographs)
    ├── quadrant_enumeration/
    │   ├── train_quadrant_enumeration.json (18,095 annotations across 634 images)
    │   └── xrays/                       (634 PNG radiographs)
    ├── quadrant-enumeration-disease/
    │   ├── train_quadrant_enumeration_disease.json (3,529 annotations across 705 images)
    │   └── xrays/                       (705 PNG radiographs)
    └── unlabelled/
        └── xrays/                       (1,571 PNG radiographs for self-supervised pretraining)
```

### B. Structure of `validation_data.zip`
```
validation_data.zip
└── validation_data/
    └── quadrant_enumeration_disease/
        └── xrays/                       (50 evaluation PNG radiographs + 1 checkpoint)
```
*Note on Validation Set:* The official MICCAI 2023 DENTEX validation split does not include ground-truth JSON files. In the Grand Challenge framework, this split is reserved for blinded server-side ranking. For DENTRACE, patient-level train/val/test splits (70/15/15) will be generated directly from the 705 disease-annotated training images under the strict hygiene protocol documented in `docs/DATASET_RESEARCH.md`.

---

## 3. Deep Annotation Inspection & Polygon Segmentation Discovery

Prior to this Level 0.5 audit, project documentation assumed that DENTEX provided bounding boxes only. **Our empirical inspection of the raw JSON annotations inside `training_data.zip` directly disproved this assumption.**

### A. Disease Annotation Breakdown (`train_quadrant_enumeration_disease.json`)
- **Total Images:** 705 panoramic radiographs
- **Total Annotations:** 3,529 pathology instances
- **Categories Breakdown (`categories_3`):**
  - Category 0: `Impacted` — **604 instances**
  - Category 1: `Caries` — **2,189 instances**
  - Category 2: `Periapical Lesion` — **158 instances**
  - Category 3: `Deep Caries` — **578 instances**
- **Polygon Segmentation Verification:**
  - 100% of annotations (3,529 / 3,529) contain an explicit `segmentation` array alongside standard `bbox` coordinates.
  - Coordinate count per polygon ranges from 8 coordinates (4 points) to 68 coordinates (34 points), with a mean of **24.0 coordinates (12 points per polygon)**.
  - **Clinical Engineering Impact:** DENTEX directly supports **true instance segmentation training** for caries, deep caries, periapical lesions, and impacted teeth without needing synthetic mask generation.

### B. Tooth Enumeration Breakdown (`train_quadrant_enumeration.json`)
- **Total Images:** 634 panoramic radiographs
- **Total Annotations:** 18,095 tooth instances
- **Categories:**
  - `categories_1`: Quadrants 1, 2, 3, 4 (FDI quadrant indicator)
  - `categories_2`: Tooth positions 1 through 8 (Central Incisor through Third Molar)
- **Polygon Segmentation Verification:**
  - 100% of the 18,095 tooth instances contain anatomical polygon outlines tracing individual tooth contours.

---

## 4. Archive Integrity & File Header Validation

1. **`validation_data.zip` CRC32 Integrity Test:**
   - Ran `zipfile.testzip()` across all 55 archive members.
   - **Result: PASS (0 corrupted files).** Completed in **4.76 seconds**.
2. **`training_data.zip` CRC32 Integrity Test:**
   - Ran `zipfile.testzip()` across all 3,615 archive members and 14.73 GB of uncompressed payload.
   - **Result: PASS (0 corrupted files, 100% CRC32 match).** Completed in **404.66 seconds** (~6.7 minutes).
3. **Image Raster Sampling Verification:**
   - Sampled 20 panoramic radiographs at random across all subfolders (`quadrant`, `quadrant_enumeration`, `quadrant-enumeration-disease`, `unlabelled`).
   - Parsed binary chunk headers:
     - 100% had valid 8-byte PNG signature: `\x89PNG\r\n\x1a\n`
     - Valid `IHDR` chunks with resolutions ranging from `1976x976` to `2990x1504` at 8-bit depth (color type 2 / RGB).
     - 100% terminated with valid `IEND` end-of-file chunks.
   - **Result: All archive contents confirmed bit-perfect, intact, and ready for extraction.**

---

## 5. Storage Budget & Extraction Capacity Analysis

### A. Host Drive Space Status
- **Drive `C:\`:** `140.20 GB` Free
- **Drive `D:\`:** `4.58 GB` Free

### B. Uncompressed Footprint vs Available Capacity
- Uncompressed footprint of `training_data.zip`: **13.71 GB**
- Uncompressed footprint of `validation_data.zip`: **0.19 GB**
- Total uncompressed footprint: **13.90 GB**
- **C: Drive Evaluation:** `140.20 GB - 13.90 GB = 126.30 GB Free` remaining. Safe headroom factor: **>10x**.
- **D: Drive Evaluation:** `4.58 GB < 13.90 GB`. **EXTRACTION ON D: WOULD TRIGGER CATASTROPHIC DISK EXHAUSTION.** Under no circumstances will any dataset files be placed on D:.

---

## 6. Recommended Extraction Destination & Hygiene Strategy

### Proposed Directory Layout on C:
```
C:\mini\datasets\dentex\
├── raw\
│   ├── training\                <-- Destination for training_data.zip
│   │   ├── quadrant\
│   │   ├── quadrant_enumeration\
│   │   ├── quadrant-enumeration-disease\
│   │   └── unlabelled\
│   └── validation\              <-- Destination for validation_data.zip
│       └── quadrant_enumeration_disease\
└── processed\                   <-- Patient-split YOLOv8-seg formatted dataset
    ├── train\ (70%)
    ├── val\   (15%)
    └── test\  (15%)
```

### Strict Hygiene & Safety Protocol
1. **Preserved Archives:** `training_data.zip` and `validation_data.zip` remain completely pristine in `C:\mini\` as authoritative backups.
2. **Immutable Read-Only Annotations:** Original JSON files in `raw/` are preserved as immutable ground truth.
3. **Git-Ignore Verification:** Workspace `.gitignore` enforces strict exclusion of `datasets/*`, `*.zip`, `*.png`, and `*.jpg`. Raw medical images will never enter Git history.
4. **Extraction Completed (Level 1):** Extraction completed safely with Zip-Slip defense into `C:\mini\datasets\dentex\raw/`. The reproducible inventory is recorded in `docs/dataset_inventory.json`.
5. **Held-Out Validation Isolated:** The challenge evaluation validation split (51 PNGs) remains strictly isolated and is never mixed with training data.
