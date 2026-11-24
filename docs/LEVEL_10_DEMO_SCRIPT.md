# DENTRACE Level 10: Faculty Demonstration Walkthrough Script (5–7 Minutes)

> **PROJECT TITLE:** DENTRACE — Local Dental Panoramic Radiograph Anomaly Detection & Insurance Claim Pre-Authorization Engine  
> **AUDIENCE:** Academic Project Review Panel & College Evaluators  
> **ESTIMATED DURATION:** 6 minutes 30 seconds  
> **MANDATORY LEGAL BANNER:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. Demo Setup & Pre-Requisites Checklist

Before inviting evaluators to observe:
1. Ensure Ollama service is running in background (`ollama serve` with `qwen2.5:3b`).
2. Have test radiograph sample ready: `datasets/demo/sample_opg_caries_impaction.png` (or de-identified DICOM study).
3. Open Windows terminal in project root and launch the application:
   ```cmd
   launch_dentrace.bat
   ```
4. Observe the launcher console complete 5 preflight gates and automatically open `http://127.0.0.1:8501`.

---

## 2. Timed Demonstration Script

### [0:00 – 0:50] 1. The Clinical Problem & Regulatory Boundary
- **Speaker**:  
  *"Good morning, esteemed faculty panel. Today, dental clinics face two major operational bottlenecks: first, subtle pathologies on 2D panoramic radiographs (OPGs) can be overlooked during rapid chairside reviews; second, dental insurance claim pre-authorizations require laborious manual narratives referencing ADA CDT codes, frequently taking 10 to 14 days and suffering high rejection rates due to missing diagnostic evidence.*  
  *We present **DENTRACE**: a local-first, privacy-preserving dental imaging decision-support and pre-authorization engine.  
  Before we begin, we state our foundational clinical governance directive: **'Draft for dentist review. Not a diagnosis.'** DENTRACE is strictly a clinical decision-support tool, not an autonomous medical device."*

### [0:50 – 1:40] 2. System Architecture & Zero Cloud Egress
- **Action**: Show the launcher console and the browser workstation UI at `127.0.0.1:8501`.
- **Speaker**:  
  *"Notice our runtime architecture: the application runs entirely on local loopback sockets. The backend is powered by FastAPI at `127.0.0.1:8000`, and the clinical interface runs on Streamlit at `127.0.0.1:8501`.  
  Crucially, there is **zero cloud egress**. No patient radiographs, metadata, or diagnostic observations ever leave this machine. Even our language model runs strictly on localhost using Ollama with `qwen2.5:3b`.  
  Furthermore, our launcher enforces a single-instance mutual exclusion lock and issues an ephemeral single-user token (`X-DENTRACE-TOKEN`) protecting all local API routes."*

### [1:40 – 2:45] 3. OPG Upload, DICOM Ingestion & Neural Inference
- **Action**: Navigate to the **"Study Intake / Upload"** screen. Select a DICOM or high-resolution OPG radiograph. Click **"Analyze Radiograph"**.
- **Speaker**:  
  *"During intake, our file manager de-identifies 18 standard DICOM Protected Health Information (PHI) tags and recursively strips vendor private tags.  
  Once uploaded, our multi-stage inference pipeline executes:
  1. An anatomical tooth detector locates tooth positions in milliseconds.
  2. Our calibrated anatomical FDI solver sorts teeth across all four quadrants (FDI 11 to 48), achieving 76.07% exact accuracy.
  3. Our fine-tuned YOLOv8n-Seg neural network segments four key conditions: caries, deep caries, periapical lesions, and impacted teeth.  
  Notice our inference latency: on our host NVIDIA RTX 2050 GPU, inference executes in under 20 milliseconds; even on an Intel i5 CPU, our FP32 ONNX model completes in just 113 milliseconds."*

### [2:45 – 3:50] 4. Interactive Diagnostic Canvas & Odontogram Review
- **Action**: Navigate to the **"Diagnostic Workstation"** screen. Show the interactive canvas viewer. Toggle masks on/off, pan/zoom, and inspect the Okabe-Ito color-coded polygons.
- **Speaker**:  
  *"Here in the diagnostic workstation, our HTML5 canvas viewer renders true polygon instance masks tracing exact abnormal tooth margins—color-coded using the colorblind-safe Okabe-Ito palette. In accordance with our Level 3 commitment to scientific truthfulness, we strictly distinguish instance segmentation masks from bounding boxes.  
  Below the canvas is our interactive 32-tooth permanent adult odontogram. Notice our human-in-the-loop safety rule: if an algorithm flags an ambiguous tooth assignment, the system marks it as `UNCONFIRMED`. If a tooth is unconfirmed, the downstream pre-authorization engine **blocks claim generation** under rule `BLOCKED_BY_UNCONFIRMED_TOOTH`. The dentist must critically inspect and confirm the tooth before proceeding.  
  Furthermore, notice our honest handling of alveolar bone loss: because standard OPGs lack cementoenamel junction (CEJ) landmarks, DENTRACE returns `UNSUPPORTED_MISSING_LANDMARKS` rather than hallucinating fabricated bone loss percentages."*

### [3:50 – 5:00] 5. Evidence Engine & Faithfulness-Audited AI Narrative
- **Action**: Navigate to the **"Insurance Pre-Auth Studio"**. Show the clinical evidence inputs (pulp vitality, probing depth) and click **"Generate Clinical Narrative"**.
- **Speaker**:  
  *"Now we proceed to insurance documentation. The clinician enters chairside findings, such as an electric pulp test or percussion response.  
  DENTRACE maps the verified pathology to standardized ADA CDT procedure codes (for example, D2391 for composite resin restorations, D3310 for endodontic therapy, or D7210 for surgical extraction of an impacted tooth).  
  Our local Ollama SLM synthesizes a structured, 10-section medical necessity narrative.  
  Crucially, to prevent AI hallucinations, our downstream **FaithfulnessChecker** audits the narrative sentence-by-sentence. If the language model hallucinates an ungrounded tooth number or an unobserved condition, the engine rejects the generated text and instantly reverts to our deterministic clinical template."*

### [5:00 – 6:00] 6. PDF Claim Pack Generation & Attestation
- **Action**: Click **"Download Pre-Authorization Packet (PDF)"**. Open the downloaded PDF in the browser viewer.
- **Speaker**:  
  *"Finally, DENTRACE generates a comprehensive 2-page ReportLab clinical claim packet.  
  Notice the clinical governance features:
  - Prominent running header: 'Draft for dentist review. Not a diagnosis.'
  - Semi-transparent 'PROVISIONAL REVIEW DRAFT' watermark.
  - Complete findings table with tooth-level FDI assignments and CDT procedure justification.
  - An empty, bordered pen-and-ink signature block requiring the licensed practitioner's physical handwritten signature, date, and state license number. We deliberately prohibit automated fake digital signatures.  
  This packet is fully exportable, printable, and ready for payer submission after chairside attestation."*

### [6:00 – 6:30] 7. Conclusion & Summary of Engineering Rigor
- **Speaker**:  
  *"To conclude: DENTRACE fulfills all 25 compulsory outcomes of the College Problem Statement with verified 100% test pass rate across 155 automated QA tests. It operates offline, respects memory budgets, protects patient privacy, and maintains uncompromising scientific honesty.  
  Thank you, and we welcome your questions."*
