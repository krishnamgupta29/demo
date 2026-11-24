# LEVEL 13 — 3D ASSET LICENSING & ATTRIBUTION AUDIT

**Compliance Framework:** Local-First Academic & Decision Support Use  
**Audit Date:** 2026-11-14  

---

## 1. Model A: OrganUI Teeth 3D Dental Arch

### 1.1 Source Repository & Authors
- **Repository:** `https://github.com/organui/teeth-3d`
- **Authors/Maintainers:** OrganUI Contributors
- **Code License:** MIT License

### 1.2 Underlying Medical Data: BodyParts3D / Anatomography
- **Original Source:** BodyParts3D, Database Center for Life Science (DBCLS), Japan.
- **Dataset Release:** BodyParts3D release 4.3 (FMA 3.0 ontology)
- **Data License:** Creative Commons Attribution-ShareAlike 2.1 Japan (`CC BY-SA 2.1 JP`)
- **Official URL:** `https://lifesciencedb.jp/bp3d/`

### 1.3 Mandatory Attribution Statement
> *"BodyParts3D / Anatomography, © The Database Center for Life Science. Licensed under Creative Commons Attribution-Share Alike 2.1 Japan. Adapted by OrganUI for three-dimensional web visualization."*

---

## 2. Model B: Dental Scope Anatomical Cutaway

### 2.1 Source Repository & Authors
- **Repository:** `https://github.com/Yoosseph/dental-scope`
- **Authors/Maintainers:** Yoosseph and contributors
- **Code License:** MIT License

### 2.2 Content & 3D Geometry License
- **Content License:** Creative Commons Attribution-ShareAlike 4.0 International (`CC BY-SA 4.0`)
- **Underlying Anatomical Meshes:** Adapted from BodyParts3D (`CC BY-SA 2.1 JP`)

### 2.3 Mandatory Attribution Statement
> *"Dental-Scope 3D Tooth Anatomy, © Yoosseph and contributors. Licensed under CC BY-SA 4.0 / CC BY-SA 2.1 Japan. Cross-sectional anatomical layers adapted from BodyParts3D."*

---

## 3. Commercial & Redistribution Compliance Matrix

| Requirement | OrganUI `teeth.glb` | Dental-Scope `tooth-cutaway.glb` | DENTRACE Compliance Status |
| :--- | :--- | :--- | :--- |
| **Attribution Required** | Yes (CC BY-SA 2.1 JP) | Yes (CC BY-SA 4.0) | **Satisfied** (Documented in UI & License Audit) |
| **ShareAlike Required** | Yes (Modifications under SA) | Yes (Modifications under SA) | **Satisfied** (Open academic college distribution) |
| **Commercial Use Allowed** | Yes (with attribution) | Yes (with attribution) | **Satisfied** |
| **Offline Bundling Allowed** | Yes | Yes | **Satisfied** (Local bundling under public/models) |
| **Patent / Device Disclaimer** | Required by DENTRACE PS | Required by DENTRACE PS | **Satisfied** (*"Draft for dentist review. Not a diagnosis."*) |
