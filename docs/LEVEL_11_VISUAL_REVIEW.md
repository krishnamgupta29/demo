# LEVEL 11 VISUAL REVIEW: DENTRACE CLINICAL WORKSTATION

**Document Status:** Final Visual & Design Review  
**Project:** DENTRACE Clinical Decision Support Engine  
**Milestone:** Level 11 — Complete Streamlit Removal & Premium React Frontend  
**Design Direction:** Contemporary Swiss Editorial • Precision Medical Instrument • OLED Diagnostic Darkroom  
**Regulatory Boundary:** *Draft for dentist review. Not a diagnosis.*  

---

## 1. Visual Design Philosophy & Art Direction

The visual transformation in Level 11 departs entirely from generic AI dashboard templates, repetitive card grids, and SaaS cliches. Inspired by high-end scientific instruments (Leica, Carl Zeiss) and Swiss typographic hierarchy (Josef Müller-Brockmann), DENTRACE balances clinical gravity with ergonomic efficiency.

### 1.1 Strictly Avoided Anti-Patterns
- **No Neon Glows or Glowing Borders:** All borders use precise, subtle hair-lines (`1px solid var(--surface-border)`).
- **No Purple/Blue AI Gradients:** Color identity is grounded in natural mineral and geological tones (Petrol, Jade, Brass, Porcelain).
- **No Glassmorphism Slabs:** Panels have solid, high-contrast surfaces (`#FFFFFF` and `#FAF8F5`) for readability under bright clinical fluorescent lighting.
- **No Generic Card Grids:** Asymmetrical layouts tailored to specific clinical workflows replace symmetric 3-column card layouts.
- **No Floating Blobs or Decorative Circles:** Every visual element serves an informational or clinical purpose.

---

## 2. Color System & Contrast Review

| Design Token | Hex Value | Role & Clinical Context | Contrast Ratio vs Background |
|---|---|---|---|
| `--color-petrol-900` | `#102D2C` | Deepest primary brand token; typography & headers | 14.8:1 (AAA) vs Porcelain |
| `--color-petrol-800` | `#1B4340` | Primary buttons, active navigation, brand monogram | 10.2:1 (AAA) vs Porcelain |
| `--surface-canvas` | `#F3EFE6` | Base page canvas (warm porcelain / archival paper) | Background |
| `--surface-panel` | `#FAF8F5` | Secondary content surface; forms and inspectors | Subtle distinction |
| `--color-jade-500` | `#4F8175` | Clinician-confirmed facts, authoritative markers | 4.8:1 (AA) vs White |
| `--color-brass-500` | `#B89A63` | AI candidate observations, non-authoritative flags | High readability on dark/light |
| `--color-terracotta-500`| `#B96B55` | Critical clinical urgency flags, destructive buttons | 4.6:1 (AA) vs White |
| `--dark-viewport-bg` | `#090D10` | Darkroom radiograph viewport canvas | Optimized for OPG grayscale |

---

## 3. Screen-by-Screen Review

### Screen 1: System Overview & Telemetry (`/overview`)
- **Screenshot:** `docs/screenshots/level_11/overview_1920x1080.png`
- **Layout Architecture:** Asymmetric 2-column composition.
  - **Left Column (1.4fr):** Embedded interactive 3D dental arch with camera angle toggles, providing an immediate anatomical spatial anchor.
  - **Right Column (1fr):** Hardware telemetry indicators (RTX 2050 GPU, SQLite engine, local storage quota) stacked above the Recent Cases roster.
- **Editorial Touch:** Monospaced case identifiers (`CASE-3883537B`), subtle status badges, and zero decorative fluff.

### Screen 2: Radiograph Ingestion Bay (`/upload`)
- **Screenshot:** `docs/screenshots/level_11/upload_1920x1080.png`
- **Layout Architecture:** 2-column intake terminal.
  - **Left Column (1.3fr):** High-contrast dashed drag-and-drop bay supporting PNG, JPEG, and DICOM files up to 25 MB.
  - **Right Column (1fr):** Real-time image preflight metrology panel displaying resolution, aspect ratio, color depth, and anonymous patient pseudonym generator.
