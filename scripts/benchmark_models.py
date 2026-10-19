"""Reproducible local model benchmarking utility for DENTRACE.

Enforces:
1. Truthful benchmark reporting: never invent latencies or throughput.
2. If weights are not present on disk, reports MODEL_UNAVAILABLE.
3. When weights exist, measures cold-start, warmup, and N-iteration latency distribution (mean, p50, p95).
4. Supports synthetic ONNX generation for benchmarking test harnesses offline.
"""

import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.model_adapter import model_registry, ModelTask


def benchmark_model(
    model_id: str,
    iterations: int = 50,
    warmup: int = 10,
) -> dict:
  """Benchmark inference latency for a registered model if weights are available."""
  entry = model_registry.get_entry(model_id)
  if not entry:
    return {
        "model_id": model_id,
        "status": "NOT_REGISTERED",
        "error": f"Model '{model_id}' not found in registry",
    }

  adapter = model_registry.get_adapter(model_id)
  if not entry.is_available():
    return {
        "model_id": model_id,
        "model_name": entry.model_name,
        "version": entry.version,
        "status": "MODEL_UNAVAILABLE",
        "weight_path": entry.weight_rel_path,
        "message": (
            f"Physical checkpoint '{entry.weight_rel_path}' not found on host. "
            "No synthetic or fabricated benchmark results are reported."
        ),
    }

  # Attempt session initialization
  t_init_0 = time.perf_counter()
  loaded = adapter.load_session()
  init_time_ms = (time.perf_counter() - t_init_0) * 1000.0

  if not loaded:
    return {
        "model_id": model_id,
        "status": "INIT_FAILED",
        "error": "Failed to load ONNX Runtime session",
    }

  # Generate deterministic synthetic input matching input_shape contract
  rng = np.random.default_rng(42)
  dummy_input = rng.standard_normal(entry.input_shape, dtype=np.float32)

  # Warmup runs
  for _ in range(warmup):
    adapter.run_inference(dummy_input)

  # Benchmark runs
  latencies_ms = []
  for _ in range(iterations):
    t0 = time.perf_counter()
    res = adapter.run_inference(dummy_input)
    t1 = time.perf_counter()
    if res.get("status") != "AVAILABLE":
      return {
          "model_id": model_id,
          "status": "INFERENCE_ERROR",
          "error": res.get("error"),
      }
    latencies_ms.append((t1 - t0) * 1000.0)

  latencies_ms = np.array(latencies_ms)
  return {
      "model_id": model_id,
      "model_name": entry.model_name,
      "version": entry.version,
      "status": "BENCHMARKED",
      "iterations": iterations,
      "warmup_runs": warmup,
      "init_time_ms": round(init_time_ms, 2),
      "mean_latency_ms": round(float(np.mean(latencies_ms)), 2),
      "std_latency_ms": round(float(np.std(latencies_ms)), 2),
      "p50_latency_ms": round(float(np.percentile(latencies_ms, 50)), 2),
      "p95_latency_ms": round(float(np.percentile(latencies_ms, 95)), 2),
      "min_latency_ms": round(float(np.min(latencies_ms)), 2),
      "max_latency_ms": round(float(np.max(latencies_ms)), 2),
      "throughput_fps": round(1000.0 / float(np.mean(latencies_ms)), 1),
  }


def main():
  parser = argparse.ArgumentParser(description="DENTRACE Model Benchmark Suite")
  parser.add_argument(
      "--model",
      type=str,
      default="all",
      help="Specific model ID to benchmark or 'all'",
  )
  parser.add_argument(
      "--iterations", type=int, default=50, help="Number of measured iterations"
  )
  parser.add_argument(
      "--warmup", type=int, default=10, help="Number of warmup iterations"
  )
  args = parser.parse_args()

  print("=" * 70)
  print("DENTRACE LOCAL MODEL BENCHMARKING SUITE")
  print("=" * 70)

  models = (
      [m["model_id"] for m in model_registry.list_models()]
      if args.model == "all"
      else [args.model]
  )
  results = []

  for mid in models:
    print(f"\nEvaluating candidate model: {mid}...")
    res = benchmark_model(mid, iterations=args.iterations, warmup=args.warmup)
    results.append(res)
    print(json.dumps(res, indent=2))

  output_file = PROJECT_ROOT / "docs/model_benchmark_results.json"
  output_file.parent.mkdir(parents=True, exist_ok=True)
  with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": results,
        },
        f,
        indent=2,
    )
  print(f"\n[DONE] Results saved to: {output_file}")


if __name__ == "__main__":
  main()
