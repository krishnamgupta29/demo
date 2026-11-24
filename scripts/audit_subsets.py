"""Comprehensive audit of all 3 DENTEX training annotation JSON files."""
import json
from collections import Counter
from pathlib import Path

raw_dir = Path("datasets/dentex/raw/training/training_data")

subsets = [
    ("quadrant", "train_quadrant.json"),
    ("quadrant_enumeration", "train_quadrant_enumeration.json"),
    ("quadrant-enumeration-disease", "train_quadrant_enumeration_disease.json"),
]

for sub, jname in subsets:
    json_file = raw_dir / sub / jname
    if not json_file.exists():
        print(f"File not found: {json_file}")
        continue
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 70)
    print(f"SUBSET: {sub} ({jname})")
    print(f"Total Images: {len(data.get('images', []))}")
    print(f"Total Annotations: {len(data.get('annotations', []))}")

    cat_keys = [k for k in sorted(data.keys()) if "categor" in k]
    for ck in cat_keys:
        print(f"  {ck}: {data[ck]}")

    anns = data.get("annotations", [])
    if anns:
        sample = anns[0]
        ann_cat_keys = [k for k in sample.keys() if "cat" in k]
        print(f"  Annotation category keys: {ann_cat_keys}")
        for ack in ann_cat_keys:
            counts = Counter(a.get(ack) for a in anns)
            print(f"    {ack} counts: {dict(sorted(counts.items()))}")
