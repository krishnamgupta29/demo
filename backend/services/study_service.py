"""Study lifecycle service: registration, retrieval, archiving, and audit logging."""

from datetime import datetime
import json
from typing import Optional
import uuid
from backend.database.connection import get_db
from backend.schemas.clinician import (
    ClinicianConfirmation,
    PhysicalSignatureStatus,
    ReviewDecision,
)
from backend.schemas.finding import (
    AnnotationModality,
    ClinicalEvidence,
    FindingBoundingBox,
    FindingPolygon,
    PathologyClass,
    PathologyFinding,
    UrgencyLevel,
)
from backend.schemas.study import (
    ImageQualityAssessment,
    RadiographMetadata,
    StudyDetail,
    StudyList,
    StudyResponse,
    StudyStatus,
)
from backend.schemas.tooth import ToothBox
from backend.storage.file_manager import storage_manager


class StudyService:
  """Coordinates study intake, database records, file operations, and audit trails."""

  def create_study(
      self,
      raw_bytes: bytes,
      original_filename: str,
      patient_anonymous_id: Optional[str] = None,
      clinical_indication: Optional[str] = None,
      acquisition_date: Optional[str] = None,
  ) -> StudyResponse:
    """Ingest a new dental radiograph, persist files, and record in database."""
    study_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    patient_id = patient_anonymous_id or f"PT-{uuid.uuid4().hex[:6].upper()}"

    # 1. Process and store image file
    metadata, quality = storage_manager.save_upload(
        study_id=study_id,
        raw_bytes=raw_bytes,
        original_filename=original_filename,
    )

    now = datetime.utcnow()

    # 2. Persist study and radiograph in SQLite transaction
    with get_db() as conn:
      conn.execute(
          """
                INSERT INTO studies (
                    study_id, patient_anonymous_id, status, acquisition_date,
                    clinical_indication, created_at, updated_at, archived
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0);
                """,
          (
              study_id,
              patient_id,
              StudyStatus.INGESTED.value,
              acquisition_date,
              clinical_indication,
              now,
              now,
          ),
      )

      conn.execute(
          """
                INSERT INTO radiographs (
                    study_id, original_filename, storage_rel_path, preview_rel_path,
                    file_size_bytes, sha256_hash, mime_type, width_px, height_px,
                    aspect_ratio, is_dicom, metadata_sanitized, blur_score,
                    aspect_ratio_valid, resolution_valid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
          (
              study_id,
              metadata.original_filename,
              metadata.storage_rel_path,
              metadata.preview_rel_path,
              metadata.file_size_bytes,
              metadata.sha256_hash,
              metadata.mime_type,
              metadata.width_px,
              metadata.height_px,
              metadata.aspect_ratio,
              1 if metadata.is_dicom else 0,
              1 if metadata.metadata_sanitized else 0,
              quality.blur_score_variance,
              1 if quality.aspect_ratio_valid else 0,
              1 if quality.resolution_valid else 0,
          ),
      )

      # 3. Log initial intake audit event
      conn.execute(
          """
                INSERT INTO audit_events (
                    event_id, study_id, event_type, actor, timestamp, payload_json
                ) VALUES (?, ?, 'STUDY_INTAKE', 'intake_system', ?, ?);
                """,
          (
              f"AUD-{uuid.uuid4().hex[:8].upper()}",
              study_id,
              now,
              json.dumps({
                  "filename": metadata.original_filename,
                  "sha256": metadata.sha256_hash,
                  "quality_passed": quality.passed,
              }),
          ),
      )

    return StudyResponse(
        study_id=study_id,
        patient_anonymous_id=patient_id,
        status=StudyStatus.INGESTED,
        created_at=now,
        radiograph=metadata,
        quality=quality,
    )

  def get_study(self, study_id: str) -> Optional[StudyDetail]:
    """Retrieve complete study detail including teeth, findings, and confirmation."""
    with get_db() as conn:
      row = conn.execute(
          """
                SELECT s.study_id, s.patient_anonymous_id, s.status, s.created_at, s.archived,
                       r.original_filename, r.storage_rel_path, r.preview_rel_path,
                       r.file_size_bytes, r.sha256_hash, r.mime_type, r.width_px,
                       r.height_px, r.aspect_ratio, r.is_dicom, r.metadata_sanitized,
                       r.blur_score, r.aspect_ratio_valid, r.resolution_valid
                FROM studies s
                JOIN radiographs r ON s.study_id = r.study_id
                WHERE s.study_id = ?;
                """,
          (study_id,),
      ).fetchone()

      if not row:
        return None

      # Fetch teeth
      teeth_rows = conn.execute(
          """
                SELECT fdi_number, x_min, y_min, x_max, y_max, confidence
                FROM teeth WHERE study_id = ? ORDER BY fdi_number;
                """,
          (study_id,),
      ).fetchall()

      teeth = [
          ToothBox(
              fdi_number=t["fdi_number"],
              x_min=t["x_min"],
              y_min=t["y_min"],
              x_max=t["x_max"],
              y_max=t["y_max"],
              confidence=t["confidence"],
          )
          for t in teeth_rows
      ]

      # Fetch findings
      finding_rows = conn.execute(
          """
                SELECT finding_id, study_id, tooth_fdi, pathology_class,
                       annotation_modality, confidence, urgency, bbox_json,
                       polygon_json, evidence_json, suggested_procedure, demo_cdt_code
                FROM findings WHERE study_id = ?;
                """,
          (study_id,),
      ).fetchall()

      findings = []
      for f in finding_rows:
        bbox = (
            FindingBoundingBox(**json.loads(f["bbox_json"]))
            if f["bbox_json"]
            else None
        )
        polygon = (
            FindingPolygon(**json.loads(f["polygon_json"]))
            if f["polygon_json"]
            else None
        )
        evidence = (
            ClinicalEvidence(**json.loads(f["evidence_json"]))
            if f["evidence_json"]
            else ClinicalEvidence()
        )

        findings.append(
            PathologyFinding(
                finding_id=f["finding_id"],
                study_id=f["study_id"],
                tooth_fdi=f["tooth_fdi"],
                pathology_class=PathologyClass(f["pathology_class"]),
                annotation_modality=AnnotationModality(f["annotation_modality"]),
                confidence=f["confidence"],
                urgency=UrgencyLevel(f["urgency"]),
                bbox=bbox,
                polygon=polygon,
                evidence=evidence,
                suggested_procedure=f["suggested_procedure"],
                demo_cdt_code=f["demo_cdt_code"],
            )
        )

      # Fetch confirmation
      conf_row = conn.execute(
          """
                SELECT confirmation_id, clinician_name, license_number, decision,
                       review_timestamp, clinical_notes, physical_signature_status
                FROM confirmations WHERE study_id = ?;
                """,
          (study_id,),
      ).fetchone()

      confirmation = None
      if conf_row:
        confirmation = ClinicianConfirmation(
            confirmation_id=conf_row["confirmation_id"],
            clinician_name=conf_row["clinician_name"],
            license_number=conf_row["license_number"],
            decision=ReviewDecision(conf_row["decision"]),
            review_timestamp=conf_row["review_timestamp"],
            clinical_notes=conf_row["clinical_notes"],
            physical_signature_status=PhysicalSignatureStatus(
                conf_row["physical_signature_status"]
            ),
        )

      metadata = RadiographMetadata(
          original_filename=row["original_filename"],
          storage_rel_path=row["storage_rel_path"],
          preview_rel_path=row["preview_rel_path"],
          file_size_bytes=row["file_size_bytes"],
          sha256_hash=row["sha256_hash"],
          mime_type=row["mime_type"],
          width_px=row["width_px"],
          height_px=row["height_px"],
          aspect_ratio=row["aspect_ratio"],
          is_dicom=bool(row["is_dicom"]),
          metadata_sanitized=bool(row["metadata_sanitized"]),
      )

      quality = ImageQualityAssessment(
          passed=bool(row["aspect_ratio_valid"] and row["resolution_valid"]),
          blur_score_variance=row["blur_score"],
          aspect_ratio_valid=bool(row["aspect_ratio_valid"]),
          resolution_valid=bool(row["resolution_valid"]),
      )

      return StudyDetail(
          study_id=row["study_id"],
          patient_anonymous_id=row["patient_anonymous_id"],
          status=StudyStatus(row["status"]),
          created_at=row["created_at"],
          radiograph=metadata,
          quality=quality,
          teeth=teeth,
          findings=findings,
          confirmation=confirmation,
          archived=bool(row["archived"]),
      )

  def list_studies(
      self, limit: int = 50, offset: int = 0, include_archived: bool = False
  ) -> StudyList:
    """Retrieve paginated study summaries."""
    with get_db() as conn:
      archived_filter = "" if include_archived else "WHERE s.archived = 0"

      total = conn.execute(
          f"SELECT COUNT(*) as cnt FROM studies s {archived_filter};"
      ).fetchone()["cnt"]

      rows = conn.execute(
          f"""
                SELECT s.study_id, s.patient_anonymous_id, s.status, s.created_at,
                       r.original_filename, r.storage_rel_path, r.preview_rel_path,
                       r.file_size_bytes, r.sha256_hash, r.mime_type, r.width_px,
                       r.height_px, r.aspect_ratio, r.is_dicom, r.metadata_sanitized,
                       r.blur_score, r.aspect_ratio_valid, r.resolution_valid
                FROM studies s
                JOIN radiographs r ON s.study_id = r.study_id
                {archived_filter}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?;
                """,
          (limit, offset),
      ).fetchall()

      items = []
      for row in rows:
        metadata = RadiographMetadata(
            original_filename=row["original_filename"],
            storage_rel_path=row["storage_rel_path"],
            preview_rel_path=row["preview_rel_path"],
            file_size_bytes=row["file_size_bytes"],
            sha256_hash=row["sha256_hash"],
            mime_type=row["mime_type"],
            width_px=row["width_px"],
            height_px=row["height_px"],
            aspect_ratio=row["aspect_ratio"],
            is_dicom=bool(row["is_dicom"]),
            metadata_sanitized=bool(row["metadata_sanitized"]),
        )
        quality = ImageQualityAssessment(
            passed=bool(row["aspect_ratio_valid"] and row["resolution_valid"]),
            blur_score_variance=row["blur_score"],
            aspect_ratio_valid=bool(row["aspect_ratio_valid"]),
            resolution_valid=bool(row["resolution_valid"]),
        )
        items.append(
            StudyResponse(
                study_id=row["study_id"],
                patient_anonymous_id=row["patient_anonymous_id"],
                status=StudyStatus(row["status"]),
                created_at=row["created_at"],
                radiograph=metadata,
                quality=quality,
            )
        )

      return StudyList(total=total, items=items)

  def delete_study(self, study_id: str, hard_delete: bool = False) -> bool:
    """Soft-archive or permanently delete a study and associated files."""
    with get_db() as conn:
      row = conn.execute(
          "SELECT r.storage_rel_path, r.preview_rel_path FROM radiographs r"
          " WHERE study_id = ?;",
          (study_id,),
      ).fetchone()
      if not row:
        return False

      if hard_delete:
        # Delete from disk
        storage_manager.delete_study_files(
            row["storage_rel_path"], row["preview_rel_path"]
        )
        # Delete cascades in database
        conn.execute("DELETE FROM studies WHERE study_id = ?;", (study_id,))
      else:
        # Soft delete / archive
        conn.execute(
            """
                    UPDATE studies
                    SET archived = 1, status = 'archived', updated_at = ?
                    WHERE study_id = ?;
                    """,
            (datetime.utcnow(), study_id),
        )

      return True


study_service = StudyService()
