import os
import sys
from pathlib import Path
import time
import numpy as np
from PIL import Image
import onnx
import onnxruntime as ort
from onnxruntime.quantization import (
    quantize_static,
    CalibrationDataReader,
    QuantType,
    QuantFormat,
    CalibrationMethod,
)

# 1. Calibration Data Reader
class DentexTrainCalibrationDataReader(CalibrationDataReader):
    def __init__(self, image_dir: Path, num_images: int = 200, input_size: int = 640):
        self.image_paths = sorted(list(image_dir.glob("*.png")))[:num_images]
        self.input_size = input_size
        self.enum_data = iter(self.image_paths)
        print(f"[Calibration] Initialized with {len(self.image_paths)} training images from {image_dir}")

    def _preprocess(self, img_path: Path) -> np.ndarray:
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        scale = min(self.input_size / w, self.input_size / h)
        nw, nh = int(round(w * scale)), int(round(h * scale))
        img_resized = img.resize((nw, nh), Image.Resampling.BILINEAR)

        pad_w = self.input_size - nw
        pad_h = self.input_size - nh
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left

        canvas = Image.new("RGB", (self.input_size, self.input_size), (114, 114, 114))
        canvas.paste(img_resized, (left, top))

        arr = np.array(canvas, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))  # (3, H, W)
        arr = np.expand_dims(arr, axis=0)  # (1, 3, H, W)
        return arr

    def get_next(self):
        try:
            p = next(self.enum_data)
            tensor = self._preprocess(p)
            return {"images": tensor}
        except StopIteration:
            return None

    def rewind(self):
        self.enum_data = iter(self.image_paths)


def build_static_qdq():
    model_fp32 = Path("ml/models/checkpoints/dentex_yolov8n_seg_best.onnx")
    model_opset17 = Path("ml/models/checkpoints/dentex_yolov8n_seg_best_opset17.onnx")
    model_int8 = Path("ml/models/checkpoints/dentex_yolov8n_seg_static_qdq_int8.onnx")
    train_dir = Path("ml/datasets/dentex/yolo_seg/images/train")

    from onnx import version_converter
    onnx_proto = onnx.load(str(model_fp32))
    if onnx_proto.opset_import[0].version < 13:
        print("Converting opset from 12 to 17...")
        onnx_proto = version_converter.convert_version(onnx_proto, 17)
        onnx.save(onnx_proto, str(model_opset17))
        model_to_quantize = model_opset17
    else:
        model_to_quantize = model_fp32

    excluded_nodes = []
    for node in onnx_proto.graph.node:
        # Exclude all segmentation head, proto-mask, and detection head nodes
        if "model.22" in node.name or "proto" in node.name.lower() or "cv4" in node.name.lower():
            excluded_nodes.append(node.name)

    print(f"Total graph nodes: {len(onnx_proto.graph.node)}")
    print(f"Nodes to exclude from quantization: {len(excluded_nodes)}")

    reader = DentexTrainCalibrationDataReader(train_dir, num_images=200)

    print(f"Starting static QDQ quantization -> {model_int8}...")
    t0 = time.time()
    quantize_static(
        model_input=str(model_to_quantize),
        model_output=str(model_int8),
        calibration_data_reader=reader,
        quant_format=QuantFormat.QDQ,
        per_channel=True,
        weight_type=QuantType.QInt8,
        activation_type=QuantType.QUInt8,
        nodes_to_exclude=excluded_nodes,
        calibrate_method=CalibrationMethod.MinMax,
    )
    t1 = time.time()
    print(f"Static quantization complete in {t1 - t0:.2f}s! Output size: {model_int8.stat().st_size / 1e6:.2f} MB")

if __name__ == "__main__":
    build_static_qdq()
