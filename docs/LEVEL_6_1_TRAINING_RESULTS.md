# DENTRACE Level 6.1 — Training Results

**Generated:** 2026-10-21 21:19

> [!NOTE]
> All metrics are measured on the held-out validation split (141 images, 689 instances). No patient data is included.

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Experiment name | `dentex_yolov8n_seg_4class_v2` |
| Architecture | YOLOv8n-seg (pretrained COCO transfer) |
| Classes | cavity, missing_tooth, impacted_tooth, periapical_lesion |
| Train images | 564 |
| Val images | 141 |
| Image size | 640 px |
| Batch size | 8 |
| Total epochs | 26 |

## Best Epoch Summary

**Best epoch: 25** (selected by highest Box mAP50 on validation set)

| Metric | Box (Detection) | Mask (Segmentation) |
|--------|-----------------|---------------------|
| Precision | 0.5172 | 0.4697 |
| Recall | 0.5435 | 0.5099 |
| **mAP50** | **0.4816** | **0.4460** |
| mAP50-95 | 0.2972 | 0.2732 |

## Per-Epoch Validation Metrics

| Epoch | Box mAP50 | Mask mAP50 | Box mAP50-95 | Mask mAP50-95 | Box Loss | Cls Loss |
|------:|----------:|-----------:|-------------:|--------------:|---------:|---------:|
|     1 | 0.237 | 0.237 | 0.132 | 0.127 | 1.657 | 3.913 |
|     2 | 0.294 | 0.294 | 0.169 | 0.163 | 1.310 | 2.026 |
|     3 | 0.293 | 0.290 | 0.170 | 0.163 | 1.280 | 1.899 |
|     4 | 0.311 | 0.306 | 0.188 | 0.176 | 1.293 | 1.871 |
|     5 | 0.341 | 0.332 | 0.192 | 0.186 | 1.270 | 1.761 |
|     6 | 0.340 | 0.332 | 0.196 | 0.193 | 1.253 | 1.756 |
|     7 | 0.371 | 0.344 | 0.221 | 0.199 | 1.248 | 1.704 |
|     8 | 0.346 | 0.342 | 0.204 | 0.200 | 1.236 | 1.662 |
|     9 | 0.372 | 0.362 | 0.221 | 0.213 | 1.197 | 1.664 |
|    10 | 0.391 | 0.379 | 0.229 | 0.231 | 1.198 | 1.629 |
|    11 | 0.356 | 0.352 | 0.212 | 0.209 | 1.170 | 1.615 |
|    12 | 0.395 | 0.381 | 0.242 | 0.229 | 1.167 | 1.597 |
|    13 | 0.393 | 0.375 | 0.243 | 0.228 | 1.167 | 1.542 |
|    14 | 0.382 | 0.381 | 0.217 | 0.217 | 1.160 | 1.545 |
|    15 | 0.389 | 0.377 | 0.237 | 0.228 | 1.174 | 1.554 |
|    16 | 0.445 | 0.415 | 0.267 | 0.248 | 1.157 | 1.533 |
|    17 | 0.445 | 0.425 | 0.262 | 0.254 | 1.139 | 1.512 |
|    18 | 0.442 | 0.425 | 0.274 | 0.257 | 1.138 | 1.506 |
|    19 | 0.443 | 0.422 | 0.273 | 0.266 | 1.115 | 1.452 |
|    20 | 0.430 | 0.415 | 0.268 | 0.252 | 1.098 | 1.451 |
|    21 | 0.417 | 0.402 | 0.257 | 0.242 | 1.100 | 1.492 |
|    22 | 0.425 | 0.409 | 0.263 | 0.248 | 1.070 | 1.448 |
|    23 | 0.462 | 0.438 | 0.291 | 0.265 | 1.050 | 1.434 |
|    24 | 0.461 | 0.418 | 0.294 | 0.262 | 1.051 | 1.408 |
|    25 | 0.482 | 0.446 | 0.297 | 0.273 | 1.045 | 1.381 |
|    26 | 0.471 | 0.448 | 0.302 | 0.279 | 1.038 | 1.371 |

> [!IMPORTANT]
> Level 6 (epoch 1, cold-start): mAP50 = 0.000 for all classes. Level 6.1 pretrained transfer corrected this.

## Clinical Interpretation Constraints

- Class-wise per-condition mAP metrics require per-class YOLO evaluation output (run `model.val(split='val')` with verbose=True).
- This model is a decision-support tool. All detections must be reviewed by a licensed dentist.
- Validation split is a random 20% hold-out from the DENTEX quadrant-enumeration-disease subset.

## Limitations

- Dataset size (705 panoramic radiographs, 4 classes) is small relative to clinical diversity.
- Training resolution 640px may miss fine-grained periapical lesions in low-contrast regions.
- Bone loss and root canal condition are handled by rule-based clinical layer, not this segmentation model.

## Per-Class Breakdown (best.pt final validation, val split)

| Class | Box P | Box R | Box mAP50 | Box mAP50-95 | Mask P | Mask R | Mask mAP50 | Mask mAP50-95 |
|-------|------:|------:|----------:|-------------:|-------:|-------:|-----------:|--------------:|
| **impacted_tooth** | 0.727 | 0.904 | **0.864** | 0.524 | 0.741 | 0.908 | **0.867** | 0.544 |
| **deep_caries** | 0.400 | 0.438 | **0.440** | 0.279 | 0.438 | 0.430 | **0.430** | 0.245 |
| **caries** | 0.278 | 0.653 | **0.317** | 0.225 | 0.291 | 0.607 | **0.317** | 0.210 |
| **periapical_lesion** | 0.315 | 0.281 | **0.284** | 0.198 | 0.257 | 0.188 | **0.171** | 0.111 |
| **all (mean)** | 0.430 | 0.569 | **0.476** | 0.306 | 0.432 | 0.533 | **0.446** | 0.278 |

> [!NOTE]
> Class names in the DENTEX annotation set: caries, deep_caries, impacted_tooth, periapical_lesion.
> impacted_tooth achieves highest mAP50 (0.864 box) — these are geometrically distinctive.
> periapical_lesion has lowest mAP50 (0.284 box) — small, low-contrast lesions require more data.

## Training Completion

- **Total epochs trained:** 30 (patience=10 stopped best improvement after epoch 25)
- **Training duration:** 1.102 hours on NVIDIA GeForce RTX 2050 (4 GB VRAM)
- **GPU memory peak:** ~1.69 GB
