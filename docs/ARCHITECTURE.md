# DENTRACE — System Architecture & Technical Specification

> **DOCUMENT ID:** DOC-ARCH-004  
> **STATUS:** LEVEL 1 IMPLEMENTED & VERIFIED  
> **DATE:** 2026-10-19  

---

## 1. High-Level System Architecture

DENTRACE is organized as a decoupled, local-first medical AI application designed to run entirely offline on standard clinical hardware without external network transmission.

```
                              LOCAL HOST WORKSTATION (NO EXTERNAL EGRESS)
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                        │
 │  [Dental Radiograph (OPG)]                                                             │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────┐                                               │
 │  │ 1. OPG File Intake & Privacy Shield │ ──► Strips DICOM/EXIF metadata                │
 │  └─────────────────────────────────────┘                                               │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────┐                                               │
 │  │ 2. Automated Image Quality Screener │ ──► Aspect ratio, blur, resolution check      │
 │  └─────────────────────────────────────┘                                               │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 3. Dual-Head Vision Pipeline (ONNX Runtime CPU / PyTorch GPU)   │                   │
 │  │   ┌───────────────────────────────┐ ┌─────────────────────────┐ │                   │
 │  │   │ 3A. Tooth Numbering (DENTEX)  │ │ 3B. Pathology Detector  │ │                   │
 │  │   │     FDI Boxes 11–48           │ │     5 Target Anomalies  │ │                   │
 │  │   └───────────────────────────────┘ └─────────────────────────┘ │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                   │                                       │
 │            ▼                                   ▼                                       │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 4. Geometric Matcher & Topological Post-Processor               │                   │
 │  │    - Spatial overlap ratio matching (>15%)                      │                   │
 │  │    - Max 8 teeth per quadrant rule                              │                   │
 │  │    - FDI deduplication (preserves highest confidence candidate) │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 5. DETERMINISTIC CLINICAL RULE LAYER (Authoritative Governance) │                   │
 │  │    - Assigns: Tooth #, Condition, Category, Demo CDT Code       │                   │
 │  │    - Decides: Clinical Urgency ('routine', 'soon', 'urgent')    │                   │
 │  │    - Flags: Suspected Endodontic Failure (RCT + Periapical)     │                   │
 │  │    - Emits: "Needs periapical radiograph" hint                  │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 6. Bidirectional Faithfulness Validator & Local Ollama Engine  │                   │
 │  │    - Local Ollama (qwen2.5:3b-instruct / phi3:mini)             │                   │
 │  │    - Pydantic JSON Schema Format Constraint                     │                   │
 │  │    - Bidirectional Faithfulness Check (Max 2 retries)           │                   │
 │  │    - Guaranteed Deterministic Fallback Template                 │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 7. Clinical Interface & Document Generation                     │                   │
 │  │    - Streamlit UI with custom HTML5 Canvas Mask Viewer          │                   │
 │  │    - Interactive FDI Odontogram & Findings Table                │                   │
 │  │    - Two-Page ReportLab PDF Claim Pack with Dentist Sign-Off    │                   │
 │  │    - Local SQLite Audit Ledger                                  │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │                                                                                        │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Budget & Resource Allocation

| Resource | Available Host Capacity | DENTRACE Allocation / Limit | Strategy & Mitigation |
|---|---|---|---|
| **OS** | Windows 11 x64 | Windows 11 x64 Native | Standardized PowerShell scripts and cross-platform path handling (`pathlib.Path`). |
| **Python** | Python 3.11.9 (`py -3.11`) | Dedicated Python 3.11 virtual environment | Enforced via `.env` and scripts. Prevents Python 3.13 / 3.15 bytecode incompatibility. |
| **CPU** | Multi-core x86_64 host | 4 Intra-op Threads | Target CPU inference latency: <50ms with INT8 ONNX Runtime optimization. |
| **GPU** | NVIDIA RTX 2050 (4 GB VRAM) | Max 3.2 GB Allocated | Batch size $\le 8$, mixed-precision FP16. Local fine-tuning supported; large epoch runs offloaded to Colab T4. |
| **RAM** | ~16 GB Physical | Peak working set $\le 6\text{ GB}$ | Streaming image buffers, on-demand session loading, lightweight models. |
| **Storage (C:)** | ~150 GB Free | Primary Storage for Datasets & Models | Pip wheels, HuggingFace caches, Ollama model weights stored here. |
| **Storage (D:)** | **~4.58 GB Free** | Codebase & Project Config ONLY | **ZERO DATASETS ON D:.** Enforced by `.gitignore` and `.env.example`. |

---

## 3. Pipeline Step Specifications

### Step 1: OPG Intake & Privacy Shield
- Accepts PNG, JPG, or DICOM files.
- Strips all patient metadata (Patient Name, DOB, Institution, Machine Serial Number) before memory staging.
- Assigns an anonymous unique Case ID: `CASE-[UUID8]`.

### Step 2: Automated Image Quality Screening
- Evaluates:
  1. Resolution: Flags images $<900\times 450$ px.
  2. Aspect Ratio: Flags images with aspect ratio $<1.4:1$ (non-panoramic crop).
  3. Blur: Computes Laplacian variance. Scores $<50.0$ trigger a "Motion blur / quality caution" alert.

### Step 3: Dual-Head Vision Pipeline
- **Head 3A (Tooth Localization):** Detects tooth bounding boxes and classifies into 32 FDI permanent tooth classes (11–48).
- **Head 3B (Pathology Segmentation & Detection):** Detects 5 target pathologies. Emits true pixel polygons for Caries, Periapical Lesions, and Root Canal Treatments; emits bounding regions for Impacted Teeth and Alveolar Bone Loss.

### Step 4: Geometric Matcher & Topological Post-Processor
- Associates each pathology finding with a host tooth box using spatial intersection over pathology area:
  $$\text{Overlap Ratio} = \frac{\text{Area}(\text{Pathology} \cap \text{Tooth})}{\text{Area}(\text{Pathology})} \ge 0.15$$
- Enforces dental anatomy rules:
  - Quadrant 1: Teeth 11–18 (at most 8 teeth)
  - Quadrant 2: Teeth 21–28 (at most 8 teeth)
  - Quadrant 3: Teeth 31–38 (at most 8 teeth)
  - Quadrant 4: Teeth 41–48 (at most 8 teeth)
  - De-duplication: If multiple boxes claim Tooth 16, retains the candidate with highest detection confidence.

### Step 5: Deterministic Clinical Rule Layer
- The central governance gate of DENTRACE.
- Authoritatively assigns:
  - FDI tooth number
  - Pathology condition
  - Urgency level (`routine`, `soon`, `urgent`)
  - Suggested procedure category & illustrative CDT demo code
- Special condition rules:
  - If a tooth exhibits **both** `Root Canal Treatment` and `Periapical Lesion`:
    * Flags `suspected_endodontic_failure = True`
    * Elevates urgency to `urgent`
    * Sets category to `"Endodontic Retreatment / Apicoectomy"`
    * Assigns hint: `"Needs intraoral periapical radiograph"`
  - If a tooth exhibits `Periapical Lesion`: sets `"Needs periapical radiograph"`.

### Step 6: Schema-Constrained Local LLM & Faithfulness Validator
- Local Ollama query using `qwen2.5:3b-instruct` or `phi3:mini`.
- Structured findings JSON formatted with Pydantic JSON schema format constraint at temperature $0.1$.
- **Bidirectional Faithfulness Checker:**
  1. Verifies that every tooth number in the narrative exists in the findings JSON.
  2. Verifies that every condition in the narrative exists in the findings JSON.
  3. Verifies that all findings are represented.
  4. If violations occur: retries up to 2 times with explicit feedback.
  5. If retries fail or Ollama is offline: automatically triggers the deterministic clinical fallback template.

### Step 7: Clinical UI & ReportLab Claim Pack PDF
- Streamlit multi-tab clinical dashboard.
- Custom HTML5 Canvas viewer with colorblind-safe Okabe-Ito overlays and hover tooltips.
- Interactive FDI odontogram grid.
- Editable pre-authorization narrative form.
- Two-page clinical PDF with embedded radiograph, tabulated findings, and empty physical dentist signature line.
- SQLite audit ledger for local session tracking.
