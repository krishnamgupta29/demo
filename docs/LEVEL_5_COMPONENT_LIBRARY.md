# DENTRACE — Level 5 Component Library Specification

**Framework:** Streamlit 1.39+ / Custom HTML5 Canvas / Vanilla CSS  
**Target Architecture:** High-DPI Medical Display / Desktop Browser  
**Compliance:** Strict Separation of Clinical Facts / Zero Telemetry

---

## 1. Overview of Component Suite

The DENTRACE component library is modularized under `frontend/components/` and `frontend/styles.py`:

| Component Name | Module Path | Technology | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Top Clinical Header** | `frontend.components.header` | HTML / CSS | Persistent regulatory warning banner, active case breadcrumb, offline loopback heartbeat. |
| **Radiograph Canvas Viewer** | `frontend.components.canvas_viewer` | HTML5 Canvas / JS | 60 FPS pan/zoom, 1:1 pixel fidelity, polygon masks, bbox overlays, tooth label tooltips. |
| **Interactive Odontogram** | `frontend.components.odontogram` | HTML / Streamlit State | Permanent 32-tooth quadrant visualizer (FDI 11–48), anomaly indicator badges, tooth focus. |
| **Clean HTML Sanitizer** | `frontend.styles.clean_html` | Python String Utility | Strips multiline indentation to prevent Markdown parsers interpreting HTML as code blocks. |
| **Curie-Nordic Theme Engine**| `frontend.styles` | CSS Injection | Injects design tokens, Okabe-Ito colors, dark slate cards, and reduced-motion media rules. |
| **Dentrace API Client** | `frontend.api_client` | HTTPX / In-Process | Unified REST interface to FastAPI endpoints with transparent TestClient test-mode fallback. |

---

## 2. Component Specifications

### 2.1 Top Clinical Header (`render_header`)
- **API Signature:**
  ```python
  def render_header(
      active_study_id: Optional[str] = None,
      backend_status: str = "online",
      ollama_status: str = "online",
      ollama_model: str = "qwen2.5:3b",
      hardware_status: str = "NVIDIA RTX 2050 (4 GB)",
  ) -> None
  ```
- **Guarantees:**
  - Mandatory regulatory warning: `"⚠ Draft for dentist review. Not a diagnosis."` rendered in high-contrast amber-red badge.
  - Heartbeat indicators for local FastAPI backend and Ollama LLM service.
  - Active study ID display with monospace truncation.
  - Offline local boundary indicator: `"🔒 Localhost-Only"`.

### 2.2 Radiograph Canvas Viewer (`render_radiograph_canvas`)
- **API Signature:**
  ```python
  def render_radiograph_canvas(
      image_bytes: Optional[bytes],
      findings: List[Dict[str, Any]],
      selected_tooth_fdi: Optional[int] = None,
      min_confidence: float = 0.25,
      mask_opacity: float = 0.45,
      height: int = 580,
  ) -> None
  ```
- **Features & Controls:**
  - **Pan & Zoom:** Smooth hardware-accelerated pan with left-mouse drag; zoom centered on mouse cursor via wheel event.
  - **Aspect Ratio:** Strictly locked to original radiograph aspect ratio; zero vertical or horizontal stretching.
  - **Pixel Preservation:** Rendered with grayscale 1:1 pixel mapping; zero sharpening filters, dynamic scan effects, or decorative pulses over radiograph pixels.
  - **Toolbars:** Zoom In (`+`), Zoom Out (`-`), Fit to Viewport (`Fit`), Reset Transform (`Reset`).
  - **Toggles:** Bounding Boxes toggle, True Segmentation Polygons toggle, FDI Tooth Numbers toggle.
  - **Opacity Slider:** Interactive alpha blending slider (0% to 100%) for instance segmentation overlays.
  - **Pathology Hover Tooltips:** Moving cursor over finding displays pathology label, confidence score, and tooth number in real time.

### 2.3 Interactive Odontogram (`render_odontogram`)
- **API Signature:**
  ```python
  def render_odontogram(
      findings_by_tooth: Dict[int, List[Dict[str, Any]]],
      confirmations_by_tooth: Dict[int, List[Dict[str, Any]]],
      selected_tooth_fdi: Optional[int] = None,
      key_prefix: str = "odonto",
  ) -> Optional[int]
  ```
- **Anatomical Structure:**
  - **Quadrant 1 (Maxillary Right):** FDI 18, 17, 16, 15, 14, 13, 12, 11
  - **Quadrant 2 (Maxillary Left):** FDI 21, 22, 23, 24, 25, 26, 27, 28
  - **Quadrant 4 (Mandibular Right):** FDI 48, 47, 46, 45, 44, 43, 42, 41
  - **Quadrant 3 (Mandibular Left):** FDI 31, 32, 33, 34, 35, 36, 37, 38
- **Visual Feedback:**
  - Unconfirmed AI findings render with an amber anomaly badge (`●`).
  - Clinician-confirmed findings render with a bright emerald badge (`✓`).
  - Active selection renders with a technical sky-blue border (`#38BDF8`) and elevated surface.

### 2.4 Reusable CSS Classes & Cards
- `.dent-card`: Elevated surface (`#131B22`), subtle 1px border (`#1E2A36`), rounded 8px corners, 16px padding.
- `.dent-metric-card`: Compact diagnostic metric container with uppercase muted label (`#64748B`) and 20px bold technical metric value.
- `.status-pill`: Rounded pill with 10.5px bold text; variants: `.status-pill-online` (emerald), `.status-pill-offline` (crimson), `.status-pill-warning` (amber), `.status-pill-info` (sky blue).
- `.badge-caries`, `.badge-periapical`, `.badge-impacted`: Okabe-Ito colorblind-safe pathology badges.
