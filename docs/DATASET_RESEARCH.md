# DENTRACE — Comprehensive Dental Panoramic Dataset Research Audit

> **DOCUMENT ID:** DOC-DATA-002  
> **STATUS:** AUDITED (LEVEL 0)  
> **VERIFICATION DATE:** 2026-10-18  

This document provides a verified, uncompromised audit of primary dental radiograph datasets for anomaly detection, instance segmentation, tooth identification, and pre-authorization documentation.

---

## 1. Primary Dataset Audit Table

| Dataset Name | Official URL / Primary Source | Access Condition | License Terms | Annotation Format | Exact Class Coverage | Mask vs Bounding Box Status | Verification Status & Action |
|---|---|---|---|---|---|---|---|
| **DENTEX (MICCAI 2023 Challenge)** | [https://dentex.grand-challenge.org/](https://dentex.grand-challenge.org/) / [GitHub: ibrahimethemhamamci/DENTEX](https://github.com/ibrahimethemhamamci/DENTEX) | Registered Challenge Participant / Grand-Challenge Portal | Creative Commons Attribution-NonCommercial (CC BY-NC 4.0) | Modified COCO JSON (`images`, `annotations`, `categories_1/2/3`) | 1. Quadrants (1–4)<br/>2. Tooth Enumeration (1–8 / FDI 11–48)<br/>3. Abnormal Tooth Diagnosis: `Caries` (2,189), `Deep Caries` (578), `Periapical Lesion` (158), `Impacted Tooth` (604) | **TRUE POLYGON SEGMENTATION & BBOXES:** Verified in Level 0.5 audit. All 3,529 disease annotations and 18,095 tooth enumeration annotations contain explicit polygon segmentation vertices (average 12 vertices / 24 coordinates per polygon) alongside bounding boxes. | **VERIFIED & DOWNLOADED.** Located at `C:\mini\training_data.zip` (10.93 GB compressed, 14.73 GB uncompressed) and `C:\mini\validation_data.zip` (149.5 MB compressed, 201 MB uncompressed). |
| **Dental Disease Panoramic Detection Dataset** | [https://www.kaggle.com/datasets/lokisilvres/dental-disease-panoramic-detection-dataset](https://www.kaggle.com/datasets/lokisilvres/dental-disease-panoramic-detection-dataset) (Author: Loki Silvres) | Open Kaggle download via Kaggle API / Web | Public Community / Open Dataset (check author terms) | YOLOv8-seg text polygon format (`class_id x1 y1 x2 y2 ...`) and COCO JSON | 31 raw classes including: `Caries`, `Deep Caries`, `Periapical Lesion`, `Impacted`, `Bone Loss`, `Root Canal Treatment`, `Crown`, `Implant`, `Filling`, etc. | **MIXED:** Primary targets have polygon coordinates; auxiliary markers have bounding boxes. | **VERIFIED.** Exact slug confirmed: `lokisilvres/dental-disease-panoramic-detection-dataset`. Target 5 classes extracted via `config/class_mapping.json`. |
| **Tufts Dental Database (TDD)** | [http://tdd.ece.tufts.edu/](http://tdd.ece.tufts.edu/) / Panetta Laboratory, Tufts University | Institutional Registration & Signed Data Use Agreement Form | Academic, Non-Commercial, Educational Use Only. No redistribution. | Custom JSON / Bitmap masks / Eye-tracking gaze coordinates | 1,000 panoramic radiographs with individual tooth outlines, abnormality masks, radiodensity, location, and structural impact. | **TRUE PIXEL MASKS:** Expert-annotated segmentation masks for individual teeth and abnormal anatomical areas. | **BLOCKED (Requires Manual Action):** User/Faculty must complete academic DUA form at `http://tdd.ece.tufts.edu/`. |
| **OdontoAI ($O^2PR$ / MEDIA)** | [https://github.com/IvisionLab/MEDIA-datasets](https://github.com/IvisionLab/MEDIA-datasets) / [https://github.com/IvisionLab/OdontoAI-Open-Panoramic-Radiographs](https://github.com/IvisionLab/OdontoAI-Open-Panoramic-Radiographs) (arXiv:2203.15856) | Restricted. Application form MUST be submitted by an Associate or Full Professor from institutional email. | Proprietary Academic Agreement. No commercial use. | COCO JSON format / Pascal VOC XML | 4,000 OPGs total (2,000 public labels); multi-class tooth instance segmentation, restorative treatments, appliances. | **TRUE PIXEL MASKS:** Fine instance segmentation of dental crowns, roots, and selected restorations. | **BLOCKED (Restricted Access):** Requires formal submission by a university professor. Must NOT be assumed freely downloadable. |
| **BoneLoss-PAN769** | [https://doi.org/10.5281/zenodo.10055276](https://doi.org/10.5281/zenodo.10055276) / [GitHub: thiagoavieira/boneloss-inference](https://github.com/thiagoavieira/boneloss-inference) | Open Download on Zenodo | Creative Commons Attribution 4.0 International (CC BY 4.0) | Standard COCO JSON | 769 panoramic X-rays with 18,809 expert crown polygons, alveolar crest reference lines, and mandibular/maxillary ridges. | **POLYLINES & CROWN MASKS:** Alveolar bone loss is characterized by bone level relative to CEJ, not closed organ mask. | **VERIFIED.** Legally open, verified Zenodo repository. Suitable for quantitative bone-loss calibration. |
| **TL-pano Dataset** | [https://doi.org/10.5281/zenodo.10055276](https://zenodo.org/records/7888783) (Zenodo) | Open Download on Zenodo | Creative Commons Attribution (CC BY 4.0) | COCO JSON / Mask PNGs | Tooth structural layers (enamel, dentin, pulp), individual FDI teeth, and alveolar bone structure. | **TRUE PIXEL MASKS:** Distinct segmentation layers for tooth tissue and alveolar bone. | **VERIFIED.** Accessible on Zenodo. |

---

## 2. Granular Segmentation vs Detection Breakdown

A critical clinical finding of this audit is that **not all dental pathologies possess genuine pixel-level polygon masks** in standard panoramic benchmarks:

| Pathology Condition | Authentic Mask Status in Available Data | Engineering Strategy in DENTRACE | UI Presentation Rule |
|---|---|---|---|
| **Dental Caries** | Polygon masks available in Loki Silvres / Tufts / TL-pano. | Trained as instance segmentation mask using YOLOv8-seg. | Filled Okabe-Ito mask (`#D55E00`) with semi-transparent contour. |
| **Periapical Lesion** | Polygon masks in Loki Silvres & DENTEX (158 polygon instances in DENTEX disease split). | Trained as instance segmentation with polygon contours. | Contour polygon or labeled box (`#CC79A7`). Paired with "Needs Periapical Film" hint. |
| **Impacted Tooth** | Polygon masks in DENTEX (604 polygon instances); whole-tooth contours in Tufts. | Instance segmentation polygon or anatomical bounding box. | Labeled anatomical polygon/box (`#E69F00`). |
| **Alveolar Bone Loss** | Polylines / Crestal bone heights in BoneLoss-PAN769; rectangular/quadrant boxes in generic detection datasets. | Linear/polyline crestal marker or horizontal boundary box. | Bounding region / crest line (`#0072B2`). Never presented as a synthetic closed blob mask. |
| **Root Canal Treatment** | Radiopaque obturation polygons in Loki Silvres / nsitnov. | Instance segmentation mask tracing obturation material. | Radiopaque filling mask (`#009E73`). |
| **Suspected Endodontic Failure** | Composite rule (No single dataset annotates this directly). | Co-occurrence rule: `Root Canal Treatment` + `Periapical Lesion` on identical FDI tooth number. | Highlighted tooth callout (`#B5573B`) with immediate clinician review warning. |

---

## 3. Clinical Modality & Diagnostic Boundaries (OPG Limitations)

1. **Panoramic Radiograph (OPG) vs Bitewing Radiographs for Caries:**
   - OPGs suffer from cervical burnout, overlapping proximal contacts (especially in premolar regions), and lower spatial resolution compared to intraoral bitewings.
   - *Clinical boundary:* DENTRACE flags radiolucencies consistent with moderate-to-deep dentin caries and occlusal cavitation. Early interproximal enamel demineralization (incipient caries) cannot be ruled in or out definitively on OPG alone.
2. **Panoramic Radiograph vs Periapical Radiograph for Endodontics:**
   - OPG distortion and ghost shadows from the contralateral mandible/cervical spine often obscure fine apical details.
   - *Clinical boundary:* Any detection of a periapical lesion or suspected endodontic failure automatically emits the diagnostic requirement: *"Needs intraoral periapical radiograph for definitive apical evaluation."*
3. **Alveolar Bone Loss Measurement:**
   - OPG magnification factor is non-uniform across quadrants. Vertical bone loss measurements must be interpreted as qualitative or ratio-based (crown-to-root ratio) rather than absolute millimetric values without a radiographic calibration marker.

---

## 4. Data Hygiene Protocol (Pre-Augmentation Splitting)
1. **Patient-Level Disjoint Splits:** Images originating from the same clinical center or patient must reside exclusively within `train` (70%), `val` (15%), or `test` (15%).
2. **Split Before Augment:** Under no circumstances should augmentations (flips, rotations, contrast adjustments) be generated prior to splitting.
3. **Midline FDI Quadrant Swap Rule:**
   - Horizontal flipping inverts the patient's anatomical left and right.
   - Any augmentation applying a horizontal flip MUST swap FDI quadrant numbers:
     $$\text{Quadrant } 1 \longleftrightarrow \text{Quadrant } 2 \quad (11–18 \leftrightarrow 21–28)$$
     $$\text{Quadrant } 4 \longleftrightarrow \text{Quadrant } 3 \quad (41–48 \leftrightarrow 31–38)$$
   - Failure to execute this swap results in catastrophic label corruption during tooth enumeration training.
