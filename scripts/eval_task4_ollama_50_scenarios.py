import time
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from backend.schemas.finding import PathologyClass, FindingBoundingBox, UrgencyLevel
from backend.schemas.clinician import ReviewDecision
from backend.schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    DentistFindingConfirmation,
    ClinicalExaminationRecord,
    RequestedProcedureRecord,
    EvidenceSource,
    VerificationStatus,
    PayerPolicyTemplate,
)
from backend.services.ollama_service import OllamaService

def make_scenario(idx: int, teeth: list[int], pathologies: list[PathologyClass]) -> ClinicalEvidencePackage:
    study_id = f"SCENARIO-{idx+1:02d}"
    rad_id = f"opg_{idx+1:02d}.png"
    
    obs_list = []
    cfm_list = []
    proc_list = []

    for f_idx, (t_fdi, path_cls) in enumerate(zip(teeth, pathologies)):
        ev_id = f"EVID-RAD-{idx+1:02d}-{f_idx+1}"
        find_id = f"FIND-{idx+1:02d}-{f_idx+1}"
        
        # Bbox in pixel coordinates
        bx1 = 200.0 + (t_fdi % 10) * 150.0
        by1 = 300.0 if t_fdi // 10 in (1, 2) else 800.0
        bx2 = bx1 + 120.0
        by2 = by1 + 180.0
        
        obs = RadiographicObservation(
            evidence_id=ev_id,
            study_id=study_id,
            radiograph_id=rad_id,
            finding_id=find_id,
            pathology_candidate=path_cls,
            confidence=0.75 + (f_idx * 0.05),
            annotation_modality="instance_segmentation" if path_cls in (PathologyClass.CARIES, PathologyClass.DEEP_CARIES) else "detection_bounding_box",
            bbox=FindingBoundingBox(x_min=bx1, y_min=by1, x_max=bx2, y_max=by2),
            tooth_fdi=t_fdi,
            fdi_uncertain=False,
            model_id="dentex-yolov8n-seg",
            model_version="1.0.0",
            source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
            verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        )
        obs_list.append(obs)
        
        # Clinician confirmation for some scenarios
        if idx % 2 == 0:
            cfm = DentistFindingConfirmation(
                evidence_id=f"EVID-CFM-{idx+1:02d}-{f_idx+1}",
                finding_id=find_id,
                reviewer_name="Dr. Evaluator",
                license_number="DEN-12345",
                decision=ReviewDecision.CONFIRMED,
                confirmed_fdi=t_fdi,
                confirmed_pathology=path_cls,
                clinical_notes=f"Confirmed {path_cls.value.replace('_', ' ')} on #{t_fdi}.",
                verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
            )
            cfm_list.append(cfm)
            
        if path_cls == PathologyClass.CARIES:
            cdt = "D2140" if t_fdi % 10 in (6, 7, 8) else "D2391"
            proc_title = "Amalgam/Resin Restoration"
        elif path_cls == PathologyClass.DEEP_CARIES:
            cdt = "D3330" if t_fdi % 10 in (6, 7, 8) else ("D3320" if t_fdi % 10 in (4, 5) else "D3310")
            proc_title = "Endodontic Therapy"
        elif path_cls == PathologyClass.PERIAPICAL_LESION:
            cdt = "D3330" if t_fdi % 10 in (6, 7, 8) else ("D3320" if t_fdi % 10 in (4, 5) else "D3310")
            proc_title = "Root Canal Therapy"
        elif path_cls == PathologyClass.IMPACTED_TOOTH:
            cdt = "D7240"
            proc_title = "Surgical Extraction of Impacted Tooth"
        else:
            cdt = "D0140"
            proc_title = "Limited Oral Evaluation"

        proc = RequestedProcedureRecord(
            procedure_id=f"PROC-{idx+1:02d}-{f_idx+1}",
            tooth_fdi=t_fdi,
            procedure_name=proc_title,
            suggested_cdt_code=cdt,
            cdt_code_verified_by_dentist=True,
            clinician_rationale=f"Clinical intervention required for {path_cls.value.replace('_', ' ')}.",
            urgency=UrgencyLevel.SOON if path_cls in (PathologyClass.DEEP_CARIES, PathologyClass.PERIAPICAL_LESION) else UrgencyLevel.ROUTINE,
            source_type=EvidenceSource.CLINICAL_RATIONALE,
        )
        proc_list.append(proc)
        
    return ClinicalEvidencePackage(
        package_id=f"PKG-{idx+1:02d}",
        study_id=study_id,
        radiograph_id=rad_id,
        created_at=datetime.utcnow(),
        ai_observations=obs_list,
        dentist_confirmations=cfm_list,
        clinical_examinations=[],
        patient_symptoms=[],
        requested_procedures=proc_list,
        payer_template=PayerPolicyTemplate(),
    )

