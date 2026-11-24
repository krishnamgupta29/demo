"""
Generate YOLOv8-Seg 4-Class Dataset from DENTEX quadrant-enumeration-disease.

Preserves 4 separate classes:
0: impacted_tooth
1: caries
2: periapical_lesion
3: deep_caries

Strictly adheres to:
- Random seed = 42
- 80% train (564 images), 20% val (141 images)
- Normalization of polygon coordinates to [0, 1]
- Abnormal-tooth instance segmentation labeling
"""

import json
import os
import shutil
import zipfile
from pathlib import Path
import numpy as np


def prepare_yolo_seg_dataset(output_dir: str = "datasets/dentex/yolo_seg"):
    out_path = Path(output_dir)
    images_train = out_path / "images" / "train"
    images_val = out_path / "images" / "val"
    labels_train = out_path / "labels" / "train"
    labels_val = out_path / "labels" / "val"

    for p in [images_train, images_val, labels_train, labels_val]:
        p.mkdir(parents=True, exist_ok=True)

    print(f"Reading DENTEX annotations from training_data.zip...")
    with zipfile.ZipFile("training_data.zip", "r") as zf:
        with zf.open("training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json") as f:
            data = json.load(f)

    images = {img["id"]: img for img in data["images"]}
    anns_by_img = {}
    for a in data["annotations"]:
        anns_by_img.setdefault(a["image_id"], []).append(a)

    sorted_img_ids = sorted(images.keys())
    rng = np.random.RandomState(42)
    shuffled = sorted_img_ids.copy()
    rng.shuffle(shuffled)

    n_val = int(round(len(shuffled) * 0.20))
    val_ids = set(shuffled[:n_val])
    train_ids = set(shuffled[n_val:])

    print(f"Total images: {len(sorted_img_ids)}. Train: {len(train_ids)}, Val: {len(val_ids)}")

    # Extract images from zip if not already on disk
    with zipfile.ZipFile("training_data.zip", "r") as zf:
        zip_namelist = set(zf.namelist())
        for img_id, img_info in images.items():
            fname = img_info["file_name"]
            is_val = img_id in val_ids
            dest_img_dir = images_val if is_val else images_train
            dest_lbl_dir = labels_val if is_val else labels_train

            dest_img_file = dest_img_dir / fname
            dest_lbl_file = dest_lbl_dir / f"{Path(fname).stem}.txt"

            # 1. Extract image strictly from quadrant-enumeration-disease/xrays
            z_candidate = f"training_data/quadrant-enumeration-disease/xrays/{fname}"
            if z_candidate in zip_namelist:
                with zf.open(z_candidate) as source, open(dest_img_file, "wb") as target:
                    shutil.copyfileobj(source, target)
            else:
                raise FileNotFoundError(f"Missing image {z_candidate} in training_data.zip")

            # 2. Write polygon labels
            w = img_info["width"]
            h = img_info["height"]
            img_anns = anns_by_img.get(img_id, [])

            lines = []
            for a in img_anns:
                cat3 = a.get("category_id_3")  # 0: Impacted, 1: Caries, 2: Periapical, 3: Deep Caries
                seg = a.get("segmentation", [[]])[0]
                if not seg or len(seg) < 6:
                    continue

                # Normalize coordinates
                coords_norm = []
                for i in range(0, len(seg), 2):
                    px = max(0.0, min(1.0, seg[i] / w))
                    py = max(0.0, min(1.0, seg[i + 1] / h))
                    coords_norm.extend([f"{px:.6f}", f"{py:.6f}"])

                line = f"{cat3} " + " ".join(coords_norm)
                lines.append(line)

            with open(dest_lbl_file, "w", encoding="utf-8") as f_lbl:
                f_lbl.write("\n".join(lines) + ("\n" if lines else ""))

    # 3. Create data.yaml
    yaml_content = f"""# DENTEX 4-Class Abnormal-Tooth Instance Segmentation Dataset
path: {out_path.resolve().as_posix()}
train: images/train
val: images/val

names:
  0: impacted_tooth
  1: caries
  2: periapical_lesion
  3: deep_caries

nc: 4
description: "DENTEX 4-Class abnormal-tooth instance segmentation (crown-to-root whole abnormal tooth contours)."
"""
    yaml_path = out_path / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f_yaml:
        f_yaml.write(yaml_content)

    print(f"Dataset preparation complete! data.yaml written to {yaml_path}")


if __name__ == "__main__":
    prepare_yolo_seg_dataset()
