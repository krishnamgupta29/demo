# DENTRACE Clinical Workstation Live Demonstration Script

> **MANDATORY CLINICAL & REGULATORY NOTICE**  
> *"Draft for dentist review. Not a diagnosis."*  
> DENTRACE is an academic decision-support prototype. It is not a certified medical device. All findings and claim narratives must be reviewed, edited, and approved by a licensed dentist.

---

## 1. Demonstration Objective
This script provides step-by-step instructions for demonstrating the end-to-end DENTRACE workflow: from one-click launcher startup to radiograph analysis, polygon mask visualization, FDI tooth attribution, chairside clinician editing, local LLM pre-authorization narrative synthesis, and ADA claim pack PDF generation.

---

## 2. Step-by-Step Clinical Demo Flow

### Step 1: Launch Application
1. Open PowerShell or Command Prompt in the repository root.
2. Run the supervisor batch launcher:
   ```cmd
   launch_dentrace.bat
   ```
   *Expected behavior:* The supervisor launcher performs 5 preflight checks (Python 3.11 environment, SQLite database migration, ONNX model weights integrity, local Ollama daemon detection, and port allocation).
3. The supervisor launches the FastAPI backend on `http://127.0.0.1:8000` and the React Clinical Studio on `http://localhost:5173`. Your default browser automatically opens to `http://localhost:5173`.

### Step 2: Ingest Sample Radiograph
1. In the DENTRACE Clinical Studio, navigate to the **Intake / Upload** panel.
2. Select or drag-and-drop one of the validated sample radiographs from the local `samples/` directory:
   - `samples/sample_opg_1.png` (Caries & deep caries case)
   - `samples/sample_opg_2.png` (Multi-quadrant caries case)
   - `samples/sample_opg_3.png` (Impacted tooth case)
3. Enter optional patient metadata (Patient ID: `DEMO-PATIENT-01`, Clinic: `City Dental Health`).
4. Click **Run Clinical Analysis**.

### Step 3: Inspect Multi-Pathology Polygon Masks & Overlays
1. The viewport renders the OPG with high-resolution pathology overlays rendered in the colorblind-safe **Okabe-Ito** palette:
   - Yellow/Orange: `caries` / `deep_caries`
   - Vermillion/Red: `periapical_lesion`
   - Sky Blue: `impacted_tooth`
2. Toggle the **Show Segmentation Masks** switch:
   - Observe real pixel-level polygon masks (`has_mask: true`) originating from `dentex_yolov8n_seg_static_qdq_int8.onnx`.
   - Secondary screening detections from `liodon-panoramic-screener` appear with bounding boxes (`has_mask: false`), faithfully adhering to the zero-fabricated-masks policy.
3. Click any pathology contour to view confidence score, bounding coordinates, and area in pixels.

### Step 4: Verify FDI Tooth Numbering & Safety Net
1. In the Odontogram panel, observe permanent teeth numbered in two-digit FDI notation (11–48) localized by the production `dentex_fdi_yolov8s_best.onnx` detector.
2. Inspect the **FDI Attribution** badge on each pathology finding.
3. Observe the **FDI Safety Net**: If any finding has low geometric overlap ($<0.15$) or ambiguous tooth assignment, the `fdi_uncertain: true` badge is visibly displayed, prompting immediate chairside manual review.

### Step 5: Chairside Clinician Editing & Probing Depth
1. In the **Findings Editor** panel, click on a detected finding to modify its attributes:
   - Verify or modify tooth number (e.g. adjust `#16` to `#17`).
   - Modify pathology classification or toggle verification status from `UNVERIFIED_AI_SUSPICION` to `CONFIRMED_BY_CLINICIAN`.
2. In the **Periodontal Examination** section, enter chairside clinical probing depth (e.g. `probing_depth_mm: 5.0`).
   - *Clinical Rule:* CDT code `D4341` (periodontal scaling and root planing) is unlocked only when clinician probing depth $\ge 4.0\text{ mm}$ is recorded.

### Step 6: Generate Evidence-Grounded Insurance Pre-Authorization Narrative
1. Navigate to the **Pre-Authorization Narrative** panel.
2. Click **Generate Narrative Draft**.
3. The local Ollama SLM (`qwen2.5:3b`) synthesizes the 10-section narrative strictly grounded in verified radiograph observations and ADA CDT terminology.
4. If Ollama is offline or fails the automated `FaithfulnessChecker`, observe the seamless fallback to the deterministic narrative generator with a visible engine indicator:
   - `Engine: Local SLM (Ollama: qwen2.5:3b)` OR `Engine: Deterministic Clinical Fallback`.
5. Observe the mandatory hedged wording:
   > *"Clinical evaluation and treatment planning is recommended for teeth #... to address suspected ..., pending clinician confirmation of this AI-assisted finding."*

### Step 7: Export 2-Page ADA Claim Pack PDF
1. Click **Export Claim Pack PDF**.
2. The system compiles an ADA-compliant 2-page claim pack containing:
   - Page 1: Header metadata, 10-section pre-auth narrative, Okabe-Ito radiograph overlay crop, and CDT code recommendation table.
   - Page 2: Full-resolution radiograph visual with annotated tooth contours, tabular finding matrix, and physical dentist signature/license block.
3. Verify that the generated PDF contains the prominent disclaimer header:
   > **"Draft for dentist review. Not a diagnosis."**
