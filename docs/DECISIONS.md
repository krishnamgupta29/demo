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
