# DENTRACE — Premium Clinical Workstation Frontend Design System

> **DOCUMENT ID:** DOC-UI-010  
> **STATUS:** SPECIFICATION & ART DIRECTION (LEVEL 0.5)  
> **DESIGN ENGINE:** `ui-ux-pro-max` (Searchable Local UI Intelligence)  
> **DATE:** 2026-10-18  

---

## 1. Design Philosophy & Art Direction: "Curie-Nordic Radiography Workstation"

DENTRACE is a clinical-grade dental decision-support environment, not a consumer SaaS dashboard, generic AI template, or colorful marketing page.

### Core Aesthetic Principles
1. **Darkroom Diagnostic Primacy:** Dental panoramic radiographs (OPGs) are grayscale transmission images with subtle density variations (enamel, dentin, pulpal chamber, cortical bone, trabecular bone). The interface surrounds the radiograph with deep, glare-free obsidian surfaces (`#080B0E`), preventing eye fatigue and optical glare.
2. **Clinical Restraint & Quiet Precision:** No glowing AI particle effects, no holographic scanners, and no bouncing micro-interactions on the medical viewer. Diagnostic information is displayed with structured typographic rhythm, crisp borders, and calm confidence.
3. **Colorblind-Safe Chromatic Semantics:** Pathologies must never be distinguished by red vs green alone. We employ an expanded Okabe-Ito colorblind-accessible palette with distinct shapes, textures, and unambiguous textual labels.
4. **Zero Diagnostic Distortion:** Diagnostic pixels are sacrosanct. The radiograph is rendered without lossy downsampling artifacts, color tints, or synthetic post-processing that could simulate or obscure real dental lesions.

---

## 2. Design Tokens & Color Architecture

### A. Surface & Neutral Hierarchy (Dark Clinical Mode)
```css
:root {
  /* Surface Layers */
  --dent-surface-canvas:      #070A0D; /* Glare-free radiograph viewport */
  --dent-surface-shell:       #0D1217; /* Main application background */
  --dent-surface-panel:       #131B22; /* Primary content cards & sidebars */
  --dent-surface-elevated:    #1A242E; /* Modals, dropdowns, hovered panels */
  --dent-surface-inset:       #0A0F14; /* Inset data tables & code blocks */

  /* Structural Dividers & Outlines */
  --dent-border-subtle:       #1E2A36; /* Section dividers */
  --dent-border-strong:       #2A3B4C; /* Active card borders & inputs */
  --dent-border-accent:       #38BDF8; /* Focused controls & active teeth */

  /* Text & Typography */
  --dent-text-primary:        #F1F5F9; /* High-contrast headers & vital metrics (14.2:1 contrast) */
  --dent-text-secondary:      #94A3B8; /* Body descriptions & findings (7.1:1 contrast) */
  --dent-text-muted:          #64748B; /* Secondary timestamps & metadata (4.5:1 contrast) */
  --dent-text-disabled:       #334155; /* Inactive controls */

  /* Brand Signature */
  --dent-brand-primary:       #0EA5E9; /* Electric Cyan */
  --dent-brand-secondary:     #0D9488; /* Clinical Teal */
  --dent-brand-glow:          rgba(14, 165, 233, 0.15);
}
```

### B. Semantic Pathology Overlays (Okabe-Ito Colorblind-Safe Palette)
Every finding category possesses a dedicated high-visibility hue calibrated for legibility against dark radiograph grayscales:

| Anomaly Target | Hex Token | Color Name | Visual Presentation | Mandatory Annotation Modality | Clinical Diagnostic Callout |
|---|---|---|---|---|---|
| **Caries (Enamel/Dentin)** | `#E67E22` | Vermilion Amber | Semi-transparent fill (alpha 0.35) + 2px solid boundary | True Polygon Mask | Tooth #, Surface (Occlusal/Interproximal) |
| **Deep Caries (Pulpal Involvement)** | `#E74C3C` | Clinical Crimson | High-contrast fill (alpha 0.45) + solid amber border (static, no animation) | True Polygon Mask | *"Near pulpal exposure — evaluate vitality"* |
| **Periapical Lesion** | `#CC79A7` | Reddish Mauve | Cross-hatched polygon contour | True Polygon Mask / Labeled Region | **"Needs intraoral periapical radiograph"** |
| **Impacted Tooth** | `#F59E0B` | Radiopaque Ochre | Crisp geometric bounding polygon | Anatomical Polygon / Box Fallback | Angulation: Mesioangular / Horizontal / Vertical |
| **Alveolar Bone Loss** | `#38BDF8` | Crestal Cyan | Horizontal reference polyline / Crest marker | Linear Marker / Regional Fallback | Qualitative Crown-to-Root ratio marker |
| **Root Canal Treatment** | `#009E73` | Radiopaque Emerald | High-luminance obturation polygon | True Polygon Mask | Obturation density & apical seal marker |
| **Treated Tooth with Periapical Radiolucency** | `#D9534F` | High-Attention Coral | High-contrast solid accent border with static warning pill badge | Clinical Co-occurrence Marker | **"Clinical correlation & periapical radiograph required for endodontic evaluation. Not a diagnosis of failure."** |

