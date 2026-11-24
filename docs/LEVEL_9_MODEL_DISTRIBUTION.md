# DENTRACE Level 9: Neural Model Distribution, Verification & Licensing Policy

## 1. Overview & Policy Scope

DENTRACE employs a multi-stage offline neural inference architecture consisting of:
1. An instance segmentation model for OPG pathosis detection (Caries, Deep Caries, Periapical Lesion, Impacted Tooth).
2. An anatomical tooth detector for 32-tooth FDI numbering assignment.
3. A local quantized language model (Ollama `qwen2.5:3b`) for structured clinical pre-authorization narrative generation.

This document details the distribution policy, licensing restrictions, cryptographic integrity validation, and lifecycle management for all deployed model artifacts.

---

## 2. Model Manifest Inventory

All neural artifacts distributed with DENTRACE are registered in `config/model_manifest.json`:

```json
{
  "manifest_version": "1.0.0",
  "models": [
    {
      "model_id": "dentex_yolov8n_seg_best_pt",
      "filename": "dentex_yolov8n_seg_best.pt",
      "architecture": "YOLOv8n-Seg",
      "task": "instance_segmentation",
      "classes": ["Caries", "Deep Caries", "Periapical Lesion", "Impacted"],
      "input_resolution": [640, 640],
      "sha256": "43e068e541f5341cfab9d5e3532ea48dafa19eb14c81a2575feae0095640aa91",
      "license": "Academic Research Use / AGPLv3 derivative",
      "redistribution_policy": "Bundled with release"
    },
    {
      "model_id": "dentex_yolov8n_seg_best_onnx",
      "filename": "dentex_yolov8n_seg_best.onnx",
      "architecture": "YOLOv8n-Seg (ONNX)",
      "task": "instance_segmentation",
      "classes": ["Caries", "Deep Caries", "Periapical Lesion", "Impacted"],
      "input_resolution": [640, 640],
      "sha256": "8064d4c6792dc87e6fa18968032fa69c104e768e914041b6ec26040e0b355fa9",
      "license": "Academic Research Use / AGPLv3 derivative",
      "redistribution_policy": "Bundled with release"
    },
    {
      "model_id": "fdi_detector_best_onnx",
      "filename": "fdi_detector_best.onnx",
      "architecture": "YOLOv8n (ONNX)",
      "task": "tooth_detection_and_fdi_assignment",
      "classes": ["tooth"],
      "input_resolution": [640, 640],
      "sha256": "0dc78081f9b3cf2fa8e71887e025e17316fc12cf69c7ce09315993cbccba339b",
      "license": "Research and Decision Support",
      "redistribution_policy": "Bundled with release"
    }
  ],
  "llm": {
    "engine": "Ollama",
    "model_name": "qwen2.5:3b",
    "distribution": "Installed separately via local Ollama engine",
    "license": "Qwen Research License",
    "offline_endpoint": "http://127.0.0.1:11434"
  }
}
```

---

## 3. Cryptographic Verification Gate

Prior to model loading during application startup, the inference orchestrator performs SHA-256 cryptographic verification against `config/model_manifest.json`:
- **Verification Rule**: If any model file fails SHA-256 hash matching, model loading is rejected. The service logs a critical security alert and prevents tainted model inference from generating unverified clinical findings.
- **Tamper Protection**: Prevents corrupted downloads, incomplete file system copies, or malicious weight substitutions.

---

## 4. Offline Model Delivery Strategy

### Vision Models (Segmentation and FDI Detection)
- All vision model checkpoints (`.pt` and `.onnx`) are packaged directly within the `models/` directory of the release bundle.
- Package size impact is minimal (~26 MB total for both models), allowing direct inclusion in `DENTRACE-v0.1.0-win64.zip`.
- No internet access is required during or after installation.

### Local LLM (Ollama `qwen2.5:3b`)
- To keep the desktop package compact and honor local machine disk budgets, the language model is managed by the local Ollama instance running at `127.0.0.1:11434`.
- Pre-installation steps require running `ollama pull qwen2.5:3b` in the offline environment or importing the GGUF model artifact into Ollama's local library.
- If Ollama is offline or unavailable, DENTRACE gracefully degrades to deterministic rule-based template generation without blocking dental image processing.

---

## 5. Licensing and Academic Use Directives

1. **Academic Decision-Support Boundary**: DENTRACE is an academic decision-support project developed for clinical pair-review. It is not an FDA/CE/MDR-cleared medical device.
2. **Clinical Safety Mandate**: All outputs produced by the distributed models are explicitly marked: *"Draft for dentist review. Not a diagnosis."*
3. **Weight Modification**: Any retraining or fine-tuning of neural weights must recalculate SHA-256 digests and update `config/model_manifest.json` before deployment.
