"""TASK 0B: Real-Data Narrative Check on 10 Real OPGs.

Runs full real detection & segmentation pipeline, builds real ClinicalEvidencePackages,
invokes Ollama narrative generation on CPU, validates faithfulness, generates PDFs,
and extracts unedited narrative text as rendered in the PDF.
"""

import os
import sys
import time
import json
import uuid
from pathlib import Path
from PIL import Image

# Force CPU execution
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["YOLO_AUTOINSTALL"] = "0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.segmentation_engine import DentalSegmentationEngine
from backend.ml.inference_engine import ONNXInferenceEngine
from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.fdi_solver import ResolvedTooth
from backend.ml.association import ToothPathologyAssociator
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
from backend.clinical.faithfulness import FaithfulnessChecker
from backend.clinical.evidence_engine import ClinicalEvidenceEngine


def run_real_data_narratives():
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

    print("Initializing real vision pipeline engines on CPU...")
    ckpt_seg = "models/checkpoints/dentex_yolov8n_seg_best.onnx"
    if not (PROJECT_ROOT / ckpt_seg).exists():
        ckpt_seg = "models/dentex_yolov8n_seg_best.onnx"

    seg_engine = DentalSegmentationEngine(
        model_id="dentex-yolov8n-seg",
        model_name="DENTEX 4-Class Segmenter",
        version="1.0.0",
        checkpoint_rel_path=ckpt_seg,
        class_names=["impacted_tooth", "caries", "periapical_lesion", "deep_caries"],
        conf_threshold=0.25,
        iou_threshold=0.35,
    )
    fdi_engine = FDINumberingEngine()
    associator = ToothPathologyAssociator()
    ollama = OllamaService()

    results = []
    sample_narratives_pdf = []

    print("\nStarting real-data narrative generation across 10 real OPGs on CPU...")
    print("-" * 80)

    for idx, img_path in enumerate(test_paths):
        case_id = f"REAL-OPG-{idx+1:02d}"
        filename = img_path.name

        with Image.open(img_path) as pil_img:
            img = pil_img.convert("RGB")
        w, h = img.size

        # 1. Vision Detection & Segmentation
        t_v0 = time.perf_counter()
        seg_res = seg_engine.predict_image(img, conf_threshold=0.25)
        raw_findings = seg_res.get("findings", [])
        teeth_res = fdi_engine.predict_teeth(img, conf_threshold=0.25)
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

        # 2. Geometric FDI Association
        norm_findings = []
        for f_idx, rf in enumerate(raw_findings):
            find_id = f"F-{idx+1}-{f_idx+1}"
            norm_findings.append({
                "id": find_id,
                "label": rf.class_name,
                "confidence": float(rf.confidence),
                "bbox": rf.bbox_orig,
                "polygon": rf.mask_polygon if rf.has_mask else [],
            })
        _, associations = associator.associate(norm_findings, resolved_teeth)
        assoc_map = {a.finding_id: a for a in associations}
        t_v1 = time.perf_counter()

        # 3. Assemble ClinicalEvidencePackage
        obs_list = []
        proc_list = []

        for f_idx, rf in enumerate(raw_findings):
            find_id = f"F-{idx+1}-{f_idx+1}"
            cond = rf.class_name
            try:
                path_cls = PathologyClass(cond)
            except Exception:
                path_cls = PathologyClass.CARIES

            box = rf.bbox_orig
            poly = rf.mask_polygon
            has_mask = bool(rf.has_mask and poly and len(poly) >= 3)
            conf = float(rf.confidence)

            assoc = assoc_map.get(find_id)
            fdi_num = assoc.associated_fdi_number if assoc else None
            fdi_unc = assoc.uncertain_association if assoc else True

            obs = RadiographicObservation(
                evidence_id=f"EVID-RAD-{idx+1:02d}-{f_idx+1}",
                study_id=case_id,
                radiograph_id=filename,
                finding_id=find_id,
                pathology_candidate=path_cls,
                confidence=conf,
                annotation_modality=AnnotationModality.INSTANCE_SEGMENTATION if has_mask else AnnotationModality.DETECTION_BOUNDING_BOX,
                geometry_semantics="instance_segmentation" if has_mask else "bounding_box_detection",
                bbox=FindingBoundingBox(x_min=box[0], y_min=box[1], x_max=box[2], y_max=box[3]),
                polygon=FindingPolygon(points=poly) if has_mask else None,
                tooth_fdi=fdi_num,
                fdi_uncertain=fdi_unc,
                model_id="dentex-yolov8n-seg",
                model_version="1.0.0",
                source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
                verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
            )
            obs_list.append(obs)

            # Map realistic procedure
            pos = (fdi_num % 10) if fdi_num else 6
            if path_cls == PathologyClass.CARIES:
                cdt = "D2330" if pos in (1, 2, 3) else "D2391"
                proc_name = "Composite Restoration"
                urg = UrgencyLevel.ROUTINE
            elif path_cls == PathologyClass.DEEP_CARIES:
                cdt = "D3310" if pos in (1, 2, 3) else ("D3320" if pos in (4, 5) else "D3330")
                proc_name = "Endodontic Therapy"
                urg = UrgencyLevel.SOON
            elif path_cls == PathologyClass.PERIAPICAL_LESION:
                cdt = "D3310" if pos in (1, 2, 3) else ("D3320" if pos in (4, 5) else "D3330")
                proc_name = "Root Canal Therapy"
                urg = UrgencyLevel.SOON
            elif path_cls == PathologyClass.IMPACTED_TOOTH:
                cdt = "D7240"
                proc_name = "Surgical Impaction Extraction"
                urg = UrgencyLevel.ROUTINE
            else:
                cdt = "D0140"
                proc_name = "Problem-Focused Evaluation"
                urg = UrgencyLevel.ROUTINE

            proc = RequestedProcedureRecord(
                procedure_id=f"PROC-{idx+1:02d}-{f_idx+1}",
                tooth_fdi=fdi_num,
                procedure_name=proc_name,
                suggested_cdt_code=cdt,
                cdt_code_verified_by_dentist=True,
                clinician_rationale=f"Clinical treatment indicated for {path_cls.value.replace('_', ' ')}.",
                urgency=urg,
                source_type=EvidenceSource.CLINICAL_RATIONALE,
            )
            proc_list.append(proc)

        package = ClinicalEvidencePackage(
            package_id=f"PKG-{case_id}",
            study_id=case_id,
            radiograph_id=filename,
            ai_observations=obs_list,
            requested_procedures=proc_list,
            payer_template=PayerPolicyTemplate(),
        )

        # 4. Generate Pre-Auth Draft via Ollama on CPU
        t_llm0 = time.perf_counter()
        draft, metrics = ollama.generate_pre_auth_draft(package, model_tag="qwen2.5:3b")
        t_llm1 = time.perf_counter()
        llm_lat_ms = (t_llm1 - t_llm0) * 1000.0

        is_faithful = metrics.get("faithfulness_pass", False)
        engine = metrics.get("engine_used", "")
        completeness_errs = FaithfulnessChecker.evaluate_completeness(draft.statements, package)
        is_complete = len(completeness_errs) == 0

        # 5. Generate Real PDF Claim Pack
        pdf_dir = PROJECT_ROOT / "scratch" / "real_narrative_pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"{case_id}_claim_pack.pdf"
        readiness = ClinicalEvidenceEngine.evaluate_package(package)
        sel_fdi = obs_list[0].tooth_fdi if obs_list else 16

        pdf_bytes = LocalClaimPackPDFGenerator.generate_claim_pack_pdf(
            package=package,
            draft=draft,
            readiness=readiness,
            selected_fdi=sel_fdi,
            output_path=str(pdf_path),
        )

        res_item = {
            "case_id": case_id,
            "filename": filename,
            "findings_count": len(obs_list),
            "vision_latency_ms": round((t_v1 - t_v0) * 1000.0, 1),
            "llm_latency_ms": round(llm_lat_ms, 1),
            "is_faithful": is_faithful,
            "is_complete": is_complete,
            "completeness_errors": completeness_errs,
            "engine": engine,
            "pdf_generated": os.path.exists(pdf_path),
            "pdf_size_bytes": len(pdf_bytes) if pdf_bytes else 0,
            "section_5": draft.section_5_radiographic_observations,
            "section_7": draft.section_7_clinical_rationale,
        }
        results.append(res_item)

        # Checkpoint progress
        with open(PROJECT_ROOT / "scratch" / "task0b_real_eval_progress.json", "w") as pf:
            json.dump(results, pf, indent=2)

        print(
            f"[{idx+1}/10] {case_id} ({filename}) | Findings: {len(obs_list)} | "
            f"LLM Lat: {llm_lat_ms:.1f}ms | Faithful: {is_faithful} | Complete: {is_complete} | Engine: {engine}",
            flush=True,
        )

    # Summarize results
    faithful_count = sum(1 for r in results if r["is_faithful"] and "fallback" not in r["engine"])
    complete_count = sum(1 for r in results if r["is_complete"])
    fallback_count = len(results) - faithful_count
    latencies = [r["llm_latency_ms"] for r in results]

    summary = {
        "total_real_opgs": len(results),
        "faithful_first_attempt": faithful_count,
        "complete_count": complete_count,
        "fallback_count": fallback_count,
        "faithful_rate_pct": round(faithful_count / len(results) * 100.0, 1),
        "complete_rate_pct": round(complete_count / len(results) * 100.0, 1),
        "mean_llm_latency_ms": round(float(sum(latencies) / len(latencies)), 1),
        "min_llm_latency_ms": round(float(min(latencies)), 1),
        "max_llm_latency_ms": round(float(max(latencies)), 1),
        "cases": results,
    }

    with open(PROJECT_ROOT / "scratch" / "task0b_real_eval.json", "w") as jf:
        json.dump(summary, jf, indent=2)

    print("\n" + "=" * 80)
    print("TASK 0B REAL-DATA NARRATIVE EVALUATION SUMMARY (10 REAL OPGS, CPU)")
    print("=" * 80)
    print(f"Total Real OPGs Evaluated: {len(results)}")
    print(f"Faithful Rate: {faithful_count} / {len(results)} ({summary['faithful_rate_pct']}%)")
    print(f"Fallback Count: {fallback_count} / {len(results)}")
    print(f"Mean LLM Latency: {summary['mean_llm_latency_ms']} ms")
    print("-" * 80)

    # Print 3 complete unedited narrative texts as they appear in the PDF
    print("\n=== THREE UNEDITED REAL-DATA NARRATIVES AS RENDERED IN PDF ===\n")
    for sample_idx in [0, 1, 3]:
        c = results[sample_idx]
        print(f"--- CASE {c['case_id']} ({c['filename']}) ---")
        print(f"Findings Count: {c['findings_count']}")
        print(f"Section 5 (Radiographic Observations):\n{c['section_5']}")
        print(f"Section 7 (Clinical Rationale):\n{c['section_7']}\n")


if __name__ == "__main__":
    run_real_data_narratives()
