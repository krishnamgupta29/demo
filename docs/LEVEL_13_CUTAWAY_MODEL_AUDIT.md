# LEVEL 13 — MODEL B (CUTAWAY TOOTH) AUDIT

**Model Name:** Anatomical Cutaway Tooth (Maxillary 1st Molar)  
**Asset File:** `/models/tooth-cutaway.glb` (`d:\mini\web\public\models\tooth-cutaway.glb`)  
**Source Repository:** [https://github.com/Yoosseph/dental-scope](https://github.com/Yoosseph/dental-scope) (`tooth-16.glb`)  
**Primary Dataset:** BodyParts3D dental anatomy adapted for educational cross-sectional inspection  
**Audit Date:** 2026-11-14  

---

## 1. Asset Specifications & Cryptographic Verification

| Property | Value |
| :--- | :--- |
| **Format** | Binary glTF 2.0 (`.glb`, standard native accessors) |
| **Byte Size** | 1,050,440 bytes (1.00 MB) |
| **SHA-256 Checksum** | `cf619a0a86b1f20fb142fe9d56eb722c26217dc436fc7bfb650a3ee4685ff530` |
| **Mesh Count** | 10 discrete anatomical structures |
| **Extensions Required** | None (dequantized to standard IEEE-754 floats to comply with strict offline CSP) |
| **Bounding Box** | Centered at `(0, 0, 0)`, Dimensions: `1.13 x 2.49 x 1.12` Three.js units |

---

## 2. Layer-by-Layer Histological Structure Inventory

| Mesh Identifier | Layer Name | Category | Vertices | Assigned Shading / Material Properties |
| :--- | :--- | :--- | :--- | :--- |
| `enamel-16` | Crown Enamel | Enamel | 8,001 | Translucent Hydroxyapatite (`#F5F2E8`), clearcoat 1.0, roughness 0.14, transmission 0.25 |
| `dentin-coronal-16` | Coronal Dentin | Dentin | 5,502 | Warm Ivory (`#E5D3A3`), roughness 0.38, opaque solid |
| `dentin-radicular-16` | Radicular Dentin | Dentin | 7,875 | Deep Mineralized Dentin (`#D1BD84`), roughness 0.40 |
| `cementum-16` | Root Cementum | Cementum | 7,436 | Calcified Root Surface (`#BFA673`), roughness 0.45 |
| `pdl-16` | Periodontal Ligament | PDL | 2,502 | Fibrous Membrane (`#E5989B`), opacity 0.60, default OFF |
| `pulp-chamber-16` | Coronal Pulp Chamber | Pulp | 2,252 | Highly Vascular Ruby (`#DC2626`), emissive intensity 0.35 |
| `canal-distobuccal-16` | Distobuccal Canal | Canal | 902 | Vascular Conduit (`#B91C1C`), emissive intensity 0.35 |
| `canal-palatal-16` | Palatal Canal | Canal | 902 | Largest Canal Conduit (`#B91C1C`), emissive intensity 0.35 |
| `canal-mesiobuccal-1-16`| Mesiobuccal Canal 1 (MB1)| Canal | 902 | Anterior-Buccal Canal (`#B91C1C`), emissive intensity 0.35 |
| `canal-mesiobuccal-2-16`| Mesiobuccal Canal 2 (MB2)| Canal | 902 | Accessory MB Canal (`#B91C1C`), critical endodontic landmark |

---

## 3. Engineering & Offline Security Audit

### 3.1 Content Security Policy (CSP) Compatibility
The original raw asset from `dental-scope` utilized `EXT_meshopt_compression` which relied on runtime WebAssembly compilation via `MeshoptDecoder`. When deployed under the local CSP in `d:\mini\backend\main.py`:
```
script-src 'self' 'unsafe-inline'
```
The browser correctly rejected `WebAssembly.instantiate()` because `'wasm-unsafe-eval'` was not permitted.

**Resolution:**
The asset was processed via Three.js `GLTFExporter` offline during integration to unpack all compressed vertex buffers into clean standard binary glTF buffers. The resultant `.glb`:
- Requires **zero external decoders or WebAssembly instantiation**.
- Compiles with **zero CSP violations** and **zero console errors**.
- Loads instantly into WebGL memory with zero decompression latency.

### 3.2 Clinical Educational Value
The model provides dentists and students with immediate cross-sectional verification:
1. **Endodontic Anatomy:** Visualizing MB1, MB2, DB, and Palatal canals allows direct explanation of root canal therapy (CDT D3330) and periapical pathology.
2. **Caries Progression:** Clinicians can toggle the enamel shell off to illustrate dentinal tubule invasion and proximity to the pulp horns.
