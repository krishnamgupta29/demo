"""
Targeted Numerical Parity Comparison between 8024.pt and 8024.onnx.
"""
import json
import time
import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ultralytics import YOLO
from backend.ml.preprocessor import ImagePreprocessor

# 1. PyTorch Forward Pass
print("1. Running PyTorch Forward Pass on CUDA...")
pt_model = YOLO("models/checkpoints/8024.pt")
img_path = "datasets/dentex/raw/training/training_data/quadrant/xrays/train_0.png"
img = Image.open(img_path).convert("RGB")

# Warmup + run
_ = pt_model.predict(img, conf=0.25, device="cuda:0", verbose=False)
t0 = time.time()
pt_res = pt_model.predict(img, conf=0.25, device="cuda:0", verbose=False)[0]
pt_warm_ms = (time.time() - t0) * 1000.0

pt_boxes = pt_res.boxes.xyxy.cpu().numpy()  # [N, 4]
pt_scores = pt_res.boxes.conf.cpu().numpy()  # [N]
pt_classes = pt_res.boxes.cls.cpu().numpy().astype(int)  # [N]
pt_masks = pt_res.masks.data.cpu().numpy() if pt_res.masks is not None else None

print(f"PyTorch Warm Latency: {pt_warm_ms:.2f} ms")
print(f"PyTorch Boxes ({len(pt_boxes)}):")
for i in range(len(pt_boxes)):
    print(f"  [{i}] Class: {pt_classes[i]}, Conf: {pt_scores[i]:.4f}, Box: {np.round(pt_boxes[i], 1)}")

# 2. ONNX Forward Pass
print("\n2. Running ONNX Forward Pass on CPU...")
sess = ort.InferenceSession("models/checkpoints/8024.onnx", providers=["CPUExecutionProvider"])
tensor, meta = ImagePreprocessor.letterbox(img, target_size=640)

t1 = time.time()
onnx_outs = sess.run(None, {sess.get_inputs()[0].name: tensor})
onnx_ms = (time.time() - t1) * 1000.0

raw_out0 = onnx_outs[0][0]  # [44, 8400]
preds = raw_out0.T          # [8400, 44]
boxes_xywh = preds[:, :4]
scores_all = preds[:, 4:12] # 8 classes

max_scores = np.max(scores_all, axis=1)
argmax_classes = np.argmax(scores_all, axis=1)

mask = max_scores >= 0.25
c_xywh = boxes_xywh[mask]
c_scores = max_scores[mask]
c_classes = argmax_classes[mask]

# Convert to xyxy 640x640 space
c_x1 = c_xywh[:, 0] - c_xywh[:, 2] / 2.0
c_y1 = c_xywh[:, 1] - c_xywh[:, 3] / 2.0
c_x2 = c_xywh[:, 0] + c_xywh[:, 2] / 2.0
c_y2 = c_xywh[:, 1] + c_xywh[:, 3] / 2.0
c_xyxy_lb = np.stack([c_x1, c_y1, c_x2, c_y2], axis=1)

# NMS
from torchvision.ops import batched_nms
keep = batched_nms(torch.tensor(c_xyxy_lb), torch.tensor(c_scores), torch.tensor(c_classes), iou_threshold=0.70).numpy()

onnx_boxes_lb = c_xyxy_lb[keep]
onnx_scores = c_scores[keep]
onnx_classes = c_classes[keep]

# Unletterbox
onnx_boxes_orig = np.array([ImagePreprocessor.unletterbox_box(b, meta) for b in onnx_boxes_lb])

print(f"ONNX Latency: {onnx_ms:.2f} ms")
print(f"ONNX Boxes ({len(onnx_boxes_orig)}):")
for j in range(len(onnx_boxes_orig)):
    print(f"  [{j}] Class: {onnx_classes[j]}, Conf: {onnx_scores[j]:.4f}, Box: {np.round(onnx_boxes_orig[j], 1)}")

# 3. Match and calculate parity metrics
matched_diffs = []
score_diffs = []
class_agreements = []

for i in range(len(pt_boxes)):
    pb = pt_boxes[i]
    best_iou = 0.0
    best_j = None
    for j in range(len(onnx_boxes_orig)):
        ob = onnx_boxes_orig[j]
        xx1 = max(pb[0], ob[0])
        yy1 = max(pb[1], ob[1])
        xx2 = min(pb[2], ob[2])
        yy2 = min(pb[3], ob[3])
        inter = max(0.0, xx2 - xx1) * max(0.0, yy2 - yy1)
        union = (pb[2] - pb[0]) * (pb[3] - pb[1]) + (ob[2] - ob[0]) * (ob[3] - ob[1]) - inter
        iou = inter / union if union > 0 else 0
        if iou > best_iou:
            best_iou = iou
            best_j = j
    if best_j is not None and best_iou > 0.50:
        coord_d = np.max(np.abs(pb - onnx_boxes_orig[best_j]))
        score_d = abs(pt_scores[i] - onnx_scores[best_j])
        cls_agree = (pt_classes[i] == onnx_classes[best_j])
        matched_diffs.append(coord_d)
        score_diffs.append(score_d)
        class_agreements.append(cls_agree)
        print(f"\nMatch PT[{i}] <-> ONNX[{best_j}]:")
        print(f"  IoU: {best_iou:.4f}")
        print(f"  Max Coord Diff: {coord_d:.4f} px")
        print(f"  Score Diff:     {score_d:.6f}")
        print(f"  Class Match:    {cls_agree} (PT:{pt_classes[i]} vs ONNX:{onnx_classes[best_j]})")

results = {
    "pytorch_warm_latency_ms": round(pt_warm_ms, 2),
    "onnx_cpu_latency_ms": round(onnx_ms, 2),
    "matched_instances": len(matched_diffs),
    "total_pt_instances": len(pt_boxes),
    "total_onnx_instances": len(onnx_boxes_orig),
    "max_coord_diff_px": round(float(np.max(matched_diffs)), 4) if matched_diffs else 0.0,
    "mean_coord_diff_px": round(float(np.mean(matched_diffs)), 4) if matched_diffs else 0.0,
    "max_score_diff": round(float(np.max(score_diffs)), 6) if score_diffs else 0.0,
    "class_agreement_pct": round(float(np.mean(class_agreements)) * 100.0, 2) if class_agreements else 0.0,
}

print("\n--- FINAL PARITY SUMMARY ---")
print(json.dumps(results, indent=2))

with open("docs/LEVEL_3_ONNX_PARITY.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
