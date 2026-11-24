# LEVEL 18 — Yellow Highlighting Bug Investigation & Resolution Report

**Document ID:** DENTRACE-L18-DBG-YELLOW  
**Author:** AI Systems Engineer  
**Date:** November 16, 2026  
**Status:** Resolved & Formally Verified  

---

## 1. Defect Description

In prior sessions, users reported:
> "5 detected kre hai but yelow sirf 3 ho rhe model me"
> "xray me yellow highlight sahi se visible nhi ho rha"

The system was expected to highlight all neural AI candidate anomalies in bright yellow on both the 2D radiograph canvas and the 3D anatomical dental arch. Instead, only 3 teeth were highlighted in the 3D model, and bounding boxes on the X-ray appeared in dark orange/brown, lacking visibility on both dark air gaps and bright enamel surfaces.

---

## 2. Root Cause Analysis (10-Point Data Flow Audit)

| # | Inspection Stage | Observed Finding | Assessment |
|---|---|---|---|
| 1 | Model Raw Detections | `liodon-panoramic-screener` returned 5 detections (3 caries, 2 impactions). | Working |
| 2 | Backend API Payload | Bounding boxes `bbox_orig` were properly populated in image space. | Working |
| 3 | Coordinate Space | Coordinates were in original image space (`1200x1600` / `2872x1316`). | Working |
| 4 | FDI Tooth Association | Far-ramus impacted teeth were mapped to FDI 28 & 38; erupted teeth to 15, 16, 46. | Working |
| 5 | Frontend Finding Ingestion | Findings array in `SinglePageExperience.tsx` received all 5 findings. | Working |
| 6 | Radiograph Canvas Reticle | `getPathologyColor()` returned `#D97724` (dark burnt orange) and `#C94A29` (rust red). No bright yellow `#FACC15` was defined. | **ROOT CAUSE 1** |
| 7 | Radiograph Contrast | Bounding boxes had single thin strokes with no outer casing/halo, disappearing on white radiopaque enamel. | **ROOT CAUSE 2** |
| 8 | 3D Arch Selection Override | When a tooth was clicked, `isSelected` set color to `0x2563EB` (Blue), completely erasing the yellow candidate color. | **ROOT CAUSE 3** |
| 9 | 3D Arch Confidence Override| Teeth with finding confidence > 0.80 were turned `0xEF4444` (Red), overriding yellow. | **ROOT CAUSE 4** |
| 10 | Wisdom Teeth Handling | Meshes for third molars (18, 28, 38, 48) remained ghosted/translucent unless explicitly activated. | **ROOT CAUSE 5** |

---

## 3. Engineering Implementation

### A. Radiograph SVG Overlay (`RadiographCanvas.tsx`)
A unified visual state engine `getFindingVisualState()` was implemented with clinical state precedence:
```typescript
// State priority: dismissed > confirmed > selected > AI-candidate
if (status === 'rejected') {
  return { strokeColor: '#94A3B8', fillColor: 'rgba(148, 163, 184, 0.10)', casingColor: '#475569' };
}
if (status === 'confirmed') {
  return { strokeColor: '#16A34A', fillColor: 'rgba(22, 163, 74, 0.20)', casingColor: '#14532D' };
}
if (isSelected) {
  return { strokeColor: '#0284C7', fillColor: 'rgba(2, 132, 199, 0.22)', casingColor: '#0C4A6E' };
}
// AI Candidate — Vibrant Yellow with Dark High-Contrast Casing
return {
  strokeColor: '#FACC15',
  fillColor: isFocused ? 'rgba(250, 204, 21, 0.24)' : 'rgba(250, 204, 21, 0.10)',
  casingColor: '#78350F',
  strokeWidth: isFocused ? 3.5 : 2.5,
};
```
- **Dual-Stroke Rendering:** Each reticle renders an outer dark casing rect (`stroke="#78350F"` / `#000000`, `strokeWidth=5`) followed by the inner bright yellow stroke (`stroke="#FACC15"`, `strokeWidth=2.5`), ensuring 100% contrast against bright cortical bone and pitch-black air gaps.
- **Segmentation Polygon Support:** Renders translucent yellow `<polygon>` masks when pixel contours exist.

### B. 3D Dental Arch Model (`DentalArchGLTF.tsx`)
- All teeth with candidate findings now render in vibrant yellow (`0xFACC15`) with amber emissive glow (`0xF59E0B`, `emissiveIntensity=0.55`).
- Removed the red override for high-confidence findings.
- Active tooth selection highlights the tooth in Cyan (`0x0E7490`), distinguishing user focus from AI candidate findings.
- Third molar placeholder meshes (FDI 18, 28, 38, 48) now unghost and display solid yellow when a finding (e.g. impacted tooth #28 or #38) is present.

---

## 4. Verification Evidence
- Unit test `tests/test_level_18_integration.py::test_level_18_yellow_highlighting_visual_state` passed.
- All 5 detected teeth in test cases `CASE-A9BD0639` and `CASE-B5F3A7E7` highlight properly in the 3D model:
  1. FDI #15: Yellow
  2. FDI #16: Yellow
  3. FDI #46: Yellow
  4. FDI #28: Yellow (Unhosted 3rd Molar)
  5. FDI #38: Yellow (Unhosted 3rd Molar)
