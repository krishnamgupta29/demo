# DENTRACE Level 6.1 — FDI Solver Accuracy Comparison

**Generated:** 2026-10-21 21:19

> [!NOTE]
> FDI accuracy is measured separately from segmentation mAP. The FDI solver assigns ISO/FDI tooth numbers to detected centroids using anatomical priors. No patient data.

## Evaluation Protocol

- Radiographs evaluated: **150** panoramic images
- Total teeth evaluated: **4224**
- Metric: Exact FDI number match (e.g. tooth 36 predicted vs. tooth 36 annotated)
- Split: Development set (annotated DENTEX quadrant-enumeration subset)

## Accuracy Comparison

| Solver | Exact FDI Accuracy | Notes |
|--------|--------------------|-------|
| Level 3 baseline (`FDISolver`) | 74.55% | Uniform width distribution, no gap threshold |
| Level 6.1 calibrated (`CalibratedFDISolver`) | **76.07%** | Anatomical width factors + gap_pitch_ratio_threshold=1.35 |
| Abstention rate (calibrated) | ≤ 3.2% | Teeth where solver declines to assign FDI number |

## Key Design Decisions

1. **Anatomical width priors**: Posterior teeth (molars) are wider than anteriors; width factors are region-specific (maxilla vs. mandible).
2. **Gap-pitch threshold**: When the inter-tooth gap exceeds 1.35× the median pitch, the solver inserts a missing-tooth slot to prevent cascading misassignment.
3. **Abstention**: When confidence is below threshold, the solver returns `ABSTAIN` rather than a wrong FDI number. This is flagged in the UI for clinician review.
4. **No silent deployment**: A lower-accuracy solver is never silently substituted for a higher-accuracy one.

## Failure Modes (Documented)

| Failure Mode | Frequency | Root Cause |
|--------------|-----------|------------|
| Third-molar misidentification | ~12% of posterior errors | Eruption variants; solver uses fixed arch length |
| Edentulous quadrant cascade | ~8% of full-arch errors | Missing teeth break pitch estimation |
| Bilateral symmetry assumption | ~5% | Asymmetric jaw anatomy not modeled |

> [!WARNING]
> FDI accuracy of 76.07% is insufficient for autonomous clinical use. This is a decision-support tool — the clinician must verify all tooth assignments.
