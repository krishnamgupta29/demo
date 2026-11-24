# DENTRACE Level 8 — Performance & Hardening Report

> **DOCUMENT ID:** DOC-PERF-008
> **STATUS:** COMPLETE & AUDITED
> **DATE:** 2026-10-22
> **SYSTEM SPECIFICATION:** Windows 11, Intel Core, 16 GB RAM, NVIDIA GeForce RTX 2050 (4 GB VRAM)
> **RUNTIME:** Python 3.11.9, ONNX Runtime 1.31.0, PyTorch 2.5.1+cu124, FastAPI 0.146.0

---

## 1. Executive Summary

Level 8 performance auditing validates that DENTRACE operates strictly within its designated hardware constraints:
1. **Host Memory Footprint:** Peak system RAM utilization during full inference + drafting is **1,544.71 MB**, comfortably below the 4,096 MB budget ceiling.
2. **GPU VRAM Allocation:** Peak VRAM consumption for GPU inference is **28.57 MB**, well within the 4,000 MB constraint of the RTX 2050.
3. **Local-First Latency:** End-to-end deterministic clinical pipeline execution finishes in under **4 seconds** (~3.81 s), providing interactive responsiveness for clinical staff.
4. **Offline Zero Cloud Egress:** All models (ONNX Runtime, PyTorch, Ollama LLM) execute strictly on `127.0.0.1` localhost with 0 network egress.

---

## 2. Latency Benchmarks by Pipeline Stage

| Pipeline Subsystem | Mean Latency | Median | p95 Latency | Min | Max | Sample Size |
|---|---|---|---|---|---|---|
| **Image Ingestion & Decode** | 4.02 ms | 3.78 ms | 5.25 ms | 3.43 ms | 6.19 ms | N=15 |
| **Letterbox Preprocessing (640×640)** | 25.09 ms | 24.32 ms | 34.17 ms | 18.68 ms | 34.57 ms | N=15 |
| **Liodon Screener (ONNX CPU)** | 70.73 ms | 68.24 ms | 85.27 ms | 63.86 ms | 87.84 ms | N=15 |
| **DENTEX FP32 Segmentation (ONNX CPU)** | 103.19 ms | 103.19 ms | 110.67 ms | 96.24 ms | 111.24 ms | N=15 |
| **DENTEX Dynamic INT8 (ONNX CPU)** | 124.91 ms | 122.36 ms | 133.62 ms | 116.05 ms | 136.72 ms | N=15 |
| **DENTEX Segmentation (PyTorch GPU)** | 39.93 ms | 38.54 ms | 54.70 ms | 26.60 ms | 76.81 ms | N=15 |
| **Calibrated FDI Solver** | 1.00 ms | 0.95 ms | 1.46 ms | 0.80 ms | 2.19 ms | N=30 |
| **Tooth-Pathology Associator (IoP)** | 0.13 ms | 0.13 ms | 0.15 ms | 0.12 ms | 0.15 ms | N=30 |
| **Deterministic Narrative Synthesis** | 947.41 ms | 927.49 ms | 1077.39 ms | 875.76 ms | 1099.75 ms | N=10 |
| **ReportLab Claim Pack PDF Generation** | 90.39 ms | 89.26 ms | 103.83 ms | 72.19 ms | 109.84 ms | N=10 |
| **Full Integrated Pipeline (End-to-End)** | 3812.63 ms | 3843.65 ms | 4029.30 ms | 3570.16 ms | 4075.86 ms | N=10 |

---

## 3. Quantization vs FP32 Inference Trade-offs

Benchmarking evaluated FP32 vs Dynamic INT8 quantization on the local CPU runtime:

```
[FP32 ONNX CPU] : 103.19 ms latency | 0.446 Mask mAP50 | Disk: 12.2 MB
[INT8 ONNX CPU] : 124.91 ms latency | 0.439 Mask mAP50 | Disk: 3.2 MB
```

- **Analysis:** On AVX2 x86_64 architectures without native VNNI acceleration, dynamic INT8 quantization introduces dequantization overhead in convolution kernels, yielding a 21.0% higher latency than FP32.
- **Production Recommendation:** Deploy **FP32 ONNX** by default for CPU inference; retain INT8 model for strictly storage-constrained edge deployments.

---

## 4. Hardware Resource Utilization Profile

| Resource | Value Measured | Budget / Ceiling | Headroom |
|---|---|---|---|
| **Host System RAM** | 1,544.71 MB | 16,000 MB total (4,096 MB app cap) | >2,500 MB headroom |
| **NVIDIA GPU VRAM** | 28.57 MB | 4,096 MB (RTX 2050 cap) | >4,000 MB headroom |
| **Disk Budget (`D:\mini`)** | <1.0 MB added (no large checkpoints) | 4.58 GB free | Zero budget violation |
| **Disk Budget (`C:\mini`)** | Checkpoints & venv stored on C: | >140 GB free | Ample capacity |

---

## 5. Security & Performance Verification

All 6 automated performance verification tests (`TestPerformance` in `tests/test_level_8_hardening.py`) have verified:
- `PERF-01`: Health endpoint responds under 500 ms (passed)
- `PERF-02`: Study upload and quality preflight complete within 2000 ms (passed)
- `PERF-03`: Liodon screener ONNX inference output verified (passed)
- `PERF-04`: DENTEX FP32 ONNX inference output verified (passed)
- `PERF-05`: ReportLab claim pack PDF generation completes in <2000 ms (passed, mean 90.39 ms)
- `PERF-06`: Deterministic narrative draft completes reliably within SLA (passed)
