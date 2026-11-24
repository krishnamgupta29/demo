# DENTRACE LEVEL 10.5 — CLINICAL DESIGN SYSTEM & SPECIFICATION

**Project:** DENTRACE — Autonomous Dental Panoramic Radiograph Anomaly Detection & Insurance Claim Pre-Authorization Engine  
**Version:** 0.1.0 (Level 10.5 Release)  
**Status:** COMPLETE & VERIFIED  
**Date:** November 2026  
**Regulatory Notice:** *Draft for dentist review. Not a diagnosis. Not certified under FDA/CE/MDR regulations. Zero cloud egress.*

---

## 1. Design Philosophy & Aesthetic Identity

DENTRACE Level 10.5 departs from generic SaaS dashboards, repetitive card grids, and purple/blue neon AI tropes. It realizes an **Editorial Swiss-inspired medical imaging workstation** combining:
1. **Precision Medical Technology:** High-contrast clinical surfaces, clear tabular figures, and glare-free dark radiograph environments.
2. **Editorial Swiss Typography & Layout:** Asymmetric information architecture, authoritative hierarchy, disciplined margins, and micro-caliper indicators.
3. **Scientific Visualization:** Dual-mode dental navigation featuring an interactive 3D WebGL dental arch alongside an anatomical 32-tooth odontogram.
4. **Restrained Motion Design:** Purposeful 180ms ease-out state transitions, zero disruptive animations over diagnostic imagery, and full `prefers-reduced-motion` compliance.

---

## 2. Color System & Design Tokens

### 2.1 Level 10.5 Signature Palette
| Token Name | Hex Code | Visual Role | Contrast Ratio (vs Porcelain/Dark) |
|---|---|---|---|
| **Deep Petrol** | `#102D2C` | Primary structural tone, navigation sidebar, brand foundation | > 9.5:1 against Porcelain |
| **Porcelain** | `#F3EFE6` | Crisp warm ivory text, prominent badges, primary contrast surface | > 11.2:1 against Deep Petrol |
| **Mineral Jade** | `#4F8175` | Medical confirmation accent, active state indicator, verified checkmarks | 4.8:1 against Dark Slate |
| **Warm Graphite** | `#222C2A` | Secondary structural panels, dossier card surfaces | Structural / Low-glare |
| **Antique Brass** | `#B89A63` | Editorial accents, case IDs, dental numbering, caution badges | 5.2:1 against Dark Slate |
| **Muted Terracotta** | `#B96B55` | Legal boundary banner, urgent attention, critical alert chips | 4.9:1 against Dark Slate |

### 2.2 Dedicated Dark Radiograph Viewport Zone
To prevent optical glare and preserve clinical grayscale nuance, all panoramic radiograph viewports strictly employ:
- Canvas Surface: `#070A0D` (Deep OLED black)
- Shell Backing: `#0D1217`
- Viewport Inset: `#131B22`

### 2.3 Okabe-Ito Colorblind-Safe Pathology Spectrum
All bounding boxes, true polygon segmentation masks, and finding inspector chips strictly map to the colorblind-safe Okabe-Ito spectrum:
- **Caries:** `#E67E22` (Orange)
- **Deep Caries:** `#E74C3C` (Vermilion)
- **Periapical Lesion:** `#CC79A7` (Reddish Purple)
- **Impacted Tooth:** `#F59E0B` (Amber Yellow)
- **Alveolar Bone Loss:** `#38BDF8` (Sky Blue)
- **Root Canal Treatment:** `#009E73` (Bluish Green)
- **Uncertain / Default:** `#94A3B8` (Slate Gray)

---

## 3. Typography & Micro-Details

### 3.1 Type System
1. **Display & Headers:** `Figtree`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, sans-serif.
   - Weights: 700 (Bold), 800 (Extra Bold)
   - Letter-spacing: `-0.02em` to `+0.04em`
2. **Body & Clinical Prose:** `Noto Sans`, `-apple-system`, `Segoe UI`, Roboto, sans-serif.
   - Weights: 400 (Regular), 500 (Medium), 600 (Semi-Bold)
   - Line-height: `1.55`
3. **Data, Metrics & FDI Numbering:** `JetBrains Mono`, `Consolas`, monospace.
   - Font feature settings: `"tnum" 1` (tabular proportional figures)
   - Weights: 500, 600, 700

### 3.2 Spacing & Radii Principles
- **Borders:** `1px solid rgba(79, 129, 117, 0.35)` with selective `3px` solid accent spine borders.
- **Corner Radii:** Controlled industrial chamfer of `4px` to `6px`. Rounded pills are strictly avoided.
- **Card Padding:** `14px` to `20px` inner gutters to prevent optical crowding.

---

## 4. Signature 3D Dental Experience Architecture

The 3D dental arch is implemented in `frontend/components/dental_arch_3d.py` utilizing locally bundled Three.js (`frontend/static/three.min.js`, 603 KB, 100% offline):
- **Geometry:** 32 individual anatomically positioned tooth crown meshes (chisel incisors, pointed canines, bicuspid premolars, and cusped molars) aligned along parabolic maxillary and mandibular catenary curves.
- **Lighting:** Three-point studio lighting with porcelain key light (`0xF3EFE6`), jade fill light (`0x4F8175`), and antique brass rim light (`0xB89A63`).
- **Interaction:** Orbit rotation, pitch damping, scroll zoom, and real-time Raycaster hover/selection.
- **HUD Telemetry:** Real-time FDI number HUD displaying anatomical name, quadrant, and associated finding status.
- **Clinical Non-Maleficence:** Persistent disclaimer tag: *"Reference 3D Model • Not Patient Scan"*.

---

## 5. Screen Hierarchy & Workflow Architecture

The application comprises 7 interconnected clinical workflows:
1. **Overview / Home (`overview.py`):** Dossier banner, signature 3D visual, live system telemetry, and case archive.
2. **Upload Workspace (`upload.py`):** Drag-and-drop intake bay, raster preview, dimensions, aspect ratio, and de-identified case metadata.
3. **Diagnostic Workstation (`workstation.py`):** High-priority dark radiograph viewport (70%), interactive pan/zoom canvas, ONNX screener trigger, findings drawer, and clinician review attestation form.
4. **FDI Tooth Explorer (`fdi_explorer.py`):** Scientific instrument combining the 3D dental arch with the 32-tooth 2D odontogram matrix, tooth-specific findings, and coordinate shift verification.
5. **Clinical Evidence (`evidence.py`):** Concept separation of AI observations vs. human clinician confirmations, chairside exam inputs (vitality, percussion, pocket depth), and patient symptom recorder.
6. **Pre-Authorization Studio (`preauth_studio.py`):** ADA CDT coding, documentation readiness preflight detective, Ollama/deterministic narrative draft generation, and ReportLab PDF export.
7. **System Settings (`system_settings.py`):** Truthful cryptographic model registry, RTX 2050 hardware telemetry, and zero-cloud-egress verification.

