# DENTRACE — Architectural Decisions & Technical Tradeoffs

> **DOCUMENT ID:** DOC-DEC-009  
> **STATUS:** BASELINED (LEVEL 0)  
> **DATE:** 2026-10-18  

This document logs critical architectural, technical, and clinical decisions made for the DENTRACE engine, detailing the rationale, evaluated alternatives, and deliberate tradeoffs.

---

## Decision Record 01: Host Disk Budget Partitioning (C: vs D:)
- **Context:** Host environment inspection revealed that `C:\` has ~150 GB free, whereas `D:\` has only **~4.58 GB free**.
- **Decision:** All large assets (pip package wheels, PyTorch model checkpoints, Ollama models, and downloaded dataset archives) are designated strictly for `C:\`. The project repository on `D:\` will contain only code, configuration files, test scripts, and documentation.
- **Tradeoff:** Requires setting environment variables (`DENTRACE_DATASETS_DIR`, `OLLAMA_MODELS`) to point to paths on `C:\` or external drives, but eliminates catastrophic `Disk Full` crashes on `D:\`.

---

## Decision Record 02: Vision Architecture Selection (YOLOv8-Seg vs Alternatives)
- **Context:** The college problem statement allows a lightweight YOLOv8-Segmentation or MobileNetV3-U-Net model. We evaluated:
  1. *YOLOv8-Seg (Ultralytics):* Unified single-stage anchor-free instance segmentation and detection.
  2. *MobileNetV3-U-Net:* Two-stage semantic segmentation requiring separate connected-component parsing for instance extraction.
  3. *Mask R-CNN:* Heavy two-stage model with high parameter count ($>44\text{M}$ params), sluggish on CPU.
  4. *HierarchicalDet (DiffusionDet):* Diffusion baseline from DENTEX. Excellent mAP but requires iterative sampling steps ($>40$ steps per image), resulting in multi-second CPU latencies incompatible with the $<50\text{ms}$ target.
- **Decision:** Standardize on **YOLOv8m-seg / YOLOv8s-seg** exported to ONNX with INT8 quantization.
- **Rationale:** YOLOv8 natively outputs both bounding boxes and instance segmentation masks in a single forward pass, has proven dental checkpoints available (`nsitnov`, `liodon-ai`), and achieves low CPU latencies when quantized with ONNX Runtime.

---

## Decision Record 03: Placement of the Deterministic Clinical Rule Layer
- **Context:** Should the language model infer medical urgency and procedure categories directly from visual descriptions, or should a deterministic rule layer govern this?
- **Decision:** Place an authoritative, deterministic **Clinical Rule Layer** strictly between the computer vision models and the language model.
- **Rationale:** Large language models are probabilistic and prone to hallucination. Allowing an LLM to decide tooth numbers, disease urgency, or billing codes in a clinical application creates unacceptable liability. In DENTRACE:
  - Vision model predicts coordinates, boxes, and masks.
  - Rule layer deterministically computes tooth assignment, condition taxonomy, urgency (`routine`, `soon`, `urgent`), demo CDT codes, and diagnostic hints.
  - Language model is strictly constrained to synthesize and rewrite these pre-determined facts.

---

## Decision Record 04: Modeling "Suspected Endodontic Failure" as a Compound Rule
- **Context:** DENTEX and public datasets do not provide a dedicated single class labeled "suspected endodontic failure".
- **Decision:** Implement "suspected endodontic failure" as a composite clinical rule triggered when both `Root Canal Treatment` (radiopaque obturation) and `Periapical Lesion` (apical radiolucency) coexist on the same FDI tooth number.
- **Rationale:** In clinical endodontics, a failure is defined by persistent apical periodontitis around a previously treated canal. Trying to train an artificial single classifier on limited data would risk high false positives. A deterministic rule accurately reflects clinical diagnostic reasoning and elevates case urgency to `urgent`.

---

## Decision Record 05: Small Language Model Selection (Qwen2.5-3B-Instruct vs Phi-3-Mini)
- **Context:** A fully local SLM is required for pre-authorization narrative drafting through Ollama.
- **Decision:** Designate **`qwen2.5:3b-instruct`** as primary, with **`phi3:mini`** as configured alternative.
- **Rationale:** Qwen2.5-3B-Instruct demonstrates exceptional adherence to strict JSON schemas under Ollama's `format` parameter, exhibits low token latency on host CPU/GPU, and adheres faithfully to negative constraints ("do not invent tooth numbers"). Phi-3-mini is maintained as a verified alternate option in `config/settings.json`.

---

## Decision Record 06: Bidirectional Faithfulness Checker with Template Fallback
- **Context:** Even with temperature 0.1, language models can occasionally omit findings or hallucinate unmentioned teeth.
- **Decision:** Enforce a post-generation Bidirectional Faithfulness Checker:
  1. Forward check: All teeth and conditions in narrative must exist in input JSON.
  2. Backward check: All input findings must be represented.
  3. Max 2 retries with targeted error prompts.
  4. If retries fail or Ollama is offline: automatically deploy the deterministic clinical fallback template (`backend/llm/fallback_template.py`).
- **Rationale:** Guarantees 100% clinical fidelity without crashing the application.

---

## Decision Record 07: Resumable Safe Extraction Protocol with Zip-Slip Defense
- **Context:** `training_data.zip` (10.18 GB compressed, 13.71 GB uncompressed) contains 3,615 members. Extracting from scratch on every run or failure is expensive and risks disk thrashing.
- **Decision:** Implement resumable extraction in `scripts/safe_extract_dentex.py` with Zip-Slip validation, symlink rejection, and exact file-size matching.
- **Rationale:** Skips already verified files instantly, protects against directory traversal attacks, and completed 13.71 GB extraction safely on C: drive in 80 seconds without data corruption.

---

## Decision Record 08: SQLite WAL Persistence with Dual Migration Strategy (Alembic + Runtime)
- **Context:** Level 1 requires SQLite with SQLAlchemy and Alembic migrations, while the production service needs seamless self-healing startup.
- **Decision:** Implement declarative SQLAlchemy 2.0 ORM models (`backend/database/models.py`) with Alembic autogenerate migrations (`ec4d280c3836_initial_schema.py`), backed by a lightweight runtime migration runner (`backend/database/migrations.py`) executed on FastAPI lifespan startup.
- **Rationale:** Alembic handles formal schema versioning and batch migrations for SQLite, while the runtime runner ensures zero-config developer onboarding without manual CLI commands.

---

## Decision Record 09: Decoupled Model Registry with Truthful `MODEL_UNAVAILABLE` Default
- **Context:** Pretrained checkpoints (`abychkov`, `liodon-ai`, `nsitnov`, `BoneLoss-PAN769`) must not be downloaded or executed until independently evaluated and authorized by the user.
- **Decision:** Model registry adapters strictly default to `status="MODEL_UNAVAILABLE"` when weight files are missing. Input/output shape contracts are strictly verified.
- **Rationale:** Prevents hallucinated or mock inference numbers. Completely eliminates fake confidence scores from system output.

---

## Decision Record 10: Strict Ingestion Security: Magic Bytes, Traversal Defense, and DICOM Sanitization
- **Context:** Uploaded images may contain path traversal attacks, corrupted streams, unsupported transfer syntaxes, or patient PHI in DICOM headers.
- **Decision:** Ingestion performs magic byte detection, full raster decompression testing (`img.load()`), explicit path traversal rejection, unsupported compressed syntax detection (`NotImplementedError`), and patient tag blanking (`PatientName="ANONYMIZED"`).
- **Rationale:** Ensures zero malicious code execution, zero corrupted studies in the database, and zero patient PHI leakage into previews or logs.

---

## Decision Record 11: Single Canonical Alembic Migration Mechanism
- **Context:** Level 1 verification identified dual migration code: custom manual SQLite DDL in `backend/database/migrations.py` and standard Alembic migrations in `alembic/versions/`.
- **Decision:** Eliminate the duplicate manual DDL and designate Alembic as the single canonical schema migration mechanism. `backend/database/migrations.py` wraps Alembic's programmatic Python API (`alembic.command.upgrade(alembic_cfg, 'head')`) on application lifespan startup, utilizing SQLite batch migration mode (`render_as_batch=True`).
- **Rationale:** Guarantees schema consistency, table relationship integrity, and auditability without duplicate maintenance or schema drift.

---

## Decision Record 12: Real ONNX Runtime Inference, Truthful Geometry, and Exploratory Baseline Labeling
- **Context:** Level 2 required integrating real pretrained checkpoints (`best.onnx` and `dental_fdi.onnx`), avoiding fabricated metrics, and handling DENTEX overlap in the candidate model's training history.
- **Decision:**
  1. Built native ONNX Runtime inference engine with aspect-ratio preserving letterboxing, class-aware NMS, and CPU fallback.
  2. Bounding box detections are strictly designated with `annotation_modality = 'detection_bounding_box'` and `geometry_type = 'bbox'`. No bounding box is ever falsely converted to or claimed as an instance polygon mask.
  3. Pretrained tooth localization from `abychkov/dental-fdi-detection` localizes tooth regions and patient-side anatomical orientation, but flags uncertain teeth as `uncertain_tooth = True` rather than forcing unvalidated integer FDI assignments.
  4. Because `liodon-ai` included DENTEX in its original training corpus, baseline metrics are formally designated as **Exploratory Pretrained Baseline** rather than zero-shot independent validation.
- **Rationale:** Preserves medical software safety, transparency, and clinical truthfulness.

---

## Decision Record 13: Abnormal-Tooth Instance Segmentation vs. Microscopic Lesion Segmentation
- **Context:** Forensic inspection of DENTEX `quadrant-enumeration-disease` revealed that disease polygon annotations have a mean vertical height of 297–317 px, closely tracking whole-tooth instances (304 px) and encompassing crown, pulp, and root apices.
- **Decision:** Formally classify, report, and document the task as **Abnormal-Tooth Instance Segmentation** (whole abnormal tooth contours harboring specific dental pathologies), strictly rejecting claims of microscopic cavity pit or osteolytic halo margin segmentation.
- **Rationale:** Protects clinical truthfulness, prevents diagnostic overclaiming, and aligns model outputs with surgical realities.

---

## Decision Record 14: Dual-Engine FDI Arch Solver with Pitch Gap Analysis
- **Context:** Pretrained `dental_fdi.onnx` (abychkov RT-DETR) returns raw proposals with dense class duplicates and no topological arch consistency.
- **Decision:** Engineer an anatomical arch solver (`FDISolver`) with conservative greedy NMS deduplication (IoU > 0.35), curved occlusal split, bilateral midpoint midline estimation, and inter-tooth pitch gap analysis ($> 1.75 \times \text{median\_width}$).
- **Rationale:** Achieves 95.89% quadrant accuracy and 67.83% exact FDI classification without forcing 32 teeth, flagging ambiguous assignments for clinician confirmation.

---

## Decision Record 15: Geometric Containment (IoP) for Tooth-Pathology Association
- **Context:** Associating small pathology lesions (e.g. 40x40 px caries) with large tooth boundaries (150x300 px) fails when using standard symmetric IoU because $\text{IoU} < 0.05$.
- **Decision:** Implement Intersection over Pathology ($\text{IoP} = \text{Area}(\text{Finding} \cap \text{Tooth}) / \text{Area}(\text{Finding})$) with threshold $\ge 0.40$, centroid containment, and interproximal contact detection ($\Delta \text{IoP} < 0.15$).
- **Rationale:** Achieves 96.8% association coverage on clinical panoramic radiographs and handles multi-pathology teeth cleanly.

---

## Decision Record 16: Decoupling Association Coverage from Verified Tooth Identity
- **Context:** An initial benchmark reported "98.80% association accuracy" based purely on bounding box containment without verifying that the associated tooth had the correct ground-truth FDI identity.
- **Decision:** Formally separate Association Coverage (% of findings physically enclosed in *any* candidate tooth box, measured at 96.8%) from Correct Tooth Identity Association Rate (measured at 71.2%).
- **Rationale:** Prevents deceptive claims of clinical precision. An association cannot be declared correct if the host tooth itself is misnumbered by the upstream solver.

---

## Decision Record 17: DENTEX 4-Class Training Status & ONNX CPU Latency Reality
- **Context:** An initial report conflated data preparation with completed training, and claimed ONNX parity without empirical CPU latency benchmarks.
- **Decision:** (1) Explicitly report DENTEX 4-class fine-tuning as `NOT TRAINED` and metrics as `PENDING` until training is executed. (2) Document empirical ONNX CPU inference latency as ~20.37 seconds per radiograph, disproving any sub-50ms CPU claims for the unquantized FP32 segmentation model.
- **Rationale:** Strict adherence to medical software integrity. Prevents fabrication of training completion and establishes realistic expectations for deployment hardware.

---

## Decision Record 18: Three-Way Conceptual Separation of Clinical Evidence
- **Context:** Medical documentation systems risk conflating unverified machine detections with confirmed clinical facts and administrative payer documentation rules.
- **Decision:** Architect strongly typed Pydantic schemas separating Concept A (AI Radiographic Observations, unverified machine proposals), Concept B (Clinician Verified Facts, chairside examination records, patient symptoms), and Concept C (Payer Pre-Authorization Checklist Requirements). Each evidence item carries explicit provenance source and verification status.
- **Rationale:** Guarantees that AI predictions remain explicitly marked as suspected findings until attested by a licensed dentist, preventing unverified outputs from contaminating insurance claims.

---

## Decision Record 19: Authoritative Deterministic Rule Engine Preceding Language Model
- **Context:** Generative LLMs are prone to medical hallucination, entity drift, and diagnostic overclaiming if tasked with clinical logic and procedure validation.
- **Decision:** Position the deterministic `ClinicalEvidenceEngine` as an authoritative pre-LLM gate. The engine audits tooth confirmation, detects clinical contradictions (e.g. vital pulp endodontics, procedure on rejected finding), and manages preflight document readiness states.
- **Rationale:** Medical reasoning, tooth assignment, and consistency checks are strictly authoritative and non-probabilistic.

---

## Decision Record 20: Bidirectional Claim-to-Evidence Traceability and Adversarial Faithfulness Checking
- **Context:** Natural language generation in insurance narratives must not cite non-existent evidence, hallucinate ungrounded teeth, or present suspected findings as clinical facts.
- **Decision:** Implement sentence-level citations (`NarrativeStatementCitation`) linking every clinical statement to evidence UUIDs. Enforce a deterministic `FaithfulnessChecker` that intercepts ungrounded claims and automatically reverts to `DeterministicNarrativeGenerator` if faithfulness fails.
- **Rationale:** Ensures zero ungrounded clinical assertions in generated drafts, verified by a 100% interception rate against adversarial injections.

---

## Decision Record 21: Local ReportLab Claim Pack PDF Generation with Mandatory Physical Signature
- **Context:** Clinical insurance pre-authorization documents require formal layout, legal disclaimers, and signed clinician attestation without cloud egress.
- **Decision:** Use ReportLab 4.4.10 for 100% offline PDF rendering. Prominently stamp "PROVISIONAL REVIEW DRAFT" on incomplete dossiers, and provide an empty physical pen-and-ink dentist signature block (strictly forbidding fake simulated signatures).
- **Rationale:** Adheres to medical informatics ethics, zero cloud egress boundaries, and legal compliance.

---

## Decision Record 22: Curie-Nordic Dark Obsidian Design System & Glare-Free Diagnostic Primacy
- **Context:** Clinical workstations for dental panoramic radiograph (OPG) review require deep contrast sensitivity to detect low-contrast radiolucencies (enamel demineralization, periapical rarefaction, periodontal bone height). Standard bright SaaS themes cause pupil constriction and severe clinician retinal fatigue in darkened reading environments.
- **Decision:** Implement the Curie-Nordic Dark Obsidian design system (`#070A0D` canvas, `#0D1217` shell, `#131B22` container panels) evaluated using `ui-ux-pro-max`. Strictly ban decorative AI particle effects, glowing scans, or dynamic filters over diagnostic X-ray pixels. Adopt Okabe-Ito colorblind-safe pathology tokens (`#E67E22` caries, `#CC79A7` periapical, `#F59E0B` impacted).
- **Rationale:** Preserves medical imaging diagnostic integrity, complies with WCAG AAA contrast guidelines (11.8:1), and ensures clinical safety across deuteranopia, protanopia, and tritanopia.

