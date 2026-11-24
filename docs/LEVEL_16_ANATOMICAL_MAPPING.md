# LEVEL 16 — DENTRACE 3D ANATOMICAL MAPPING & ARCH ARCHITECTURE
**Technical Specification: 28 Anatomical Teeth vs 4 Placeholder Markers, Cutaway Layer Highlighting, and Educational Correlations**  
*Academic College Decision Support Prototype | Localhost Execution (127.0.0.1)*  
*Date of Specification: November 14, 2026*  
*Regulatory Boundary: "Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR."*

---

## 1. 3D Architectural Architecture & Ground Truth

DENTRACE incorporates interactive 3D WebGL visualizations using Three.js to provide clinicians with visual reference models alongside 2D panoramic radiographs.

### 1.1 Mandatory Regulatory Boundary
All 3D models embedded in DENTRACE are **generic educational reference meshes**, not patient-specific reconstructions generated from cone-beam computed tomography (CBCT) or stereolithography (STL) scans. 

Both the 3D full dental arch view and the tooth cutaway view display a persistent clinical pill:
> **"Reference 3D Dental Anatomy — Not Patient-Specific"**

---

## 2. Full Dental Arch Architecture: 28 Solid Teeth vs 4 Wisdom Tooth Markers

### 2.1 The 28-Tooth Anatomical Foundation
The primary 3D dental arch (`web/src/components/3d/DentalArchGLTF.tsx`) renders the standard adult dentition consisting of **28 fully modeled anatomical teeth**:
- **Maxillary Arch (Upper Jaw):**
  - Central Incisors: 11, 21
  - Lateral Incisors: 12, 22
  - Canines: 13, 23
  - Premolars: 14, 15, 24, 25
  - First & Second Molars: 16, 17, 26, 27
- **Mandibular Arch (Lower Jaw):**
  - Central Incisors: 31, 41
  - Lateral Incisors: 32, 42
  - Canines: 33, 43
  - Premolars: 34, 35, 44, 45
  - First & Second Molars: 36, 37, 46, 47

These 28 teeth are loaded from individual high-resolution `.glb` mesh assets with accurate coronal morphology, root morphology, and gingival margins.

### 2.2 The 4 Wisdom Tooth Placeholder Markers (FDI 18, 28, 38, 48)
Because the reference base mesh does not contain full third molar anatomical geometries, FDI teeth **18, 28, 38, and 48** are rendered as **semi-transparent reference placeholder markers**:
- **Visual Styling:** Rendered with 40% opacity, dotted boundary rings, and a distinct neutral tone.
- **Clinical Banner Notification:**
  When a user selects a third molar (e.g., FDI 48), the UI displays:
  > *"FDI #48 is a Reference Marker. This position serves as a spatial reference indicator; high-fidelity 3D geometry is available for the 28 primary arch teeth."*
- **Truthful Disclosure:** DENTRACE never presents these 4 markers as full anatomical teeth.

---

## 3. Tooth Cutaway View: High-Fidelity Reference Molar (FDI 16)

### 3.1 Single-Tooth Cutaway Architecture
The cutaway mode (`web/src/components/3d/ToothCutaway3D.tsx`) renders an isolated, sectioned Maxillary Right First Molar (**FDI 16**):
- **Why FDI 16?** The maxillary first molar is the largest tooth in the human arch, displaying complex trifurcated root anatomy (mesiobuccal, distobuccal, palatal roots) and multi-layered internal histology (enamel cap, coronal and radicular dentin, pulp chamber, root canals, and apical foramina).
- **Why One Tooth?** Sectioning all 32 teeth simultaneously would incur severe WebGL shader and memory overhead and create visual clutter. Highlighting the representative internal histology of a molar provides clear educational context for any coronal or periapical finding.
- **State Preservation:** Switching between the Full Arch and Tooth Cutaway views preserves the current case findings, active selection, and review statuses without reloading or resetting camera positions.

### 3.2 Internal Histological Layers
The cutaway model exposes five distinct tissue layers:
1. **Enamel:** Outermost hard mineralized shell covering the anatomical crown.
2. **Coronal & Radicular Dentin:** Primary structural bulk of the tooth surrounding the pulp cavity.
3. **Pulp Chamber & Root Canals:** Vascularized, innervated soft tissue core extending from coronal pulp horns to root apices.
4. **Periodontal Ligament (PDL):** Fibrous connective tissue anchoring root cementum to the alveolar bone.
5. **Apical Foramen & Periapical Bone:** Terminal aperture at root tips and surrounding trabecular bone.

---

## 4. Educational Pathology Correlation Matrix

When an AI finding or clinician review selects a specific pathology, `ToothCutaway3D` highlights the corresponding histological structures using color-coded emissive materials:

| Pathology | Correlated Histological Structure | Emissive Color Code | Educational Clinical Description |
|---|---|---|---|
| **Caries (Enamel / Shallow)** | Enamel Cap & Coronal Dentin | Amber (`#F59E0B`) | Demineralization restricted to outer enamel rod matrix and outer dentin boundary; pulp chamber intact. |
| **Deep Caries** | Inner Dentin & Coronal Pulp Horns | Orange-Red (`#F97316`) | Advanced bacterial infiltration penetrating deep secondary dentin, threatening or contacting coronal pulp horns. |
| **Periapical Lesion** | Root Apex, PDL & Apical Foramen | Crimson (`#EF4444`) | Inflammatory osteolysis and radiolucency at root apex following pulpal necrosis and bacterial egress through apical foramina. |
| **Impacted Tooth** | Distal/Mesial Boundary & Alveolar Margin | Indigo (`#6366F1`) | Spatial impaction against adjacent root structures (e.g., second molar distal root) or alveolar bone crest. |

### 4.1 Educational Banner in UI
Whenever an anomaly is active, the bottom of the 3D viewport renders a dedicated educational context card:
> **"Educational Anatomy Correlation:** Showing anatomical layers for **[Pathology Name]**. Lesion correlates with **[Correlated Tissue]** in reference model."

---

## 5. WebGL Canvas Snapshot Capture Contract

To guarantee seamless integration into the 4-page PDF export:
1. Both `DentalArchGLTF.tsx` and `ToothCutaway3D.tsx` instantiate the `THREE.WebGLRenderer` with `preserveDrawingBuffer: true`.
2. When the clinician opens the **Pre-Authorization Studio Modal**, the client reads `canvas.toDataURL("image/png")` and includes the Base64 data in the `POST /api/v1/insurance/studies/{id}/claim-pack/pdf` payload as `snapshot_3d_bytes`.
3. The backend decodes this buffer and renders the live visual snapshot directly onto **Page 3** of the clinical report alongside the educational correlation table.
