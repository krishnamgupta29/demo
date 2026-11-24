import os
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

# Force CPU-only and disable background pip installs
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["YOLO_AUTOINSTALL"] = "0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.segmentation_engine import DentalSegmentationEngine
from backend.ml.inference_engine import ONNXInferenceEngine
from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.fdi_solver import CalibratedFDISolver

def compute_box_iou(b1, b2):
    ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
    ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    a1 = max(0.0, b1[2] - b1[0]) * max(0.0, b1[3] - b1[1])
    a2 = max(0.0, b2[2] - b2[0]) * max(0.0, b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0

def render_overlay(img: Image.Image, findings: list, teeth: list) -> Image.Image:
    """Draw bounding boxes, translucent polygon masks, and FDI labels."""
    overlay = img.copy()
    draw = ImageDraw.Draw(overlay, "RGBA")
    
    # 1. Draw tooth boxes & FDI labels
    for t in teeth:
        box = t.bbox
        draw.rectangle([box[0], box[1], box[2], box[3]], outline=(59, 130, 246, 200), width=2)
        if t.fdi_number:
            draw.text((box[0] + 3, box[1] + 3), f"#{t.fdi_number}", fill=(255, 255, 255, 255))
            
    # 2. Draw pathology findings & polygons
    for f in findings:
        box = f.get("bbox", [0, 0, 0, 0])
        cond = f.get("condition", "pathology")
        draw.rectangle([box[0], box[1], box[2], box[3]], outline=(239, 68, 68, 240), width=2)
        poly = f.get("polygon", [])
        if poly and len(poly) >= 3:
            flat_poly = [(pt[0], pt[1]) for pt in poly]
            draw.polygon(flat_poly, fill=(239, 68, 68, 80), outline=(220, 38, 38, 220))
        draw.text((box[0] + 3, box[1] + 3), cond, fill=(255, 255, 255, 255))
        
    return overlay

def benchmark_task8_pipeline():
    print("=" * 75)
    print("TASK 8: FULL PIPELINE LATENCY BENCHMARK (10 REAL OPGS, CPU-ONLY)")
    print("=" * 75)
    print("Components: Preprocess + Detection (Primary Seg + Secondary Screener) + FDI (Detector + Solver) + Overlay Rendering")
    print("Execution Provider: CPUExecutionProvider (CUDA disabled)")
    print("-" * 75)
    
    test_paths = [
        PROJECT_ROOT / "samples" / "sample_opg_1.png",
        PROJECT_ROOT / "samples" / "sample_opg_2.png",
        PROJECT_ROOT / "samples" / "sample_opg_3.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_0.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_101.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_104.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_112.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_118.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_123.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_130.png",
    ]
    
    ckpt_seg = "models/checkpoints/dentex_yolov8n_seg_static_qdq_int8.onnx"
    if not (PROJECT_ROOT / ckpt_seg).exists():
        ckpt_seg = "models/checkpoints/dentex_yolov8n_seg_best.onnx"

    seg_engine = DentalSegmentationEngine(
        model_id="dentex-yolov8n-seg-static-qdq-int8",
        model_name="DENTEX 4-Class Segmenter (Static QDQ INT8)",
        version="1.0.0",
        checkpoint_rel_path=ckpt_seg,
        class_names=["impacted_tooth", "caries", "periapical_lesion", "deep_caries"],
        conf_threshold=0.25,
        iou_threshold=0.35,
    )
    screener_engine = ONNXInferenceEngine(
        model_id="liodon-panoramic-screener",
        model_name="Liodon Panoramic Screener",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/best.onnx",
        class_names=["caries", "periapical_lesion", "impacted_tooth"],
        conf_threshold=0.25,
        iou_threshold=0.35,
    )
    fdi_engine = FDINumberingEngine()
    fdi_solver = CalibratedFDISolver()
    
    # Warmup
    print("Warming up models on CPU...")
    warmup_img = Image.open(test_paths[0]).convert("RGB")
    seg_engine.predict_image(warmup_img)
    screener_engine.predict_image(warmup_img)
    fdi_engine.predict_teeth(warmup_img)
    print("Warmup complete. Starting benchmark on 10 real OPGs...")
    print("-" * 75)
    
    per_image_results = []
    
    for idx, img_path in enumerate(test_paths):
        t_start = time.perf_counter()
        
        # 1. Preprocess (file load & RGB conversion)
        t_pre0 = time.perf_counter()
        with Image.open(img_path) as pil_img:
            img = pil_img.convert("RGB")
        orig_w, orig_h = img.size
        t_pre1 = time.perf_counter()
        preprocess_ms = (t_pre1 - t_pre0) * 1000.0
        
        # 2. Primary Seg Detection (dentex_yolov8n_seg)
        t_det0 = time.perf_counter()
        seg_res = seg_engine.predict_image(img, conf_threshold=0.25)
        raw_seg_findings = seg_res.get("findings", [])
        
        # Secondary Detection (liodon screener) & IoU Merge
        screen_res = screener_engine.predict_image(img, conf_threshold=0.25)
        raw_screen_findings = screen_res.get("findings", [])
        
        merged_findings = []
        for sf in raw_seg_findings:
            merged_findings.append({
                "condition": sf.class_name,
                "bbox": sf.bbox_orig,
                "polygon": sf.mask_polygon or [],
                "has_mask": sf.has_mask,
            })
            
        for sc in raw_screen_findings:
            sc_b = sc.bbox_orig
            sc_cls = sc.class_name
            duplicate = False
            for sf in merged_findings:
                if sc_cls == sf["condition"] and compute_box_iou(sc_b, sf["bbox"]) > 0.5:
                    duplicate = True
                    break
            if not duplicate:
                merged_findings.append({
                    "condition": sc_cls,
                    "bbox": sc_b,
                    "polygon": [],
                    "has_mask": False,
                })
        t_det1 = time.perf_counter()
        detection_ms = (t_det1 - t_det0) * 1000.0
        
        # 3. FDI Detection & Solver
        t_fdi0 = time.perf_counter()
        fdi_res = fdi_engine.predict_teeth(img)
        pred_teeth = fdi_res.get("teeth", [])
        raw_props = [
            {"id": f"p_{i}", "bbox": t.bbox_orig, "confidence": t.confidence}
            for i, t in enumerate(pred_teeth)
        ]
        resolved_teeth = fdi_solver.solve(raw_props, image_width=orig_w, image_height=orig_h)
        t_fdi1 = time.perf_counter()
        fdi_ms = (t_fdi1 - t_fdi0) * 1000.0
        
        # 4. Overlay Rendering
        t_ov0 = time.perf_counter()
        overlay_img = render_overlay(img, merged_findings, resolved_teeth)
        t_ov1 = time.perf_counter()
        overlay_ms = (t_ov1 - t_ov0) * 1000.0
        
        total_pipeline_ms = (time.perf_counter() - t_start) * 1000.0
        
        rec = {
            "image": img_path.name,
            "dimensions": f"{orig_w}x{orig_h}",
            "preprocess_ms": round(preprocess_ms, 2),
            "detection_ms": round(detection_ms, 2),
            "fdi_ms": round(fdi_ms, 2),
            "overlay_ms": round(overlay_ms, 2),
            "total_ms": round(total_pipeline_ms, 2),
            "findings_count": len(merged_findings),
            "teeth_count": len(resolved_teeth)
        }
        per_image_results.append(rec)
        print(f"[{idx+1:02d}/10] {img_path.name:18s} ({orig_w:4d}x{orig_h:4d}) | Total: {total_pipeline_ms:6.2f} ms | Pre: {preprocess_ms:4.1f}ms | Det: {detection_ms:5.1f}ms | FDI: {fdi_ms:5.1f}ms | Overlay: {overlay_ms:4.1f}ms")
        
    totals = [r["total_ms"] for r in per_image_results]
    mean_ms = float(np.mean(totals))
    median_ms = float(np.median(totals))
    p95_ms = float(np.percentile(totals, 95))
    
    print("-" * 75)
    print("TASK 8 PIPELINE LATENCY SUMMARY (CPU-ONLY):")
    print(f"  Mean Latency:   {mean_ms:.2f} ms")
    print(f"  Median Latency: {median_ms:.2f} ms")
    print(f"  p95 Latency:    {p95_ms:.2f} ms")
    print("=" * 75)
    
    import json
    out_file = PROJECT_ROOT / "scratch" / "task8_pipeline_latency_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "mean_ms": round(mean_ms, 2),
            "median_ms": round(median_ms, 2),
            "p95_ms": round(p95_ms, 2),
            "per_image": per_image_results
        }, f, indent=2)
    print(f"Wrote latency results to {out_file}")

if __name__ == "__main__":
    benchmark_task8_pipeline()