### C. Clinical Urgency Badges
- **Routine (`routine`):** `#10B981` (Clinical Emerald) — Preventive cleaning, shallow restorations.
- **Soon (`soon`):** `#F59E0B` (Clinical Amber) — Progressive dentin caries, moderate crestal loss.
- **Urgent (`urgent`):** `#EF4444` (Clinical Crimson) — Suspected endodontic failure, acute periapical infection, impacted third molar impinging second molar roots.

---

## 3. Typography Hierarchy & Font Engine

Sourced via Google Fonts through `ui-ux-pro-max` clinical intelligence pairing:

- **Headings & Structural Hierarchy:** **`Figtree`** (Weights: 400, 500, 600, 700)  
  *Rationale:* Geometric clarity with humanist terminal strokes; creates immediate clinical authority without cold sterility.
- **Body & Data Tables:** **`Noto Sans`** (Weights: 400, 500, 600)  
  *Rationale:* Engineered for extreme international readability, distinct glyph disambiguation (`1`, `l`, `I`), and high DPI legibility.
- **FDI Tooth Numbers, CDT Codes & Hex Metrics:** **`JetBrains Mono`** / **`IBM Plex Mono`**  
  *Rationale:* Monospace alignment for tooth numbers (e.g., `16`, `24`, `38`), coordinates, and claim codes.

```css
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Noto+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

body {
  font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--dent-text-primary);
  background-color: var(--dent-surface-shell);
}

h1, h2, h3, h4, .dent-title {
  font-family: 'Figtree', sans-serif;
  letter-spacing: -0.02em;
}

.dent-fdi-code, .dent-cdt-code, .dent-coord {
  font-family: 'JetBrains Mono', monospace;
}
```

---

## 4. Workstation Spatial Layout & Grid Structure