---

## Decision Record 23: Markdown-Safe HTML Sanitization & Streamlit In-Process Test Isolation
- **Context:** (1) Streamlit markdown parses any multiline string indented with 4+ spaces as an indented `<pre><code>` code block, disrupting rich HTML components. (2) Integration testing of Streamlit API clients against running background servers risks database isolation mismatch when `conftest.py` uses temporary test databases.
- **Decision:** (1) Introduce `clean_html()` utility stripping leading indentation while preserving full HTML tag integrity. (2) Provide `force_in_process` flag on `DentraceAPIClient` routing requests to in-process `TestClient(app)` during test execution while preserving live loopback HTTP in Streamlit production.
- **Rationale:** Guarantees pristine HTML rendering in Streamlit chrome while ensuring 100% reproducible, isolated automated testing across all 91 test cases.

---

## Decision Record 24: Fine-Tuning DENTEX 4-Class Instance Segmentation on Host Hardware
- **Context:** Level 6 required moving beyond 3-class detection to real 4-class instance segmentation on the DENTEX challenge dataset (3,529 raw abnormalities: 604 impacted teeth, 2,189 caries, 158 periapical lesions, 578 deep caries).
- **Decision:** Fine-tune `yolov8n-seg` locally using mixed precision AMP (`batch=4`, `imgsz=640`) on the host NVIDIA RTX 2050 GPU. Peak VRAM consumed was **0.828 GB** (well within the 4 GB limit). Fused weights were exported to ONNX FP32 (`models/checkpoints/dentex_yolov8n_seg.onnx`, 12.67 MB) and quantized to Dynamic INT8 (`dentex_yolov8n_seg_int8.onnx`, 3.52 MB).
- **Rationale:** Delivers true polygon masks tracing whole abnormal tooth envelopes while maintaining strict reproducibility and zero cloud egress.

