"""Clinical Evidence, Insurance Pre-Authorization, and Audit Service for DENTRACE Level 4.

Coordinates:
1. Assembly of strongly typed ClinicalEvidencePackage.
2. Dentist confirmation, rejection, and FDI correction workflows.
3. Chairside clinical examination and symptom recording.
4. Proposed procedure selection with candidate CDT checks.
5. Deterministic documentation readiness preflight checking.
6. Traceable pre-auth draft generation (Ollama + deterministic fallback).
7. Clinician draft editing with non-overwriting protections.
8. Local PDF claim pack rendering via ReportLab.
9. Chronological audit ledger recording.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from ..config import settings
from ..database.connection import get_db
from ..schemas.clinician import ReviewDecision, PhysicalSignatureStatus
from ..schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    DentistFindingConfirmation,
    ClinicalExaminationRecord,
    PatientSymptomRecord,
    RequestedProcedureRecord,
    PayerPolicyTemplate,
    EvidenceReadinessReport,
    InsurancePreAuthDraft,
    DraftState,
    PreflightStatus,
    EvidenceSource,
    VerificationStatus,
    ClinicianReviewRequest,
    ClinicalExaminationRequest,
    PatientSymptomRequest,
    ProcedureSelectionRequest,
    PreAuthDraftUpdateRequest,
    PatientInfoPayload,
    ClaimReportRequest,
)
from ..schemas.finding import (
    AnnotationModality,
    FindingBoundingBox,
    FindingPolygon,
    PathologyClass,
    UrgencyLevel,
)
from ..clinical.evidence_engine import ClinicalEvidenceEngine
from ..clinical.narrative_generator import DeterministicNarrativeGenerator
from ..clinical.faithfulness import FaithfulnessChecker
from ..clinical.cdt_coding import CDTCodingService
from ..reporting.pdf_generator import LocalClaimPackPDFGenerator
from .ollama_service import OllamaService
from ..storage.file_manager import storage_manager

logger = logging.getLogger("dentrace.clinical_service")


class ClinicalEvidenceService:
  """Service managing clinical evidence packages, preflight, pre-auth narratives, and audit trails."""

  def __init__(self):
    self._ensure_tables()

  def _ensure_tables(self, conn=None):
    """Ensures auxiliary clinical tables exist in SQLite without altering core migrations."""
    if conn is None:
      try:
        with get_db() as c:
          self._ensure_tables(c)
      except Exception:
        pass
      return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS clinical_records (
            record_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            FOREIGN KEY(study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_clinical_records_study_id
        ON clinical_records(study_id);
        """
    )

  def get_clinical_evidence(self, study_id: str) -> ClinicalEvidencePackage:
    """Assembles the full ClinicalEvidencePackage for a study."""
    with get_db() as conn:
      self._ensure_tables(conn)
      # 1. Fetch study and radiograph
      study_row = conn.execute(
          "SELECT * FROM studies WHERE study_id = ? AND archived = 0;",
          (study_id,),
      ).fetchone()

      if not study_row:
        raise ValueError(f"Study '{study_id}' was not found.")

      rad_row = conn.execute(
          "SELECT * FROM radiographs WHERE study_id = ?;",
          (study_id,),
      ).fetchone()

      radiograph_id = rad_row["storage_rel_path"] if rad_row else "unknown_radiograph"

      # 2. Fetch AI findings
      finding_rows = conn.execute(
          "SELECT * FROM findings WHERE study_id = ?;",
          (study_id,),
      ).fetchall()

      ai_observations: list[RadiographicObservation] = []
      for f in finding_rows:
        bbox_obj = None
        if f["bbox_json"]:
          try:
            b_data = json.loads(f["bbox_json"])
            bbox_obj = FindingBoundingBox(**b_data)
          except Exception:
            pass

        poly_obj = None
        if f["polygon_json"]:
          try:
            p_data = json.loads(f["polygon_json"])
            poly_obj = FindingPolygon(**p_data)
          except Exception:
            pass

        # Check FDI uncertainty (if fdi is None or marked uncertain in evidence_json)
        fdi_uncertain = False
        unc_reason = None
        ev_data = {}
        fdi_uncertain = False
        unc_reason = None
        fdi_status = "ai_estimated"
        if f["evidence_json"]:
          try:
            ev_data = json.loads(f["evidence_json"])
            fdi_uncertain = ev_data.get("fdi_uncertain", False)
            unc_reason = ev_data.get("uncertainty_reason")
            fdi_status = ev_data.get("fdi_status", "ai_estimated")
          except Exception:
            pass

        if f["tooth_fdi"] is None:
          fdi_uncertain = True
          if not unc_reason:
            unc_reason = "Unassigned tooth proposal / ambiguous spacing"

        if f["review_status"] == "confirmed":
          fdi_status = "clinician_confirmed"
          fdi_uncertain = False

        obs = RadiographicObservation(
            evidence_id=f"EVID-RAD-{f['finding_id'][-8:]}",
            study_id=study_id,
            radiograph_id=radiograph_id,
            finding_id=f["finding_id"],
            pathology_candidate=PathologyClass(f["pathology_class"]),
            confidence=f["confidence"],
            annotation_modality=AnnotationModality(f["annotation_modality"]),
            geometry_semantics=(
                "abnormal_tooth_boundary"
                if f["annotation_modality"] == AnnotationModality.INSTANCE_SEGMENTATION.value
                else "bounding_box_detection"
            ),
            bbox=bbox_obj,
            polygon=poly_obj,
            has_mask=(poly_obj is not None),
            tooth_fdi=f["tooth_fdi"],
            fdi_uncertain=fdi_uncertain,
            fdi_uncertainty_reason=unc_reason,
            fdi_status=fdi_status,
            model_id=f["model_id"] or "liodon-panoramic-screener",
            model_version=f["model_version"] or "1.0.0",
            source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
            verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        )
        ai_observations.append(obs)

      # 3. Fetch Clinician Confirmations
      confirmations: list[DentistFindingConfirmation] = []

      # Add finding-level confirmations
      for f in finding_rows:
        if f["review_status"] in ("confirmed", "rejected", "modified"):
          decision = ReviewDecision(f["review_status"])
          v_status = (
              VerificationStatus.CONFIRMED_BY_CLINICIAN
              if decision == ReviewDecision.CONFIRMED
              else (
                  VerificationStatus.REJECTED_BY_CLINICIAN
                  if decision == ReviewDecision.REJECTED
                  else VerificationStatus.MODIFIED_BY_CLINICIAN
              )
          )
          ev_data = {}
          if f["evidence_json"]:
            try:
              ev_data = json.loads(f["evidence_json"])
            except Exception:
              pass
          reviewer = ev_data.get("confirmed_by_clinician", "Licensed Dentist")
          confirmations.append(
              DentistFindingConfirmation(
                  evidence_id=f"EVID-CFM-{f['finding_id'][-8:]}",
                  finding_id=f["finding_id"],
                  reviewer_name=reviewer,
                  license_number="VERIFIED",
                  decision=decision,
                  confirmed_fdi=f["tooth_fdi"],
                  confirmed_pathology=PathologyClass(f["pathology_class"]),
                  review_timestamp=datetime.utcnow(),
                  clinical_notes=ev_data.get("clinical_notes"),
                  verification_status=v_status,
              )
          )

      cfm_rows = conn.execute(
          "SELECT * FROM confirmations WHERE study_id = ?;",
          (study_id,),
      ).fetchall()

      for c in cfm_rows:
        decision = ReviewDecision(c["decision"])
        v_status = (
            VerificationStatus.CONFIRMED_BY_CLINICIAN
            if decision == ReviewDecision.CONFIRMED
            else (
                VerificationStatus.REJECTED_BY_CLINICIAN
                if decision == ReviewDecision.REJECTED
                else VerificationStatus.MODIFIED_BY_CLINICIAN
            )
        )

        confirmations.append(
            DentistFindingConfirmation(
                evidence_id=f"EVID-CFM-{c['confirmation_id'][-8:]}",
                finding_id="GLOBAL_STUDY_REVIEW",
                reviewer_name=c["clinician_name"],
                license_number=c["license_number"],
                decision=decision,
                confirmed_fdi=None,
                review_timestamp=c["review_timestamp"] if isinstance(c["review_timestamp"], datetime) else datetime.utcnow(),
                clinical_notes=c["clinical_notes"],
                verification_status=v_status,
            )
        )

      # 4. Fetch chairside records (examinations, symptoms, procedures)
      rec_rows = conn.execute(
          "SELECT * FROM clinical_records WHERE study_id = ? ORDER BY created_at ASC;",
          (study_id,),
      ).fetchall()

      examinations: list[ClinicalExaminationRecord] = []
      symptoms: list[PatientSymptomRecord] = []
      procedures: list[RequestedProcedureRecord] = []

      for r in rec_rows:
        try:
          p = json.loads(r["payload_json"])
          rtype = r["record_type"]
          if rtype == "examination":
            examinations.append(ClinicalExaminationRecord(**p))
          elif rtype == "symptom":
            symptoms.append(PatientSymptomRecord(**p))
          elif rtype == "procedure":
            procedures.append(RequestedProcedureRecord(**p))
        except Exception as exc:
          logger.warning(f"Error parsing clinical record {r['record_id']}: {exc}")

      # Check if patient chief complaint was on study record
      if not symptoms and study_row["clinical_indication"]:
        symptoms.append(
            PatientSymptomRecord(
                evidence_id=f"EVID-SYM-{uuid.uuid4().hex[:8].upper()}",
                chief_complaint=study_row["clinical_indication"],
            )
        )

      return ClinicalEvidencePackage(
          package_id=f"PKG-{uuid.uuid4().hex[:8].upper()}",
          study_id=study_id,
          radiograph_id=radiograph_id,
          created_at=datetime.utcnow(),
          ai_observations=ai_observations,
          dentist_confirmations=confirmations,
          clinical_examinations=examinations,
          patient_symptoms=symptoms,
          requested_procedures=procedures,
          payer_template=PayerPolicyTemplate(),
      )

  def record_clinician_review(
      self,
      study_id: str,
      finding_id: str,
      req: ClinicianReviewRequest,
  ) -> DentistFindingConfirmation:
    """Records clinician review decision on a finding and persists an audit event."""
    with get_db() as conn:
      # Check study and finding exist
      f_row = conn.execute(
          "SELECT * FROM findings WHERE study_id = ? AND finding_id = ?;",
          (study_id, finding_id),
      ).fetchone()

      if not f_row:
        raise ValueError(f"Finding '{finding_id}' in study '{study_id}' was not found.")

      conf_id = f"CONF-{uuid.uuid4().hex[:8].upper()}"
      now = datetime.utcnow()

      # Insert confirmation record
      conn.execute(
          """
          INSERT OR REPLACE INTO confirmations (
              confirmation_id, study_id, clinician_name, license_number,
              decision, review_timestamp, clinical_notes, physical_signature_status
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
          """,
          (
              conf_id,
              study_id,
              req.reviewer_name,
              req.license_number,
              req.decision.value,
              now,
              req.clinical_notes,
              PhysicalSignatureStatus.REQUIRES_PHYSICAL_SIGNATURE.value,
          ),
      )

      # Update finding status and optional corrected FDI
      fdi_to_update = req.confirmed_fdi if req.confirmed_fdi is not None else f_row["tooth_fdi"]
      pathology_to_update = req.confirmed_pathology.value if req.confirmed_pathology else f_row["pathology_class"]

      # Clear uncertainty flag if clinician confirmed the tooth FDI
      ev_dict = {}
      if f_row["evidence_json"]:
        try:
          ev_dict = json.loads(f_row["evidence_json"])
        except Exception:
          pass
      ev_dict["confirmed_by_clinician"] = req.reviewer_name
      if req.confirmed_fdi is not None:
        ev_dict["fdi_uncertain"] = False

      conn.execute(
          """
          UPDATE findings
          SET review_status = ?, tooth_fdi = ?, pathology_class = ?, evidence_json = ?
          WHERE finding_id = ?;
          """,
          (
              req.decision.value,
              fdi_to_update,
              pathology_to_update,
              json.dumps(ev_dict),
              finding_id,
          ),
      )

      # Chronological Audit Ledger
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, ?, ?, ?, ?);
          """,
          (
              audit_id,
              study_id,
              f"FINDING_{req.decision.value.upper()}",
              req.reviewer_name,
              now,
              json.dumps({
                  "finding_id": finding_id,
                  "decision": req.decision.value,
                  "confirmed_fdi": req.confirmed_fdi,
                  "confirmed_pathology": req.confirmed_pathology.value if req.confirmed_pathology else None,
                  "notes": req.clinical_notes,
              }),
          ),
      )

    v_status = (
        VerificationStatus.CONFIRMED_BY_CLINICIAN
        if req.decision == ReviewDecision.CONFIRMED
        else (
            VerificationStatus.REJECTED_BY_CLINICIAN
            if req.decision == ReviewDecision.REJECTED
            else VerificationStatus.MODIFIED_BY_CLINICIAN
        )
    )

    return DentistFindingConfirmation(
        evidence_id=f"EVID-CFM-{conf_id[-8:]}",
        finding_id=finding_id,
        reviewer_name=req.reviewer_name,
        license_number=req.license_number,
        decision=req.decision,
        confirmed_fdi=req.confirmed_fdi,
        confirmed_pathology=req.confirmed_pathology,
        review_timestamp=now,
        clinical_notes=req.clinical_notes,
        verification_status=v_status,
    )

  def record_clinical_examination(
      self,
      study_id: str,
      req: ClinicalExaminationRequest,
  ) -> ClinicalExaminationRecord:
    """Stores chairside clinical examination data and logs audit event."""
    rec_id = f"EXAM-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    exam_record = ClinicalExaminationRecord(
        evidence_id=f"EVID-EXM-{rec_id[-8:]}",
        tooth_fdi=req.tooth_fdi,
        pulp_vitality=req.pulp_vitality,
        percussion_sensitivity=req.percussion_sensitivity,
        palpation_sensitivity=req.palpation_sensitivity,
        probing_depth_mm=req.probing_depth_mm,
        mobility_grade=req.mobility_grade,
        visual_cavitation=req.visual_cavitation,
        defective_restoration=req.defective_restoration,
        swelling_or_fistula=req.swelling_or_fistula,
        recorded_by=req.recorded_by,
        recorded_at=now,
    )

    with get_db() as conn:
      self._ensure_tables(conn)
      conn.execute(
          """
          INSERT INTO clinical_records (
              record_id, study_id, record_type, payload_json, created_at, updated_at
          ) VALUES (?, ?, 'examination', ?, ?, ?);
          """,
          (rec_id, study_id, exam_record.model_dump_json(), now, now),
      )

      # Audit trail
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'CLINICAL_EXAMINATION_RECORDED', ?, ?, ?);
          """,
          (
              audit_id,
              study_id,
              req.recorded_by or "clinician",
              now,
              exam_record.model_dump_json(),
          ),
      )

    return exam_record

  def record_patient_symptoms(
      self,
      study_id: str,
      req: PatientSymptomRequest,
  ) -> PatientSymptomRecord:
    """Stores patient intake symptoms and logs audit event."""
    rec_id = f"SYM-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    sym_record = PatientSymptomRecord(
        evidence_id=f"EVID-SYM-{rec_id[-8:]}",
        chief_complaint=req.chief_complaint,
        pain_character=req.pain_character,
        pain_onset_duration=req.pain_onset_duration,
        mastication_pain=req.mastication_pain,
        recorded_at=now,
    )

    with get_db() as conn:
      self._ensure_tables(conn)
      conn.execute(
          """
          INSERT INTO clinical_records (
              record_id, study_id, record_type, payload_json, created_at, updated_at
          ) VALUES (?, ?, 'symptom', ?, ?, ?);
          """,
          (rec_id, study_id, sym_record.model_dump_json(), now, now),
      )

      # Audit trail
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'PATIENT_SYMPTOMS_RECORDED', 'intake', ?, ?);
          """,
          (audit_id, study_id, now, sym_record.model_dump_json()),
      )

    return sym_record

  def select_requested_procedure(
      self,
      study_id: str,
      req: ProcedureSelectionRequest,
  ) -> RequestedProcedureRecord:
    """Stores clinician-selected treatment procedure with CDT checks and logs audit event."""
    proc_id = f"PROC-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()

    # Rule-based consistency check if CDT code is proposed
    if req.suggested_cdt_code:
      valid, err = CDTCodingService.validate_code_consistency(
          req.suggested_cdt_code, req.procedure_name, req.tooth_fdi
      )
      if not valid:
        logger.warning(f"Procedure CDT inconsistency flagged: {err}")

    proc_record = RequestedProcedureRecord(
        procedure_id=proc_id,
        tooth_fdi=req.tooth_fdi,
        procedure_name=req.procedure_name,
        suggested_cdt_code=req.suggested_cdt_code,
        cdt_code_verified_by_dentist=req.cdt_code_verified_by_dentist,
        clinician_rationale=req.clinician_rationale,
        urgency=req.urgency,
        selected_by=req.selected_by,
    )

    with get_db() as conn:
      self._ensure_tables(conn)
      conn.execute(
          """
          INSERT INTO clinical_records (
              record_id, study_id, record_type, payload_json, created_at, updated_at
          ) VALUES (?, ?, 'procedure', ?, ?, ?);
          """,
          (proc_id, study_id, proc_record.model_dump_json(), now, now),
      )

      # Audit trail
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'PROCEDURE_SELECTED', ?, ?, ?);
          """,
          (
              audit_id,
              study_id,
              req.selected_by or "clinician",
              now,
              proc_record.model_dump_json(),
          ),
      )

    return proc_record

  def check_documentation_readiness(self, study_id: str) -> EvidenceReadinessReport:
    """Runs deterministic clinical evidence engine to produce document-readiness report."""
    package = self.get_clinical_evidence(study_id)
    # Check if radiograph image file exists locally
    with get_db() as conn:
      row = conn.execute(
          "SELECT storage_rel_path FROM radiographs WHERE study_id = ?;",
          (study_id,),
      ).fetchone()
      file_exists = False
      if row and row["storage_rel_path"]:
        p = storage_manager.get_storage_path(row["storage_rel_path"])
        file_exists = p.exists() if p else False

    return ClinicalEvidenceEngine.evaluate_package(package, radiograph_file_exists=file_exists)

  def generate_pre_auth_draft(
      self,
      study_id: str,
      force_regenerate: bool = False,
      model_tag: str = "qwen2.5:3b",
  ) -> tuple[InsurancePreAuthDraft, dict[str, Any]]:
    """Synthesizes structured 10-section pre-auth draft with traceability and audit logging."""
    package = self.get_clinical_evidence(study_id)

    # Check existing draft to prevent silent overwrite of dentist edits
    with get_db() as conn:
      existing = conn.execute(
          "SELECT * FROM insurance_drafts WHERE study_id = ?;",
          (study_id,),
      ).fetchone()

      if existing and existing["narrative_json"]:
        try:
          d_obj = json.loads(existing["narrative_json"])
          if d_obj.get("draft_state") == DraftState.CLINICIAN_REVISED.value and not force_regenerate:
            raise ValueError(
                "Cannot overwrite a clinician-edited draft. Set force_regenerate=true to override."
            )
        except json.JSONDecodeError:
          pass

    # Generate draft via Ollama or fallback
    ollama_service = OllamaService()
    draft, metrics = ollama_service.generate_pre_auth_draft(package, model_tag=model_tag)

    # Persist draft to SQLite
    now = datetime.utcnow()
    with get_db() as conn:
      conn.execute(
          """
          INSERT OR REPLACE INTO insurance_drafts (
              draft_id, study_id, status, narrative_summary, narrative_json,
              suggested_cdt_codes_json, regulatory_disclaimer, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
          """,
          (
              draft.draft_id,
              study_id,
              draft.draft_state.value,
              draft.section_7_clinical_rationale,
              draft.model_dump_json(),
              json.dumps([p.suggested_cdt_code for p in package.requested_procedures if p.suggested_cdt_code]),
              draft.disclaimer,
              now,
              now,
          ),
      )

      # Audit trail
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'PRE_AUTH_DRAFT_GENERATED', ?, ?, ?);
          """,
          (
              audit_id,
              study_id,
              metrics["engine_used"],
              now,
              json.dumps({
                  "draft_id": draft.draft_id,
                  "draft_state": draft.draft_state.value,
                  "latency_ms": metrics.get("generation_latency_ms", 0.0),
              }),
          ),
      )

    return draft, metrics

  def get_pre_auth_draft(self, study_id: str) -> Optional[InsurancePreAuthDraft]:
    """Retrieves existing pre-authorization draft for a study, or None if not generated."""
    with get_db() as conn:
      row = conn.execute(
          "SELECT * FROM insurance_drafts WHERE study_id = ?;",
          (study_id,),
      ).fetchone()

      if not row or not row["narrative_json"]:
        return None

      data = json.loads(row["narrative_json"])
      return InsurancePreAuthDraft(**data)

  def update_pre_auth_draft(
      self,
      study_id: str,
      req: PreAuthDraftUpdateRequest,
  ) -> InsurancePreAuthDraft:
    """Allows clinician to edit any section of the draft, marking state as CLINICIAN_REVISED."""
    draft = self.get_pre_auth_draft(study_id)
    if not draft:
      raise ValueError(f"No draft found for study '{study_id}'. Generate a draft first.")

    now = datetime.utcnow()

    # Apply updates
    if req.section_1_case_identification is not None:
      draft.section_1_case_identification = req.section_1_case_identification
    if req.section_2_requested_procedure is not None:
      draft.section_2_requested_procedure = req.section_2_requested_procedure
    if req.section_3_tooth_identifier is not None:
      draft.section_3_tooth_identifier = req.section_3_tooth_identifier
    if req.section_4_clinician_confirmed_findings is not None:
      draft.section_4_clinician_confirmed_findings = req.section_4_clinician_confirmed_findings
    if req.section_5_radiographic_observations is not None:
      draft.section_5_radiographic_observations = req.section_5_radiographic_observations
    if req.section_6_supporting_evidence_references is not None:
      draft.section_6_supporting_evidence_references = req.section_6_supporting_evidence_references
    if req.section_7_clinical_rationale is not None:
      draft.section_7_clinical_rationale = req.section_7_clinical_rationale
    if req.section_8_missing_information is not None:
      draft.section_8_missing_information = req.section_8_missing_information
    if req.section_9_procedure_code_references is not None:
      draft.section_9_procedure_code_references = req.section_9_procedure_code_references
    if req.section_10_required_reviewer_attestation is not None:
      draft.section_10_required_reviewer_attestation = req.section_10_required_reviewer_attestation

    draft.draft_state = DraftState.CLINICIAN_REVISED
    draft.last_edited_by_dentist = req.dentist_name
    draft.last_edited_at = now
    draft.dentist_reviewed = True

    with get_db() as conn:
      conn.execute(
          """
          UPDATE insurance_drafts
          SET status = ?, narrative_summary = ?, narrative_json = ?, updated_at = ?
          WHERE study_id = ?;
          """,
          (
              draft.draft_state.value,
              draft.section_7_clinical_rationale,
              draft.model_dump_json(),
              now,
              study_id,
          ),
      )

      # Audit event
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'PRE_AUTH_DRAFT_REVISED', ?, ?, ?);
          """,
          (
              audit_id,
              study_id,
              req.dentist_name,
              now,
              json.dumps({"editor": req.dentist_name, "license": req.license_number}),
          ),
      )

    return draft

  def save_patient_info(
      self,
      study_id: str,
      info: PatientInfoPayload,
  ) -> PatientInfoPayload:
    """Stores structured patient demographics and clinical intake data without logging PHI."""
    with get_db() as conn:
      self._ensure_tables(conn)
      s_row = conn.execute(
          "SELECT * FROM studies WHERE study_id = ?;", (study_id,)
      ).fetchone()
      if not s_row:
        raise ValueError(f"Study '{study_id}' was not found.")

      rec_id = f"REC-PAT-{uuid.uuid4().hex[:8].upper()}"
      now = datetime.utcnow()

      existing = conn.execute(
          "SELECT record_id FROM clinical_records WHERE study_id = ? AND record_type = 'patient_info';",
          (study_id,),
      ).fetchone()

      payload_json = info.model_dump_json()
      if existing:
        conn.execute(
            "UPDATE clinical_records SET payload_json = ?, updated_at = ? WHERE record_id = ?;",
            (payload_json, now, existing["record_id"]),
        )
      else:
        conn.execute(
            """
            INSERT INTO clinical_records (
                record_id, study_id, record_type, payload_json, created_at, updated_at
            ) VALUES (?, ?, 'patient_info', ?, ?, ?);
            """,
            (rec_id, study_id, payload_json, now, now),
        )

      # Update study acquisition_date and clinical_indication without logging patient name
      conn.execute(
          """
          UPDATE studies
          SET acquisition_date = ?, clinical_indication = ?, updated_at = ?
          WHERE study_id = ?;
          """,
          (info.scan_date, info.chief_complaint or s_row["clinical_indication"], now, study_id),
      )

      # Audit event (Strict Privacy: Log case identifier and timestamps only, NEVER patient name)
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'PATIENT_INFO_RECORDED', 'chairside', ?, ?);
          """,
          (
              audit_id,
              study_id,
              now,
              json.dumps({"patient_id": info.patient_id, "age": info.age, "scan_date": info.scan_date}),
          ),
      )

    return info

  def get_patient_info(self, study_id: str) -> Optional[PatientInfoPayload]:
    """Retrieves persisted patient intake demographics for a study."""
    with get_db() as conn:
      self._ensure_tables(conn)
      row = conn.execute(
          """
          SELECT payload_json FROM clinical_records
          WHERE study_id = ? AND record_type = 'patient_info'
          ORDER BY updated_at DESC LIMIT 1;
          """,
          (study_id,),
      ).fetchone()

      if not row:
        return None

      try:
        return PatientInfoPayload.model_validate_json(row["payload_json"])
      except Exception:
        return None

  def export_claim_pack_pdf(
      self,
      study_id: str,
      patient_info: Optional[PatientInfoPayload] = None,
      custom_narrative: Optional[str] = None,
      snapshot_3d_bytes: Optional[bytes] = None,
      selected_fdi: Optional[int] = None,
      selected_pathology: Optional[str] = None,
      output_path: Optional[str] = None,
  ) -> bytes:
    """Generates presentation-ready local ReportLab PDF claim pack."""
    package = self.get_clinical_evidence(study_id)
    readiness = self.check_documentation_readiness(study_id)

    # Use stored patient_info if not explicitly passed
    if not patient_info:
      patient_info = self.get_patient_info(study_id)

    draft = self.get_pre_auth_draft(study_id)
    if not draft:
      # Generate initial template draft if none exists
      draft = DeterministicNarrativeGenerator.generate_draft(package)

    pdf_bytes = LocalClaimPackPDFGenerator.generate_claim_pack_pdf(
        package=package,
        draft=draft,
        readiness=readiness,
        patient_info=patient_info,
        custom_narrative=custom_narrative,
        snapshot_3d_bytes=snapshot_3d_bytes,
        selected_fdi=selected_fdi,
        selected_pathology=selected_pathology,
        output_path=output_path,
    )

    # Audit event
    now = datetime.utcnow()
    with get_db() as conn:
      audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'CLAIM_PACK_PDF_EXPORTED', 'system', ?, ?);
          """,
          (
              audit_id,
              study_id,
              now,
              json.dumps({"pdf_size_bytes": len(pdf_bytes), "output_path": output_path}),
          ),
      )

    return pdf_bytes

  def get_audit_history(self, study_id: str) -> list[dict[str, Any]]:
    """Returns chronological audit trail for a study."""
    with get_db() as conn:
      rows = conn.execute(
          "SELECT * FROM audit_events WHERE study_id = ? ORDER BY timestamp ASC;",
          (study_id,),
      ).fetchall()

      events = []
      for r in rows:
        payload = {}
        if r["payload_json"]:
          try:
            payload = json.loads(r["payload_json"])
          except Exception:
            payload = {"raw": r["payload_json"]}

        events.append({
            "event_id": r["event_id"],
            "study_id": r["study_id"],
            "event_type": r["event_type"],
            "actor": r["actor"],
            "timestamp": r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"]),
            "payload": payload,
        })
      return events


clinical_service = ClinicalEvidenceService()
