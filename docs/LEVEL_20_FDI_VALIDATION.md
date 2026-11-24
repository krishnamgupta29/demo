# LEVEL 20 — FDI TOOTH NUMBERING AUDIT & DEFAULT SELECTION ELIMINATION

> **DOCUMENT ID:** DOC-L20-FDI-003  
> **TOPIC:** Elimination of Hardcoded Default Tooth Selections & Synchronization Integrity  
> **DATE:** 2026-11-21  

---

## 1. Problem Statement

Screenshots of the application during Level 19/20 testing revealed a confusing visual defect:
- The 3D Dental Arch viewer rendered tooth FDI #16 (Maxillary Right First Molar) or FDI #12 as active/highlighted immediately upon opening the page or resetting a study.
- No finding had been clicked on the radiograph.
- No user had interacted with the odontogram.
- The IOPA focus strip was simultaneously displaying teeth #14, #15, #16, and #17, creating conflicting visual cues where the 3D model was disconnected from the radiograph findings.

---

## 2. Investigation of Hardcoded Defaults

A codebase-wide search for tooth number `16` uncovered hardcoded defaults across four key frontend components:

1. `web/src/views/SinglePageExperience.tsx`:
   ```typescript
   // Line 35:
   const [selectedFdi, setSelectedFdi] = useState<number | null>(16);
   
   // Line 451 (handleReset):
   setSelectedFdi(16);
   ```
2. `web/src/components/3d/DentalArchGLTF.tsx`:
   ```typescript
   // Line 38:
   interface DentalArchGLTFProps {
     selectedFdi?: number | null; // defaulted to 16
   }
   ```
3. `web/src/components/3d/DentalArch3D.tsx`:
   ```typescript
   // Line 17:
   export const DentalArch3D: React.FC<DentalArch3DProps> = ({
     selectedFdi = 16,
   ...
   ```
4. `web/src/components/3d/ToothCutaway3D.tsx`:
   ```typescript
   // Line 120:
   export const ToothCutaway3D: React.FC<ToothCutaway3DProps> = ({
     selectedFdi = 16,
   ...
   ```

Because of these default values, whenever a study was loaded or the page was initialized, the 3D viewer treated tooth #16 as selected, displaying clinical anatomy badges for an unselected tooth.

---

## 3. Systematic Remediation

### 3.1 Neutral State Implementation
All four components were refactored to allow and default to `null`:
- In `SinglePageExperience.tsx`:
  `const [selectedFdi, setSelectedFdi] = useState<number | null>(null);`
  `handleReset()` executes: `setSelectedFdi(null);`
- In `DentalArchGLTF.tsx`, `DentalArch3D.tsx`, `ToothCutaway3D.tsx`:
  `selectedFdi` defaults to `null`.

### 3.2 Clear "Select Tooth" UI Guidance
When `selectedFdi === null`:
- `DentalArchGLTF.tsx` bottom info bar displays:
  *"Select a tooth or finding to inspect"*
- `ToothCutaway3D.tsx` bottom badge displays:
  *"Educational Reference Anatomy — Select a tooth or finding to view anatomical tissue correlation"*
- The mandatory clinical disclaimer remains prominently visible:
  *"Reference 3D Dental Anatomy — Not Patient-Specific"*

### 3.3 Rule-Governed Auto-Selection on Case Load
When a clinical case with confirmed or candidate findings is loaded (such as sample `CASE-D49166F1`), the application intentionally selects the first detected finding's tooth:
```typescript
if (reloaded.findings && reloaded.findings.length > 0) {
  setSelectedFindingId(reloaded.findings[0].finding_id);
  if (reloaded.findings[0].tooth_fdi) {
    setSelectedFdi(reloaded.findings[0].tooth_fdi);
  }
}
```
In `CASE-D49166F1`, the primary finding is `FDI #42 · Periapical Lesion (74%)`. Thus, upon loading, tooth #42 is highlighted synchronously on both the radiograph and the 3D model. If an unanalyzed study or 0-anomaly study is loaded, `selectedFdi` remains strictly `null`.

---

## 4. Verification

1. **Initial Page Load:** Browser subagent verified at `http://127.0.0.1:5173/` that the 3D canvas is rendered in a neutral state with no highlighted teeth and the message *"Select a tooth or finding to inspect"*.
2. **Case Load Synchronization:** Loading `CASE-D49166F1` set tooth #42 active with complete cross-component synchronization.
3. **Manual Selection:** Clicking finding FDI #35 switched both the 2D bounding box and 3D arch to mandibular left second premolar.
