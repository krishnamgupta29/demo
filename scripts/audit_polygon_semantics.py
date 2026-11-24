"""
Audit DENTEX polygon semantics:
Compare tooth instance polygons vs disease polygons to verify if disease polygons
trace the whole abnormal tooth or isolated lesions.
"""
import json
import zipfile
import numpy as np

zip_path = 'training_data.zip'

with zipfile.ZipFile(zip_path, 'r') as zf:
    # 1. Load quadrant-enumeration-disease
    with zf.open('training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json') as f:
        dis_data = json.load(f)
    # 2. Load quadrant-enumeration
    with zf.open('training_data/quadrant_enumeration/train_quadrant_enumeration.json') as f:
        tooth_data = json.load(f)

print("Categories 3 (Disease):", dis_data.get('categories_3'))

dis_anns = dis_data.get('annotations', [])
tooth_anns = tooth_data.get('annotations', [])

print(f"Total disease annotations: {len(dis_anns)}")
print(f"Total tooth enumeration annotations: {len(tooth_anns)}")

# Analyze polygon bounding boxes by disease category
# cat 0: Impacted, cat 1: Caries, cat 2: Periapical Lesion, cat 3: Deep Caries
cat_stats = {0: [], 1: [], 2: [], 3: []}
for ann in dis_anns:
    cat = ann.get('category_id_3')
    bbox = ann.get('bbox', [])  # [x, y, w, h]
    seg = ann.get('segmentation', [[]])[0]
    if len(bbox) == 4 and cat in cat_stats:
        cat_stats[cat].append({
            'w': bbox[2],
            'h': bbox[3],
            'area': bbox[2] * bbox[3],
            'num_pts': len(seg) // 2
        })

cat_names = {0: 'Impacted', 1: 'Caries', 2: 'Periapical Lesion', 3: 'Deep Caries'}
for cat, stats in cat_stats.items():
    if stats:
        avg_w = np.mean([s['w'] for s in stats])
        avg_h = np.mean([s['h'] for s in stats])
        avg_pts = np.mean([s['num_pts'] for s in stats])
        print(f"\nCategory {cat} ({cat_names[cat]}): N={len(stats)}")
        print(f"  Mean width: {avg_w:.1f} px, Mean height: {avg_h:.1f} px, Mean vertices: {avg_pts:.1f}")

# Tooth enumeration baseline stats
tooth_w = [a['bbox'][2] for a in tooth_anns if len(a.get('bbox', [])) == 4]
tooth_h = [a['bbox'][3] for a in tooth_anns if len(a.get('bbox', [])) == 4]
tooth_pts = [len(a.get('segmentation', [[]])[0]) // 2 for a in tooth_anns]
print(f"\nAll Tooth Enumeration Annotations: N={len(tooth_anns)}")
print(f"  Mean width: {np.mean(tooth_w):.1f} px, Mean height: {np.mean(tooth_h):.1f} px, Mean vertices: {np.mean(tooth_pts):.1f}")
