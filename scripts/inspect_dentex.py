import zipfile
import json
import os

zip_path = 'training_data.zip'
with zipfile.ZipFile(zip_path, 'r') as zf:
    json_path = 'training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json'
    with zf.open(json_path) as f:
        data = json.load(f)
        print('=== CATEGORIES_1 (Quadrants) ===')
        print(json.dumps(data.get('categories_1'), indent=2))
        print('=== CATEGORIES_2 (Tooth Enumeration) ===')
        print(json.dumps(data.get('categories_2'), indent=2))
        print('=== CATEGORIES_3 (Abnormal Diagnosis) ===')
        print(json.dumps(data.get('categories_3'), indent=2))
        
        ann = data.get('annotations', [])
        print(f'\nTotal annotations: {len(ann)}')
        
        # Check segmentation vs bbox
        has_seg = 0
        seg_lengths = []
        for a in ann:
            s = a.get('segmentation', [])
            if s and len(s) > 0 and len(s[0]) > 0:
                has_seg += 1
                seg_lengths.append(len(s[0]))
        
        print(f'Annotations with segmentation: {has_seg} / {len(ann)}')
        if seg_lengths:
            print(f'Min coords in poly: {min(seg_lengths)}, Max coords: {max(seg_lengths)}, Avg: {sum(seg_lengths)/len(seg_lengths):.1f}')
        
        print('\n=== Sample 5 Annotations ===')
        for a in ann[:5]:
            seg = a.get('segmentation', [[]])[0]
            print({
                'id': a.get('id'),
                'image_id': a.get('image_id'),
                'bbox': [round(x, 1) for x in a.get('bbox', [])],
                'cat1': a.get('category_id_1'),
                'cat2': a.get('category_id_2'),
                'cat3': a.get('category_id_3'),
                'seg_point_count': len(seg) // 2,
                'seg_preview': [round(x, 1) for x in seg[:6]]
            })