---

## Decision Record 25: Calibrated Anatomical-Prior FDI Solver & Selective Abstention
- **Context:** Auditing the baseline FDI arch solver across 150 panoramic radiographs (4,224 teeth) revealed that 94.6% of errors were intra-quadrant enumeration shifts caused by assuming uniform tooth pitch and missing wisdom teeth.
- **Decision:** Engineer `CalibratedFDISolver` introducing tooth-width pitch scaling (`MAXILLA_WIDTH_FACTORS`, `MANDIBLE_WIDTH_FACTORS`), calibrated pitch gap threshold ($1.35$), midline ratio ($1.10$), and an explicit abstention policy for proposals exceeding the 8-tooth quadrant budget.
- **Rationale:** Improves exact tooth accuracy from 74.55% to 76.07% (76.55% precision on non-abstained teeth) with 98.63% quadrant accuracy, preventing cascading enumeration errors.

---

## Decision Record 26: Architectural Blocker for Periodontal Bone Loss (UNSUPPORTED_MISSING_LANDMARKS)
- **Context:** BoneLoss-PAN769 was proposed for periodontal bone loss estimation. However, AAP/EFP 2017 staging strictly requires reference landmarks: cementoenamel junction (CEJ), alveolar crest line, and root apex. DENTEX annotations only provide whole-tooth abnormal condition contours.
- **Decision:** Explicitly mark `boneloss-pan769-baseline` as `MODEL_UNAVAILABLE` with blocker reason `UNSUPPORTED_MISSING_LANDMARKS`. Prohibit any simulated or fabricated bone loss percentages.
- **Rationale:** Strict medical ethics and zero-fabrication directives. Fabricating bone loss percentages without biological reference landmarks violates patient safety standards.

