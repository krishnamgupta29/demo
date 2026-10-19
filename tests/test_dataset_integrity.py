"""Test suite verifying extracted DENTEX dataset manifest, polygon geometries, and split hygiene."""

import json
from pathlib import Path
import pytest
from backend.config import settings


def test_dataset_inventory_exists_and_valid():
  """Verify that docs/dataset_inventory.json exists and contains complete extraction metadata."""
  inventory_path = settings.PROJECT_ROOT / "docs/dataset_inventory.json"
  assert inventory_path.exists(), f"Inventory missing at {inventory_path}"

  with open(inventory_path, "r", encoding="utf-8") as f:
    inv = json.load(f)

  assert "extraction_manifests" in inv
  assert "annotation_analysis" in inv

  val_manifest = inv["extraction_manifests"]["validation"]
  train_manifest = inv["extraction_manifests"]["training"]

  # Validation set checks
  assert val_manifest["extracted_files"] == 51
  assert val_manifest["total_members"] == 55

  # Training set checks
  assert train_manifest["extracted_files"] == 3606
  assert train_manifest["total_members"] == 3615


def test_dentex_annotation_polygon_geometry_truthfulness():
  """Verify that DENTEX disease annotations contain authentic polygons (average ~12 vertices) without fake masks."""
  inventory_path = settings.PROJECT_ROOT / "docs/dataset_inventory.json"
  with open(inventory_path, "r", encoding="utf-8") as f:
    inv = json.load(f)

  disease_analysis = inv["annotation_analysis"]["quadrant_enumeration_disease"]
  assert disease_analysis["image_count"] == 705
  assert disease_analysis["annotation_count"] == 3529
  assert disease_analysis["orphan_annotations"] == 0
  assert disease_analysis["has_bboxes"] == 3529
  assert disease_analysis["has_segmentation_polygons"] == 3529
  assert disease_analysis["degenerate_polygons"] == 0

  # Polygon vertex statistics: range 4 to 34, avg ~12.0
  vertex_stats = disease_analysis["vertex_stats"]
  assert vertex_stats["min_vertices"] >= 3
  assert vertex_stats["max_vertices"] <= 100
  assert 10.0 <= vertex_stats["avg_vertices"] <= 15.0

  # Disease classes distribution
  dist = disease_analysis["class_distribution"]
  assert dist["disease_0"] == 604  # Impacted
  assert dist["disease_1"] == 2189  # Caries
  assert dist["disease_2"] == 158  # Periapical Lesion
  assert dist["disease_3"] == 578  # Deep Caries


def test_tooth_enumeration_polygon_geometry():
  """Verify tooth enumeration annotations contain authentic contour polygons."""
  inventory_path = settings.PROJECT_ROOT / "docs/dataset_inventory.json"
  with open(inventory_path, "r", encoding="utf-8") as f:
    inv = json.load(f)

  enum_analysis = inv["annotation_analysis"]["quadrant_enumeration"]
  assert enum_analysis["image_count"] == 634
  assert enum_analysis["annotation_count"] == 18095
  assert enum_analysis["orphan_annotations"] == 0
  assert enum_analysis["has_segmentation_polygons"] == 18095
  assert enum_analysis["degenerate_polygons"] == 0


def test_validation_set_isolation():
  """Verify that the original challenge validation set remains isolated (no annotation JSONs)."""
  val_dir = settings.PROJECT_ROOT / "datasets/dentex/raw/validation"
  if val_dir.exists():
    json_files = list(val_dir.glob("**/*.json"))
    assert len(json_files) == 0, "Validation set must not contain training labels (held-out challenge evaluation)"
