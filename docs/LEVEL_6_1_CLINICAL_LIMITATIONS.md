# DENTRACE Level 6.1 — Clinical Limitations

**Generated:** 2026-10-21 21:19

> [!CAUTION]
> DENTRACE is an academic decision-support prototype. It is NOT a certified medical device (FDA/CE/MDR). All outputs must be reviewed by a licensed dental professional. Never use for autonomous clinical diagnosis or treatment planning.

## Scope of Current System (Level 6.1)

| Capability | Status | Notes |
|------------|--------|-------|
| Panoramic OPG anomaly detection | ✅ Implemented | 4-class YOLOv8n-seg, mAP50 ≈ 0.44 |
| FDI tooth numbering | ✅ Implemented | 76.07% exact accuracy; abstention on uncertainty |
| Bone loss assessment | ⚠️ Rule-based only | No pixel-level alveolar crest segmentation |
| Root canal treatment detection | ✅ Heuristic | Based on HU density proxy; no ground-truth validated |
| Periapical lesion + RCT co-detection | ✅ Implemented | Wording: "Previously treated tooth with suspected periapical radiographic finding — requires clinician review" |
| Autonomous diagnosis | ❌ Prohibited | By design and regulatory constraint |
| Insurance claim decision | ❌ Not automated | Draft pre-auth narrative only; insurer decides |

## Known Model Limitations

1. **Small training set**: 705 panoramic images is insufficient for robust generalisation across patient populations, equipment vendors, and imaging protocols.
2. **Single modality**: Only panoramic (OPG) radiographs are supported. CBCT, periapical, and bitewing films are out of scope.
3. **Class imbalance**: `missing_tooth` and `impacted_tooth` instances are less frequent in the DENTEX dataset; per-class recall may be lower for these categories.
4. **No severity grading**: Cavity depth, bone loss percentage, and caries classification (ICDAS) are not implemented.
5. **Pixel-level segmentation**: The mask output is approximate; it is not a validated delineation for surgical planning.
6. **Age and anatomy variation**: Paediatric dentition, retained deciduous teeth, and orthodontic appliances are not modelled.

## Clinical Safety Statements

- **Observation wording**: All model outputs use hedged language ("suspected", "radiographic finding", "requires clinician review").
- **Root canal finding**: The phrase "root canal treatment failure" is explicitly prohibited. The system states: *"Previously treated tooth with suspected periapical radiographic finding — requires clinician review."*
- **Disclaimer**: Every exported report carries: *"Draft for dentist review. Not a diagnosis."*
- **No treatment assertion**: The system never recommends specific treatments or drugs.

## Bone Loss Assessment (Current State)

Bone loss detection via pixel-level alveolar crest segmentation is **not implemented** in Level 6.1. The current system:
- Detects vertical bone loss proxy using bounding box height ratios relative to root apex estimates.
- This is a geometric heuristic, not a validated radiographic measurement.
- Bone loss is reported as a risk flag, not a quantified measurement.

**Blocker for full bone loss assessment**: Requires a dedicated bone-loss–annotated dataset (e.g. BonelossDent or similar) which is not part of DENTEX.
