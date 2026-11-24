# LEVEL 13 — FDI NUMBERING & AI FINDING MAPPING AUDIT

**Specification:** ISO 3950 / FDI Two-Digit Dental Numbering System  
**Implementation File:** `d:\mini\web\src\components\3d\fdiMapping.ts`  
**Reference Asset:** `teeth.glb` (OrganUI / BodyParts3D 4.3)  
**Audit Date:** 2026-11-14  

---

## 1. Complete FDI Mapping Matrix (28 Verified Teeth)

The mapping between GLB node identifiers and FDI tooth numbers is deterministic and verified against the Foundational Model of Anatomy (FMA) ontology:

```
                      MAXILLARY (UPPER) ARCH
               Right (Q1)                Left (Q2)
       17  16  15  14  13  12  11 | 21  22  23  24  25  26  27
      ----------------------------+----------------------------
       47  46  45  44  43  42  41 | 31  32  33  34  35  36  37
               Right (Q4)                Left (Q3)
                      MANDIBULAR (LOWER) ARCH
```

### Quadrant 1: Maxillary Right
| FDI | Mesh Identifier | FMA Identifier | Anatomical Designation | Position | Verified Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **11** | `upper-right-central-incisor` | FMA55681 | Central Incisor | Anterior | Verified |
| **12** | `upper-right-lateral-incisor` | FMA55680 | Lateral Incisor | Anterior | Verified |
| **13** | `upper-right-canine` | FMA55798 | Canine (Cuspid) | Anterior | Verified |
| **14** | `upper-right-first-premolar` | FMA55689 | 1st Premolar (Bicuspid) | Posterior | Verified |
| **15** | `upper-right-second-premolar` | FMA55688 | 2nd Premolar (Bicuspid) | Posterior | Verified |
| **16** | `upper-right-first-molar` | FMA55698 | 1st Molar (6-yr Molar) | Posterior | Verified |
| **17** | `upper-right-second-molar` | FMA55697 | 2nd Molar (12-yr Molar) | Posterior | Verified |
| **18** | *(none)* | *(none)* | 3rd Molar (Wisdom Tooth)| Posterior | **UNMAPPED** |

### Quadrant 2: Maxillary Left
| FDI | Mesh Identifier | FMA Identifier | Anatomical Designation | Position | Verified Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **21** | `upper-left-central-incisor` | FMA55682 | Central Incisor | Anterior | Verified |
| **22** | `upper-left-lateral-incisor` | FMA55683 | Lateral Incisor | Anterior | Verified |
| **23** | `upper-left-canine` | FMA55799 | Canine (Cuspid) | Anterior | Verified |
| **24** | `upper-left-first-premolar` | FMA55690 | 1st Premolar (Bicuspid) | Posterior | Verified |
| **25** | `upper-left-second-premolar` | FMA55691 | 2nd Premolar (Bicuspid) | Posterior | Verified |
| **26** | `upper-left-first-molar` | FMA55699 | 1st Molar (6-yr Molar) | Posterior | Verified |
| **27** | `upper-left-second-molar` | FMA55700 | 2nd Molar (12-yr Molar) | Posterior | Verified |
| **28** | *(none)* | *(none)* | 3rd Molar (Wisdom Tooth)| Posterior | **UNMAPPED** |

### Quadrant 3: Mandibular Left
| FDI | Mesh Identifier | FMA Identifier | Anatomical Designation | Position | Verified Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **31** | `lower-left-central-incisor` | FMA55685 | Central Incisor | Anterior | Verified |
| **32** | `lower-left-lateral-incisor` | FMA55686 | Lateral Incisor | Anterior | Verified |
| **33** | `lower-left-canine` | FMA55801 | Canine (Cuspid) | Anterior | Verified |
| **34** | `lower-left-first-premolar` | FMA55693 | 1st Premolar (Bicuspid) | Posterior | Verified |
| **35** | `lower-left-second-premolar` | FMA55694 | 2nd Premolar (Bicuspid) | Posterior | Verified |
| **36** | `lower-left-first-molar` | FMA55702 | 1st Molar (6-yr Molar) | Posterior | Verified |
| **37** | `lower-left-second-molar` | FMA55703 | 2nd Molar (12-yr Molar) | Posterior | Verified |
| **38** | *(none)* | *(none)* | 3rd Molar (Wisdom Tooth)| Posterior | **UNMAPPED** |

### Quadrant 4: Mandibular Right
| FDI | Mesh Identifier | FMA Identifier | Anatomical Designation | Position | Verified Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **41** | `lower-right-central-incisor` | FMA55684 | Central Incisor | Anterior | Verified |
| **42** | `lower-right-lateral-incisor` | FMA55687 | Lateral Incisor | Anterior | Verified |
| **43** | `lower-right-canine` | FMA55800 | Canine (Cuspid) | Anterior | Verified |
| **44** | `lower-right-first-premolar` | FMA55692 | 1st Premolar (Bicuspid) | Posterior | Verified |
| **45** | `lower-right-second-premolar` | FMA55695 | 2nd Premolar (Bicuspid) | Posterior | Verified |
| **46** | `lower-right-first-molar` | FMA55701 | 1st Molar (6-yr Molar) | Posterior | Verified |
| **47** | `lower-right-second-molar` | FMA55704 | 2nd Molar (12-yr Molar) | Posterior | Verified |
| **48** | *(none)* | *(none)* | 3rd Molar (Wisdom Tooth)| Posterior | **UNMAPPED** |

---

## 2. AI Finding Synchronization Rules

1. **Deterministic Tooth Highlighting:**
   - When a clinical finding from the backend has a valid mapped FDI number (e.g. `tooth_fdi: 42`), the matching mesh (`lower-right-lateral-incisor`) is highlighted.
   - High confidence (>0.80): High-urgency Coral/Red (`#EF4444`).
   - Moderate confidence (≤0.80): Amber/Gold (`#F59E0B`).
2. **Third Molar Findings (FDI 18, 28, 38, 48):**
   - In CASE-D49166F1, the AI detects a finding on **FDI 38 (Caries, 36%)**.
   - Because FDI 38 is unmapped, DENTRACE **does not highlight an arbitrary tooth**. The finding is accurately represented in the findings dossier and radiograph overlay without corrupting the 3D anatomical viewer.
3. **General Findings (No Tooth FDI):**
   - Findings without an assigned FDI number (e.g. generalized bone loss, sinus opacification) remain in the clinical evidence review and do not trigger arbitrary tooth selections.
4. **Case Switching & Cache Invalidation:**
   - Whenever `currentStudy` changes, all previous 3D highlights and selection rings are immediately invalidated and rebuilt from the incoming study findings.