The workstation layout follows a high-density, professional radiologist split:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOP STATUS BAR: Case ID | Quality Badge | Ollama: Online | "Draft for dentist review" │
├───────────────────────────────────────────────────────┬────────────────────────────────┤
│                                                       │ CLINICAL FINDINGS DRAWER (35%) │
│                                                       │ ┌────────────────────────────┐ │
│            INTERACTIVE RADIOGRAPH CANVAS (65%)        │ │ Interactive Odontogram     │ │
│                                                       │ │  18 17 16 15 14 13 12 11   │ │
│  ┌─────────────────────────────────────────────────┐  │ │  21 22 23 24 25 26 27 28   │ │
│  │                                                 │  │ │  48 47 46 45 44 43 42 41   │ │
│  │     [ High-DPI OPG Viewport with Pan/Zoom ]     │  │ │  31 32 33 34 35 36 37 38   │ │
│  │                                                 │  │ ├────────────────────────────┤ │
│  │   - Caries polygon [FDI #16]                    │  │ │ Tabulated Findings List    │ │
│  │   - Periapical lesion mask [FDI #24]            │  │ │ Tooth 16: Deep Caries      │ │
│  │   - Crestal bone line [Quadrant 3]              │  │ │ Tooth 24: Suspected Endo   │ │
│  │                                                 │  │ ├────────────────────────────┤ │
│  └─────────────────────────────────────────────────┘  │ │ Pre-Auth Narrative Draft   │ │
│  Controls: Zoom [+][-] | Opacity [====|] | Reset [⟲]  │ │ Medical Necessity (Editable)│ │
├───────────────────────────────────────────────────────┴────────────────────────────────┤
│ ACTION FOOTER: [Re-run Screener] [Export PDF Claim Pack] [Physical Signature Checklist] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Motion Choreography & Usability Rules

### A. Diagnostic Viewing Area (Strict Motion Ban)
- **Zero Distracting Animations:** When displaying the panoramic radiograph, all animations (scanners, pulses, strobes, looping radar sweeps) are **strictly forbidden**. Clinicians inspecting trabecular patterns or subtle radiolucencies must never be distracted by synthetic movement.
- **Smooth Viewport Transforms:** Pan and zoom transitions on the HTML5 canvas must use hardware-accelerated affine matrix transforms (`transform: translate3d(...) scale(...)`) capped at 60 FPS without frame jitter.

### B. Interface State Transitions
- **Hover & Tooltips:** Micro-duration `150ms ease-out`. Tooltip appears adjacent to cursor showing: Tooth #, Detected Condition, Detection Modality (Polygon vs Bounding Box), Confidence %.
- **Drawer & Tab Expansion:** Duration `200ms cubic-bezier(0.16, 1, 0.3, 1)` (snappy decelerated curve, zero spring overshoot).
- **Reduced-Motion Fallback:**
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```

---

## 6. Streamlit Technical Constraint & Custom Component Architecture

### A. The Compulsory Streamlit Requirement
The College Problem Statement explicitly specifies a **Streamlit clinical UI**. We do not discard or silently swap Streamlit for a pure React framework. Instead, we architect a **Streamlit + Custom Component Hybrid**:

```
 ┌──────────────────────────────────────────────────────────────┐
 │                      Streamlit Python Engine                 │
 │   - Session State Machine (Case ID, Radiograph Buffer, JSON) │
 │   - Deterministic Clinical Rule Execution                    │
 │   - Local Ollama Client & Faithfulness Validator             │
 │   - ReportLab PDF Generation Endpoint                        │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │          Streamlit UI Layer + Custom Injection Shell         │
 │   - Custom Theme (.streamlit/config.toml)                    │
 │   - Injected Workstation CSS (fonts, obsidian panels, tables)│
 │   - Native Input Controls (Confidence sliders, CDT select)   │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │       Custom HTML5 Radiograph Canvas Component (Iframe / JS) │
 │   - Bi-directional Streamlit Component (components.v1)       │
 │   - Hardware-accelerated HTML5 Canvas with Pan / Zoom        │
 │   - Real-time Polygon Mask Rendering & Opacity Slider        │
 │   - Tooth Hover Tooltips & Click Event Bubble-Up to Streamlit│
 └──────────────────────────────────────────────────────────────┘
```

### B. Streamlit Theme Configuration (`.streamlit/config.toml`)
```toml
[theme]
base = "dark"
primaryColor = "#0EA5E9"
backgroundColor = "#0D1217"
secondaryBackgroundColor = "#131B22"
textColor = "#F1F5F9"
font = "sans serif"

[browser]
gatherUsageStats = false

[server]
address = "127.0.0.1"
port = 8501
headless = true
enableCORS = false
enableXsrfProtection = true
```

### C. Honest Documentation of Streamlit Limitations & Engineering Mitigations
1. **Limitation: Whole-page script re-execution on user input.**
   - *Mitigation:* Heavy assets (ONNX sessions, Ollama health check, image buffers) cached with `@st.cache_resource` and `@st.cache_data`. Active canvas interactions (zooming, mask toggling, opacity) handled client-side inside the HTML5 component without triggering Python re-runs.
2. **Limitation: Native Streamlit does not support multi-layer interactive medical canvas with pan/zoom.**
   - *Mitigation:* Implemented as a dedicated HTML5 Canvas custom component (`frontend/components/canvas_viewer.py`) using `components.v1.html` with bi-directional JavaScript postMessage communication.
3. **Limitation: Streamlit default styling looks like SaaS boilerplate.**
   - *Mitigation:* Comprehensive CSS stylesheet injected via `st.markdown()` overriding Streamlit chrome (`.stApp`, `header`, `.stTabs`, `button`, `.stMetric`) to present an unbranded, high-density obsidian clinical darkroom aesthetic.

---

## 7. Medical Usability & Human-in-the-Loop Safeguards

1. **Persistent Regulatory Notice:** The banner *"Draft for dentist review. Not a diagnosis."* is pinned persistently to the top navigation header and cannot be scrolled out of view.
2. **Interactive Confidence Thresholding:** A dual-slider control allows the clinician to dynamically adjust detection confidence ($0.25$ to $0.85$), filtering out low-confidence suspicions without reloading.
3. **Disambiguation Legend:** Every rendered overlay has an accompanying legend badge clearly distinguishing:
   - ⬡ **Polygon Contour:** True pixel-level instance segmentation (Caries, Periapical Lesion, Root Canal obturation).
   - ▢ **Bounding Box:** Detection fallback (Impacted tooth, anatomical quadrant).
   - ━ **Reference Line:** Alveolar crest bone loss marker.
4. **Interactive Dental Odontogram (FDI 11–48):**
   - Clickable 32-tooth dental arch layout.
   - Clicking tooth `16` scrolls and zooms the radiograph canvas directly to the coordinate centroid of Tooth 16.
   - Displays color-coded pip indicators for all associated findings.
5. **Physical Dentist Signature Verification Block:**
   - The exported PDF claim pack reserves a mandatory blank signature and license number block.
   - The UI displays an explicit pre-submission warning: *"This claim pack is invalid for insurance submission without physical clinician signature and license attestation."*
