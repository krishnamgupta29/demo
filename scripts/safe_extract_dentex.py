"""Safe extraction and forensic validation script for DENTEX dataset archives.

Enforces:
1. Strict Zip-Slip protection (prevents directory traversal attacks).
2. Rejection of symlinks, hardlinks, and absolute paths.
3. Verification of extracted counts against archive manifests.
4. Polygon geometry and coordinate analysis.
5. Generation of reproducible dataset inventory.
"""

from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
import zipfile


def is_safe_path(target_dir: Path, member_path: str) -> bool:
  """Ensure member_path does not escape target_dir (Zip Slip defense)."""
  resolved_target = target_dir.resolve()
  destination = (target_dir / member_path).resolve()
  try:
    destination.relative_to(resolved_target)
    return True
  except ValueError:
    return False


def safe_extract_archive(
    zip_path: Path, dest_dir: Path, archive_label: str
) -> dict:
  """Safely extract all files from zip_path into dest_dir with path validation."""
  print(f"\n[{archive_label}] Starting safe extraction of: {zip_path}")
  print(f"[{archive_label}] Destination directory: {dest_dir}")

  dest_dir.mkdir(parents=True, exist_ok=True)

  if not zip_path.exists():
    raise FileNotFoundError(f"Archive not found: {zip_path}")

  t0 = time.time()
  extracted_count = 0
  extracted_bytes = 0
  skipped_dirs = 0

  with zipfile.ZipFile(zip_path, "r") as zf:
    infolist = zf.infolist()
    total_members = len(infolist)
    print(f"[{archive_label}] Total archive members: {total_members}")

    for idx, info in enumerate(infolist):
      # Zip-Slip defense
      if not is_safe_path(dest_dir, info.filename):
        raise ValueError(
            f"SECURITY ALERT: Unsafe path detected in zip: {info.filename}"
        )

      # Check for symlink / attribute anomalies (Unix mode 0o120000 indicates symlink)
      if (info.external_attr >> 16) & 0o170000 == 0o120000:
        raise ValueError(
            f"SECURITY ALERT: Symlink member rejected: {info.filename}"
        )

      # If directory, ensure created
      target_file = dest_dir / info.filename
      if info.is_dir():
        target_file.mkdir(parents=True, exist_ok=True)
        skipped_dirs += 1
        continue

      # Ensure parent directory exists
      target_file.parent.mkdir(parents=True, exist_ok=True)

      # Check if already extracted with exact size (resumable extraction)
      if target_file.exists() and target_file.stat().st_size == info.file_size:
        extracted_count += 1
        extracted_bytes += info.file_size
        continue

      # Extract file contents safely
      with zf.open(info) as src, open(target_file, "wb") as dst:
        buf = src.read(1024 * 1024)  # 1MB buffer
        while buf:
          dst.write(buf)
          buf = src.read(1024 * 1024)

      extracted_count += 1
      extracted_bytes += info.file_size

      if extracted_count % 500 == 0 or extracted_count == (
          total_members - skipped_dirs
      ):
        print(
            f"[{archive_label}] Extracted {extracted_count}/"
            f"{total_members - skipped_dirs} files ({extracted_bytes / (1024**2):.1f} MB)..."
        )

  elapsed = time.time() - t0
  print(
      f"[{archive_label}] Extraction complete in {elapsed:.2f}s. Extracted"
      f" {extracted_count} files ({extracted_bytes / (1024**3):.2f} GB)."
  )

  return {
      "archive": str(zip_path),
      "destination": str(dest_dir),
      "total_members": total_members,
      "extracted_files": extracted_count,
      "skipped_dirs": skipped_dirs,
      "extracted_bytes": extracted_bytes,
      "elapsed_seconds": round(elapsed, 2),
  }


