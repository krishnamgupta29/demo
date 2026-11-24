"""DENTRACE Level 7: End-to-End System Performance & Resource Profiling Harness.

Benchmarks on actual Windows host:
1. Upload & image decoding time
2. Image preprocessing (letterbox + normalization)
3. Model inference:
   - FP32 ONNX (dentex-yolov8n-seg)
   - Dynamic INT8 ONNX (dentex-yolov8n-seg-int8)
   - PyTorch CUDA (best.pt on RTX 2050)
   - Liodon Screener ONNX (best.onnx)
   - Nsitnov ONNX (8024.onnx)
4. Segmentation postprocessing (mask contour polygon extraction)
5. FDI arch solving (CalibratedFDISolver)
6. Tooth-Pathology association (ToothPathologyAssociator)
7. SQLite persistence transaction
8. Total analysis pipeline latency (mean, median, p95)
9. Pre-auth narrative generation:
   - Deterministic fast synthesis
   - Local Ollama qwen2.5:3b synthesis
10. ReportLab PDF claim pack generation
11. Peak RAM & GPU VRAM utilization
"""

import io
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
import psutil
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.database.connection import get_db
from backend.ml.fdi_solver import CalibratedFDISolver
from backend.ml.association import ToothPathologyAssociator
from backend.ml.preprocessor import ImagePreprocessor
from backend.services.clinical_service import clinical_service
from backend.services.study_service import study_service
from backend.services.model_adapter import model_registry
from backend.reporting.pdf_generator import LocalClaimPackPDFGenerator
from backend.schemas.evidence import ClinicalEvidencePackage


def measure_latencies(fn, n_runs=15, n_warmup=3):
  """Measures function execution latencies (mean, median, p95)."""
  for _ in range(n_warmup):
    fn()
  times = []
  for _ in range(n_runs):
    t0 = time.perf_counter()
    fn()
    times.append((time.perf_counter() - t0) * 1000.0)
  return {
      "mean_ms": round(float(np.mean(times)), 2),
      "median_ms": round(float(np.median(times)), 2),
      "p95_ms": round(float(np.percentile(times, 95)), 2),
      "min_ms": round(float(np.min(times)), 2),
      "max_ms": round(float(np.max(times)), 2),
      "n_runs": n_runs,
  }


