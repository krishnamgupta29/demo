"""Missing Evidence Detective for DENTRACE Clinical Intelligence.

Identifies missing documentation, examination tests, and confirmations
BEFORE claim narrative generation.
Strictly separates:
- Radiographic observations
- Clinically confirmed diagnoses
- Proposed treatments
- Payer documentation requirements
"""

import uuid
from typing import Optional
from ..schemas.finding import PathologyClass
from ..schemas.evidence import (
    ClinicalEvidencePackage,
    MissingEvidenceItem,
    EvidenceSource,
    VerificationStatus,
)


class MissingEvidenceDetective:
  """Deterministic checklist detective generating targeted documentation questions."""

  @classmethod
  def detect_missing_evidence(
      cls,
      package: ClinicalEvidencePackage,
  ) -> list[MissingEvidenceItem]:
    """Inspects a ClinicalEvidencePackage and returns an itemized checklist of missing clinical items."""
    missing: list[MissingEvidenceItem] = []

    # 1. Inspect AI radiographic observations
    for obs in package.ai_observations:
      # Tooth FDI confirmation check
      fdi = obs.tooth_fdi
      fdi_confirmed = False

      # Check if any dentist confirmation matches this finding
      matching_cfms = [
          c for c in package.dentist_confirmations
          if c.finding_id == obs.finding_id
      ]

      if not matching_cfms:
        readable_path = obs.pathology_candidate.value.replace("_", " ")
        missing.append(
            MissingEvidenceItem(
                item_id=f"MISS-CFM-{uuid.uuid4().hex[:8].upper()}",
                target_field="dentist_finding_review",
                target_tooth_fdi=fdi,
                clinical_reason=(
                    f"AI observation of suspected {readable_path} requires "
                    "licensed dentist clinical review and verification."
                ),
                question_prompt=(
                    f"Please review suspected {readable_path} "
                    f"associated with tooth {fdi if fdi else 'unspecified'} and confirm, modify, or reject."
                ),
                severity="REQUIRED",
            )
        )
      else:
        for cfm in matching_cfms:
          if cfm.confirmed_fdi is not None:
            fdi = cfm.confirmed_fdi
            fdi_confirmed = True

      # If tooth number is unknown, unconfirmed, or flagged uncertain
      if obs.fdi_uncertain or fdi is None or not fdi_confirmed:
        missing.append(
            MissingEvidenceItem(
                item_id=f"MISS-FDI-{uuid.uuid4().hex[:8].upper()}",
                target_field="tooth_fdi_confirmation",
                target_tooth_fdi=fdi,
                clinical_reason=(
                    "FDI tooth numbering is uncertain or unverified. Pre-authorization cannot "
                    "attribute procedures to ambiguous tooth numbers."
                ),
                question_prompt=(
                    f"Please confirm or assign the authoritative FDI tooth number (11-48) for finding {obs.finding_id}."
                ),
                severity="REQUIRED",
            )
        )

    # 2. Inspect requested procedures and procedure-specific documentation
    if not package.requested_procedures:
      missing.append(
          MissingEvidenceItem(
              item_id=f"MISS-PROC-{uuid.uuid4().hex[:8].upper()}",
              target_field="requested_procedure",
              target_tooth_fdi=None,
              clinical_reason="No clinical procedure has been proposed for pre-authorization review.",
              question_prompt="Please select the proposed dental treatment procedure.",
              severity="REQUIRED",
          )
      )
    else:
      for proc in package.requested_procedures:
        p_name = proc.procedure_name.lower()
        p_fdi = proc.tooth_fdi

        # Rationale check
        if not proc.clinician_rationale or len(proc.clinician_rationale.strip()) < 10:
          missing.append(
              MissingEvidenceItem(
                  item_id=f"MISS-RAT-{uuid.uuid4().hex[:8].upper()}",
                  target_field="clinician_rationale",
                  target_tooth_fdi=p_fdi,
                  clinical_reason="Payer pre-authorization requires explicit clinical rationale from the treating dentist.",
                  question_prompt=f"Please state the clinical justification and prognosis for {proc.procedure_name} on tooth {p_fdi}.",
                  severity="REQUIRED",
              )
          )

        # Candidate CDT check
        if proc.suggested_cdt_code and not proc.cdt_code_verified_by_dentist:
          missing.append(
              MissingEvidenceItem(
                  item_id=f"MISS-CDT-{uuid.uuid4().hex[:8].upper()}",
                  target_field="cdt_code_verification",
                  target_tooth_fdi=p_fdi,
                  clinical_reason="Suggested CDT code must be explicitly attested by the treating clinician.",
                  question_prompt=f"Please verify whether CDT code {proc.suggested_cdt_code} appropriately reflects the proposed clinical procedure.",
                  severity="REQUIRED",
              )
          )

        # Check examination records for target tooth
        matching_exams = [
            e for e in package.clinical_examinations
            if e.tooth_fdi == p_fdi or (e.tooth_fdi is None and p_fdi is not None)
        ]
        exam = matching_exams[0] if matching_exams else None

        # Procedure-specific checklists
        # A. Endodontics (Root canal therapy)
        if "endodontic" in p_name or "root canal" in p_name or (proc.suggested_cdt_code and proc.suggested_cdt_code.startswith("D33")):
          # Pulp vitality
          if not exam or exam.pulp_vitality in (None, "not_tested", ""):
            missing.append(
                MissingEvidenceItem(
                    item_id=f"MISS-PULP-{uuid.uuid4().hex[:8].upper()}",
                    target_field="pulp_vitality",
                    target_tooth_fdi=p_fdi,
                    clinical_reason="Endodontic therapy requires recorded pulp vitality testing (cold, thermal, or EPT) to substantiate pulp necrosis or irreversible pulpitis.",
                    question_prompt=f"What was the pulp vitality test result on tooth {p_fdi} (responsive, non-vital, delayed)?",
                    severity="REQUIRED",
                )
            )

          # Percussion sensitivity
          if not exam or exam.percussion_sensitivity is None:
            missing.append(
                MissingEvidenceItem(
                    item_id=f"MISS-PERC-{uuid.uuid4().hex[:8].upper()}",
                    target_field="percussion_sensitivity",
                    target_tooth_fdi=p_fdi,
                    clinical_reason="Apical periodontitis documentation requires testing for percussion tenderness.",
                    question_prompt=f"Does tooth {p_fdi} exhibit tenderness to vertical or lateral percussion?",
                    severity="REQUIRED",
                )
            )

          # Intraoral periapical radiograph mandate (OPG screening limitation)
          missing.append(
              MissingEvidenceItem(
                  item_id=f"MISS-IOPA-{uuid.uuid4().hex[:8].upper()}",
                  target_field="intraoral_periapical_radiograph",
                  target_tooth_fdi=p_fdi,
                  clinical_reason=(
                      "Mandatory Modality Rule: Panoramic radiographs have focal trough distortion. "
                      "Endodontic therapy pre-authorization requires an intraoral periapical (IOPA) radiograph for root apex visualization."
                  ),
                  question_prompt=f"Has an intraoral periapical radiograph been taken and attached for tooth {p_fdi}?",
                  severity="REQUIRED",
              )
          )

        # B. Restorative (Composite or Amalgam)
        elif "composite" in p_name or "amalgam" in p_name or "restoration" in p_name or (proc.suggested_cdt_code and proc.suggested_cdt_code.startswith("D2")):
          if not exam or exam.visual_cavitation is None:
            missing.append(
                MissingEvidenceItem(
                    item_id=f"MISS-CAV-{uuid.uuid4().hex[:8].upper()}",
                    target_field="visual_cavitation",
                    target_tooth_fdi=p_fdi,
                    clinical_reason="Restorative pre-authorization requires confirmation of structural cavitation or dentin involvement beyond the enamel junction.",
                    question_prompt=f"Has physical cavitation or dentinal soft decay been verified on tooth {p_fdi}?",
                    severity="REQUIRED",
                )
            )

        # C. Oral Surgery / Extraction
        elif "extraction" in p_name or "surgical" in p_name or (proc.suggested_cdt_code and proc.suggested_cdt_code.startswith("D7")):
          if not exam or (exam.mobility_grade is None and not exam.defective_restoration and not exam.visual_cavitation):
            missing.append(
                MissingEvidenceItem(
                    item_id=f"MISS-SURG-{uuid.uuid4().hex[:8].upper()}",
                    target_field="surgical_indication_details",
                    target_tooth_fdi=p_fdi,
                    clinical_reason="Payer pre-authorization for extraction requires structural non-restorability, severe mobility grade, or impaction pathology.",
                    question_prompt=f"What is the structural or periodontal reason tooth {p_fdi} cannot be restored (mobility, root fracture, deep subgingival caries)?",
                    severity="RECOMMENDED",
                )
            )

        # D. Periodontics
        elif "scaling" in p_name or "periodontal" in p_name or (proc.suggested_cdt_code and proc.suggested_cdt_code.startswith("D4")):
          if not exam or exam.probing_depth_mm is None or exam.probing_depth_mm < 4.0:
            missing.append(
                MissingEvidenceItem(
                    item_id=f"MISS-PROBE-{uuid.uuid4().hex[:8].upper()}",
                    target_field="probing_depth_mm",
                    target_tooth_fdi=p_fdi,
                    clinical_reason="Periodontal scaling pre-authorization requires documented periodontal pocket depths >= 4mm.",
                    question_prompt="Please provide the periodontal pocket probing depth measurements (mm) for the affected teeth.",
                    severity="REQUIRED",
                )
            )

    # 3. Patient symptoms check
    if not package.patient_symptoms or (
        not package.patient_symptoms[0].chief_complaint
        and not package.patient_symptoms[0].pain_character
    ):
      missing.append(
          MissingEvidenceItem(
              item_id=f"MISS-SYM-{uuid.uuid4().hex[:8].upper()}",
              target_field="patient_symptoms",
              target_tooth_fdi=None,
              clinical_reason="Patient-reported symptoms and chief complaint establish clinical necessity and urgency.",
              question_prompt="Are there any patient-reported symptoms (pain duration, temperature sensitivity, chewing discomfort)?",
              severity="RECOMMENDED",
          )
      )

    return missing
