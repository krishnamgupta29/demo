# DENTRACE Level 6 — Endodontic Assessment & Root Canal Analysis Report

**Document ID:** DENTRACE-L6-ENDO-001  
**Status:** COMPLETE & AUDITED  
**Date:** October 2026  
**Clinical Standards:** AAE (American Association of Endodontists) Diagnostic Guidelines  

---

## 1. Clinical Context & Semantic Distinction

In dental panoramic radiography, endodontically treated teeth present unique diagnostic challenges. Machine learning models that do not distinguish past restorative interventions from active pathological lesions risk generating false alarms or claiming unverified treatment failures.

DENTRACE enforces a strict semantic distinction between **past restorative therapy** and **active endodontic pathology**:

| Model Class | Clinical Semantic | Radiographic Density | Pathology Taxonomy | Urgency |
|:---|:---|:---:|:---|:---:|
| **Class 7: Root-Canal-Treatment** | Past restorative endodontic obturation (gutta-percha) | Radiopaque (dense white filling in root canal) | `PathologyClass.ROOT_CANAL_TREATMENT` | Routine |
| **Class 5: Periapical-lesion** | Periapical bone resorption / rarefying osteitis | Radiolucent (dark halo at root apex) | `PathologyClass.PERIAPICAL_LESION` | Soon |
| **Class 7 + Class 5 Co-Occurrence** | Suspected persistent or recurrent apical periodontitis | Mixed (radiopaque obturation with apical radiolucency) | `PathologyClass.PERIAPICAL_LESION` + Endodontic Failure Draft | Soon |

> [!IMPORTANT]
> **Clinical Fact Separation Rule:** An endodontic obturation is evidence of **past treatment**, never active pathology. It must never be coded as a disease or billed as a restorative need without verified recurrent pathology.

---

## 2. Audit of Pretrained Candidate (`nsitnov/8024-yolov8-model`)

The `nsitnov/8024-yolov8-model` was audited for endodontic and restorative instance segmentation:
- **Repository:** `https://huggingface.co/nsitnov/8024-yolov8-model`
- **Architecture:** YOLOv8x-seg (Instance Segmentation)
- **Physical Weights:**
  - `models/checkpoints/8024.pt` (137.0 MB)
  - `models/checkpoints/8024.onnx` (273.91 MB)
  - `models/checkpoints/8024_int8.onnx` (70.11 MB, 3.91x compression)
- **Supported Classes (8 total):**
  0. `Caries`
  1. `Crown`
  2. `Filling`
  3. `Implant`
  4. `Missing-tooth`
  5. `Periapical-lesion`
  6. `Root Piece`
  7. `Root-Canal-Treatment`

---

## 3. Composite Endodontic Rule Engine

When DENTRACE executes the analysis pipeline (`study_service.analyze_study`), tooth-pathology associations are resolved geometrically. If a single permanent tooth entity ($FDI$) is associated with both a root canal filling and an apical lesion, the composite rule is triggered:

```python
# Composite endodontic check: if a tooth has both root canal obturation and a periapical lesion,
# flag suspected persistent/recurrent apical periodontitis requiring chairside confirmation
tooth_findings_map = {}
for idx, f in enumerate(findings):
  if f.tooth_fdi:
    tooth_findings_map.setdefault(f.tooth_fdi, []).append((idx, f))

for tooth_num, tf_tuples in tooth_findings_map.items():
  has_rct = any(tf.pathology_class == PathologyClass.ROOT_CANAL_TREATMENT for _, tf in tf_tuples)
  has_apical = any(tf.pathology_class == PathologyClass.PERIAPICAL_LESION for _, tf in tf_tuples)
  if has_rct and has_apical:
    for idx, tf in tf_tuples:
      if tf.pathology_class == PathologyClass.PERIAPICAL_LESION:
        tf.evidence.observed_features.append(
            "Suspected persistent or recurrent periapical radiolucency on endodontically treated tooth (suspected endodontic failure). "
            "Draft for dentist review. Chairside clinical confirmation (vitality, percussion, palpation) is required."
        )
        tf.urgency = UrgencyLevel.SOON
```

### Potential Clinical Etiologies
1. **Persistent Infection:** Persistent apical periodontitis from un-instrumented accessory canals (e.g., missed MB2 canal in maxillary first molars).
2. **Coronal Microleakage:** Degradation of coronal restoration allowing saliva and bacterial ingress.
3. **Over/Under-Extension:** Inadequate apical seal or extruded obturation material causing foreign-body reaction.
4. **Vertical Root Fracture (VRF):** Radicular fracture line that may present radiographically as a 'halo' or 'J-shaped' periapical radiolucency.
5. **Apical Scar Tissue:** Fibrous healing tissue that remains radiolucent indefinitely despite biological success.

---

## 4. Chairside Clinician Confirmation Boundary

Because radiographic radiolucency alone cannot distinguish an active persisting infection from a resolving apical healing scar or asymptomatic apical fibrous tissue, the engine **strictly requires chairside clinical attestation**:
- Cold / Electric Pulp Testing (EPT) — controls for adjacent tooth vitality
- Vertical and lateral percussion sensitivity
- Palpation sensitivity over apical mucosa
- Periodontal pocket probing (isolated narrow deep pocket suggestive of VRF)
- Review of historical radiographs (comparing lesion dimensions over 6–24 months)

Automated claim submission without dentist attestation is blocked at the preflight stage.
