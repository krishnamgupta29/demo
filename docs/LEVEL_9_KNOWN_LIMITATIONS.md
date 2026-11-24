# DENTRACE Level 9: Known Limitations & Operational Constraints

## 1. Regulatory & Clinical Boundary

1. **Non-Diagnostic Decision Support**:
   - DENTRACE is an academic prototype and decision-support tool. It is **not** an FDA-cleared, CE-marked, or MDR-certified medical device.
   - Outputs must never be used as autonomous diagnoses, definitive treatment plans, or automatic insurance adjudication decisions.
   - Every report and UI screen explicitly bears the legally binding notice:
     **"Draft for dentist review. Not a diagnosis."**

2. **Dentist Verification Prerequisite**:
   - Every segmented lesion, tooth assignment, and pre-authorization claim must be inspected and validated by a licensed dental professional before patient consultation or insurance submission.

---

## 2. Radiograph & Algorithm Limitations

1. **Burned-In PHI Annotations**:
   - While metadata tags (18 standard PHI fields + vendor private groups) are completely purged, legacy OPG scanners may burn patient names directly into pixel borders.
   - DENTRACE detects and flags suspicious burned-in peripheral text, but deliberately refrains from destructive pixel cropping or AI inpainting to prevent unintentional excision of anatomical structures (such as alveolar crest resorption or mandibular angles).

2. **Tooth Overlap & Crowding Artifacts**:
   - Severely crowded anterior teeth or complex supernumerary dentition can occasionally cause FDI numbering assignment ambiguities.
   - The interactive Streamlit odontogram allows clinicians to manually reassign, adjust, or discard any tooth-level observation.

3. **Restoration & Artifact Distortions**:
   - Radiopaque artifacts caused by dental implants, metallic crowns, orthodontic appliances, or spinal ghost shadows can cause false-positive caries or lesion alerts.
   - Dentists should use the visual overlay toggle to inspect raw pixel attenuation.

---

## 3. Hardware & Runtime Constraints

1. **Local LLM Availability**:
   - Clinical narrative justification relies on Ollama running `qwen2.5:3b` locally on `127.0.0.1:11434`.
   - If Ollama is stopped or unavailable, DENTRACE automatically activates a deterministic template fallback engine. Dental segmentation and tooth numbering continue unaffected, but narrative drafts use structured pre-set medical terminology rather than dynamic prose.

2. **GPU VRAM Ceiling**:
   - Optimized for NVIDIA RTX 2050 (4 GB VRAM).
   - If running concurrent VRAM-heavy applications (e.g., 3D CBCT renderers or large language model fine-tuning), PyTorch or ONNX Runtime may fall back to CPU execution, increasing inference latency from ~0.4s to ~1.8s.

3. **Single-Instance Concurrency**:
   - DENTRACE is designed for single-clinician workstation usage. Mutual exclusion locks (`.dentrace.lock`) prevent running concurrent processes against the same SQLite database file to preserve transactional integrity.
