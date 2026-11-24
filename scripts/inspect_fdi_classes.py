import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import onnxruntime as ort
import numpy as np
from PIL import Image
from backend.ml.preprocessor import ImagePreprocessor

with open("datasets/dentex/raw/training/training_data/quadrant_enumeration/train_quadrant_enumeration.json") as f:
    t_data = json.load(f)

img_info = next(im for im in t_data["images"] if im["file_name"] == "train_0.png")
gt_anns = [a for a in t_data["annotations"] if a["image_id"] == img_info["id"]]

img_path = "datasets/dentex/raw/training/training_data/quadrant_enumeration/xrays/train_0.png"
img = Image.open(img_path).convert("RGB")
w, h = img.size

sess = ort.InferenceSession("models/checkpoints/dental_fdi.onnx", providers=["CPUExecutionProvider"])
tensor, meta = ImagePreprocessor.letterbox(img, target_size=640)
outputs = sess.run(None, {sess.get_inputs()[0].name: tensor})
proposals = outputs[0][0]
coords = proposals[:, :4]
scores = proposals[:, 4:]
max_s = np.max(scores, axis=1)
classes = np.argmax(scores, axis=1)

mask = max_s >= 0.35
cand_coords = coords[mask]
cand_scores = max_s[mask]
cand_classes = classes[mask]

cand_boxes = []
for c in cand_coords:
    cx, cy, bw, bh = c
    x1 = (cx - bw / 2.0) * meta.target_size
    y1 = (cy - bh / 2.0) * meta.target_size
    x2 = (cx + bw / 2.0) * meta.target_size
    y2 = (cy + bh / 2.0) * meta.target_size
    cand_boxes.append(ImagePreprocessor.unletterbox_box([x1, y1, x2, y2], meta))

print(f"Total GT teeth: {len(gt_anns)}")
print(f"Total candidates above 0.35: {len(cand_boxes)}")

matched = []
for ga in gt_anns:
    gb = ga["bbox"]
    g_box = [gb[0], gb[1], gb[0] + gb[2], gb[1] + gb[3]]
    gt_fdi = (ga["category_id_1"] + 1) * 10 + (ga["category_id_2"] + 1)

    best_iou = 0
    best_idx = None
    for i, cb in enumerate(cand_boxes):
        xx1 = max(g_box[0], cb[0])
        yy1 = max(g_box[1], cb[1])
        xx2 = min(g_box[2], cb[2])
        yy2 = min(g_box[3], cb[3])
        inter = max(0.0, xx2 - xx1) * max(0.0, yy2 - yy1)
        union = (g_box[2] - g_box[0]) * (g_box[3] - g_box[1]) + (cb[2] - cb[0]) * (cb[3] - cb[1]) - inter
        iou = inter / union if union > 0 else 0
        if iou > best_iou:
            best_iou = iou
            best_idx = i

    if best_iou > 0.5:
        matched.append({
            "gt_fdi": gt_fdi,
            "pred_cls": int(cand_classes[best_idx]),
            "score": float(cand_scores[best_idx]),
            "iou": round(best_iou, 2)
        })

matched.sort(key=lambda m: m["gt_fdi"])
print("\n--- GT FDI vs Predicted Raw Class Index ---")
for m in matched:
    print(f"GT FDI: {m['gt_fdi']} -> Pred Class: {m['pred_cls']}, Score: {m['score']:.2f}, IoU: {m['iou']}")
