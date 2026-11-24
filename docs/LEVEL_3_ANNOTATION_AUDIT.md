# DENTRACE Level 3: Annotation Audit & Polygon Semantics Report

**Document Version:** 1.0.0  
**Date:** 2026-10-19  
**Status:** Complete & Verified  
**Regulatory Notice:** *Draft for dentist review. Not a diagnosis. Academic decision-support prototype.*

---

## 1. Executive Summary & Clinical Truthfulness

A rigorous investigation into the DENTEX challenge dataset annotations was conducted to resolve a critical medical computer vision question:

> **Do the polygon segmentation masks in DENTEX represent localized pathology contours (e.g., the cavity pit of caries or apical radiolucency of a periapical lesion), or do they delineate whole tooth instances exhibiting abnormal conditions?**

### The Forensic Finding:
The polygon annotations in `training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json` **delineate whole abnormal tooth contours (crown, cementoenamel junction, and root apex), NOT isolated lesion margins**.

Presenting a model trained on these labels as a "lesion segmenter" would be scientifically and clinically fraudulent. Therefore, DENTRACE formally designates and reports this task as:
**Abnormal-Tooth Instance Segmentation**.

---

## 2. Quantitative Geometric Evidence

A comparison of all annotations in `train_quadrant_enumeration_disease.json` ($N=3,529$) against normal whole-tooth enumeration annotations ($N=18,095$) reveals identical geometric scale and morphological distributions:

| Annotation Category | Count ($N$) | Mean Bounding Width | Mean Bounding Height | Mean Polygon Vertices | Semantic Target |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **All Tooth Instances (Baseline)** | **18,095** | **125.6 px** | **304.3 px** | **11.6** | Full anatomical tooth contour |
| **Category 0: Impacted Tooth** | 604 | 191.6 px | 216.7 px | 11.1 | Complete impacted tooth |
| **Category 1: Caries** | 2,189 | 171.8 px | 297.0 px | 12.4 | Complete tooth with caries |
| **Category 2: Periapical Lesion** | 158 | 185.8 px | 317.3 px | 11.9 | Complete tooth with apical lesion |
| **Category 3: Deep Caries** | 578 | 167.9 px | 271.0 px | 11.5 | Complete tooth with deep caries |

### Key Observations:
1. **Vertical Span Equivalence:**
   - The mean vertical height of Caries annotations is **297.0 px**, Periapical Lesions is **317.3 px**, and Deep Caries is **271.0 px**, closely tracking the mean height of whole tooth instances (**304.3 px**).
   - If Caries annotations traced only the localized demineralized enamel/dentin pit, typical vertical heights would range from **15 px to 50 px**.
2. **Morphological Extent:**
   - Manual visual inspection of polygon coordinates across `train_0.png`, `train_1.png`, `train_4.png`, and `train_88.png` confirms that the polygon vertices traverse from the occlusal/incisal edge down both proximal surfaces to the root apices.
   - For Periapical Lesions, the polygon surrounds the host tooth (and in some instances slightly expands around the apex) rather than segmenting solely the radiolucent halo.
3. **Multi-Label Hierarchy in DENTEX:**
   - Every annotation in `train_quadrant_enumeration_disease.json` contains three hierarchical labels:
     - `category_id_1`: Quadrant index (0: Upper Right, 1: Upper Left, 2: Lower Left, 3: Lower Right)
     - `category_id_2`: Tooth enumeration within quadrant (0: Central Incisor to 7: Third Molar)
     - `category_id_3`: Pathology diagnosis (0: Impacted, 1: Caries, 2: Periapical Lesion, 3: Deep Caries)
   - This architectural schema confirms that DENTEX annotators identified **the tooth itself** and labeled its quadrant, position, and diagnosis.

---

## 3. Annotation Schema Specification

To ensure total transparency across research papers, API consumers, and UI presentations, the DENTRACE segmentation ontology is specified as follows:

```
[OPG Radiograph]
       │
       ├──> Tooth Enumeration (32 FDI classes: 11-48) ────> Spatial Boundary: Whole Tooth Anatomical Mask
       │
       └──> Pathology Findings (4 Compulsory Classes)
              │
              ├── Caries (DENTEX Cat 1) ─────────────────> Spatial Boundary: Tooth Exhibiting Caries Mask
              ├── Deep Caries (DENTEX Cat 3) ────────────> Spatial Boundary: Tooth Exhibiting Deep Caries Mask
              ├── Periapical Lesion (DENTEX Cat 2) ──────> Spatial Boundary: Tooth Exhibiting Periapical Lesion Mask
              └── Impacted Tooth (DENTEX Cat 0) ─────────> Spatial Boundary: Complete Impacted Tooth Mask
```

### Distinction between DENTEX and Clinical Restorations Checkpoints:
- **DENTEX 4-Class YOLOv8-Seg:** Output masks represent **Abnormal-Tooth Instances**.
- **`nsitnov/8024-yolov8-model` (8-Class):** Output masks represent **Restorations & Lesions** (Filling, Crown, Implant, Root Canal Treatment, Caries, Periapical Lesion, Missing Tooth, Root Piece). In `8024.pt`, fillings, crowns, and implants segment localized materials, whereas caries and periapical lesions segment the affected tooth area.

---

## 4. Engineering & Safety Rules for Level 3

1. **No False Margin Claims:** The user interface, clinical documentation, and API must describe segmented boundaries as `"Tooth boundary affected by [Pathology]"` or `"Abnormal tooth mask"`, never as `"Excavation margin"` or `"Cavity margin"`.
2. **Four-Class Preservation:** Caries (Cat 1) and Deep Caries (Cat 3) must be strictly treated as separate classes during evaluation and model training. They must never be merged under an ad-hoc single label without explicit ablation documentation.
3. **Zero Pixel Mask Invention:** When a detection-only model (such as RT-DETR tooth proposal or Level 2 YOLOv8x-DENTEX) generates bounding boxes, bounding box corners must **never** be synthesized into a 4-point rectangle polygon and labeled as a "segmentation mask". Only genuine convolutional/contour segmentation masks from instance segmentation heads are valid.

---

## 5. Audit Conclusion

The DENTEX polygon annotations provide high-quality ground truth for **abnormal tooth instance segmentation**. The dataset is well-suited for training YOLOv8-Seg models to locate, classify, and segment whole teeth that harbor dental anomalies. All Level 3 evaluation metrics (Mask AP50, Mask AP50-95, and Dice coefficients) will be reported against these whole-tooth ground truth contours.
