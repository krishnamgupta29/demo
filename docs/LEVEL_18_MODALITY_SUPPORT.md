# LEVEL 18 — Modality Support & Clinical AI Safety Boundaries

**Document ID:** DENTRACE-L18-MODALITY  
**Author:** AI Systems Engineer  
**Date:** November 16, 2026  
**Status:** Implemented & Verified  

---

## 1. Clinical Modality Framework

DENTRACE distinguishes four radiograph imaging modalities:
1. **Panoramic Radiograph (OPG):** Full maxillofacial curved focal trough scan showing both upper and lower arches from condyle to condyle.
2. **Intraoral Periapical (IOPA):** High-detail limited-field radiograph showing 2 to 4 complete teeth from crown to root apex and surrounding alveolar bone.
3. **Bitewing Radiograph:** High-detail interproximal radiograph showing coronal portions of maxillary and mandibular premolars and molars.
4. **Unknown / Unspecified:** Non-standard crops, oblique views, or photographs of physical radiographs.

---

## 2. Modality-Specific AI Safety Guard

### The Clinical Risk
The primary models currently integrated into DENTRACE (`liodon-panoramic-screener` YOLO11n and `dentex-yolov8n-seg`) were trained strictly on full-arch Panoramic OPG datasets (DENTEX Challenge and clinical OPG archives). 

Running a panoramic model on an intraoral periapical (IOPA) or bitewing radiograph causes catastrophic domain shift:
- Whole-arch spatial priors fail.
- Magnified crowns and roots are misclassified as supernumerary or ectopic structures.
- Erroneous tooth counts and false positive bounding boxes are generated.

### Safety Enforcement in `backend/services/study_service.py`
DENTRACE strictly forbids running panoramic models on intraoral radiographs:
```python
# Modality Safety Guard — enforce OPG training boundary
rel_fn = (study_row["storage_rel_path"] or "").lower()
ar = float(study_row["width_px"]) / max(1.0, float(study_row["height_px"]))
is_periapical = "periapical" in rel_fn or "iopa" in rel_fn or "intraoral" in rel_fn
is_bitewing = "bitewing" in rel_fn

if is_periapical or is_bitewing:
  modality_label = "Intraoral Periapical (IOPA)" if is_periapical else "Bitewing"
  return AnalysisResponse(
      study_id=study_id,
      status="modality_unsupported",
      model_id=target_model,
      model_version=reg_entry.version,
      execution_time_ms=None,
      execution_provider="None",
      findings_count=0,
      findings=[],
      notice=(
          f"MODALITY_SAFETY_GUARD: Pretrained model '{target_model}' is validated strictly for Panoramic OPG images. "
          f"Automated AI detection is NOT AVAILABLE for {modality_label} radiographs to prevent invalid false positives. "
          "Manual tooth chart selection and region annotation remain fully active."
      ),
  )
```

### Clinician Workstation Experience for IOPA
When an IOPA or Bitewing radiograph is uploaded:
1. The original diagnostic image is preserved without alteration.
2. An amber status badge displays `[IOPA]` or `[Bitewing]`.
3. Automated AI inference returns `status="modality_unsupported"` with explicit clinical explanation.
4. No fake bounding boxes or fabricated detections are rendered.
5. The clinician can freely use pan, zoom, fit-to-window, region annotation, and interactive tooth chart selection.

---

## 3. Future IOPA Model Feasibility Plan
To enable automated detection on intraoral periapical radiographs in future versions:
- **Datasets:** Public datasets such as Tufts Dental Database (periapicals with caries annotations) or Mendeley Dental IOPA dataset.
- **Label Taxonomy:** Must support periapical radiolucencies (apical periodontitis, cysts), root fractures, and interproximal crown caries.
- **Hardware Budget:** Requires fine-tuning on batch size $B \le 8$ within the 4 GB VRAM limit (or Google Colab T4).
- **Gate:** Model will only be enabled after achieving independently verified IoU $\ge 0.50$ and precision $\ge 0.80$ on holdout IOPA scans.
