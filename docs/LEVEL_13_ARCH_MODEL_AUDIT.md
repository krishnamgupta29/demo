# LEVEL 13 — MODEL A (DENTAL ARCH) AUDIT

**Model Name:** OrganUI Teeth 3D Dental Arch  
**Asset File:** `/models/teeth.glb` (`d:\mini\web\public\models\teeth.glb`)  
**Source Repository:** [https://github.com/organui/teeth-3d](https://github.com/organui/teeth-3d)  
**Primary Medical Dataset:** BodyParts3D / Anatomography 4.3 (Database Center for Life Science, Japan)  
**Ontology Standard:** Foundational Model of Anatomy (FMA 3.0)  
**Audit Date:** 2026-11-14  

---

## 1. Asset Specifications & Cryptographic Verification

| Property | Value |
| :--- | :--- |
| **Format** | Binary glTF 2.0 (`.glb`) |
| **Byte Size** | 1,518,540 bytes |
| **SHA-256 Checksum** | `89a1074b0806eb41c318d38c78a269134c5070be7b90cb2f93ab2de7d35ec239` |
| **Manifest Checksum** | `c3d16c891016da13447de2fc3241d05d92e8f9dc460e363233c03f420b935d4f` |
| **Total Nodes** | 33 |
| **Total Meshes** | 33 |
| **Total Materials** | 33 |
| **Required Extensions** | None (100% native Three.js WebGL compatibility) |
| **Bounding Box (All)** | `[-1.33, -1.40, -1.18]` to `[1.33, 1.40, 1.18]` |
| **Bounding Box (Teeth)**| `[-0.82, -1.26, -0.27]` to `[0.82, 0.18, 1.16]` (Size: 1.64 x 1.43 x 1.43) |

---

## 2. Anatomical Structure Inventory (33 Meshes)

### 2.1 Maxillary Arch (Upper Jaw) — 14 Teeth
| Node Name | FMA Concept | FDI Code | Vertices | Triangles | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `upper-right-central-incisor` | FMA55681 | 11 | 647 | 1,288 | Maxillary Right Central Incisor |
| `upper-right-lateral-incisor` | FMA55680 | 12 | 686 | 1,368 | Maxillary Right Lateral Incisor |
| `upper-right-canine` | FMA55798 | 13 | 698 | 1,392 | Maxillary Right Canine |
| `upper-right-first-premolar` | FMA55689 | 14 | 816 | 1,610 | Maxillary Right 1st Premolar |
| `upper-right-second-premolar` | FMA55688 | 15 | 748 | 1,466 | Maxillary Right 2nd Premolar |
| `upper-right-first-molar` | FMA55698 | 16 | 1,099 | 2,156 | Maxillary Right 1st Molar (Trifurcated) |
| `upper-right-second-molar` | FMA55697 | 17 | 961 | 1,850 | Maxillary Right 2nd Molar (Trifurcated) |
| `upper-left-central-incisor` | FMA55682 | 21 | 646 | 1,288 | Maxillary Left Central Incisor |
| `upper-left-lateral-incisor` | FMA55683 | 22 | 691 | 1,378 | Maxillary Left Lateral Incisor |
| `upper-left-canine` | FMA55799 | 23 | 698 | 1,392 | Maxillary Left Canine |
| `upper-left-first-premolar` | FMA55690 | 24 | 816 | 1,610 | Maxillary Left 1st Premolar |
| `upper-left-second-premolar` | FMA55691 | 25 | 748 | 1,466 | Maxillary Left 2nd Premolar |
| `upper-left-first-molar` | FMA55699 | 26 | 1,099 | 2,156 | Maxillary Left 1st Molar (Trifurcated) |
| `upper-left-second-molar` | FMA55700 | 27 | 961 | 1,850 | Maxillary Left 2nd Molar (Trifurcated) |

### 2.2 Mandibular Arch (Lower Jaw) — 14 Teeth
| Node Name | FMA Concept | FDI Code | Vertices | Triangles | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `lower-left-central-incisor` | FMA55685 | 31 | 589 | 1,170 | Mandibular Left Central Incisor |
| `lower-left-lateral-incisor` | FMA55686 | 32 | 609 | 1,210 | Mandibular Left Lateral Incisor |
| `lower-left-canine` | FMA55801 | 33 | 695 | 1,386 | Mandibular Left Canine |
| `lower-left-first-premolar` | FMA55693 | 34 | 748 | 1,466 | Mandibular Left 1st Premolar |
| `lower-left-second-premolar` | FMA55694 | 35 | 807 | 1,592 | Mandibular Left 2nd Premolar |
| `lower-left-first-molar` | FMA55702 | 36 | 1,079 | 2,118 | Mandibular Left 1st Molar (Bifurcated) |
| `lower-left-second-molar` | FMA55703 | 37 | 993 | 1,944 | Mandibular Left 2nd Molar (Bifurcated) |
| `lower-right-central-incisor` | FMA55684 | 41 | 589 | 1,170 | Mandibular Right Central Incisor |
| `lower-right-lateral-incisor` | FMA55687 | 42 | 609 | 1,210 | Mandibular Right Lateral Incisor |
| `lower-right-canine` | FMA55800 | 43 | 695 | 1,386 | Mandibular Right Canine |
| `lower-right-first-premolar` | FMA55692 | 44 | 748 | 1,466 | Mandibular Right 1st Premolar |
| `lower-right-second-premolar` | FMA55695 | 45 | 807 | 1,592 | Mandibular Right 2nd Premolar |
| `lower-right-first-molar` | FMA55701 | 46 | 1,079 | 2,118 | Mandibular Right 1st Molar (Bifurcated) |
| `lower-right-second-molar` | FMA55704 | 47 | 993 | 1,944 | Mandibular Right 2nd Molar (Bifurcated) |

### 2.3 Supporting Soft Tissue & Craniofacial Bones — 5 Structures
| Node Name | FMA Concept | Role | Default Rendering |
| :--- | :--- | :--- | :--- |
| `upper-gum` | FMA59762 | Maxillary Gingiva | Vascular Mucosal Pink (`#B95A64`), Toggleable |
| `lower-gum` | FMA59762 | Mandibular Gingiva | Vascular Mucosal Pink (`#B95A64`), Toggleable |
| `right-maxilla` | FMA52749 | Right Upper Jawbone | Cortical Bone (`#D2C8B8`), Transparent (Opacity 0.65), Default OFF |
| `left-maxilla` | FMA52749 | Left Upper Jawbone | Cortical Bone (`#D2C8B8`), Transparent (Opacity 0.65), Default OFF |
| `mandible` | FMA52748 | Lower Jawbone | Cortical Bone (`#D2C8B8`), Transparent (Opacity 0.65), Default OFF |

---

## 3. Critical Clinical Findings & Limitations

1. **Third Molars (Wisdom Teeth):**
   - The OrganUI / BodyParts3D asset strictly provides **28 teeth**.
   - FDI 18, 28, 38, and 48 are not present in the mesh hierarchy.
   - **Compliance Rule:** Under no circumstances are missing wisdom teeth procedurally fabricated or falsely presented.
   - DENTRACE handles backend findings referencing FDI 18/28/38/48 in the findings dossier without highlighting false geometry in the 3D viewer.
2. **True Solid Mesh Geometry:**
   - Unlike the retired procedural lofting generator which suffered from open polygonal caps and interior backface artifacts, every mesh in `teeth.glb` is a sealed, watertight, anatomically scanned solid.
   - Viewing from inferior, superior, or occlusal perspectives reveals no hollow black voids or interpenetrating geometric shells.
