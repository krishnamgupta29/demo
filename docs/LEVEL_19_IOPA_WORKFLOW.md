# LEVEL 19 — INTRAORAL PERIAPICAL (IOPA) WORKFLOW SPECIFICATION

**System:** DENTRACE Clinical Decision Support Engine  
**Modality:** Limited-Field Intraoral Periapical (IOPA) Radiography  
**Regulatory Notice:** *Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR.*

---

## 1. Clinical Context & Modality Distinction

Dental panoramic radiographs (OPGs) capture the entire maxilla and mandible, including temporomandibular joints and maxillary sinuses, with significant geometric distortion, horizontal magnification variation, and cervical burnout. In contrast, **intraoral periapical (IOPA)** radiographs capture a localized field of typically 2 to 4 teeth with high spatial resolution and minimal geometric distortion, focusing specifically on crown margins, pulp chambers, root canals, and periapical alveolar bone.

Applying neural object detection models trained exclusively on panoramic OPGs to periapical images leads to severe diagnostic failure modes:
1. **False positive tooth counting:** The panoramic topological solver expects 14 to 32 teeth and attempts to force tooth numbers across a 2-tooth crop.
2. **Hallucinated impaction:** Normal anatomical teeth appear angled relative to the narrow film sensor boundary.
3. **Spurious caries labels:** Non-calibrated contrast variations trigger false positives on sound enamel surfaces.

**Engineering Rule:** Panoramic models must NEVER run on IOPA images without independently validated periapical models.

---

## 2. Persisted Modality Architecture

```sql
-- SQLite Radiographs Table Schema
ALTER TABLE radiographs ADD COLUMN modality VARCHAR(32) DEFAULT 'unknown';
```

Supported modality enumerations:
- `panoramic_opg`: Full arch panoramic radiograph.
- `intraoral_periapical`: Limited field periapical radiograph (2–4 teeth).
- `bitewing`: Coronal interproximal radiograph.
- `unknown`: Unspecified modality. AI inference disabled by default.

### Enforcement Policy
When `analyze_study` is invoked, `study_service.py` performs a strict database check:
```python
if persisted_modality in ("intraoral_periapical", "bitewing", "unknown"):
    return AnalysisResponse(
        study_id=study_id,
        status="modality_unsupported",
        findings_count=0,
        findings=[],
        notice="MODALITY_SAFETY_GUARD: Selected model is calibrated exclusively for Panoramic OPG images."
    )
```
This check is immune to filename manipulation (`scan001.jpg`, `patient_image.png`, `random_image_123.jpg`).

---

## 3. Four-Tooth IOPA Focus Strip

When viewing an IOPA radiograph, the workstation displays the **4-Tooth IOPA Focus Strip**:
1. **Interactive Tooth Slots:** 4 individual cards representing the visible teeth in the periapical radiograph.
2. **Tooth FDI Assignment:** Dropdown allowing the dentist to assign or alter the FDI designation (e.g., #14, #15, #16, #17) based on clinical sight.
3. **Tooth Status Selector:** Clinician tags each tooth as `Sound`, `Caries`, `Periapical lesion`, or `Restored`.
4. **Active Tooth Synchronization:** Selecting any card in the strip highlights that specific tooth on the 3D dental arch and loads its 3D cutaway anatomy.

---

## 4. Manual Region Annotation System

Clinicians can draw custom observation reticles on the radiograph:
1. **Draw Tool:** Click `Annotate Region` in the X-ray toolbar.
2. **Pointer Capture:** Drag across the lesion area; coordinates are calculated in original image pixel space.
3. **Persistence:** Saved immediately via `POST /api/v1/studies/{id}/annotations`.
4. **Visual State:** Highlighted in crisp medical cyan (`#0284C7`) with casing (`#0C4A6E`) to visually separate clinician annotations from AI detections (`#FACC15`).
5. **Deletion:** One-click removal via `DELETE /api/v1/studies/{id}/annotations/{id}`.