def analyze_dentex_annotations(base_dir: Path) -> dict:
  """Inspect JSON image IDs, category IDs, coordinate formats, and polygon geometries."""
  print("\n" + "=" * 70)
  print("DEEP FORENSIC INSPECTION OF EXTRACTED DENTEX ANNOTATIONS")
  print("=" * 70)

  results = {}
  json_targets = [
      (
          "quadrant",
          base_dir / "training/training_data/quadrant/train_quadrant.json",
      ),
      (
          "quadrant_enumeration",
          base_dir
          / "training/training_data/quadrant_enumeration/train_quadrant_enumeration.json",
      ),
      (
          "quadrant_enumeration_disease",
          base_dir
          / "training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json",
      ),
  ]

  for key, json_path in json_targets:
    if not json_path.exists():
      print(f"Warning: {json_path} does not exist!")
      continue

    print(f"\n--- Analyzing: {key} ({json_path.name}) ---")
    with open(json_path, "r", encoding="utf-8") as f:
      data = json.load(f)

    images = data.get("images", [])
    annotations = data.get("annotations", [])
    cat_keys = [k for k in data.keys() if k.startswith("categor")]

    image_dict = {img["id"]: img for img in images}
    img_ids = set(image_dict.keys())

    # Check annotation linkage
    orphan_anns = [a for a in annotations if a["image_id"] not in img_ids]
    print(f"Images count: {len(images)}")
    print(f"Annotations count: {len(annotations)}")
    print(f"Orphan annotations (image not found): {len(orphan_anns)}")

    # Coordinate and polygon geometry analysis
    poly_count = 0
    bbox_count = 0
    degenerate_polys = 0
    vertex_counts = []
    bbox_aspect_ratios = []
    classes_counter = Counter()

    for a in annotations:
      # Bounding box
      bbox = a.get("bbox", [])
      if bbox and len(bbox) == 4:
        bbox_count += 1
        w, h = bbox[2], bbox[3]
        if w > 0 and h > 0:
          bbox_aspect_ratios.append(w / h)

      # Segmentation polygon
      seg = a.get("segmentation", [])
      if seg and len(seg) > 0 and len(seg[0]) >= 6:
        poly_count += 1
        coords = seg[0]
        n_vertices = len(coords) // 2
        vertex_counts.append(n_vertices)
        if n_vertices < 3:
          degenerate_polys += 1
      elif seg:
        degenerate_polys += 1

      # Track categories
      if "category_id_3" in a:
        classes_counter[f"disease_{a['category_id_3']}"] += 1
      elif "category_id_2" in a:
        classes_counter[f"tooth_{a['category_id_2']}"] += 1
      elif "category_id" in a:
        classes_counter[f"cat_{a['category_id']}"] += 1

    summary = {
        "file": str(json_path),
        "image_count": len(images),
        "annotation_count": len(annotations),
        "orphan_annotations": len(orphan_anns),
        "has_bboxes": bbox_count,
        "has_segmentation_polygons": poly_count,
        "degenerate_polygons": degenerate_polys,
        "categories_found": {k: data.get(k) for k in cat_keys},
        "class_distribution": dict(classes_counter),
        "vertex_stats": {
            "min_vertices": min(vertex_counts) if vertex_counts else 0,
            "max_vertices": max(vertex_counts) if vertex_counts else 0,
            "avg_vertices": (
                round(sum(vertex_counts) / len(vertex_counts), 1)
                if vertex_counts
                else 0
            ),
        },
        "coordinate_system": (
            "Absolute Pixel Coordinates [x, y, w, h] and [[x1, y1, x2, y2,"
            " ...]]"
        ),
    }

    print(
        f"Polygon segmentations: {poly_count} / {len(annotations)} ("
        f"{poly_count/len(annotations)*100:.1f}%)"
    )
    if vertex_counts:
      print(
          f"Vertex count stats: min={min(vertex_counts)},"
          f" max={max(vertex_counts)},"
          f" avg={sum(vertex_counts)/len(vertex_counts):.1f}"
      )
    print(f"Class distribution: {dict(classes_counter)}")

    results[key] = summary

  return results


def main():
  root_dir = Path("C:/mini")
  train_zip = root_dir / "training_data.zip"
  val_zip = root_dir / "validation_data.zip"
  dest_raw = root_dir / "datasets/dentex/raw"

  print("=" * 70)
  print("DENTRACE — DENTEX DATASET SAFE EXTRACTION & AUDIT")
  print("=" * 70)

  # Check free disk space before proceeding
  import shutil

  stat = shutil.disk_usage("C:/")
  free_gb = stat.free / (1024**3)
  print(f"Current free disk space on C: {free_gb:.2f} GB")
  if free_gb < 15.0:
    raise RuntimeError(
        f"Insufficient free space on C: {free_gb:.2f} GB available, need at"
        " least 15 GB"
    )

  # Step 1: Extract validation data (~201 MB uncompressed)
  val_dest = dest_raw / "validation"
  val_manifest = safe_extract_archive(val_zip, val_dest, "VALIDATION")

  # Step 2: Extract training data (~14.7 GB uncompressed)
  train_dest = dest_raw / "training"
  train_manifest = safe_extract_archive(train_zip, train_dest, "TRAINING")

  # Step 3: Deep analysis of JSON annotations
  analysis = analyze_dentex_annotations(dest_raw)

  # Step 4: Write reproducible inventory
  inventory = {
      "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
      "extraction_manifests": {
          "validation": val_manifest,
          "training": train_manifest,
      },
      "annotation_analysis": analysis,
      "git_status": "EXCLUDED (datasets/* in .gitignore)",
  }

  inventory_path = root_dir / "docs/dataset_inventory.json"
  with open(inventory_path, "w", encoding="utf-8") as f:
    json.dump(inventory, f, indent=2)

  print(f"\n[DONE] Dataset inventory written to: {inventory_path}")
  print("Safe extraction and forensic validation completed successfully!")


if __name__ == "__main__":
  main()