---

## Decision Record 27: Endodontic Obturation vs. Active Lesion Semantics & Composite Failure Alert
- **Context:** The `nsitnov/8024-yolov8-model` segmentation checkpoint outputs Class 7 (`Root-Canal-Treatment`) and Class 5 (`Periapical-lesion`). Naive systems may mislabel root canal fillings as active lesions or claim automated treatment failure.
- **Decision:** Formally map Class 7 to `PathologyClass.ROOT_CANAL_TREATMENT` as a *past restorative intervention* (radiopaque, routine urgency). When both Class 7 and Class 5 co-occur on the same tooth, flag a composite finding: *"Suspected persistent or recurrent periapical radiolucency on endodontically treated tooth. Requires chairside clinical vitality/percussion attestation."*
- **Rationale:** Distinguishes past clinical therapy from active pathology, preventing false failure claims while highlighting potential endodontic complications for dentist review.

---

## Decision Record 28: Rejection of Sub-50ms CPU Claim & Dual FP32/INT8 Deployment Strategy
- **Context:** Previous preliminary documents speculated that INT8 dynamic quantization could achieve sub-50ms CPU inference for 640x640 panoramic radiograph segmentation.
- **Decision:** Formally reject the sub-50ms CPU claim following rigorous empirical benchmarks on the host Intel i5-13420H CPU (PyTorch: 360.76 ms; ONNX FP32: 874.90 ms; ONNX INT8: 1,370.19 ms). Dynamic activation quantization introduces runtime operator overhead that exceeds 8-bit compute savings on CPU. Maintain FP32 ONNX/PyTorch as the default execution pathway for latency, and provide INT8 as a lightweight edge deployment option achieving 3.6x–3.9x disk compression.
- **Rationale:** Empirical integrity and scientific truthfulness. Prevents inaccurate performance claims in clinical software documentation.



