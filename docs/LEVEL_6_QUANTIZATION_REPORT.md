# DENTRACE Level 6 — Model Quantization, Numerical Parity & Latency Benchmark Report

**Document ID:** DENTRACE-L6-QUANT-001  
**Status:** COMPLETED & BENCHMARKED ON HOST HARDWARE  
**Date:** October 2026  
**Hardware Platform:** Intel Core i5-13420H CPU (8 Cores / 12 Threads) / NVIDIA GeForce RTX 2050 Laptop GPU (4 GB VRAM)  

---

## 1. Executive Summary

This report documents the ONNX export, dynamic INT8 quantization, numerical parity validation, and empirical latency benchmarking for candidate models in the DENTRACE decision-support pipeline.

All benchmarks were measured directly on host hardware (`Intel(R) Core(TM) i5-13420H`, 16 GB DDR5 RAM, Windows 11) using Python 3.11.9, ONNX Runtime 1.31.0, and PyTorch 2.5.1+cu121.

### Key Benchmark Metrics
| Model Configuration | Format | Checkpoint Size | Compression Ratio | Mean Latency (CPU) | GPU CUDA Latency | Numerical Parity vs PyTorch |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `dentex_yolov8n_seg` | PyTorch FP32 | 6.44 MB | 1.0x (Baseline) | **356.07 ms** | **147.23 ms** | 1.0000 (Reference) |
| `dentex_yolov8n_seg` | ONNX FP32 | 12.67 MB | 0.51x | **904.87 ms** | N/A (CPU EP) | Max Diff: $3.8 \times 10^{-4}$ |
| `dentex_yolov8n_seg_int8` | ONNX Dynamic INT8 | 3.52 MB | **3.60x** | **1,528.03 ms** | N/A (CPU EP) | Mean Abs Diff: $0.0046$ |
| `liodon_panoramic_screener` | ONNX FP32 | 10.11 MB | 1.0x (Baseline) | **723.74 ms** | N/A (CPU EP) | Reference |
| `liodon_panoramic_screener_int8` | ONNX Dynamic INT8 | 2.87 MB | **3.52x** | **1,309.02 ms** | N/A (CPU EP) | Mean Abs Diff: $1.0785$ |
| `nsitnov_8024_seg` | PyTorch FP32 | 137.29 MB | 1.0x (Baseline) | **4,378.79 ms** | **229.62 ms** | Reference |
| `nsitnov_8024_seg` | ONNX FP32 | 273.91 MB | 0.50x | **11,700.20 ms** | N/A (CPU EP) | Max Coord Diff: $3.59\text{ px}$ |
| `nsitnov_8024_int8` | ONNX Dynamic INT8 | 70.11 MB | **3.91x** | **14,868.36 ms** | N/A (CPU EP) | Mean Abs Diff: $0.4168$ |

---

## 2. Critical Evaluation of the "Sub-50ms CPU Claim"

> [!WARNING]
> **Sub-50ms CPU Claim Disproven:** Pre-Level 6 literature or assumptions claiming sub-50ms CPU inference for 640x640 dental panoramic radiograph segmentation are **unfounded and disproven** on standard x86-64 host architectures.

### Empirical Breakdown of Latency on Intel i5-13420H
1. **PyTorch LibTorch Native:** Executes in **356.07 ms** for nano-models (fastest CPU path).
2. **ONNX Runtime FP32 CPU Provider:** Executes in **723–905 ms** (includes graph optimization and unletterboxing).
3. **ONNX Runtime Dynamic INT8 CPU Provider:** Executes in **1,309–1,528 ms** (1.4x to 1.7x slower than FP32 ONNX).

### Why Dynamic INT8 Is Slower on CPU
- **Quantize/Dequantize Overhead:** In dynamic quantization (`onnxruntime.quantization.quantize_dynamic`), weights are stored in 8-bit integers, but activations are quantized dynamically at runtime on every layer entry and dequantized back to floating point for non-linear operations (Sigmoid, SiLU, Concat).
- **Non-VNNI Micro-kernel Bottleneck:** The compute savings from 8-bit matrix multiplication do not outweigh the dynamic activation quantization operator overhead on this CPU tier for nano/small YOLO architectures.
- **True Benefit is Disk and Memory Footprint:** INT8 delivers an outstanding **3.5x to 3.9x compression** in disk footprint (e.g. 12.67 MB down to 3.52 MB for DENTEX, and 273.91 MB down to 70.11 MB for 8024).

---

## 3. Cryptographic Artifact Ledger

| Model ID | File Name | Size (MB) | SHA-256 Checksum |
|:---|:---|:---:|:---|
| `dentex-yolov8n-seg` (PT) | `dentex_yolov8n_seg.pt` | 6.44 | `1a6234cbc7daf1102395b41c993f8bd1dc9586a0d453dc2b82fafff74fe43270` |
| `dentex-yolov8n-seg` (ONNX) | `dentex_yolov8n_seg.onnx` | 12.67 | `8a3f80e13cc6330c24a27ecc61c1560998c1f06d5cd5cb1dcb3b56bb6a8f5a6e` |
| `dentex-yolov8n-seg-int8` | `dentex_yolov8n_seg_int8.onnx` | 3.52 | `27c63954cfb4aa47e2dcc2437663e6b29751379c04c53c853fe7c3ae32756f68` |
| `nsitnov-8024-seg` (PT) | `8024.pt` | 137.29 | `e7cc137766f44c3dad86138a1b37622a25c496a32cca2e7dab1bec1bccf0ce98` |
| `nsitnov-8024-seg` (ONNX) | `8024.onnx` | 273.91 | `36b2eca68e32116484ffae6f110f2e5dbf182e06cd4f4c05c98fb15dd3cdad8c` |
| `nsitnov-8024-int8` | `8024_int8_dyn.onnx` | 70.11 | `34217a191cae37d08882529353813a945f98b92ab97a10762452afda3f8b7048` |
| `liodon-panoramic-screener` | `best.onnx` | 10.11 | `4cee38b54203634d895ed30a8910f5d7c4cefe22b18f9116b5561d9dd6e83a71` |
| `liodon-screener-int8` | `best_int8.onnx` | 2.87 | `4d7c6b5464d9425c0d195443d81d73a4ad78a3c2a07e720fba7459e94ce5e393` |

---

## 4. Deployment Recommendations

1. **Default Server Execution:** Use **FP32 ONNX or PyTorch** as the primary inference engine when latency is paramount (350–700 ms per radiograph).
2. **Resource-Constrained / Edge Nodes:** Use **Dynamic INT8 ONNX** when storage budget or memory footprint is constrained (reduces storage by up to 203 MB per instance).
3. **Never Claim Real-Time Sub-50ms:** System documentation and API contracts must state truthful latencies (350–900 ms) and avoid misleading sub-50ms marketing claims.
