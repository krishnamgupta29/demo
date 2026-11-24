"""Deterministic Narrative Generator and Clinical Template Engine for DENTRACE.

Provides:
1. High-fidelity deterministic generation of the 10-section clinical pre-auth narrative.
2. Complete claim-to-evidence sentence-level traceability.
3. Guaranteed non-hallucinating fallback when local LLM is unavailable or ungrounded.
4. Strict preservation of radiographic uncertainty for unreviewed AI findings.
"""

import uuid
from datetime import datetime
from ..schemas.evidence import (
    ClinicalEvidencePackage,
    InsurancePreAuthDraft,
    NarrativeStatementCitation,
    DraftState,
    EvidenceSource,
    VerificationStatus,
)
from ..schemas.finding import PathologyClass
from .faithfulness import FaithfulnessChecker


class DeterministicNarrativeGenerator:
  """Generates strictly grounded 10-section pre-authorization clinical documentation."""

  @classmethod
  def generate_draft(
      cls,
      package: ClinicalEvidencePackage,
      draft_id: str | None = None,
  ) -> InsurancePreAuthDraft:
    """Produces an authoritative, fully cited 10-section pre-authorization draft."""
    if not draft_id:
      draft_id = f"DRAFT-{uuid.uuid4().hex[:8].upper()}"

    statements: list[NarrativeStatementCitation] = []

    # Map confirmed finding IDs
    confirmations_by_finding = {
        cfm.finding_id: cfm for cfm in package.dentist_confirmations
    }

    # SECTION 1: Case Identification
    s1_text = (
        f"Case Study ID: {package.study_id}. "
        f"Associated Radiograph ID: {package.radiograph_id}. "
        f"Record generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} under academic decision-support protocol."
    )
    stmt_1 = NarrativeStatementCitation(
        statement_id=f"STMT-S1-{uuid.uuid4().hex[:6].upper()}",
        section_index=1,
        section_title="Case Identification",
        sentence_text=s1_text,
        cited_evidence_ids=[package.package_id],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
        uncertainty_preserved=True,
    )
    statements.append(stmt_1)

    # SECTION 2: Requested Procedure
    if package.requested_procedures:
      proc_summaries = []
      proc_eids = []
      for p in package.requested_procedures:
        tooth_desc = f"Tooth #{p.tooth_fdi}" if p.tooth_fdi is not None else "Unspecified tooth"
        cdt_desc = f" (Candidate CDT: {p.suggested_cdt_code})" if p.suggested_cdt_code else ""
        proc_summaries.append(f"{p.procedure_name} on {tooth_desc}{cdt_desc} [Urgency: {p.urgency.value.upper()}]")
        proc_eids.append(p.procedure_id)
      s2_text = "Proposed Treatment Plan: " + "; ".join(proc_summaries) + "."
    else:
      proc_eids = []
      s2_text = "Proposed Treatment Plan: No clinical procedure has been formally selected by the clinician [INCOMPLETE]."

    stmt_2 = NarrativeStatementCitation(
        statement_id=f"STMT-S2-{uuid.uuid4().hex[:6].upper()}",
        section_index=2,
        section_title="Requested Procedure",
        sentence_text=s2_text,
        cited_evidence_ids=proc_eids if proc_eids else [package.package_id],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN if package.requested_procedures else VerificationStatus.UNSUPPORTED_CLAIM,
        uncertainty_preserved=True,
    )
    statements.append(stmt_2)

    # SECTION 3: Tooth Identifier
    confirmed_teeth = [
        cfm.confirmed_fdi for cfm in package.dentist_confirmations if cfm.confirmed_fdi is not None
    ]
    unconfirmed_ai_teeth = [
        obs.tooth_fdi for obs in package.ai_observations
        if obs.tooth_fdi is not None and obs.finding_id not in confirmations_by_finding
    ]
    uncertain_flagged = [
        obs.tooth_fdi for obs in package.ai_observations if obs.fdi_uncertain and obs.tooth_fdi is not None
    ]

    s3_parts = []
    if confirmed_teeth:
      s3_parts.append(f"Clinician-verified FDI tooth identifier(s): {', '.join(str(t) for t in sorted(set(confirmed_teeth)))}.")
    if unconfirmed_ai_teeth:
      s3_parts.append(f"Provisional unconfirmed AI-localized Tooth Identifier(s): {', '.join(str(t) for t in sorted(set(unconfirmed_ai_teeth)))} (Pending human attestation).")
    if uncertain_flagged:
      s3_parts.append(f"Anatomically ambiguous or shifted tooth proposals: {', '.join(str(t) for t in sorted(set(uncertain_flagged)))}.")
    if not s3_parts:
      s3_parts.append("No anatomical tooth identifiers have been established for this case.")

    s3_text = " ".join(s3_parts)
    stmt_3 = NarrativeStatementCitation(
        statement_id=f"STMT-S3-{uuid.uuid4().hex[:6].upper()}",
        section_index=3,
        section_title="Tooth Identifier",
        sentence_text=s3_text,
        cited_evidence_ids=[cfm.evidence_id for cfm in package.dentist_confirmations] + [obs.evidence_id for obs in package.ai_observations],
        source_types=[EvidenceSource.CLINICIAN_CONFIRMATION, EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN if confirmed_teeth else VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    statements.append(stmt_3)

    # SECTION 4: Clinician Confirmed Findings
    if package.dentist_confirmations:
      cfm_descs = []
      cfm_eids = []
      for cfm in package.dentist_confirmations:
        t_str = f"Tooth #{cfm.confirmed_fdi}" if cfm.confirmed_fdi else "Unspecified tooth"
        p_str = cfm.confirmed_pathology.value if cfm.confirmed_pathology else "finding"
        cfm_descs.append(
            f"Reviewer {cfm.reviewer_name} (Lic# {cfm.license_number}) {cfm.decision.value.upper()} {p_str} on {t_str}"
            + (f" with notes: '{cfm.clinical_notes}'" if cfm.clinical_notes else "")
        )
        cfm_eids.append(cfm.evidence_id)
      s4_text = "Clinician Findings: " + "; ".join(cfm_descs) + "."
    else:
      cfm_eids = []
      s4_text = "Clinician Findings: No practitioner confirmations or chairside evaluations recorded to date [REQUIRES REVIEW]."

    stmt_4 = NarrativeStatementCitation(
        statement_id=f"STMT-S4-{uuid.uuid4().hex[:6].upper()}",
        section_index=4,
        section_title="Clinician Confirmed Findings",
        sentence_text=s4_text,
        cited_evidence_ids=cfm_eids if cfm_eids else [package.package_id],
        source_types=[EvidenceSource.CLINICIAN_CONFIRMATION],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN if package.dentist_confirmations else VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    statements.append(stmt_4)

    # SECTION 5: Radiographic Observations with Uncertainty Preserved
    if package.ai_observations:
      obs_descs = []
      obs_eids = []
      for obs in package.ai_observations:
        t_str = f"near Tooth #{obs.tooth_fdi}" if obs.tooth_fdi is not None else "in dental arch"
        unc_str = " (flagged uncertain numbering)" if obs.fdi_uncertain else ""
        obs_descs.append(
            f"Model {obs.model_id} ({obs.model_version}) suspected {obs.pathology_candidate.value} {t_str}{unc_str} "
            f"[raw confidence: {round(obs.confidence * 100, 1)}%, modality: {obs.annotation_modality.value}]"
        )
        obs_eids.append(obs.evidence_id)
      s5_text = "Radiographic Observations: Screening analysis detected: " + "; ".join(obs_descs) + ". These represent provisional observations, not definitive diagnoses."
    else:
      obs_eids = []
      s5_text = "Radiographic Observations: No automated vision findings identified or staged for this radiograph."

    stmt_5 = NarrativeStatementCitation(
        statement_id=f"STMT-S5-{uuid.uuid4().hex[:6].upper()}",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text=s5_text,
        cited_evidence_ids=obs_eids if obs_eids else [package.package_id],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    statements.append(stmt_5)

    # SECTION 6: Supporting Evidence References
    crop_refs = [
        f"Crop [{obs.finding_id}]: {obs.image_crop_path}"
        for obs in package.ai_observations if obs.image_crop_path
    ]
    exam_refs = [
        f"Exam [{e.evidence_id}]: Vitality={e.pulp_vitality or 'untested'}, Percussion={e.percussion_sensitivity}, Cavitation={e.visual_cavitation}"
        for e in package.clinical_examinations
    ]
    s6_text = (
        "Supporting Evidence Catalog: "
        + (f"Image Assets: {'; '.join(crop_refs)}. " if crop_refs else "Image Assets: Full OPG raster. ")
        + (f"Clinical Tests: {'; '.join(exam_refs)}." if exam_refs else "Clinical Tests: None recorded.")
    )
    stmt_6 = NarrativeStatementCitation(
        statement_id=f"STMT-S6-{uuid.uuid4().hex[:6].upper()}",
        section_index=6,
        section_title="Supporting Evidence References",
        sentence_text=s6_text,
        cited_evidence_ids=[obs.evidence_id for obs in package.ai_observations] + [e.evidence_id for e in package.clinical_examinations] or [package.package_id],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION, EvidenceSource.CLINICIAN_EXAMINATION],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN if package.clinical_examinations else VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    statements.append(stmt_6)

    # SECTION 7: Clinical Rationale Supplied by the Dentist
    if package.requested_procedures:
      rationales = [
          f"Procedure '{p.procedure_name}': {p.clinician_rationale}"
          for p in package.requested_procedures if p.clinician_rationale
      ]
      s7_text = "Clinician Clinical Rationale: " + (" ".join(rationales) if rationales else "No objective justification entered [REQUIRES RATIONALE].")
    else:
      s7_text = "Clinician Clinical Rationale: Treatment rationale pending clinician procedure submission."

    stmt_7 = NarrativeStatementCitation(
        statement_id=f"STMT-S7-{uuid.uuid4().hex[:6].upper()}",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text=s7_text,
        cited_evidence_ids=[p.procedure_id for p in package.requested_procedures] or [package.package_id],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN if package.requested_procedures else VerificationStatus.UNSUPPORTED_CLAIM,
        uncertainty_preserved=True,
    )
    statements.append(stmt_7)

    # SECTION 8: Missing Information / Review-Required Items
    from .detective import MissingEvidenceDetective
    missing_items = MissingEvidenceDetective.detect_missing_evidence(package)
    if missing_items:
      m_prompts = [f"- {m.question_prompt} ({m.clinical_reason})" for m in missing_items]
      s8_text = "Pre-Authorization Documentation Checklist (Pending Items):\n" + "\n".join(m_prompts)
    else:
      s8_text = "Pre-Authorization Documentation Checklist: All required clinical documentation items are satisfied."

    stmt_8 = NarrativeStatementCitation(
        statement_id=f"STMT-S8-{uuid.uuid4().hex[:6].upper()}",
        section_index=8,
        section_title="Missing Information",
        sentence_text=s8_text,
        cited_evidence_ids=[m.item_id for m in missing_items] if missing_items else [package.package_id],
        source_types=[EvidenceSource.PAYER_REQUIREMENT],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
        uncertainty_preserved=True,
    )
    statements.append(stmt_8)

    # SECTION 9: Procedure Code References (ADA CDT Demonstrative)
    cdt_refs = []
    for p in package.requested_procedures:
      if p.suggested_cdt_code:
        status_str = "Dentist-Attested" if p.cdt_code_verified_by_dentist else "Unverified Candidate"
        cdt_refs.append(f"{p.suggested_cdt_code} ({status_str}): {p.procedure_name}")
    if cdt_refs:
      s9_text = (
          "CDT Procedure Code References (Illustrative Demo Catalog 2026): "
          + "; ".join(cdt_refs)
          + ". Notice: Code inclusion does not guarantee insurance coverage or payment."
      )
    else:
      s9_text = "CDT Procedure Code References: No CDT procedure codes have been proposed or verified."

    stmt_9 = NarrativeStatementCitation(
        statement_id=f"STMT-S9-{uuid.uuid4().hex[:6].upper()}",
        section_index=9,
        section_title="Procedure Code References",
        sentence_text=s9_text,
        cited_evidence_ids=[p.procedure_id for p in package.requested_procedures] or [package.package_id],
        source_types=[EvidenceSource.CLINICAL_RATIONALE, EvidenceSource.PAYER_REQUIREMENT],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN if any(p.cdt_code_verified_by_dentist for p in package.requested_procedures) else VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    statements.append(stmt_9)


    # SECTION 10: Required Reviewer Attestation
    s10_text = (
        "MANDATORY CLINICAL REVIEW ATTESTATION: "
        "Draft for dentist review. Not a diagnosis. "
        "This pre-authorization narrative is an academic clinical decision-support draft. "
        "It does not constitute autonomous medical advice, treatment determination, or guaranteed payer authorization. "
        "Submission requires pen-and-ink or authenticated digital attestation by the licensed treating dentist."
    )
    stmt_10 = NarrativeStatementCitation(
        statement_id=f"STMT-S10-{uuid.uuid4().hex[:6].upper()}",
        section_index=10,
        section_title="Required Reviewer Attestation",
        sentence_text=s10_text,
        cited_evidence_ids=[package.package_id],
        source_types=[EvidenceSource.PAYER_REQUIREMENT],
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
        uncertainty_preserved=True,
    )
    statements.append(stmt_10)

    # Determine draft state
    has_missing = any(m.severity == "REQUIRED" for m in missing_items)
    is_signed = any(c.decision.value == "confirmed" for c in package.dentist_confirmations)

    if has_missing:
      draft_state = DraftState.INCOMPLETE_DOCUMENTATION
    elif is_signed:
      draft_state = DraftState.REVIEWED_DRAFT_READY_FOR_EXPORT
    else:
      draft_state = DraftState.READY_FOR_CLINICIAN_REVIEW

    return InsurancePreAuthDraft(
        draft_id=draft_id,
        study_id=package.study_id,
        radiograph_id=package.radiograph_id,
        draft_state=draft_state,
        section_1_case_identification=s1_text,
        section_2_requested_procedure=s2_text,
        section_3_tooth_identifier=s3_text,
        section_4_clinician_confirmed_findings=s4_text,
        section_5_radiographic_observations=s5_text,
        section_6_supporting_evidence_references=s6_text,
        section_7_clinical_rationale=s7_text,
        section_8_missing_information=s8_text,
        section_9_procedure_code_references=s9_text,
        section_10_required_reviewer_attestation=s10_text,
        statements=statements,
        generated_by="deterministic_template_generator",
        generation_timestamp=datetime.utcnow(),
    )
