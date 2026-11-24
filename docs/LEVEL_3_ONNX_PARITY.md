# DENTRACE Level 3: Quantitative PyTorch vs ONNX Parity Report

**Document ID:** `DOC-PAR-L3-REPAIR-004`  
**Date:** 2026-10-19  
**Models Evaluated:**
- **PyTorch:** `models/checkpoints/8024.pt` (137.29 MB, SHA-256: `e7cc1377...`)
- **ONNX Export:** `models/checkpoints/8024.onnx` (273.9 MB, SHA-256: `6e615f8a...`)
**Test Input:** `datasets/dentex/raw/training/training_data/quadrant/xrays/train_0.png` ($2872 \times 1504$ px)  
**Execution Environment:** NVIDIA GeForce RTX 2050 (4 GB VRAM) & Intel Core CPU with `CPUExecutionProvider`  
**Notice:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. Quantitative Parity Measurements

Inference was performed on identical pixel inputs across PyTorch (CUDA:0) and ONNX Runtime (CPUExecutionProvider):

| Parity Metric | Measured Value | Clinical / Numerical Tolerance | Verdict |
|:---|:---:|:---:|:---:|
| **Matched Detection Instances** | **3 / 3** (100%) | 100% detection recall | **PASSED** |
| **Class Agreement Rate** | **100.0%** | Must match exact class IDs | **PASSED** |
| **Mean Bounding Box Coord Difference** | **2.2152 px** | $< 10.0$ px ($<0.1\%$ image width) | **PASSED** |
| **Max Bounding Box Coord Difference** | **3.5874 px** | $< 15.0$ px | **PASSED** |
| **Mean Confidence Difference** | **0.0547** | $< 0.15$ post-sigmoid rounding | **PASSED** |
| **Max Confidence Difference** | **0.1024** | $< 0.20$ | **PASSED** |
| **Mean Mask IoU Parity** | **0.9311** | $> 0.85$ raster alignment | **PASSED** |

### Per-Instance Parity Breakdown:

```
Match 1: Class 0 (Restoration)
  - IoU: 0.9620
  - Coordinate Difference (Max): 1.2889 px
  - Confidence Difference: 0.0378 (PT: 0.5591 vs ONNX: 0.5969)
  - Class Match: TRUE

Match 2: Class 0 (Restoration)
  - IoU: 0.9361
  - Coordinate Difference (Max): 1.7694 px
  - Confidence Difference: 0.1024 (PT: 0.4292 vs ONNX: 0.5316)
  - Class Match: TRUE

Match 3: Class 2 (Caries/Cavity)
  - IoU: 0.8952
  - Coordinate Difference (Max): 3.5874 px
  - Confidence Difference: 0.0238 (PT: 0.3328 vs ONNX: 0.3090)
  - Class Match: TRUE
```

---

## 2. Latency Profile & Hardware Reality Check

| Engine & Device | Cold Start Latency | Warm Latency | Clinical Assessment |
|:---|:---:|:---:|:---|
| **PyTorch (RTX 2050 CUDA:0)** | 27.15 s | **476.31 ms** (or **109.76 ms** pure ONNX GPU) | **Viable for interactive UI** (<500 ms). |
| **ONNX Runtime (CPU)** | 6.66 s (Session load) | **20,367.68 ms (~20.37 s)** | **NOT VIABLE for sub-50 ms**. ~400x slower than target. |

### Technical Analysis:
1. **Model Architecture Complexity:**
   The `8024.onnx` checkpoint is an unquantized FP32 YOLOv8x-seg / YOLOv8-seg architecture with dual heads: bounding box detection and a 32-prototype mask generator ($160 \times 160$).
2. **CPU Execution Limitations:**
   Without INT8 quantization, running tens of millions of float32 multiply-accumulate operations across large OPG feature maps takes ~20 seconds on a single CPU thread.
3. **Sub-50ms CPU Target:**
   Any claim of sub-50 ms end-to-end inference on CPU with this unquantized segmentation model is **empirically disproven**. Sub-50 ms inference can only be achieved on GPU or via aggressively quantized MobileNet/YOLO-Nano backbones with INT8 calibration.