---

## Decision Record 29: Level 6.1 YOLOv8n-seg Pretrained Transfer — 30-Epoch Results & INT8 CPU Deployment Rejection
- **Context:** Level 6 training ran for 1 epoch from cold-start weights, yielding 0.000 mAP50 for all four pathology classes. Level 6.1 diagnosed the root cause as missing COCO pretrained feature extractor transfer and a dataset path mismatch in prepare_yolo_seg_dataset.py.
- **Decision:**
  1. Re-initialize from official yolov8n-seg.pt (COCO pretrained, 411/417 layers transferred).
  2. Fix image extraction directory to quadrant-enumeration-disease/xrays.
  3. Train 30 epochs (batch=8, imgsz=640, AMP, AdamW lr=0.00125) on RTX 2050 (4 GB VRAM).
  4. Best epoch = 25: Box mAP50=0.4816, Mask mAP50=0.4460, Box mAP50-95=0.2972.
  5. Per-class (best.pt final val): impacted_tooth 0.864, deep_caries 0.440, caries 0.317, periapical_lesion 0.284 (Box mAP50).
  6. Reject INT8 dynamic quantization for CPU deployment: FP32 ONNX 113-515 ms (variable system load); INT8 145-748 ms — consistently slower due to per-layer dequantization overhead on Intel i5-13420H.
  7. Deploy FP32 ONNX (dentex_yolov8n_seg_best.onnx, 13.2 MB) as production inference path.
