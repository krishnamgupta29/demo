import time
import numpy as np
import onnxruntime as ort

def benchmark_model(model_path: str, warmup: int = 10, runs: int = 100):
    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(model_path, sess_options=sess_opts, providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    
    # Standard 1x3x640x640 input
    dummy_input = np.random.randn(1, 3, 640, 640).astype(np.float32)

    # Warmup
    for _ in range(warmup):
        sess.run(None, {input_name: dummy_input})

    # Timed runs
    latencies = []
    for _ in range(runs):
        t0 = time.perf_counter()
        sess.run(None, {input_name: dummy_input})
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    latencies = np.array(latencies)
    mean_ms = float(np.mean(latencies))
    median_ms = float(np.median(latencies))
    p95_ms = float(np.percentile(latencies, 95))
    min_ms = float(np.min(latencies))
    max_ms = float(np.max(latencies))
    return {
        "mean_ms": round(mean_ms, 2),
        "median_ms": round(median_ms, 2),
        "p95_ms": round(p95_ms, 2),
        "min_ms": round(min_ms, 2),
        "max_ms": round(max_ms, 2),
    }

if __name__ == "__main__":
    fp32_path = "ml/models/checkpoints/dentex_yolov8n_seg_best.onnx"
    int8_static_path = "ml/models/checkpoints/dentex_yolov8n_seg_static_qdq_int8.onnx"
    int8_dyn_path = "ml/models/checkpoints/dentex_yolov8n_seg_best_int8.onnx"

    print("Benchmarking FP32...")
    res_fp32 = benchmark_model(fp32_path)
    print("FP32:", res_fp32)

    print("Benchmarking Static QDQ INT8...")
    res_int8_static = benchmark_model(int8_static_path)
    print("Static QDQ INT8:", res_int8_static)

    print("Benchmarking Dynamic INT8 (baseline)...")
    res_int8_dyn = benchmark_model(int8_dyn_path)
    print("Dynamic INT8:", res_int8_dyn)
