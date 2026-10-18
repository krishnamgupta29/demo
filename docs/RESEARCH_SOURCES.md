# DENTRACE — Verified Research Sources & Citations

> **DOCUMENT ID:** DOC-SRC-008  
> **STATUS:** BASELINED (LEVEL 0)  
> **VERIFICATION DATE:** 2026-10-18  

Every source, repository, and academic paper in this document has been actively checked and verified as accessible on the verification date.

---

## 1. Academic Datasets & Challenge Benchmarks

1. **DENTEX: Dental Enumeration and Diagnosis on Panoramic X-rays Challenge**
   - **Authors:** Ibrahim Ethem Hamamci, Sezgin Er, et al.
   - **Conference:** MICCAI 2023 Challenge.
   - **Grand-Challenge Portal:** [https://dentex.grand-challenge.org/](https://dentex.grand-challenge.org/)
   - **GitHub Repository:** [https://github.com/ibrahimethemhamamci/DENTEX](https://github.com/ibrahimethemhamamci/DENTEX)
   - **Verification Date:** 2026-10-18
   - **Notes:** Bounding box annotations in modified COCO JSON format. 3 tiers: Quadrant, Enumeration, and Abnormal Tooth Diagnosis (`Caries`, `Deep Caries`, `Periapical Lesion`, `Impacted Tooth`).

2. **Dental Disease Panoramic Detection Dataset (Loki Silvres)**
   - **Author:** Loki Silvres
   - **Kaggle Portal:** [https://www.kaggle.com/datasets/lokisilvres/dental-disease-panoramic-detection-dataset](https://www.kaggle.com/datasets/lokisilvres/dental-disease-panoramic-detection-dataset)
   - **Verification Date:** 2026-10-18
   - **Notes:** 31 dental classes formatted for YOLOv8-seg and COCO. Filtered down to target 5 classes in DENTRACE via `config/class_mapping.json`.

3. **Tufts Dental Database (TDD)**
   - **Principal Investigator:** Dr. Karen Panetta, Tufts University
   - **URL:** [http://tdd.ece.tufts.edu/](http://tdd.ece.tufts.edu/)
   - **Publication:** IEEE Transactions on Medical Robotics and Bionics.
   - **Verification Date:** 2026-10-18
   - **Notes:** 1,000 panoramic radiographs with individual tooth pixel masks, abnormality polygons, and radiologists' eye-tracking gaze data. Academic access requires submitting a formal request form.

4. **OdontoAI Open Panoramic Radiographs ($O^2PR$)**
   - **Authors:** Bernardo Silva, Luciano Oliveira, et al. (IvisionLab)
   - **ArXiv Reference:** [arXiv:2203.15856](https://arxiv.org/abs/2203.15856)
   - **GitHub Repository:** [https://github.com/IvisionLab/MEDIA-datasets](https://github.com/IvisionLab/MEDIA-datasets)
   - **Verification Date:** 2026-10-18
   - **Notes:** Restricted access. Requires formal application submitted by an associate or full professor from an institutional email account.

5. **BoneLoss-PAN769: Periodontal Bone Loss on Panoramic Radiographs**
   - **Authors:** Thiago A. Vieira, et al.
   - **Zenodo DOI:** [https://doi.org/10.5281/zenodo.10055276](https://doi.org/10.5281/zenodo.10055276)
   - **GitHub Implementation:** [https://github.com/thiagoavieira/boneloss-inference](https://github.com/thiagoavieira/boneloss-inference)
   - **Verification Date:** 2026-10-18
   - **Notes:** 769 OPGs with 18,809 expert crown polygons, alveolar-ridge polylines, and reference anatomical lines in COCO JSON format. Open access (CC BY 4.0).

6. **TL-pano: Dental Structure Segmentation Dataset for Panoramic Radiographs**
   - **Zenodo Portal:** [https://doi.org/10.5281/zenodo.7888783](https://doi.org/10.5281/zenodo.7888783)
   - **Verification Date:** 2026-10-18
   - **Notes:** True instance segmentation masks for enamel, pulp, dentin, and alveolar bone structures.

---

## 2. Models & Algorithmic Baselines

1. **HierarchicalDet: Diffusion-Based Hierarchical Multi-Label Object Detection**
   - **Authors:** Ibrahim Ethem Hamamci, et al. (MICCAI 2023)
   - **GitHub:** [https://github.com/ibrahimethemhamamci/HierarchicalDet](https://github.com/ibrahimethemhamamci/HierarchicalDet)
   - **Verification Date:** 2026-10-18
   - **Notes:** Official DENTEX baseline codebase. Code-only repository; direct weights are not bundled and must be trained locally or requested.

2. **liodon-ai/dental-panoramic-detector**
   - **HuggingFace Portal:** [https://huggingface.co/liodon-ai/dental-panoramic-detector](https://huggingface.co/liodon-ai/dental-panoramic-detector)
   - **Verification Date:** 2026-10-18
   - **Notes:** Verified YOLOv8 weights (`best.pt` and `best.onnx`) for dental panoramic detection trained on DENTEX and OralXrays-9.

3. **nsitnov/8024-yolov8-model**
   - **HuggingFace Portal:** [https://huggingface.co/nsitnov/8024-yolov8-model](https://huggingface.co/nsitnov/8024-yolov8-model)
   - **Verification Date:** 2026-10-18
   - **Notes:** Verified YOLOv8 instance segmentation weights covering caries, periapical lesions, root canal treatments, and restorations.

---

## 3. Clinical & Regulatory Frameworks

1. **American Dental Association (ADA) CDT Code Set Guidelines**
   - **Publisher:** American Dental Association (ADA)
   - **Notice:** The Current Dental Terminology (CDT) code set is copyrighted by the ADA. Educational demo subset utilized in `config/cdt_demo.json`.
2. **Fédération Dentaire Internationale (FDI) World Dental Federation Two-Digit Numbering System**
   - **Standard:** ISO 3950: Designation system for teeth and areas of the oral cavity.
   - **Structure:** Quadrants 1 to 4 for permanent dentition; tooth indices 1 (central incisor) to 8 (third molar).