def generate_50_scenarios():
    scenarios = []
    # Varied distributions: single tooth, multi-tooth, different quadrants, different pathologies
    pathology_cycle = [
        [PathologyClass.CARIES],
        [PathologyClass.DEEP_CARIES],
        [PathologyClass.IMPACTED_TOOTH],
        [PathologyClass.PERIAPICAL_LESION],
        [PathologyClass.CARIES, PathologyClass.DEEP_CARIES],
        [PathologyClass.CARIES, PathologyClass.IMPACTED_TOOTH],
        [PathologyClass.DEEP_CARIES, PathologyClass.PERIAPICAL_LESION],
        [PathologyClass.IMPACTED_TOOTH, PathologyClass.IMPACTED_TOOTH],
        [PathologyClass.CARIES, PathologyClass.CARIES, PathologyClass.CARIES],
        [PathologyClass.DEEP_CARIES, PathologyClass.PERIAPICAL_LESION, PathologyClass.IMPACTED_TOOTH],
    ]
    
    teeth_pool = [
        [16], [26], [36], [46], [18], [28], [38], [48], [11], [21], [31], [41], [14], [24], [34], [44],
        [16, 17], [26, 27], [36, 37], [46, 47], [18, 48], [28, 38], [11, 21], [31, 41],
        [15, 16], [25, 26], [35, 36], [45, 46], [13, 23], [33, 43], [12, 22], [32, 42],
        [18, 28, 38], [18, 28, 48], [16, 26, 36], [16, 26, 46], [36, 46, 47], [16, 17, 18],
        [14, 24, 34], [15, 25, 35], [44, 45, 46], [24, 25, 26], [34, 35, 36], [11, 12, 21],
        [16, 36, 46, 48], [18, 28, 38, 48], [14, 15, 24, 25], [36, 37, 46, 47], [11, 21, 31, 41],
        [17, 27, 37, 47]
    ]

    for i in range(50):
        teeth = teeth_pool[i]
        path_pattern = pathology_cycle[i % len(pathology_cycle)]
        # match length of paths to teeth
        paths = [path_pattern[j % len(path_pattern)] for j in range(len(teeth))]
        scenarios.append(make_scenario(i, teeth, paths))
        
    return scenarios

