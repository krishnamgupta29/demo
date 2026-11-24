from PIL import Image
import numpy as np
import onnxruntime as ort
import time

def nms(boxes, scores, iou_thresh):
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= iou_thresh)[0]
        order = order[inds + 1]
    return keep

def main():
    img_path = "C:/mini/datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/xrays/train_0.png"
    img = Image.open(img_path).convert("RGB")
    orig_w, orig_h = img.size
    target_size = 640
    scale = min(target_size / orig_w, target_size / orig_h)
    nw, nh = int(round(orig_w * scale)), int(round(orig_h * scale))
    pad_x = (target_size - nw) // 2
    pad_y = (target_size - nh) // 2
    resized = img.resize((nw, nh), Image.Resampling.BILINEAR)
    letterboxed = Image.new("RGB", (target_size, target_size), (114, 114, 114))
    letterboxed.paste(resized, (pad_x, pad_y))

    tensor = np.expand_dims(np.transpose(np.array(letterboxed, dtype=np.float32) / 255.0, (2, 0, 1)), 0)

    sess = ort.InferenceSession("C:/mini/models/checkpoints/best.onnx", providers=["CPUExecutionProvider"])

    # Warmup
    sess.run(None, {"images": tensor})

    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        out = sess.run(None, {"images": tensor})[0]
        times.append(time.perf_counter() - t0)

    print(f"Image: {img_path} ({orig_w}x{orig_h})")
    print(f"CPU Latency (10 runs): Mean={np.mean(times)*1000:.2f}ms, P50={np.median(times)*1000:.2f}ms, Min={np.min(times)*1000:.2f}ms, Max={np.max(times)*1000:.2f}ms")

    preds = np.transpose(out[0], (1, 0))  # (8400, 7)
    boxes_xywh = preds[:, :4]
    scores = preds[:, 4:]

    class_names = ["caries", "periapical_lesion", "impacted_tooth"]
    conf_thresh = 0.25
    iou_thresh = 0.35

    all_detections = []
    for cls_id in range(3):
        cls_scores = scores[:, cls_id]
        mask = cls_scores >= conf_thresh
        if not np.any(mask):
            continue
        cls_boxes = boxes_xywh[mask]
        cls_scores = cls_scores[mask]
        
        x1 = cls_boxes[:, 0] - cls_boxes[:, 2] / 2
        y1 = cls_boxes[:, 1] - cls_boxes[:, 3] / 2
        x2 = cls_boxes[:, 0] + cls_boxes[:, 2] / 2
        y2 = cls_boxes[:, 1] + cls_boxes[:, 3] / 2
        xyxy = np.column_stack([x1, y1, x2, y2])
        
        keep = nms(xyxy, cls_scores, iou_thresh)
        for idx in keep:
            b = xyxy[idx]
            ox1 = max(0.0, min(float(orig_w), float((b[0] - pad_x) / scale)))
            oy1 = max(0.0, min(float(orig_h), float((b[1] - pad_y) / scale)))
            ox2 = max(0.0, min(float(orig_w), float((b[2] - pad_x) / scale)))
            oy2 = max(0.0, min(float(orig_h), float((b[3] - pad_y) / scale)))
            all_detections.append({
                "class_id": cls_id,
                "class_name": class_names[cls_id],
                "confidence": float(cls_scores[idx]),
                "box_orig": [round(ox1, 1), round(oy1, 1), round(ox2, 1), round(oy2, 1)],
            })

    print(f"Total Detections: {len(all_detections)}")
    for d in all_detections:
        print(f"  [{d['class_name'].upper()}] Conf: {d['confidence']:.3f}, BBox: {d['box_orig']}")

if __name__ == "__main__":
    main()
