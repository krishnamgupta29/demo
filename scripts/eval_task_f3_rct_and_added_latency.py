"""TASK F3: Root canal treatment on real images benchmark.

Evaluates 10 real OPGs on CPU:
- Counts root_canal_treatment detections from 8024.onnx
- Counts periapical_lesion detections from dentex_yolov8n_seg
- Evaluates composite endodontic failure flags (RCT + lesion on same tooth)
- Measures CPU latency per image before and after adding 8024.onnx (FP32 and INT8)
- Generates PDF claim pack displaying flagged teeth
"""

import os
import sys
import time
import json
from pathlib import Path
from PIL import Image
import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["YOLO_AUTOINSTALL"] = "0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.segmentation_engine import DentalSegmentationEngine
from backend.ml.inference_engine import ONNXInferenceEngine
from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.fdi_solver import ResolvedTooth
from backend.ml.association import ToothPathologyAssociator
from backend.clinical.attribute_engine import ClinicalAttributeEngine
from backend.schemas.finding import (
    PathologyClass,
    FindingBoundingBox,
    FindingPolygon,
    AnnotationModality,
    UrgencyLevel,
)
from backend.schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    RequestedProcedureRecord,
    EvidenceSource,
    VerificationStatus,
    PayerPolicyTemplate,
)
from backend.services.ollama_service import OllamaService
from backend.reporting.pdf_generator import LocalClaimPackPDFGenerator
from backend.clinical.evidence_engine import ClinicalEvidenceEngine


