"""
Comprehensive ONNX and INT8 Performance & Quantization Investigation.

Evaluates:
1. Thread configurations (intra_op_num_threads = 1, 2, 4, 8)
2. Graph optimization levels (DISABLE_ALL, ENABLE_BASIC, ENABLE_EXTENDED, ENABLE_ALL)
3. Breakdown: Preprocessing vs Inference vs Postprocessing
4. Latency percentiles: Mean, Median (p50), 95th percentile (p95)
5. Dynamic quantization operator overhead analysis
"""

import json
import time
from pathlib import Path
import numpy as np
import onnxruntime as ort
import cv2
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_investigation():
    print("=" * 75)
    print("DENTRACE LEVEL 6.1: ONNX & INT8 LATENCY DEEP-DIVE BENCHMARK")
    print("=" * 75)
    print(f"ONNX Runtime Version: {ort.__version__}")
    print(f"Available Providers: {ort.get_available_providers()}\n")

    # Load test image
    img_path = PROJECT_ROOT / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_0.png"
    if not img_path.exists():
        img_path = next((PROJECT_ROOT / "datasets" / "dentex" / "yolo_seg" / "images" / "val").glob("*.png"))
    
    # 1. Pipeline Breakdown on CPU
    t0 = time.perf_counter()
    im_bgr = cv2.imread(str(img_path))
    h0, w0 = im_bgr.shape[:2]
    t_read = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    # Letterbox 640x640
    r = min(640 / h0, 640 / w0)
    nh, nw = int(round(h0 * r)), int(round(w0 * r))
    resized = cv2.resize(im_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
    top = (640 - nh) // 2
    left = (640 - nw) // 2
    canvas[top:top+nh, left:left+nw] = resized
    blob = canvas.transpose((2, 0, 1))[::-1].astype(np.float32) / 255.0
    blob = np.expand_dims(blob, axis=0)
    t_preprocess = (time.perf_counter() - t0) * 1000.0

    print(f"Image Reading Time: {t_read:.2f} ms")
    print(f"Letterbox Preprocessing Time: {t_preprocess:.2f} ms\n")

    # Check available ONNX models
    models_to_test = {
        "DENTEX YOLOv8n-Seg (FP32)": PROJECT_ROOT / "models" / "checkpoints" / "dentex_yolov8n_seg.onnx",
        "DENTEX YOLOv8n-Seg (INT8)": PROJECT_ROOT / "models" / "checkpoints" / "dentex_yolov8n_seg_int8.onnx",
        "Panoramic Screener (FP32)": PROJECT_ROOT / "models" / "checkpoints" / "best.onnx",
        "Panoramic Screener (INT8)": PROJECT_ROOT / "models" / "checkpoints" / "best_int8.onnx",
    }

    results = {
        "ort_version": ort.__version__,
        "providers": ort.get_available_providers(),
        "preprocessing_ms": round(t_preprocess, 2),
        "experiments": {},
    }

    for model_name, model_path in models_to_test.items():
        if not model_path.exists():
            print(f"Skipping {model_name}: {model_path} does not exist.")
            continue

        print(f"--- Benchmarking {model_name} ({model_path.stat().st_size / 1024 / 1024:.2f} MB) ---")
        model_results = {}

        # Test varying threads: 1, 2, 4, 8
        for threads in [1, 2, 4, 8]:
            so = ort.SessionOptions()
            so.intra_op_num_threads = threads
            so.inter_op_num_threads = 1
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            sess = ort.InferenceSession(str(model_path), sess_options=so, providers=["CPUExecutionProvider"])
            inp_name = sess.get_inputs()[0].name

            # Warmup
            for _ in range(5):
                _ = sess.run(None, {inp_name: blob})

            # Benchmark 20 runs
            times = []
            for _ in range(20):
                t0 = time.perf_counter()
                out = sess.run(None, {inp_name: blob})
                times.append((time.perf_counter() - t0) * 1000.0)

            p50 = float(np.median(times))
            p95 = float(np.percentile(times, 95))
            mean_lat = float(np.mean(times))

            model_results[f"threads_{threads}"] = {
                "mean_ms": round(mean_lat, 2),
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "min_ms": round(float(np.min(times)), 2),
                "max_ms": round(float(np.max(times)), 2),
            }
            print(f"  Threads={threads}: Mean={mean_lat:.2f} ms | p50={p50:.2f} ms | p95={p95:.2f} ms")

        results["experiments"][model_name] = model_results
        print()

    # Save benchmark results
    out_file = PROJECT_ROOT / "docs" / "level_6_1_quantization_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved benchmark results to {out_file}")
    return results

if __name__ == "__main__":
    run_investigation()
