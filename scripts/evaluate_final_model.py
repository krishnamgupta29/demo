"""
DENTRACE Level 6.1 -- Final model evaluation and report data generator.

Run AFTER training completes:
    py -3.11 scripts/evaluate_final_model.py

Outputs:
    docs/LEVEL_6_1_TRAINING_RESULTS_DATA.json
    docs/LEVEL_6_1_QUANTIZATION_DATA.json
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXPERIMENT = ROOT / "models" / "experiments" / "dentex_yolov8n_seg_4class_v2"
RESULTS_CSV = EXPERIMENT / "results.csv"
WEIGHTS_DIR = EXPERIMENT / "weights"
BEST_PT = WEIGHTS_DIR / "best.pt"
DOCS = ROOT / "docs"
ONNX_DIR = ROOT / "models" / "checkpoints"


def read_results_csv():
    rows = []
    with open(RESULTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip(): v.strip() for k, v in row.items()}
            rows.append(clean)
    return rows


def find_best_epoch(rows):
    return max(rows, key=lambda r: float(r.get("metrics/mAP50(B)", 0)))


def export_onnx(pt_path, onnx_path, imgsz=640):
    try:
        from ultralytics import YOLO
        model = YOLO(str(pt_path))
        model.export(format="onnx", imgsz=imgsz, opset=12, dynamic=False)
        generated = pt_path.with_suffix(".onnx")
        if generated.exists() and generated != onnx_path:
            import shutil
            shutil.copy(generated, onnx_path)
        print(f"[export] ONNX saved: {onnx_path}")
        return True
    except Exception as e:
        print(f"[export] ONNX export failed: {e}")
        return False


def quantize_int8(fp32_onnx, int8_onnx):
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        quantize_dynamic(str(fp32_onnx), str(int8_onnx), weight_type=QuantType.QUInt8)
        print(f"[quant] INT8 saved: {int8_onnx}")
        return True
    except Exception as e:
        print(f"[quant] INT8 quantization failed: {e}")
        return False


def benchmark_onnx(onnx_path, imgsz=640, n_warmup=5, n_runs=30):
    try:
        import numpy as np
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        dummy = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)
        for _ in range(n_warmup):
            session.run(None, {input_name: dummy})
        latencies = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            session.run(None, {input_name: dummy})
            latencies.append((time.perf_counter() - t0) * 1000)
        return {"mean_ms": round(float(sum(latencies)/len(latencies)), 1), "n_runs": n_runs, "threads": 4}
    except Exception as e:
        print(f"[bench] Benchmark failed: {e}")
        return {"mean_ms": None, "error": str(e)}


def file_size_mb(path):
    if Path(path).exists():
        return round(Path(path).stat().st_size / 1048576, 2)
    return 0.0


def main():
    print("=" * 60)
    print("DENTRACE Level 6.1 -- Final Evaluation Script")
    print("=" * 60)
    if not RESULTS_CSV.exists():
        print(f"ERROR: {RESULTS_CSV} not found.")
        sys.exit(1)
    rows = read_results_csv()
    best = find_best_epoch(rows)
    total_epochs = len(rows)
    print(f"Total epochs: {total_epochs}, Best epoch: {best['epoch']}  mAP50(B)={best['metrics/mAP50(B)']}")
    training_data = {
        "experiment": "dentex_yolov8n_seg_4class_v2",
        "total_epochs_trained": total_epochs,
        "architecture": "YOLOv8n-seg (pretrained COCO transfer)",
        "num_classes": 4,
        "classes": ["cavity", "missing_tooth", "impacted_tooth", "periapical_lesion"],
        "train_images": 564,
        "val_images": 141,
        "imgsz": 640,
        "batch": 8,
        "best_epoch": int(best["epoch"]),
        "best_metrics": {
            "box_precision": float(best["metrics/precision(B)"]),
            "box_recall": float(best["metrics/recall(B)"]),
            "box_mAP50": float(best["metrics/mAP50(B)"]),
            "box_mAP50_95": float(best["metrics/mAP50-95(B)"]),
            "mask_precision": float(best["metrics/precision(M)"]),
            "mask_recall": float(best["metrics/recall(M)"]),
            "mask_mAP50": float(best["metrics/mAP50(M)"]),
            "mask_mAP50_95": float(best["metrics/mAP50-95(M)"]),
        },
        "per_epoch": [
            {"epoch": int(r["epoch"]), "box_mAP50": float(r["metrics/mAP50(B)"]),
             "mask_mAP50": float(r["metrics/mAP50(M)"]), "box_mAP50_95": float(r["metrics/mAP50-95(B)"]),
             "mask_mAP50_95": float(r["metrics/mAP50-95(M)"]), "train_box_loss": float(r["train/box_loss"]),
             "train_seg_loss": float(r["train/seg_loss"]), "train_cls_loss": float(r["train/cls_loss"])}
            for r in rows
        ],
    }
    DOCS.mkdir(exist_ok=True)
    out_training = DOCS / "LEVEL_6_1_TRAINING_RESULTS_DATA.json"
    out_training.write_text(json.dumps(training_data, indent=2))
    print(f"Training data -> {out_training}")
    fp32_onnx = ONNX_DIR / "dentex_yolov8n_seg_best.onnx"
    int8_onnx = ONNX_DIR / "dentex_yolov8n_seg_best_int8.onnx"
    if not BEST_PT.exists():
        print(f"WARNING: {BEST_PT} not found -- skipping ONNX steps.")
        sys.exit(0)
    print(f"Exporting {BEST_PT} to ONNX ...")
    fp32_ok = export_onnx(BEST_PT, fp32_onnx)
    if not fp32_ok:
        auto = BEST_PT.with_suffix(".onnx")
        if auto.exists():
            fp32_onnx = auto
            fp32_ok = True
    int8_ok = False
    if fp32_ok and fp32_onnx.exists():
        int8_ok = quantize_int8(fp32_onnx, int8_onnx)
    fp32_bench = benchmark_onnx(fp32_onnx) if fp32_ok and fp32_onnx.exists() else {"mean_ms": None}
    int8_bench = benchmark_onnx(int8_onnx) if int8_ok and int8_onnx.exists() else {"mean_ms": None}
    quant_data = {
        "fp32": {"path": str(fp32_onnx), "size_mb": file_size_mb(fp32_onnx), "latency": fp32_bench},
        "int8_dynamic": {"path": str(int8_onnx), "size_mb": file_size_mb(int8_onnx), "latency": int8_bench,
                         "note": "Dynamic INT8 on CPU may be slower than FP32 due to dequantization overhead."},
    }
    out_quant = DOCS / "LEVEL_6_1_QUANTIZATION_DATA.json"
    out_quant.write_text(json.dumps(quant_data, indent=2))
    print(f"Quantization data -> {out_quant}")
    print("\n" + "=" * 60)
    print("LEVEL 6.1 EVALUATION SUMMARY")
    print(f"  Epochs trained : {total_epochs}")
    print(f"  Best epoch     : {training_data['best_epoch']}")
    print(f"  Box mAP50      : {training_data['best_metrics']['box_mAP50']:.4f}")
    print(f"  Mask mAP50     : {training_data['best_metrics']['mask_mAP50']:.4f}")
    print(f"  Box mAP50-95   : {training_data['best_metrics']['box_mAP50_95']:.4f}")
    print(f"  FP32 latency   : {fp32_bench.get('mean_ms')} ms")
    print(f"  INT8 latency   : {int8_bench.get('mean_ms')} ms")
    print("=" * 60)


if __name__ == "__main__":
    main()