def main():
    scenarios = generate_50_scenarios()
    print(f"Generated {len(scenarios)} distinct evaluation scenarios.")
    
    ollama = OllamaService()
    if not ollama.check_connection():
        print("ERROR: Ollama server is offline on 127.0.0.1:11434")
        return
        
    faithful_first_attempt = 0
    complete_count = 0
    fallback_count = 0
    placeholder_count = 0
    fallback_reasons = []
    latencies = []
    
    print("Starting 50-scenario CPU-ONLY evaluation against qwen2.5:3b...")
    sample_indices = {0, 4, 16, 20, 23}
    sampled_outputs = []

    import re
    from backend.clinical.faithfulness import FaithfulnessChecker

    for idx, sc in enumerate(scenarios):
        t0 = time.perf_counter()
        draft, metrics = ollama.generate_pre_auth_draft(sc, model_tag="qwen2.5:3b")
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000.0
        latencies.append(lat_ms)
        
        is_faithful = metrics.get("faithfulness_pass", False)
        engine = metrics.get("engine_used", "")
        completeness_errs = FaithfulnessChecker.evaluate_completeness(draft.statements, sc)
        is_complete = len(completeness_errs) == 0
        if is_complete:
            complete_count += 1

        # Check for placeholders
        sec5_text = draft.section_5_radiographic_observations
        sec7_text = draft.section_7_clinical_rationale
        has_placeholder = False
        for text_field in (sec5_text, sec7_text):
            brackets = re.findall(r"\[([^\]]+)\]", text_field)
            for b in brackets:
                b_str = b.strip()
                if b_str not in {"MISSING_EVIDENCE", "PENDING CLINICIAN REVIEW"}:
                    has_placeholder = True
                    break
        if has_placeholder:
            placeholder_count += 1

        if is_faithful and "fallback" not in engine:
            faithful_first_attempt += 1
        else:
            fallback_count += 1
            reason = metrics.get("fallback_reason") or "unspecified"
            fallback_reasons.append(f"Case {sc.study_id}: {reason}")
            
        print(f"[{idx+1}/50] Case {sc.study_id} ({len(sc.ai_observations)} findings) | Latency: {lat_ms:.1f}ms | Faithful: {is_faithful} | Complete: {is_complete} | Engine: {engine}", flush=True)

        if idx in sample_indices:
            prompt_str, allowed_p, allowed_t = ollama.build_reasoning_prompt(sc)
            sampled_outputs.append({
                "case_id": sc.study_id,
                "num_findings": len(sc.ai_observations),
                "input_prompt": prompt_str,
                "section_5_radiographic_observations": draft.section_5_radiographic_observations,
                "section_7_clinical_rationale": draft.section_7_clinical_rationale,
                "latency_ms": round(lat_ms, 2),
                "faithful": is_faithful,
                "allowed_pathologies": sorted(list(allowed_p)),
                "allowed_teeth": sorted(list(allowed_t)),
            })

        # Save progress checkpoint
        progress_data = {
            "completed": idx + 1,
            "total": len(scenarios),
            "faithful_first_attempt": faithful_first_attempt,
            "fallback_count": fallback_count,
            "latencies": latencies,
        }
        with open("scratch/task4_eval_progress.json", "w") as pf:
            json.dump(progress_data, pf, indent=2)

    latencies = np.array(latencies)
    mean_lat = float(np.mean(latencies))
    median_lat = float(np.median(latencies))
    p95_lat = float(np.percentile(latencies, 95))

    final_results = {
        "model": "qwen2.5:3b",
        "total_scenarios": len(scenarios),
        "faithful_first_attempt": faithful_first_attempt,
        "complete_count": complete_count,
        "fallback_count": fallback_count,
        "placeholder_count": placeholder_count,
        "fallback_reasons": fallback_reasons,
        "mean_latency_ms": round(mean_lat, 2),
        "median_latency_ms": round(median_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
    }
    with open("scratch/task4_eval_final.json", "w") as ff:
        json.dump(final_results, ff, indent=2)
    with open("scratch/task4_eval_samples.json", "w") as sf:
        json.dump(sampled_outputs, sf, indent=2)

    print("\n=== FINAL 50-SCENARIO EVALUATION RESULTS (qwen2.5:3b) ===", flush=True)
    print(f"Total Scenarios Evaluated: {len(scenarios)}", flush=True)
    print(f"Faithful on First Attempt: {faithful_first_attempt} / {len(scenarios)} ({faithful_first_attempt/len(scenarios)*100:.1f}%)", flush=True)
    print(f"Complete (All Findings Covered): {complete_count} / {len(scenarios)} ({complete_count/len(scenarios)*100:.1f}%)", flush=True)
    print(f"Fallback Count: {fallback_count} / {len(scenarios)} ({fallback_count/len(scenarios)*100:.1f}%)", flush=True)
    print(f"Outputs Containing Placeholders: {placeholder_count} / {len(scenarios)}", flush=True)
    print(f"Latency Mean: {mean_lat:.2f} ms", flush=True)
    print(f"Latency Median: {median_lat:.2f} ms", flush=True)
    print(f"Latency p95: {p95_lat:.2f} ms", flush=True)

if __name__ == "__main__":
    main()
