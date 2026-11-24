# LEVEL 19 — TOOTH-SPECIFIC ANATOMICAL CORRELATION & 3D CUTAWAY ARCHITECTURE

**System:** DENTRACE Clinical Decision Support Engine  
**Component:** 3D Anatomical Spatial Model & Micro-CT Cutaway  
**Mandatory Label:** *"Reference 3D Dental Anatomy — Not Patient-Specific."*

---

## 1. Educational vs Patient-Specific Clinical Boundary

DENTRACE provides interactive 3D visualizations to educate clinicians and patients regarding the internal dental histological structures involved in suspected pathologies. 

**Strict Clinical Limit:**
- 2D panoramic and intraoral radiographs do not record 3D volumetric depth.
- The 3D molar cutaway model (`tooth-cutaway.glb`) is an educational reference derived from high-resolution micro-CT data, NOT a reconstructed patient-specific scan.
- Under no circumstances does DENTRACE automatically claim a caries lesion reaches the pulp chamber or root canal solely based on 2D visual neural detections.
- For IOPA radiographs, anatomical structure selection is explicitly designated as **Clinician-Entered** observation.

---

## 2. Supported Anatomical Structures

DENTRACE correlates observations against 8 canonical dental histological structures:

| Structure | Anatomical Category | Clinical Significance | Educational Description |
|:---|:---:|:---|:---|
| **Enamel** | Acellular Crown Shell | Initial caries attack; remineralization target | Acellular, 96% mineralized hydroxyapatite outer protective layer of the crown. |
| **Dentin** | Coronal / Radicular Bulk | Tubule penetration; operative intervention required | Mineralized bulk containing dentinal tubules; transmits thermal and osmotic sensation. |
| **Pulp Chamber** | Coronal Endodontic Core | Pulpitis; vitality testing indicated | Vascular and neural core containing odontoblasts, fibroblasts, and capillaries. |
| **Root Canal** | Radicular Conduit | Root canal treatment (RCT) pathway | Endodontic conduit transmitting nerves and blood vessels through the root. |
| **Cementum** | Root Surface Layer | Periodontal attachment; root caries | Specialized calcified tissue covering root dentin, anchoring periodontal Sharpey fibers. |
| **Periodontal Ligament (PDL)** | Fibrous Suspension | Mobility; periodontal pocketing | Fibrous connective tissue bundle suspending the tooth root within the alveolar socket. |
| **Root Apex** | Apical Terminal | Apical periodontitis; periapical lucency | Terminal endpoint of the root housing the apical foramen where neurovascular bundles enter. |
| **Periapical Region** | Surrounding Alveolar Bone | Periapical abscess / granuloma / cyst | Surrounding bone and soft tissue at the root apex; common site of endodontic pathology. |

---

## 3. UI Synchronization & Interaction Flow

```
User selects tooth FDI on X-Ray / IOPA Strip
                   │
                   ▼
Highlights tooth in Full Dental Arch (DentalArchGLTF)
                   │
                   ▼
User clicks "Tooth Anatomy" View Mode
                   │
                   ▼
Renders 3D Cutaway Model (ToothCutaway3D)
  ├── 8 Anatomical Structure Quick Buttons
  ├── Histological Layer Visibility Toggles (Enamel, Dentin, Pulp, PDL)
  └── Persistent Reference Disclaimer Banner
```
