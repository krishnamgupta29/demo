"""Dataset utilities for DENTEX ingestion, COCO parsing, polygon validation, and reproducible split generation."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Optional
import numpy as np

from backend.config import settings


@dataclass
class AnomalyGroundTruth:
    annotation_id: int
    image_id: int
    category_id_raw: int
    pathology_class: str
    fdi_number: Optional[int]
    quadrant: Optional[int]
    tooth_number: Optional[int]
    bbox_xyxy: list[float]  # [x1, y1, x2, y2]
    area: float
    is_polygon: bool
    polygon_vertices: list[list[float]] = field(default_factory=list)


@dataclass
class DatasetImageInfo:
    image_id: int
    file_name: str
    file_path: Path
    width: int
    height: int
    annotations: list[AnomalyGroundTruth] = field(default_factory=list)


class DENTEXDatasetReader:
    """Reads, parses, and validates DENTEX COCO-style disease and enumeration annotations."""

    DENTEX_DISEASE_JSON = (
        settings.PROJECT_ROOT
        / "datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json"
    )
    DENTEX_DISEASE_IMG_DIR = (
        settings.PROJECT_ROOT
        / "datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/xrays"
    )

    CATEGORY_MAP = {
        0: "impacted_tooth",       # 'Impacted' in DENTEX
        1: "caries",               # 'Caries' in DENTEX
        2: "periapical_lesion",    # 'Periapical Lesion' in DENTEX
        3: "caries",               # 'Deep Caries' in DENTEX (grouped with caries for 3-class detection)
    }

    UNSUPPORTED_CLASSES = [
        "alveolar_bone_loss",
        "root_canal_treatment",
        "treated_tooth_with_radiolucency",
    ]

    def __init__(self, annotation_path: Optional[Path] = None, image_dir: Optional[Path] = None):
        self.annotation_path = annotation_path or self.DENTEX_DISEASE_JSON
        self.image_dir = image_dir or self.DENTEX_DISEASE_IMG_DIR
        self.images: dict[int, DatasetImageInfo] = {}
        self.loaded = False

    def load(self) -> dict[int, DatasetImageInfo]:
        """Parse COCO JSON, validate polygon geometry and bounding boxes."""
        if not self.annotation_path.exists():
            raise FileNotFoundError(f"DENTEX annotation file not found: {self.annotation_path}")

        with open(self.annotation_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse images
        for img in data.get("images", []):
            img_id = img["id"]
            fname = img["file_name"]
            img_path = self.image_dir / fname
            self.images[img_id] = DatasetImageInfo(
                image_id=img_id,
                file_name=fname,
                file_path=img_path,
                width=img["width"],
                height=img["height"],
                annotations=[],
            )

        # Parse annotations
        for anno in data.get("annotations", []):
            img_id = anno["image_id"]
            if img_id not in self.images:
                continue

            # In DENTEX quadrant-enumeration-disease:
            # category_id_1: quadrant (0..3)
            # category_id_2: tooth (0..7)
            # category_id_3: disease (0..3)
            cat_id_3 = anno.get("category_id_3", anno.get("category_id", 0))
            pathology_class = self.CATEGORY_MAP.get(cat_id_3, "caries")

            q_raw = anno.get("category_id_1")
            t_raw = anno.get("category_id_2")
            fdi_num = None
            if q_raw is not None and t_raw is not None:
                q = int(q_raw) + 1  # 1..4
                t = int(t_raw) + 1  # 1..8
                fdi_num = q * 10 + t

            # COCO bbox: [x, y, w, h]
            bbox = anno.get("bbox", [0, 0, 0, 0])
            x1 = float(bbox[0])
            y1 = float(bbox[1])
            x2 = float(bbox[0] + bbox[2])
            y2 = float(bbox[1] + bbox[3])
            area = float(anno.get("area", bbox[2] * bbox[3]))

            # Validate polygon segmentation
            seg = anno.get("segmentation", [])
            polygon_pts: list[list[float]] = []
            is_poly = False
            if seg and isinstance(seg, list) and len(seg) > 0:
                first_seg = seg[0]
                if isinstance(first_seg, list) and len(first_seg) >= 6:
                    pts = [[float(first_seg[i]), float(first_seg[i + 1])] for i in range(0, len(first_seg) - 1, 2)]
                    if len(pts) >= 3:
                        polygon_pts = pts
                        is_poly = True

            gt = AnomalyGroundTruth(
                annotation_id=anno.get("id", 0),
                image_id=img_id,
                category_id_raw=cat_id_3,
                pathology_class=pathology_class,
                fdi_number=fdi_num,
                quadrant=(int(q_raw) + 1) if q_raw is not None else None,
                tooth_number=(int(t_raw) + 1) if t_raw is not None else None,
                bbox_xyxy=[round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                area=round(area, 2),
                is_polygon=is_poly,
                polygon_vertices=polygon_pts,
            )
            self.images[img_id].annotations.append(gt)

        self.loaded = True
        return self.images

    def create_reproducible_split(
        self,
        eval_ratio: float = 0.20,
        random_seed: int = 42,
    ) -> tuple[list[int], list[int]]:
        """Generate deterministic train and dev evaluation splits.

        Returns:
            (train_image_ids, eval_image_ids)
        """
        if not self.loaded:
            self.load()

        sorted_ids = sorted(self.images.keys())
        rng = np.random.RandomState(random_seed)
        shuffled = sorted_ids.copy()
        rng.shuffle(shuffled)

        n_eval = int(round(len(shuffled) * eval_ratio))
        eval_ids = sorted(shuffled[:n_eval])
        train_ids = sorted(shuffled[n_eval:])

        return train_ids, eval_ids

    def get_class_imbalance_report(self) -> dict[str, Any]:
        """Compute frequency breakdown of ground truth pathology classes."""
        if not self.loaded:
            self.load()

        counts: dict[str, int] = {
            "caries": 0,
            "periapical_lesion": 0,
            "impacted_tooth": 0,
        }
        raw_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}

        for img in self.images.values():
            for a in img.annotations:
                counts[a.pathology_class] = counts.get(a.pathology_class, 0) + 1
                raw_counts[a.category_id_raw] = raw_counts.get(a.category_id_raw, 0) + 1

        total_annotations = sum(counts.values())
        return {
            "total_images": len(self.images),
            "total_annotations": total_annotations,
            "class_counts_3_class": counts,
            "class_percentages": {
                k: round((v / total_annotations) * 100.0, 2) if total_annotations > 0 else 0.0
                for k, v in counts.items()
            },
            "raw_dentex_categories": {
                "0_impacted": raw_counts[0],
                "1_caries": raw_counts[1],
                "2_periapical_lesion": raw_counts[2],
                "3_deep_caries": raw_counts[3],
            },
            "unsupported_in_dentex": self.UNSUPPORTED_CLASSES,
        }

    def generate_training_config_template(self) -> dict[str, Any]:
        """Generate documented training configuration template for future Level 3 fine-tuning."""
        return {
            "project_name": "DENTRACE",
            "phase": "Level 3 Future Fine-Tuning (Documented Template Only)",
            "base_checkpoint": "liodon-ai/dental-panoramic-detector",
            "task": "detect",
            "imgsz": 640,
            "batch_size": 8,  # Constrained by RTX 2050 4 GB VRAM
            "epochs": 50,
            "patience": 15,
            "optimizer": "AdamW",
            "learning_rate": 0.001,
            "weight_decay": 0.0005,
            "classes": ["caries", "periapical_lesion", "impacted_tooth"],
            "hardware_constraints": {
                "max_vram_gb": 4.0,
                "host_gpu": "NVIDIA GeForce RTX 2050",
                "recommended_offload": "Google Colab T4 for heavy epochs",
            },
            "status": "NOT_EXECUTED_PENDING_LEVEL_3_APPROVAL",
        }
