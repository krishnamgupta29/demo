"""Deterministic Clinical Evidence Engine for DENTRACE Level 4.

AUTHORITATIVE GOVERNANCE:
Runs BEFORE the language model.
Validates clinical facts, detects contradictions, isolates unconfirmed tooth IDs,
and produces a structured EvidenceReadinessReport.

MANDATORY CLINICAL BOUNDARIES:
- Does NOT autonomously establish diagnoses, medical necessity, or treatment urgency.
- Does NOT guarantee insurance coverage or reimbursement.
- Distinguishes AI radiographic observations from dentist-confirmed clinical findings.
- Preserves missing facts as 'MISSING_EVIDENCE' instead of fabricating defaults.
"""

from datetime import datetime
from typing import Optional
from ..schemas.evidence import (
    ClinicalEvidencePackage,
    EvidenceReadinessReport,
    PreflightStatus,
    MissingEvidenceItem,
    VerificationStatus,
    EvidenceSource,
)
from ..schemas.finding import PathologyClass
from .detective import MissingEvidenceDetective
from .cdt_coding import CDTCodingService


class ClinicalEvidenceEngine:
  """Authoritative deterministic rule engine validating evidence integrity prior to LLM drafting."""

  @classmethod
  def evaluate_package(
      cls,
      package: ClinicalEvidencePackage,
      radiograph_file_exists: bool = True,
  ) -> EvidenceReadinessReport:
    """Executes deterministic validation checks on a ClinicalEvidencePackage."""
    passed_checks: list[str] = []
    failed_checks: list[str] = []
    contradictions: list[str] = []
    unconfirmed_tooth_ids: set[int] = set()

    # Total check weights for checklist completeness percentage
    total_checks = 0
    passed_count = 0

    # 1. Radiographic Evidence Availability
    total_checks += 1
    if package.radiograph_id and radiograph_file_exists:
      passed_checks.append("Radiographic image evidence is staged and accessible locally.")
      passed_count += 1
    else:
      failed_checks.append("Radiographic image file is missing or inaccessible.")

    # 2. Source Finding Validation & FDI Numbering Confirmation
    total_checks += 1
    has_unconfirmed_findings = False

    # Map confirmed finding IDs
    confirmations_by_finding = {
        cfm.finding_id: cfm for cfm in package.dentist_confirmations
    }

    for obs in package.ai_observations:
      cfm = confirmations_by_finding.get(obs.finding_id)
      # Check tooth confirmation
      if obs.tooth_fdi is not None:
        if obs.fdi_uncertain:
          unconfirmed_tooth_ids.add(obs.tooth_fdi)
          has_unconfirmed_findings = True
        elif not cfm or cfm.confirmed_fdi is None:
          unconfirmed_tooth_ids.add(obs.tooth_fdi)
          has_unconfirmed_findings = True
      else:
        # FDI is None (uncertain)
        has_unconfirmed_findings = True

    if not has_unconfirmed_findings and package.ai_observations:
      passed_checks.append("All detected anatomical tooth identifiers are verified by a clinician.")
      passed_count += 1
    else:
      failed_checks.append(
          f"Contains unconfirmed, ambiguous, or shifted tooth numbering: {sorted(list(unconfirmed_tooth_ids)) if unconfirmed_tooth_ids else 'unassigned'}"
      )

    # 3. Clinician Review Decision Check
    total_checks += 1
    unreviewed_count = len([
        obs for obs in package.ai_observations
        if obs.finding_id not in confirmations_by_finding
    ])
    if unreviewed_count == 0 and package.ai_observations:
      passed_checks.append("All AI radiographic observations have been reviewed by a licensed clinician.")
      passed_count += 1
    else:
      failed_checks.append(f"{unreviewed_count} AI radiographic observations are pending clinician review.")

    # 4. Procedure Selection & Clinical Indication Check
    total_checks += 1
    if package.requested_procedures:
      passed_checks.append(f"{len(package.requested_procedures)} requested dental procedure(s) specified.")
      passed_count += 1
    else:
      failed_checks.append("No clinical procedure has been selected.")

    # 5. Clinician Rationale Check
    total_checks += 1
    procedures_with_rationale = [
        p for p in package.requested_procedures
        if p.clinician_rationale and len(p.clinician_rationale.strip()) >= 10
    ]
    if package.requested_procedures and len(procedures_with_rationale) == len(package.requested_procedures):
      passed_checks.append("All requested procedures include objective clinical rationale from the clinician.")
      passed_count += 1
    else:
      failed_checks.append("Missing clinician treatment rationale for one or more requested procedures.")

    # 6. Contradiction Detection & Unsupported Medical Statements
    total_checks += 1
    contradictions_found = False

    # Check each procedure against recorded evidence
    for proc in package.requested_procedures:
      p_fdi = proc.tooth_fdi
      p_name = proc.procedure_name.lower()

      # Contradiction A: Procedure requested on tooth with rejected finding
      for obs in package.ai_observations:
        if obs.tooth_fdi == p_fdi:
          cfm = confirmations_by_finding.get(obs.finding_id)
          if cfm and cfm.decision.value == "rejected":
            contradictions.append(
                f"Contradiction: Procedure '{proc.procedure_name}' requested for tooth {p_fdi}, "
                f"but the associated finding ({obs.pathology_candidate.value}) was explicitly REJECTED by the clinician."
            )
            contradictions_found = True

      # Contradiction B: Endodontics on normal vital tooth without deep caries / periapical lesion
      if "endodontic" in p_name or "root canal" in p_name:
        exams_for_tooth = [e for e in package.clinical_examinations if e.tooth_fdi == p_fdi]
        vitality = exams_for_tooth[0].pulp_vitality if exams_for_tooth else None
        has_deep_caries = any(
            obs.tooth_fdi == p_fdi and obs.pathology_candidate in (PathologyClass.DEEP_CARIES, PathologyClass.PERIAPICAL_LESION)
            for obs in package.ai_observations
        ) or any(
            cfm.confirmed_fdi == p_fdi and cfm.confirmed_pathology in (PathologyClass.DEEP_CARIES, PathologyClass.PERIAPICAL_LESION)
            for cfm in package.dentist_confirmations
        )
        if vitality == "responsive" and not has_deep_caries:
          contradictions.append(
              f"Contradiction: Endodontic therapy requested for tooth {p_fdi}, "
              "but pulp vitality is documented as normal/responsive with no radiographic deep caries or periapical lesion."
          )
          contradictions_found = True

      # Contradiction C: CDT code mismatch with anatomy or procedure
      if proc.suggested_cdt_code:
        valid_code, err_msg = CDTCodingService.validate_code_consistency(
            proc.suggested_cdt_code, proc.procedure_name, p_fdi
        )
        if not valid_code and err_msg:
          contradictions.append(f"CDT Inconsistency: {err_msg}")
          contradictions_found = True

    if not contradictions_found:
      passed_checks.append("Zero factual or clinical contradictions detected.")
      passed_count += 1
    else:
      failed_checks.extend(contradictions)

    # 7. Detective Missing Evidence Checklist
    missing_items = MissingEvidenceDetective.detect_missing_evidence(package)

    total_checks += 1
    if not missing_items:
      passed_checks.append("All clinical checklist requirements are satisfied.")
      passed_count += 1
    else:
      failed_checks.append(f"{len(missing_items)} required clinical evidence item(s) are missing.")

    # Calculate checklist completeness score (0 to 100%)
    completeness_pct = round((passed_count / max(1, total_checks)) * 100.0, 1)

    # Determine Preflight Status
    # Critical hierarchy:
    # 1. BLOCKED_BY_UNCONFIRMED_TOOTH if target teeth are unconfirmed
    # 2. INCOMPLETE_DOCUMENTATION if required fields or missing items exist
    # 3. REQUIRES_CODE_VERIFICATION if CDT code unverified
    # 4. READY_FOR_CLINICIAN_REVIEW if ready for dentist inspection
    # 5. REVIEWED_DRAFT_READY_FOR_EXPORT if already signed and fully verified

    target_procedure_teeth = {p.tooth_fdi for p in package.requested_procedures if p.tooth_fdi is not None}
    blocked_by_tooth = bool(target_procedure_teeth.intersection(unconfirmed_tooth_ids)) or (
        bool(package.requested_procedures) and any(p.tooth_fdi is None for p in package.requested_procedures)
    )

    unverified_cdt = any(
        p.suggested_cdt_code and not p.cdt_code_verified_by_dentist
        for p in package.requested_procedures
    )

    if blocked_by_tooth:
      preflight_status = PreflightStatus.BLOCKED_BY_UNCONFIRMED_TOOTH
      can_generate_draft = False
      can_export = False
    elif contradictions:
      preflight_status = PreflightStatus.INCOMPLETE_DOCUMENTATION
      can_generate_draft = False
      can_export = False
    elif missing_items:
      # If missing required items
      has_required_missing = any(m.severity == "REQUIRED" for m in missing_items)
      if has_required_missing:
        preflight_status = PreflightStatus.INCOMPLETE_DOCUMENTATION
        # Can still generate an incomplete review draft so clinician can see what's missing
        can_generate_draft = True
        can_export = False
      else:
        preflight_status = PreflightStatus.REQUIRES_ADDITIONAL_EVIDENCE
        can_generate_draft = True
        can_export = False
    elif unverified_cdt:
      preflight_status = PreflightStatus.REQUIRES_CODE_VERIFICATION
      can_generate_draft = True
      can_export = False
    else:
      # Check if dentist has signed
      dentist_signed = any(
          cfm.decision.value == "confirmed" for cfm in package.dentist_confirmations
      )
      if dentist_signed and completeness_pct >= 90.0:
        preflight_status = PreflightStatus.REVIEWED_DRAFT_READY_FOR_EXPORT
        can_generate_draft = True
        can_export = True
      else:
        preflight_status = PreflightStatus.READY_FOR_CLINICIAN_REVIEW
        can_generate_draft = True
        can_export = False

    return EvidenceReadinessReport(
        study_id=package.study_id,
        preflight_status=preflight_status,
        checklist_completeness_pct=completeness_pct,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        missing_evidence=missing_items,
        unconfirmed_tooth_ids=sorted(list(unconfirmed_tooth_ids)),
        contradictions_detected=contradictions,
        can_generate_draft=can_generate_draft,
        can_export_reviewed_pack=can_export,
    )