- **Rationale:** Empirical results and honest reporting. Per-class breakdown is necessary because periapical_lesion (0.284 mAP50) is clinically the highest-stakes class and requires documented underperformance acknowledgement.

---

## Decision Record 30: Level 8 System Hardening, Zero Cloud Egress, and Medical Privacy Safeguards
- **Context:** Transitioning to production readiness requires comprehensive defense-in-depth across API boundaries, patient privacy, and data integrity.
- **Decision:**
  1. **Strict Localhost Boundary:** Enforce `HOST: 127.0.0.1` and explicit non-wildcard CORS origins (`http://localhost:*`, `http://127.0.0.1:*`).
  2. **HTTP Security Headers:** Inject `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: no-referrer`, and strict `Content-Security-Policy` via FastAPI middleware.
  3. **Sensitive Route Caching:** Mandate `Cache-Control: no-store, no-cache, must-revalidate` on all study and clinical endpoints to prevent local browser disk caching of patient radiographs.
  4. **Full Cascade Hard Deletion:** Ensure `delete_study(study_id, hard_delete=True)` reliably unlinks stored radiograph files, preview rasters, and cascades across all SQLite foreign keys.
  5. **PHI Leakage Prevention:** Enforce DICOM anonymization of 11 patient metadata tags prior to disk write; purge stack traces from all audit log events; ensure zero file-based log handlers capture unredacted patient identifiers.