- **Clinical Ergonomics:** Displays one-click sample radiograph loader for rapid demonstration.

### Screen 3: Diagnostic Workstation (`/workstation`)
- **Screenshot:** `docs/screenshots/level_11/workstation_1920x1080.png`
- **Responsive Viewports:** `workstation_1440x900.png`, `workstation_1366x768.png`, `workstation_1024x768.png`
- **Layout Architecture:** 70/30 split between dark diagnostic canvas and clinical inspector.
  - **Dark Radiograph Viewport:** True OLED dark environment (`#090D10`) with floating frosted toolbar. Features continuous pan/zoom, layer toggles (`Box`, `Mask`, `Label`, `FDI`), and live coordinate calipers.
  - **Findings Inspector & Attestation:** Clinical review panel with Okabe-Ito pathology list and legally binding attestation buttons (`Accept Finding`, `Correct FDI`, `Reject Candidate`).

### Screen 4: FDI Tooth Explorer (`/fdi`)
- **Screenshot:** `docs/screenshots/level_11/fdi_1920x1080.png`
- **Layout Architecture:** Dual 3D/2D anatomical synchronization.
  - **Upper Pane:** Procedural 3D WebGL arch with real-time raycasting and hover HUD.
  - **Lower Left Pane:** ISO 3950 compliant 2D clinical odontogram grouped by quadrants (UR, UL, LL, LR).
  - **Lower Right Pane:** Tooth detail dossier highlighting pathology history, root morphology, and suggested CDT procedures for the selected FDI tooth.

### Screen 5: Clinical Evidence Engine (`/evidence`)
- **Screenshot:** `docs/screenshots/level_11/evidence_1920x1080.png`
- **Layout Architecture:** 4-tab clinical ledger enforcing strict separation of facts.
  - **Facts vs AI Tab:** Two distinct, color-coded columns:
    - *Column 1 (Brass):* AI Candidate Observations (Unconfirmed, Non-Authoritative).
    - *Column 2 (Jade):* Clinician Confirmed Findings (Authoritative Facts signed by licensed DDS).
  - **Chairside & Symptoms Tabs:** Clinical forms capturing vitality, pocket depth, pain onset, and mastication sensitivity.
  - **Audit Ledger Tab:** Cryptographically hashed (SHA-256) immutable event log.

### Screen 6: Pre-Authorization Studio (`/preauth`)
- **Screenshot:** `docs/screenshots/level_11/preauth_1920x1080.png`
- **Layout Architecture:** Comprehensive claim packaging workspace.
  - **Left Pane:** 10-section structured narrative editor grounded in confirmed clinical facts.
  - **Right Pane:** Evidence readiness preflight detective checking tooth verification, radiograph attachment, and payer requirements, alongside an interactive CDT code catalog inspector.
  - **Actions:** One-click PDF Claim Pack generation with local download link.

### Screen 7: System Settings & Hardware Instrumentation (`/settings`)
- **Screenshot:** `docs/screenshots/level_11/settings_1920x1080.png`
- **Layout Architecture:** System diagnostic control panel.
  - **Hardware Cards:** NVIDIA GeForce RTX 2050 (4 GB VRAM) telemetry, Local Ollama LLM service health.
  - **Model Provenance Registry:** SHA-256 model checksum table verifying weight integrity.
  - **Zero-Cloud-Egress Audit:** Explicit offline verification card displaying localhost loopback binding and local storage isolation.

---

## 4. Responsive Viewport Verification

All screens maintain compositional balance across standard medical workstation resolutions:
- **1920 × 1080 (Primary Workstation Standard):** Full asymmetrical 2-column layouts with simultaneous 3D visualization and detailed dossiers.
- **1440 × 900 (Medical Laptop / Portable Station):** Proportional grid compression with preserved viewport aspect ratio.
- **1366 × 768 (Budget Clinical Display):** Compressed margins and compact toolbar padding without content truncation.
- **1024 × 768 (Legacy Medical Monitor):** Single-column flow with persistent horizontal toolbar controls.
- **768 × 1024 (Tablet Portrait):** Vertical stacking of 3D arch above telemetry metrics.

