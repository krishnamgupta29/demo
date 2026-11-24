# LEVEL 13 — DUAL 3D DENTAL ANATOMY INTEGRATION REPORT

**Project:** DENTRACE — Local-First Clinical Decision Support Engine  
**Release Gate:** Level 13 (Dual 3D Anatomy Replacement & Integration)  
**Status:** COMPLETE & VERIFIED  
**Date:** 2026-11-14  
**Runtime:** Localhost (FastAPI + React 18 + Three.js r168)  
**Zero Cloud Egress:** Strictly Preserved  

---

## 1. Executive Summary

Level 13 replaced the experimental procedural tooth generator (`anatomicalToothBuilder.ts` and associated parametric lofting algorithms) with two authentic, locally bundled 3D anatomical models:
1. **Model A (Full Dental Arch):** OrganUI `teeth-3d` GLB model containing 28 individually selectable human teeth with natural anatomical proportions, complete roots, gingiva (gums), and maxillomandibular context.
2. **Model B (Detailed Cutaway Tooth):** 10-layer anatomical cross-section model (`tooth-cutaway.glb`) detailing enamel, coronal dentin, radicular dentin, cementum, periodontal ligament (PDL), coronal pulp chamber, and four discrete root canals (MB1, MB2, DB, Palatal).

A single-page clinical dual-mode switch (`[Full Dental Arch]` | `[Tooth Anatomy]`) allows clinicians and students to transition between spatial arch synchronization and microscopic histopathological cutaway inspection without disrupting case review or finding dossiers.

---

## 2. Integrated Asset Summary

| Specification | Model A: Complete Dental Arch | Model B: Anatomical Cutaway Tooth |
| :--- | :--- | :--- |
| **Asset Filename** | `/models/teeth.glb` | `/models/tooth-cutaway.glb` |
| **Local Staging Path** | `d:\mini\web\public\models\teeth.glb` | `d:\mini\web\public\models\tooth-cutaway.glb` |
| **Source Repository** | [github.com/organui/teeth-3d](https://github.com/organui/teeth-3d) | [github.com/Yoosseph/dental-scope](https://github.com/Yoosseph/dental-scope) |
| **Primary Dataset** | BodyParts3D / Anatomography 4.3 (FMA 3.0) | BodyParts3D adapted by Yoosseph / dental-scope |
| **File Format** | Binary glTF 2.0 (`.glb`) | Binary glTF 2.0 (`.glb`, native Three.js compatible) |
| **File Size** | 1,518,540 bytes (1.45 MB) | 1,050,440 bytes (1.00 MB) |
| **SHA-256** | `89a1074b0806eb41c318d38c78a269134c5070be7b90cb2f93ab2de7d35ec239` | `cf619a0a86b1f20fb142fe9d56eb722c26217dc436fc7bfb650a3ee4685ff530` |
| **Total Mesh Nodes** | 33 nodes (28 teeth + 2 gums + 3 jaw bones) | 10 anatomical layers |
| **Tooth Count** | 28 teeth (FDI 11–17, 21–27, 31–37, 41–47) | 1 maxillary 1st molar cutaway (FDI 16) |
| **3rd Molars** | Absent in source (FDI 18, 28, 38, 48 Unmapped) | N/A |
| **License** | CC BY-SA 2.1 Japan | CC BY-SA 4.0 / CC BY-SA 2.1 Japan |

---

## 3. Architecture & Integration Details

### 3.1 Dual-View Switcher (`DentalArch3D.tsx`)
`DentalArch3D.tsx` acts as the unified high-level presentation component. It preserves the exact backward-compatible interface:
```typescript
interface DentalArch3DProps {
  selectedFdi?: number | null;
  onSelectTooth?: (fdi: number) => void;
  findings?: Finding[];
  height?: number | string;
}
```
All existing consumers (`SinglePageExperience.tsx`, `OverviewView.tsx`, `FdiExplorerView.tsx`) require zero modification and automatically receive the dual 3D anatomy capabilities.

### 3.2 Model A Viewer (`DentalArchGLTF.tsx`)
- **Teeth Centering:** Re-centered around the 28-tooth bounding box (`center = (0.0, -0.54, 0.45) -> (0,0,0)`) so the occlusal plane sits directly in the camera focal volume.
- **Material Tuning:** Photorealistic ivory enamel (`MeshPhysicalMaterial`, roughness `0.16`, clearcoat `1.0`, clearcoatRoughness `0.05`, IOR `1.55`).
- **Anatomy Toggles:**
  - `Gums` (Show/Hide): Enables viewing teeth in isolation with full roots (matching clinical reference) or embedded in vascular gingiva.
  - `Bone` (Show/Hide): Default OFF to avoid obscuring apical anatomy; toggleable for maxillomandibular cranial context.
  - `Arch Filter`: Both Arches, Upper Only, Lower Only.
  - `Camera Presets`: 3D Orbit, Frontal, Upper Occlusal, Lower Occlusal, Reset.
- **Finding Synchronization:** Amber (`#F59E0B`) and Red (`#EF4444`) highlighting synchronized directly with YOLO/CDT findings via `fdiMapping.ts`.

### 3.3 Model B Viewer (`ToothCutaway3D.tsx`)
- **Cross-Sectional Layers:**
  - `enamel-16`: Translucent hydroxyapatite outer shell (transmission `0.25`, roughness `0.14`, clearcoat `1.0`).
  - `dentin-coronal-16`: Coronal dentin substrate (`#E5D3A3`).
  - `dentin-radicular-16`: Root dentin bulk (`#D1BD84`).
  - `cementum-16`: Acellular/cellular root cementum (`#BFA673`).
  - `pdl-16`: Periodontal ligament membrane (`#E5989B`, opacity `0.60`).
  - `pulp-chamber-16`: Vascular coronal pulp chamber (`#DC2626`, emissive `#7F1D1D`).
  - `canal-distobuccal-16`, `canal-palatal-16`, `canal-mesiobuccal-1-16`, `canal-mesiobuccal-2-16`: Discrete endodontic canals with emissive vascular rendering.
- **Layer Toggles:** Enamel, Dentin, Pulp/Canals, PDL.
- **Histopathology Dossier:** Interactive card displays clinical description and histological notes for any selected structure.

---

## 4. Preservation of System Baseline

1. **FastAPI Backend:** Zero backend modifications. All routes (`/api/v1/health`, `/api/v1/studies`, `/api/v1/insurance`, etc.) unchanged.
2. **AI Inference & YOLO Segmentation:** Unchanged; neural bounding boxes and polygon confidence scores pass directly to the 3D model.
3. **ReportLab PDF Claim Pack:** Generates multi-page pre-authorization claim packs with 100% parity.
4. **Offline Operation:** Zero external network requests; all assets served locally from `d:\mini\web\dist`.
5. **Regulatory Disclaimers:** Visible in every view:
   - *"Draft for dentist review. Not a diagnosis."*
   - *"Reference 3D Dental Anatomy — Not Patient-Specific"*
   - *"Anatomical Cutaway — Educational Reference"*

---

## 5. Verification Sign-Off

- [x] Model A loads locally without network egress
- [x] Model B loads locally without network egress
- [x] Gums and bone toggles work interactively
- [x] Verified FDI mapping matches actual geometry
- [x] Backend findings synchronize with FDI highlights
- [x] Responsive layout verified at 1920x1080 and 1366x768
- [x] TypeScript compilation: 0 errors
- [x] Browser console: 0 errors
