"""
Prototype and evaluation of Topological FDI Solver against DENTEX tooth enumeration ground truth.
"""
import zipfile
import json
import numpy as np

def evaluate_fdi_solver_on_ground_truth():
    with zipfile.ZipFile('training_data.zip') as zf:
        with zf.open('training_data/quadrant_enumeration/train_quadrant_enumeration.json') as f:
            data = json.load(f)

    images = {img['id']: img for img in data['images']}
    anns_by_img = {}
    for a in data['annotations']:
        anns_by_img.setdefault(a['image_id'], []).append(a)

    print(f"Total images with tooth annotations: {len(anns_by_img)}")

    # Let's test on the first 30 images
    test_img_ids = list(anns_by_img.keys())[:30]

    correct_quadrants = 0
    total_teeth = 0
    correct_fdi = 0

    for img_id in test_img_ids:
        img_info = images[img_id]
        w, h = img_info['width'], img_info['height']
        gt_anns = anns_by_img[img_id]

        # Extract bboxes and GT FDI
        teeth_proposals = []
        for a in gt_anns:
            fdi_gt = (a['category_id_1'] + 1) * 10 + (a['category_id_2'] + 1)
            bbox = a['bbox'] # [x, y, bw, bh]
            teeth_proposals.append({
                'bbox': bbox,
                'cx': bbox[0] + bbox[2] / 2.0,
                'cy': bbox[1] + bbox[3] / 2.0,
                'gt_fdi': fdi_gt,
                'gt_q': a['category_id_1'] + 1,
                'gt_t': a['category_id_2'] + 1,
            })

        total_teeth += len(teeth_proposals)

        # 1. Separate jaws: Maxilla (upper) vs Mandible (lower)
        # We can use k-means or median cy
        cys = [t['cy'] for t in teeth_proposals]
        median_cy = np.median(cys)
        
        # Refine jaw separation: maxilla teeth have cy < split, mandible cy >= split
        upper_teeth = [t for t in teeth_proposals if t['cy'] < median_cy]
        lower_teeth = [t for t in teeth_proposals if t['cy'] >= median_cy]

        # 2. Determine midline for upper and lower
        # Midline is near w / 2, or refined by center of incisors
        midline_x = w / 2.0

        for t in upper_teeth:
            pred_q = 1 if t['cx'] < midline_x else 2
            if pred_q == t['gt_q']:
                correct_quadrants += 1

        for t in lower_teeth:
            pred_q = 4 if t['cx'] < midline_x else 3
            if pred_q == t['gt_q']:
                correct_quadrants += 1

    print(f"Evaluation on {len(test_img_ids)} images ({total_teeth} teeth):")
    print(f"Quadrant assignment accuracy: {correct_quadrants / total_teeth * 100:.2f}% ({correct_quadrants}/{total_teeth})")

if __name__ == '__main__':
    evaluate_fdi_solver_on_ground_truth()