def run_rct_benchmark():
    test_paths = [
        PROJECT_ROOT / "samples" / "sample_opg_1.png",
        PROJECT_ROOT / "samples" / "sample_opg_2.png",
        PROJECT_ROOT / "samples" / "sample_opg_3.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_0.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_101.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_104.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_112.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_118.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_123.png",
        PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val" / "train_130.png",
    ]

    print("Initializing models on CPU...")
    # 1. Default Flow Segmenter
    ckpt_seg = "models/checkpoints/dentex_yolov8n_seg_best.onnx"
    if not (PROJECT_ROOT / ckpt_seg).exists():
        ckpt_seg = "models/dentex_yolov8n_seg_best.onnx"

    dentex_seg = DentalSegmentationEngine(
        model_id="dentex-yolov8n-seg",
        model_name="DENTEX 4-Class Segmenter",
        version="1.0.0",
        checkpoint_rel_path=ckpt_seg,
        class_names=["impacted_tooth", "caries", "periapical_lesion", "deep_caries"],
        conf_threshold=0.25,
        iou_threshold=0.35,
    )

    # 2. Secondary 8024 Models (FP32 & INT8)
    ckpt_8024_fp32 = "ml/models/checkpoints/8024.onnx"
    ckpt_8024_int8 = "ml/models/checkpoints/8024_int8.onnx"

    engine_8024_fp32 = DentalSegmentationEngine(
        model_id="nsitnov-8024-seg",
        model_name="Dental Restorations & Lesions Segmenter",
        version="1.0.0",
        checkpoint_rel_path=ckpt_8024_fp32,
        class_names=[
            "Caries",
            "Crown",
            "Filling",
            "Implant",
            "Missing teeth",
            "Periapical lesion",
            "Root Piece",
            "Root canal obturation",
        ],
        conf_threshold=0.25,
        iou_threshold=0.40,
    )

    engine_8024_int8 = DentalSegmentationEngine(
        model_id="nsitnov-8024-seg-int8",
        model_name="Dental Restorations & Lesions Segmenter (INT8)",
        version="1.0.0",
        checkpoint_rel_path=ckpt_8024_int8,
        class_names=[
            "Caries",
            "Crown",
            "Filling",
            "Implant",
            "Missing teeth",
            "Periapical lesion",
            "Root Piece",
            "Root canal obturation",
        ],
        conf_threshold=0.25,
        iou_threshold=0.40,
    )

    fdi_engine = FDINumberingEngine()
    associator = ToothPathologyAssociator()
    ollama = OllamaService()

    rows = []
    flagged_pdf_path = None

    print(f"\nProcessing {len(test_paths)} real OPGs on CPU...")
    print(f"{'Image':<14} | {'RCT Det':<8} | {'PA Lesion':<10} | {'Endo Fail':<10} | {'Def Lat (ms)':<13} | {'+8024 FP32':<11} | {'+8024 INT8':<11}")
    print("-" * 88)

    for idx, p in enumerate(test_paths):
        img_name = p.name
        with Image.open(p) as pil_img:
            img = pil_img.convert("RGB")

        # 1. Default Flow Latency (Dentex + FDI)
        t_d0 = time.perf_counter()
        dentex_res = dentex_seg.predict_image(img, conf_threshold=0.25)
        teeth_res = fdi_engine.predict_teeth(img, conf_threshold=0.25)
        t_d1 = time.perf_counter()
        default_latency_ms = (t_d1 - t_d0) * 1000.0

        raw_dentex = dentex_res.get("findings", [])
        pa_lesions = [f for f in raw_dentex if f.class_name == "periapical_lesion"]

        # 2. Run 8024 FP32
        t_8024_0 = time.perf_counter()
        res_8024 = engine_8024_fp32.predict_image(img, conf_threshold=0.25)
        t_8024_1 = time.perf_counter()
        added_fp32_ms = (t_8024_1 - t_8024_0) * 1000.0

        # 3. Run 8024 INT8
        t_int8_0 = time.perf_counter()
        res_8024_int8 = engine_8024_int8.predict_image(img, conf_threshold=0.25)
        t_int8_1 = time.perf_counter()
        added_int8_ms = (t_int8_1 - t_int8_0) * 1000.0

        raw_8024 = res_8024.get("findings", [])
        rct_dets = [f for f in raw_8024 if f.class_name in ("Root canal obturation", "Root-Canal-Treatment")]

        # FDI teeth resolution
        raw_teeth = teeth_res.get("teeth", [])
        resolved_teeth = []
        for t_i, tb in enumerate(raw_teeth):
            bx = tb.bbox_orig
            cx = (bx[0] + bx[2]) / 2.0
            cy = (bx[1] + bx[3]) / 2.0
            q = tb.quadrant or ((tb.fdi_number // 10) if tb.fdi_number else 1)
            pos = (tb.fdi_number % 10) if tb.fdi_number else None
            resolved_teeth.append(ResolvedTooth(
                tooth_id=f"t_{t_i+1}",
                fdi_number=tb.fdi_number,
                fdi_name=f"FDI #{tb.fdi_number}" if tb.fdi_number else "Unassigned",
                quadrant=q,
                tooth_index=pos,
                confidence=tb.confidence,
                bbox=bx,
                centroid=[cx, cy],
                jaw=tb.jaw or ("maxilla" if q in (1, 2) else "mandible"),
                patient_side=tb.patient_side or ("patient_right" if q in (1, 4) else "patient_left"),
                uncertain_tooth=tb.uncertain_tooth,
            ))

        # Associate both dentex findings and 8024 RCT findings
        all_norm = []
        for d_i, df in enumerate(raw_dentex):
            all_norm.append({
                "id": f"D-{idx+1}-{d_i+1}",
                "label": df.class_name,
                "confidence": float(df.confidence),
                "bbox": df.bbox_orig,
                "polygon": df.mask_polygon if df.has_mask else [],
            })
        for r_i, rf in enumerate(rct_dets):
            all_norm.append({
                "id": f"RCT-{idx+1}-{r_i+1}",
                "label": "root_canal_treatment",
                "confidence": float(rf.confidence),
                "bbox": rf.bbox_orig,
                "polygon": rf.mask_polygon if rf.has_mask else [],
            })

        _, associations = associator.associate(all_norm, resolved_teeth)
        assoc_map = {a.finding_id: a for a in associations}

        # Build observations
        obs_list = []
        for item in all_norm:
            assoc = assoc_map.get(item["id"])
            fdi_num = assoc.associated_fdi_number if assoc else None
            is_rct = item["label"] == "root_canal_treatment"
            path_cls = PathologyClass.ROOT_CANAL_TREATMENT if is_rct else PathologyClass(item["label"])

            obs = RadiographicObservation(
                evidence_id=f"EVID-{item['id']}",
                study_id=f"RCT-STUDY-{idx+1:02d}",
                radiograph_id=img_name,
                finding_id=item["id"],
                pathology_candidate=path_cls,
                confidence=item["confidence"],
                annotation_modality=AnnotationModality.INSTANCE_SEGMENTATION if item["polygon"] else AnnotationModality.DETECTION_BOUNDING_BOX,
                bbox=FindingBoundingBox(x_min=item["bbox"][0], y_min=item["bbox"][1], x_max=item["bbox"][2], y_max=item["bbox"][3]),
                polygon=FindingPolygon(points=item["polygon"]) if item["polygon"] else None,
                tooth_fdi=fdi_num,
                fdi_uncertain=assoc.uncertain_association if assoc else True,
                model_id="nsitnov-8024-seg" if is_rct else "dentex-yolov8n-seg",
                model_version="1.0.0",
                source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
                verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
            )
            obs_list.append(obs)

        # Evaluate endodontic failure composite rule
        flagged_teeth = []
        for obs in obs_list:
            if obs.pathology_candidate == PathologyClass.PERIAPICAL_LESION and obs.tooth_fdi:
                is_flagged, alert_msg = ClinicalAttributeEngine.evaluate_endodontic_failure(obs_list, obs.tooth_fdi)
                if is_flagged:
                    flagged_teeth.append((obs.tooth_fdi, alert_msg))

        unique_flagged = sorted(list({t for t, _ in flagged_teeth}))
        endo_fail_count = len(unique_flagged)

        row_info = {
            "image": img_name,
            "rct_count": len(rct_dets),
            "pa_lesion_count": len(pa_lesions),
            "endo_fail_count": endo_fail_count,
            "flagged_teeth": unique_flagged,
            "default_latency_ms": round(default_latency_ms, 1),
            "added_fp32_ms": round(added_fp32_ms, 1),
            "added_int8_ms": round(added_int8_ms, 1),
        }
        rows.append(row_info)

        print(f"{img_name:<14} | {len(rct_dets):<8} | {len(pa_lesions):<10} | {endo_fail_count:<10} | {default_latency_ms:<13.1f} | {added_fp32_ms:<11.1f} | {added_int8_ms:<11.1f}")

        # If endodontic failure flagged, generate PDF demonstrating the flagged tooth
        if endo_fail_count > 0 and flagged_pdf_path is None:
            pkg = ClinicalEvidencePackage(
                package_id=f"PKG-RCT-{idx+1:02d}",
                study_id=f"RCT-STUDY-{idx+1:02d}",
                radiograph_id=img_name,
                ai_observations=obs_list,
                payer_template=PayerPolicyTemplate(),
            )
            draft, _ = ollama.generate_pre_auth_draft(pkg)
            readiness = ClinicalEvidenceEngine.evaluate_package(pkg)
            pdf_out = PROJECT_ROOT / "scratch" / f"task_f3_rct_flagged_{img_name}.pdf"
            LocalClaimPackPDFGenerator.generate_claim_pack_pdf(
                package=pkg,
                draft=draft,
                readiness=readiness,
                selected_fdi=unique_flagged[0] if unique_flagged else (obs_list[0].tooth_fdi if obs_list else 16),
                output_path=str(pdf_out),
            )
            flagged_pdf_path = str(pdf_out)

    mean_def = np.mean([r["default_latency_ms"] for r in rows])
    mean_fp32 = np.mean([r["added_fp32_ms"] for r in rows])
    mean_int8 = np.mean([r["added_int8_ms"] for r in rows])

    print("-" * 88)
    print(f"Mean Latency: Default={mean_def:.1f} ms | +8024 FP32={mean_fp32:.1f} ms | +8024 INT8={mean_int8:.1f} ms")
    print(f"Sample PDF Generated: {flagged_pdf_path}")

    results_data = {
        "rows": rows,
        "mean_default_ms": round(float(mean_def), 1),
        "mean_added_fp32_ms": round(float(mean_fp32), 1),
        "mean_added_int8_ms": round(float(mean_int8), 1),
        "flagged_pdf": flagged_pdf_path,
    }
    with open(PROJECT_ROOT / "scratch" / "task_f3_results.json", "w") as f:
        json.dump(results_data, f, indent=2)

    return results_data


if __name__ == "__main__":
    run_rct_benchmark()