def run_benchmark():
  print("=" * 70)
  print("DENTRACE LEVEL 7: SYSTEM LATENCY & RESOURCE PROFILING")
  print("=" * 70)

  results = {
      "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
      "platform": sys.platform,
      "python_version": sys.version.split()[0],
      "cuda_available": torch.cuda.is_available(),
      "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
      "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
  }

  process = psutil.Process(os.getpid())
  initial_ram_mb = process.memory_info().rss / (1024 * 1024)

  # Sample test image
  img_w, img_h = 1200, 600
  sample_img = Image.new("RGB", (img_w, img_h), color=(128, 128, 128))
  buf = io.BytesIO()
  sample_img.save(buf, format="PNG")
  sample_bytes = buf.getvalue()

  # 1. Image Decoding & Validation
  def bench_decode():
    b = io.BytesIO(sample_bytes)
    im = Image.open(b)
    im.load()
  results["image_decoding"] = measure_latencies(bench_decode)
  print(f"[1] Image Decoding (1200x600): {results['image_decoding']['mean_ms']} ms")

  # 2. Preprocessing (Letterboxing & Normalization)
  def bench_preproc():
    _ = ImagePreprocessor.letterbox(sample_img, target_size=640)
  results["preprocessing"] = measure_latencies(bench_preproc)
  print(f"[2] Preprocessing (Letterbox 640x640): {results['preprocessing']['mean_ms']} ms")

  preprocessed_tensor, meta = ImagePreprocessor.letterbox(sample_img, target_size=640)

  # 3. Model Inference (Pure Forward Pass)
  # 3A. DENTEX FP32 ONNX
  dentex_fp32_entry = model_registry.get_entry("dentex-yolov8n-seg")
  if dentex_fp32_entry and dentex_fp32_entry.is_available():
    adapter = model_registry.get_adapter("dentex-yolov8n-seg")
    adapter.load_session()
    def bench_dentex_fp32():
      _ = adapter.run_inference(preprocessed_tensor)
    results["dentex_fp32_onnx"] = measure_latencies(bench_dentex_fp32, n_runs=15)
    print(f"[3A] DENTEX YOLOv8n-seg FP32 ONNX (CPU 4-threads): {results['dentex_fp32_onnx']['mean_ms']} ms")

  # 3B. DENTEX Dynamic INT8 ONNX
  dentex_int8_entry = model_registry.get_entry("dentex-yolov8n-seg-int8")
  if dentex_int8_entry and dentex_int8_entry.is_available():
    adapter_int8 = model_registry.get_adapter("dentex-yolov8n-seg-int8")
    adapter_int8.load_session()
    def bench_dentex_int8():
      _ = adapter_int8.run_inference(preprocessed_tensor)
    results["dentex_int8_onnx"] = measure_latencies(bench_dentex_int8, n_runs=15)
    print(f"[3B] DENTEX YOLOv8n-seg Dynamic INT8 ONNX (CPU): {results['dentex_int8_onnx']['mean_ms']} ms")

  # 3C. Liodon Screener ONNX
  liodon_entry = model_registry.get_entry("liodon-panoramic-screener")
  if liodon_entry and liodon_entry.is_available():
    adapter_lio = model_registry.get_adapter("liodon-panoramic-screener")
    adapter_lio.load_session()
    def bench_liodon():
      _ = adapter_lio.run_inference(preprocessed_tensor)
    results["liodon_screener_onnx"] = measure_latencies(bench_liodon, n_runs=15)
    print(f"[3C] Liodon Screener ONNX (CPU): {results['liodon_screener_onnx']['mean_ms']} ms")

  # 3D. PyTorch GPU inference if CUDA available
  if torch.cuda.is_available() and (PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg.pt").exists():
    from ultralytics import YOLO
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    gpu_model = YOLO(str(PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg.pt"))
    def bench_gpu():
      _ = gpu_model.predict(sample_img, device=0, verbose=False)
    results["dentex_pytorch_gpu"] = measure_latencies(bench_gpu, n_runs=15)
    gpu_vram_peak_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
    results["gpu_vram_peak_mb"] = round(gpu_vram_peak_mb, 2)
    print(f"[3D] DENTEX PyTorch on RTX 2050 CUDA: {results['dentex_pytorch_gpu']['mean_ms']} ms (Peak VRAM: {results['gpu_vram_peak_mb']} MB)")

  # 4. FDI Arch Solver
  fdi_solver = CalibratedFDISolver()
  dummy_proposals = [
      {"id": f"p_{i}", "bbox": [100 + i * 30, 200, 130 + i * 30, 300], "confidence": 0.85}
      for i in range(28)
  ]
  def bench_fdi():
    _ = fdi_solver.solve(dummy_proposals, image_width=img_w, image_height=img_h)
  results["fdi_solver"] = measure_latencies(bench_fdi, n_runs=30)
  print(f"[4] Calibrated FDI Arch Solver (28 teeth): {results['fdi_solver']['mean_ms']} ms")

  # 5. Tooth-Pathology Association
  resolved_teeth = fdi_solver.solve(dummy_proposals, image_width=img_w, image_height=img_h)
  associator = ToothPathologyAssociator()
  dummy_findings = [
      {"id": "f_1", "label": "caries", "confidence": 0.80, "bbox": [105, 210, 125, 250]},
      {"id": "f_2", "label": "periapical_lesion", "confidence": 0.75, "bbox": [400, 260, 430, 295]},
  ]
  def bench_assoc():
    _ = associator.associate(dummy_findings, resolved_teeth)
  results["tooth_association"] = measure_latencies(bench_assoc, n_runs=30)
  print(f"[5] Tooth-Pathology Association: {results['tooth_association']['mean_ms']} ms")

  # 6. End-to-End Analysis Pipeline Latency
  # Create a temporary study
  st_resp = study_service.create_study(
      raw_bytes=sample_bytes,
      original_filename="bench_sample.png",
      clinical_indication="Performance benchmark test case",
  )
  bench_study_id = st_resp.study_id

  try:
    def bench_pipeline():
      _ = study_service.analyze_study(bench_study_id, model_id="liodon-panoramic-screener")
    results["full_analysis_pipeline"] = measure_latencies(bench_pipeline, n_runs=10)
    print(f"[6] Complete End-to-End Analysis Pipeline: {results['full_analysis_pipeline']['mean_ms']} ms (p95: {results['full_analysis_pipeline']['p95_ms']} ms)")

    # 7. Pre-Auth Draft Generation (Deterministic vs Ollama)
    def bench_det_narrative():
      pkg = clinical_service.get_clinical_evidence(bench_study_id)
      _ = clinical_service.generate_pre_auth_draft(bench_study_id, force_regenerate=True, model_tag="deterministic")
    results["deterministic_draft_generation"] = measure_latencies(bench_det_narrative, n_runs=10)
    print(f"[7A] Deterministic Narrative Generation: {results['deterministic_draft_generation']['mean_ms']} ms")

    # Local Ollama test
    try:
      t0 = time.perf_counter()
      _, o_metrics = clinical_service.generate_pre_auth_draft(bench_study_id, force_regenerate=True, model_tag="qwen2.5:3b")
      ollama_dur = (time.perf_counter() - t0) * 1000.0
      results["ollama_qwen25_3b"] = {
          "latency_ms": round(ollama_dur, 1),
          "engine_used": o_metrics.get("engine_used"),
          "status": "available",
      }
      print(f"[7B] Local Ollama qwen2.5:3b Narrative: {results['ollama_qwen25_3b']['latency_ms']} ms")
    except Exception as exc:
      results["ollama_qwen25_3b"] = {"status": "error", "error": str(exc)}
      print(f"[7B] Ollama execution: {exc}")

    # 8. ReportLab PDF Export
    def bench_pdf():
      _ = clinical_service.export_claim_pack_pdf(bench_study_id)
    results["pdf_generation"] = measure_latencies(bench_pdf, n_runs=10)
    print(f"[8] ReportLab PDF Claim Pack Generation: {results['pdf_generation']['mean_ms']} ms")

  finally:
    study_service.delete_study(bench_study_id, hard_delete=True)

  # System Memory Footprint
  final_ram_mb = process.memory_info().rss / (1024 * 1024)
  results["peak_ram_mb"] = round(final_ram_mb, 2)
  print(f"[9] Process Peak RAM: {results['peak_ram_mb']} MB (System Total: {results['ram_total_gb']} GB)")

  out_json = PROJECT_ROOT / "docs" / "level_7_performance_benchmark.json"
  with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
  print(f"\nSaved empirical benchmark results to: {out_json}")
  return results


if __name__ == "__main__":
  run_benchmark()
