# LEVEL 13 — TEST BATTERY & VERIFICATION REPORT

**Project:** DENTRACE  
**Test Date:** 2026-11-14  
**Environment:** Windows (PowerShell, Chromium Headless, FastAPI, React 18, Three.js 0.168.0)  
**Overall Result:** 17 / 17 TESTS PASSED (100% PASS RATE)  

---

## 1. Test Execution Matrix

| # | Test Case Description | Target Component | Expected Result | Actual Result | Status |
| :- | :--- | :--- | :--- | :--- | :--- |
| **1** | Model A Offline Loading | `DentalArchGLTF.tsx` | Loads `/models/teeth.glb` with zero network egress | Loaded 1,518,540 bytes from local static mount | **PASS** |
| **2** | Upper & Lower Jaws Display | `DentalArchGLTF.tsx` | Both maxillary & mandibular arches render simultaneously | Rendered with anatomically correct occlusal spacing | **PASS** |
| **3** | Individual Tooth Selection | `DentalArchGLTF.tsx` | Raycasting selects individual mesh and triggers `onSelectTooth` | Raycaster intersects tooth meshes; sets `activeFdi` | **PASS** |
| **4** | FDI Mapping Verification | `fdiMapping.ts` | 28 teeth map to verified FDI 11–17, 21–27, 31–37, 41–47 | All 28 meshes resolve correctly; 3rd molars marked unmapped | **PASS** |
| **5** | FDI 38 & 43 Highlights | `DentalArchGLTF.tsx` | FDI 43 highlights tooth; FDI 38 does not highlight arbitrary tooth | FDI 43 highlights #43; unmapped FDI 38 does not trigger false mesh | **PASS** |
| **6** | General Findings Handling | `DentalArchGLTF.tsx` | Findings without tooth FDI do not highlight random teeth | Only findings with valid mapped tooth FDI highlight | **PASS** |
| **7** | Model B Offline Loading | `ToothCutaway3D.tsx` | Loads `/models/tooth-cutaway.glb` with zero network egress | Loaded 1,050,440 bytes from local static mount | **PASS** |
| **8** | Anatomical Structures Visible | `ToothCutaway3D.tsx` | Enamel, coronal/radicular dentin, pulp, canals, PDL visible | All 10 internal meshes render with differentiated shaders | **PASS** |
| **9** | Labels Match Actual Meshes | `ToothCutaway3D.tsx` | Selecting structure displays accurate clinical/histological note | 100% match with `CUTAWAY_STRUCTURES` metadata dictionary | **PASS** |
| **10**| Context Preservation on Toggle | `DentalArch3D.tsx` | Switching Arch <-> Cutaway maintains study & finding state | State persists in parent `SinglePageExperience.tsx` | **PASS** |
| **11**| OPG Upload & Inference | Backend & Workstation | Image upload, neural detection, and polygon overlay work | CASE-D49166F1 loaded with 4 real findings | **PASS** |
| **12**| Finding Dossier Synchronization | Workstation & 3D Arch | Clicking finding selects matching tooth in 3D arch | Clicking finding FND-64F84929 activates FDI #42 in 3D | **PASS** |
| **13**| Case Switching Cache Reset | SinglePageExperience | Switching studies clears previous tooth highlights | Stale highlights purged on `currentStudy` update | **PASS** |
| **14**| Local ReportLab PDF Export | Insurance API Route | Generates valid multi-page PDF claim pack | HTTP 200, 9,728 bytes returned with `%PDF-1.4` header | **PASS** |
| **15**| Zero Console Errors / Leaks | Chromium Headless | Zero JavaScript errors, zero WebGL warnings | 0 errors logged across all test workflows | **PASS** |
| **16**| Localhost / Offline Security | FastAPI Security | Zero cloud egress, strictly localhost `127.0.0.1:8000` | CSP verified; all static assets served locally | **PASS** |
| **17**| Responsive Layout Tests | UI Viewports | 1920x1080, 1366x768, and laptop viewports render cleanly | Screenshots captured at 1920x1080 and 1366x768 verified | **PASS** |

---

## 2. Evidence Artifacts

1. `level13_v3_arch_gums.png` — Complete 3D dental arch with anatomical gingival tissues and floating clinical control bar.
2. `level13_v3_pure_teeth.png` — Pure photorealistic human teeth with full roots floating in dark studio mode (gums toggled off), matching user's reference photograph.
3. `level13_v3_cutaway.png` — Microscopic anatomical cross-section highlighting coronal enamel, dentin, coronal pulp chamber, and 4 root canals.
4. `level13_v3_case_loaded.png` — Single-page clinical workspace synchronizing panoramic OPG radiograph, neural bounding reticles, 4 actual model detections, and synchronized 3D FDI highlight.
5. `level13_responsive_1920x1080.png` — High-resolution desktop clinical display.
6. `level13_responsive_1366x768.png` — Standard laptop clinical display.

---

## 3. Regulatory Statement

All rendered 3D views feature prominent medical disclaimers:
- **Header Disclaimer:** *"Draft for dentist review. Not a diagnosis."*
- **Arch Model Label:** *"Reference 3D Dental Anatomy — Not Patient-Specific"*
- **Cutaway Model Label:** *"Anatomical Cutaway — Educational Reference"*
