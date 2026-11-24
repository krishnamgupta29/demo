# DENTRACE Level 6.1 — ONNX Quantization Benchmark

**Generated:** 2026-10-21 21:19

> [!NOTE]
> Latency measured on CPU (4 threads, 30 runs after 5 warmup runs), input size 1×3×640×640 float32. GPU inference is used at training time but not during clinical offline inference.

## Results

| Model | File Size | Mean Latency (CPU) | Notes |
|-------|-----------|--------------------|-------|
| FP32 ONNX | 13.16 MB | 113.8 ms | Full precision baseline |
| Dynamic INT8 ONNX | 3.64 MB | 145.7 ms | `onnxruntime.quantization.quantize_dynamic` |
| INT8 / FP32 ratio | — | 1.28× (INT8 is slower) | — |

## INT8 CPU Overhead Explanation

Dynamic INT8 quantization compresses model weights (reducing file size) but introduces **per-layer dequantization** at inference time on CPU. This is a known ONNXRuntime behaviour — static INT8 with pre-calibrated activations would avoid this but requires a representative calibration dataset.

**Recommendation:** Deploy FP32 ONNX for offline CPU inference in the current system. INT8 is beneficial only for edge deployment with INT8-optimised hardware accelerators.

## Model Files

| File | Path |
|------|------|
| Best PyTorch weights | `models/experiments/dentex_yolov8n_seg_4class_v2/weights/best.pt` |
| FP32 ONNX | `models/checkpoints/dentex_yolov8n_seg_best.onnx` |
| INT8 ONNX | `models/checkpoints/dentex_yolov8n_seg_best_int8.onnx` |

> [!IMPORTANT]
> All inference runs strictly offline. No data is transmitted to external services (Zero Cloud Egress policy).