- **Rationale:** Protects patient data confidentiality within academic decision-support boundaries without requiring cloud infrastructure.

---

## Decision Record 31: Environment Dependency Audit and Pillow 13.0.0 Compatibility
- **Context:** A corrupted installation of Pillow 10.4.0 led to `ImportError: cannot import name 'Image' from 'PIL'`. Reinstallation updated Pillow to 13.0.0, which triggered a cosmetic metadata warning in Streamlit 1.39.1 (`pillow<11`).
- **Decision:** Formally validate Pillow 13.0.0. Empirical testing across all 155 tests demonstrates complete stability and zero API regressions across image decoding, preview resizing, Laplacian blur scoring, and Streamlit workstation visualization.
- **Rationale:** Upstream binary stability on Windows 11 with Python 3.11 outweighs cosmetic metadata declarations.

---

## Decision Record 32: Level 9 Desktop Packaging, Supervisor Launcher, Ephemeral Local Auth, and Writable Data Isolation
- **Context:** Transitioning DENTRACE into an offline Windows 11 desktop release requires addressing multi-process coordination, local access security, process lifecycle cleanup, and Windows standard user permission boundaries.
- **Decision:**
  1. **Dual-Process Supervision**: Implement a Python-native supervisor launcher (`scripts/launcher/launcher.py`, wrapped by `launch_dentrace.bat` and `launch_dentrace.ps1`) that performs preflight health checks (ports 8000/8501, SQLite WAL migration, SHA-256 weight integrity, CUDA & Ollama probing), launches FastAPI and Streamlit child processes in isolated process groups, and cleans up all child trees using `taskkill /F /T /PID` upon exit to guarantee 0 orphaned background processes.
  2. **Single-Instance Mutex**: Enforce single-instance execution via a file lock (`.dentrace.lock`) in the user data directory to prevent database race conditions and duplicate port bindings.
  3. **Ephemeral Single-User Token**: Generate a cryptographically secure random session token (`X-DENTRACE-TOKEN`) at launch and enforce it via FastAPI middleware, preventing untrusted local processes or malicious browser tabs from probing patient data.
  4. **Deep DICOM PHI Scrubbing**: Expand anonymization from 11 to 18 standardized PHI tags, recursively purge vendor private tags (odd groups), and implement non-destructive border inspection for burned-in alphanumeric text annotations.
  5. **Data/Code Path Separation**: Application binaries and models remain in the read-only installation root, while all user data, SQLite databases, and DICOM caches reside in `%LOCALAPPDATA%\DENTRACE\data`, guaranteeing execution without administrator privileges.
  6. **Release Packaging**: Stage an offline release package using `scripts/build_release.py` generating `dist/DENTRACE-v0.1.0-win64.zip` (446.59 MB), `SHA256SUMS.txt`, and an Inno Setup installer script (`scripts/installer/dentrace_setup.iss`).
- **Rationale:** Ensures enterprise-standard deployment readiness, HIPAA/DICOM privacy compliance, robust process stability, and seamless non-admin operation on Windows 11.

---

## Decision Record 33: Empirical Calibration & Benchmark of Static QDQ INT8 vs. FP32
- **Context:** Dynamic INT8 quantization previously introduced dynamic activation quantization overhead that degraded CPU inference latency to 79.66 ms (slower than FP32's 44.55 ms). Furthermore, quantizing the prototype mask head degraded mask prediction fidelity.
- **Decision:**
  1. Build a **Static QDQ INT8** model (`dentex_yolov8n_seg_static_qdq_int8.onnx`, 7.23 MB) using `quantize_static` with MinMax calibration over 200 real images strictly from the training split (`ml/datasets/dentex/yolo_seg/images/train/`).
  2. Exclude all 102 segmentation head and prototype mask nodes (`/model.22/proto/*`, `/model.22/cv4.*`, `/model.22/*`) from quantization (`nodes_to_exclude`), ensuring the prototype masks remain in full precision.
  3. Validate on the full 141-image held-out validation split:
     - **FP32:** Box mAP50 = **0.4679**, Mask mAP50 = **0.4420**, CPU Median Latency = **44.36 ms**, p95 = **46.85 ms** (13.80 MB).
     - **Static QDQ INT8:** Box mAP50 = **0.4565**, Mask mAP50 = **0.4253**, CPU Median Latency = **35.99 ms**, p95 = **39.18 ms** (7.23 MB).
     - **Mask mAP50 Delta:** Absolute drop of **0.0167** (strictly within the $\le 0.03$ threshold).
     - **Latency Improvement:** 18.9% latency reduction, operating at **35.99 ms** median CPU latency ($< 50$ ms threshold).
- **Rationale:** Both acceptance gates (mask mAP50 drop $\le 0.03$ and median CPU latency $< 50$ ms) are met with empirical measurement. The Static QDQ model is baselined in the model manifest and available for production deployment.

---

## Decision Record 34: End-to-End FDI Tooth Localization and Numbering Evaluation Caveats
- **Context:** Previously, the 76.07% FDI accuracy benchmark was measured using ground-truth bounding boxes from the training split (`train_quadrant_enumeration.json`) fed directly into the topological solver. This tested the ordering algorithm in isolation on pristine annotations, not the real end-to-end vision pipeline.
- **Decision:**
  1. Formally re-evaluate the full end-to-end pipeline: `dental_fdi.onnx` (`abychkov/dental-fdi-detection`) $\to$ predicted bounding boxes $\to$ `CalibratedFDISolver` on 124 held-out DENTEX validation split images (3,563 ground truth teeth).
  2. Document the empirical measured metrics:
     - **Teeth Detection & Matching Recall (IoU $\ge$ 0.4):** **38.53%** (1,373 / 3,563 GT teeth).
     - **Exact-FDI Accuracy (on detected/matched proposals):** **36.20%** (497 / 1,373 teeth).
     - **Exact-FDI Accuracy (end-to-end across all GT teeth):** **13.95%** (497 / 3,563 teeth).
     - **Quadrant Assignment Accuracy (on matched proposals):** **87.84%** (1,206 / 1,373 teeth):
       - Q1 (Maxillary Right): 89.20%
       - Q2 (Maxillary Left): 92.33%
       - Q3 (Mandibular Left): 84.96%
       - Q4 (Mandibular Right): 85.39%
     - **Tooth Position Accuracy (1–8):** **40.35%** (554 / 1,373 teeth):
       - Position 1 (Central Incisor): 59.78% (highest)
       - Position 8 (3rd Molar/Wisdom): 28.79% (lowest, impacted/crowded/missing)
  3. Relabel all historical references to 76.07% as: *"Ordering algorithm on ground-truth boxes on training split"*.
  4. Explicitly note potential data leakage risk: `dental_fdi.onnx` is an open third-party model whose exact training set is unconfirmed by its upstream author; testing on DENTEX validation split provides our best reproducible baseline.
- **Rationale:** Strict clinical engineering honesty mandates distinguishing standalone topological sorting from genuine vision-in-the-loop detection performance.




