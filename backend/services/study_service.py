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
from backend.schemas.analysis import AnalysisResponse
from backend.ml.inference_engine import ONNXInferenceEngine
from backend.ml.segmentation_engine import DentalSegmentationEngine
from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.fdi_solver import CalibratedFDISolver, FDISolver
from backend.ml.association import ToothPathologyAssociator
from backend.schemas.provenance import ModelAvailabilityStatus
from backend.services.model_adapter import model_registry
from backend.storage.file_manager import storage_manager
from backend.config import settings
from PIL import Image


class StudyService:
  """Coordinates study intake, database records, file operations, and audit trails."""

  def create_study(
      self,
      raw_bytes: bytes,
      original_filename: str,
      patient_anonymous_id: Optional[str] = None,
      clinical_indication: Optional[str] = None,
      acquisition_date: Optional[str] = None,
      modality: Optional[str] = None,
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

    # Determine persisted modality
    valid_modalities = {"panoramic_opg", "intraoral_periapical", "bitewing", "unknown"}
    if modality and modality.lower() in valid_modalities:
      persisted_modality = modality.lower()
    else:
      # If not explicitly specified by user:
      # A new study must NEVER silently default to IOPA.
      # When modality is uncertain (e.g. portrait photo of OPG or non-panoramic ratio),
      # set to 'unknown' so the clinician confirms modality instead of silently guessing.
      if metadata.aspect_ratio >= 1.5:
        persisted_modality = "panoramic_opg"
      else:
        persisted_modality = "unknown"

    metadata.modality = persisted_modality
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
                    aspect_ratio_valid, resolution_valid, modality
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
              persisted_modality,
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
                       r.blur_score, r.aspect_ratio_valid, r.resolution_valid, r.modality
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

      persisted_mod = row["modality"] if "modality" in row.keys() and row["modality"] else "unknown"

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
          modality=persisted_mod,
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
      self,
      limit: int = 50,
      offset: int = 0,
      include_archived: bool = False,
      patient_id: Optional[str] = None,
  ) -> StudyList:
    """Retrieve paginated study summaries, optionally filtered by patient ID."""
    with get_db() as conn:
      clauses = []
      params = []
      if not include_archived:
        clauses.append("s.archived = 0")
      if patient_id:
        clauses.append("s.patient_anonymous_id = ?")
        params.append(patient_id)

      where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""

      total = conn.execute(
          f"SELECT COUNT(*) as cnt FROM studies s {where_str};",
          params,
      ).fetchone()["cnt"]

      rows = conn.execute(
          f"""
                SELECT s.study_id, s.patient_anonymous_id, s.status, s.created_at,
                       r.original_filename, r.storage_rel_path, r.preview_rel_path,
                       r.file_size_bytes, r.sha256_hash, r.mime_type, r.width_px,
                       r.height_px, r.aspect_ratio, r.is_dicom, r.metadata_sanitized,
                       r.blur_score, r.aspect_ratio_valid, r.resolution_valid, r.modality
                FROM studies s
                JOIN radiographs r ON s.study_id = r.study_id
                {where_str}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?;
                """,
          (*params, limit, offset),
      ).fetchall()

      items = []
      for row in rows:
        persisted_mod = row["modality"] if "modality" in row.keys() and row["modality"] else "unknown"

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
            modality=persisted_mod,
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

  def analyze_study(
      self,
      study_id: str,
      model_id: Optional[str] = "liodon-panoramic-screener",
      conf_threshold: float = 0.25,
      iou_threshold: float = 0.35,
  ) -> AnalysisResponse:
    """Execute real dental AI model analysis on study radiograph and persist detected findings."""
    with get_db() as conn:
      study_row = conn.execute(
          """
          SELECT s.study_id, s.status, r.storage_rel_path, r.width_px, r.height_px, r.modality
          FROM studies s
          JOIN radiographs r ON s.study_id = r.study_id
          WHERE s.study_id = ?;
          """,
          (study_id,),
      ).fetchone()

    if not study_row:
      raise ValueError(f"Study with ID '{study_id}' was not found")

    persisted_modality = (study_row["modality"] or "unknown").lower() if "modality" in study_row.keys() else "unknown"

    if model_id:
      target_model = model_id
    elif persisted_modality == "intraoral_periapical":
      target_model = "iopa-periapical-screener"
    else:
      target_model = "liodon-panoramic-screener"

    # 1. Truthful handling of unsupported capabilities (Bone loss missing reference landmarks)
    if target_model == "boneloss-pan769-baseline":
      return AnalysisResponse(
          study_id=study_id,
          status="model_unavailable",
          model_id=target_model,
          model_version="1.0.0",
          execution_time_ms=None,
          execution_provider="None",
          findings_count=0,
          findings=[],
          notice=(
              "UNSUPPORTED_MISSING_LANDMARKS: Quantitative alveolar bone loss assessment requires reference landmarks "
              "(cementoenamel junction, alveolar crest line, root apex). DENTEX challenge annotations provide whole-tooth "
              "abnormal condition polygons, not crestal reference lines. Quantitative bone loss assessment is explicitly "
              "unsupported until anatomically valid reference landmarks are available. Fabricating bone loss is prohibited."
          ),
      )

    # 2. Lookup candidate in Model Registry
    reg_entry = model_registry.get_entry(target_model)
    if not reg_entry:
      return AnalysisResponse(
          study_id=study_id,
          status="model_unavailable",
          model_id=target_model,
          model_version="1.0.0",
          execution_time_ms=None,
          execution_provider="None",
          findings_count=0,
          findings=[],
          notice=f"Model '{target_model}' is unavailable: not registered or recognized by DENTRACE.",
      )

    if not reg_entry.is_available():
      notice = reg_entry.blocker_reason or (
          f"Model '{target_model}' is unavailable: weights are not installed on disk at {reg_entry.weight_rel_path}. "
          "Pretrained model downloads require explicit user authorization."
      )
      return AnalysisResponse(
          study_id=study_id,
          status="model_unavailable",
          model_id=target_model,
          model_version=reg_entry.version,
          execution_time_ms=None,
          execution_provider="None",
          findings_count=0,
          findings=[],
          notice=notice,
      )

    # 2.5 Strict Persisted Modality Safety Guard — enforce OPG training boundary
    # Do NOT rely on filename or storage path! Read the persisted modality field from DB.
    supported_mods = getattr(reg_entry, "supported_modalities", ["panoramic_opg"])

    if persisted_modality == "unknown":
      return AnalysisResponse(
          study_id=study_id,
          status="modality_unsupported",
          model_id=target_model,
          model_version=reg_entry.version,
          execution_time_ms=None,
          execution_provider="None",
          findings_count=0,
          findings=[],
          notice=(
              "MODALITY_SAFETY_GUARD: Radiograph modality is UNKNOWN. Automated AI inference is disabled "
              "to prevent clinically invalid predictions. Please select and confirm the radiograph modality "
              "(e.g., Panoramic OPG or Intraoral Periapical) before executing neural models."
          ),
      )

    if persisted_modality not in supported_mods:
      modality_label = "Intraoral Periapical (IOPA)" if persisted_modality == "intraoral_periapical" else (
          "Bitewing" if persisted_modality == "bitewing" else persisted_modality.replace("_", " ").title()
      )
      if persisted_modality in ("intraoral_periapical", "bitewing") and "panoramic_opg" in supported_mods:
        notice_msg = (
            f"MODALITY_SAFETY_GUARD: AI model '{target_model}' is trained and validated strictly on Panoramic OPG images. "
            f"Automated AI detection is NOT AVAILABLE for {modality_label} radiographs. "
            "Manual tooth chart selection and region annotation remain fully active."
        )
      else:
        notice_msg = (
            f"MODALITY_SAFETY_GUARD: AI model '{target_model}' does not support {modality_label} radiographs. "
            "Manual tooth chart selection and region annotation remain fully active."
        )

      return AnalysisResponse(
          study_id=study_id,
          status="modality_unsupported",
          model_id=target_model,
          model_version=reg_entry.version,
          execution_time_ms=None,
          execution_provider="None",
          findings_count=0,
          findings=[],
          notice=notice_msg,
      )

    image_path = storage_manager.get_storage_path(study_row["storage_rel_path"])
    if not image_path or not image_path.exists():
      raise ValueError(f"Radiograph image file not found on disk at {study_row['storage_rel_path']}")

    try:
      img = Image.open(image_path).convert("RGB")
    except Exception as exc:
      raise ValueError(f"Failed to load radiograph image for inference: {str(exc)}") from exc

    # 3. Route to appropriate inference engine
    active_model_id = reg_entry.model_id
    active_model_name = reg_entry.model_name
    active_model_version = reg_entry.version
    is_segmentation_model = False

    if target_model in ("dentex-yolov8n-seg", "dentex-yolov8n-seg-int8"):
      # DENTEX 4-Class instance segmenter
      ckpt_rel = reg_entry.weight_rel_path
      if target_model == "dentex-yolov8n-seg" and (settings.PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg.pt").exists():
        ckpt_rel = "models/checkpoints/dentex_yolov8n_seg.pt"

      seg_engine = DentalSegmentationEngine(
          model_id=target_model,
          model_name=active_model_name,
          version=active_model_version,
          checkpoint_rel_path=ckpt_rel,
          class_names=["impacted_tooth", "caries", "periapical_lesion", "deep_caries"],
          conf_threshold=conf_threshold,
          iou_threshold=iou_threshold,
      )
      infer_result = seg_engine.predict_image(img, conf_threshold=conf_threshold, iou_threshold=iou_threshold)
      is_segmentation_model = True

    elif target_model in ("nsitnov-8024-seg", "nsitnov-dental-segmentation"):
      ckpt_rel = reg_entry.weight_rel_path
      if target_model == "nsitnov-8024-seg" and (settings.PROJECT_ROOT / "models/checkpoints/8024.pt").exists():
        ckpt_rel = "models/checkpoints/8024.pt"

      seg_engine = DentalSegmentationEngine(
          model_id=target_model,
          model_name=active_model_name,
          version=active_model_version,
          checkpoint_rel_path=ckpt_rel,
          class_names=[
              "Caries",
              "Crown",
              "Filling",
              "Implant",
              "Missing-tooth",
              "Periapical-lesion",
              "Root Piece",
              "Root-Canal-Treatment",
          ],
          conf_threshold=conf_threshold,
          iou_threshold=iou_threshold,
      )
      infer_result = seg_engine.predict_image(img, conf_threshold=conf_threshold, iou_threshold=iou_threshold)
      is_segmentation_model = True

    else:
      # Detection screener (FP32 or INT8 ONNX)
      det_engine = ONNXInferenceEngine(
          model_id=target_model,
          model_name=active_model_name,
          version=active_model_version,
          checkpoint_rel_path=reg_entry.weight_rel_path,
          class_names=["caries", "periapical_lesion", "impacted_tooth"],
          conf_threshold=conf_threshold,
          iou_threshold=iou_threshold,
      )
      infer_result = det_engine.predict_image(img, conf_threshold=conf_threshold, iou_threshold=iou_threshold)

    if infer_result["status"] != ModelAvailabilityStatus.AVAILABLE.value:
      return AnalysisResponse(
          study_id=study_id,
          status=infer_result["status"],
          model_id=active_model_id,
          model_version=active_model_version,
          execution_time_ms=infer_result.get("latency_ms"),
          execution_provider=infer_result.get("execution_provider", "None"),
          findings_count=0,
          findings=[],
          notice=infer_result.get("error", "Model execution failed"),
      )

    raw_detections = infer_result["findings"]
    if target_model == "iopa-periapical-screener":
      raw_detections = [d for d in raw_detections if getattr(d, "class_name", "") in ("caries", "periapical_lesion")]

    latency_ms = infer_result.get("latency_ms")
    exec_provider = infer_result.get("execution_provider", "CPUExecutionProvider")
    now = datetime.utcnow()

    # 4. Map raw detections to PathologyFinding domain models
    dentex_class_map = {
        "impacted_tooth": PathologyClass.IMPACTED_TOOTH,
        "caries": PathologyClass.CARIES,
        "periapical_lesion": PathologyClass.PERIAPICAL_LESION,
        "deep_caries": PathologyClass.DEEP_CARIES,
    }
    nsitnov_class_map = {
        "Caries": PathologyClass.CARIES,
        "Periapical-lesion": PathologyClass.PERIAPICAL_LESION,
        "Root-Canal-Treatment": PathologyClass.ROOT_CANAL_TREATMENT,
        "Crown": PathologyClass.CARIES,
        "Filling": PathologyClass.CARIES,
        "Implant": PathologyClass.CARIES,
        "Missing-tooth": PathologyClass.CARIES,
        "Root Piece": PathologyClass.CARIES,
    }
    screener_class_map = {
        "caries": PathologyClass.CARIES,
        "periapical_lesion": PathologyClass.PERIAPICAL_LESION,
        "impacted_tooth": PathologyClass.IMPACTED_TOOTH,
    }

    findings: list[PathologyFinding] = []
    finding_db_records = []

    for det in raw_detections:
      finding_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
      raw_cls = getattr(det, "class_name", "caries")

      if is_segmentation_model:
        if target_model.startswith("dentex"):
          pathology_enum = dentex_class_map.get(raw_cls, PathologyClass.CARIES)
        else:
          pathology_enum = nsitnov_class_map.get(raw_cls, PathologyClass.CARIES)
      else:
        pathology_enum = screener_class_map.get(raw_cls, PathologyClass.CARIES)

      ox1, oy1, ox2, oy2 = det.bbox_orig
      bbox = FindingBoundingBox(x_min=ox1, y_min=oy1, x_max=ox2, y_max=oy2)

      # Modality and geometry: distinguish true polygon instance segmentation from bounding box
      has_poly = getattr(det, "has_mask", False) and getattr(det, "mask_polygon", None) is not None
      if has_poly:
        polygon = FindingPolygon(points=det.mask_polygon)
        modality = AnnotationModality.INSTANCE_SEGMENTATION
        geom_type = "polygon"
        polygon_json_val = json.dumps({"points": det.mask_polygon})
        if target_model.startswith("dentex"):
          obs = [f"DENTEX whole-tooth abnormal condition contour (not exact cavity margin) via {active_model_name}"]
        else:
          obs = [f"Instance segmentation polygon contour via {active_model_name}"]
      else:
        polygon = None
        modality = AnnotationModality.DETECTION_BOUNDING_BOX
        geom_type = "bbox"
        polygon_json_val = None
        if target_model == "iopa-periapical-screener":
          obs = [f"IOPA periapical anomaly candidate via {active_model_name}"]
        else:
          obs = [f"AI proposal from {active_model_name}"]

      # Radiographic density & root canal treatment semantic distinction
      if pathology_enum == PathologyClass.ROOT_CANAL_TREATMENT:
        density = "radiopaque"
        obs.append("Endodontic obturation material in root canal (past restorative intervention; not an active pathology)")
        urgency = UrgencyLevel.ROUTINE
      elif pathology_enum in (PathologyClass.PERIAPICAL_LESION, PathologyClass.DEEP_CARIES):
        density = "radiolucent"
        urgency = UrgencyLevel.SOON
      else:
        density = "radiolucent"
        urgency = UrgencyLevel.ROUTINE

      evidence = ClinicalEvidence(
          radiographic_density=density,
          affected_surface=None,
          observed_features=obs,
      )

      finding_obj = PathologyFinding(
          finding_id=finding_id,
          study_id=study_id,
          tooth_fdi=None,
          pathology_class=pathology_enum,
          annotation_modality=modality,
          confidence=det.confidence,
          urgency=urgency,
          bbox=bbox,
          polygon=polygon,
          evidence=evidence,
          suggested_procedure=None,
          demo_cdt_code=None,
      )
      findings.append(finding_obj)

      finding_db_records.append([
          finding_id,
          study_id,
          None,
          pathology_enum.value,
          modality.value,
          det.confidence,
          urgency.value,
          geom_type,
          json.dumps({"x_min": ox1, "y_min": oy1, "x_max": ox2, "y_max": oy2}),
          polygon_json_val,
          json.dumps({"observed_features": evidence.observed_features, "radiographic_density": evidence.radiographic_density}),
          active_model_id,
          active_model_version,
          "pending",
          None,
          None,
      ])

    # 5. Run FDI tooth proposal engine and Calibrated arch solver (for panoramic radiographs)
    teeth_boxes: list[ToothBox] = []
    resolved_teeth = []
    if persisted_modality != "intraoral_periapical":
      fdi_engine = FDINumberingEngine()
      if fdi_engine.is_available():
        fdi_res = fdi_engine.predict_teeth(img)
        if fdi_res["status"] == ModelAvailabilityStatus.AVAILABLE.value and fdi_res["teeth"]:
          raw_tooth_props = [
              {
                  "id": f"tooth_prop_{i}",
                  "bbox": t.bbox_orig,
                  "confidence": t.confidence,
              }
              for i, t in enumerate(fdi_res["teeth"])
          ]
          solver = CalibratedFDISolver()
          resolved_teeth = solver.solve(
              raw_tooth_props,
              image_width=img.width,
              image_height=img.height,
          )
          for rt in resolved_teeth:
            teeth_boxes.append(
                ToothBox(
                    fdi_number=rt.fdi_number,
                    x_min=rt.bbox[0],
                    y_min=rt.bbox[1],
                    x_max=rt.bbox[2],
                    y_max=rt.bbox[3],
                    confidence=rt.confidence,
                    uncertain_tooth=rt.uncertain_tooth,
                )
            )

    # 6. Geometry-based tooth-pathology association & composite endodontic checks
    if resolved_teeth and findings:
      findings_payload = [
          {
              "id": f.finding_id,
              "label": f.pathology_class.value,
              "confidence": f.confidence,
              "bbox": [f.bbox.x_min, f.bbox.y_min, f.bbox.x_max, f.bbox.y_max] if f.bbox else [0, 0, 0, 0],
          }
          for f in findings
      ]
      associator = ToothPathologyAssociator()
      _, associations = associator.associate(findings_payload, resolved_teeth)

      # Update findings and DB records with associated tooth FDI
      for idx, (f, assoc) in enumerate(zip(findings, associations)):
        if assoc.associated_fdi_number:
          f.tooth_fdi = assoc.associated_fdi_number
          if assoc.is_interproximal and assoc.secondary_fdi_number:
            f.evidence.observed_features.append(f"Interproximal contact with FDI #{assoc.secondary_fdi_number}")
          if assoc.uncertain_association:
            f.evidence.observed_features.append("Uncertain tooth association (borderline overlap)")

          old_rec = finding_db_records[idx]
          old_rec[2] = assoc.associated_fdi_number
          old_rec[10] = json.dumps({
              "observed_features": f.evidence.observed_features,
              "radiographic_density": f.evidence.radiographic_density,
          })

      # Composite endodontic check: if a tooth has both root canal obturation and a periapical lesion,
      # flag suspected persistent/recurrent apical periodontitis requiring chairside confirmation
      tooth_findings_map = {}
      for idx, f in enumerate(findings):
        if f.tooth_fdi:
          tooth_findings_map.setdefault(f.tooth_fdi, []).append((idx, f))

      for tooth_num, tf_tuples in tooth_findings_map.items():
        has_rct = any(tf.pathology_class == PathologyClass.ROOT_CANAL_TREATMENT for _, tf in tf_tuples)
        has_apical = any(tf.pathology_class == PathologyClass.PERIAPICAL_LESION for _, tf in tf_tuples)
        if has_rct and has_apical:
          for idx, tf in tf_tuples:
            if tf.pathology_class == PathologyClass.PERIAPICAL_LESION:
              tf.evidence.observed_features.append(
                  "Previously treated tooth with suspected periapical radiographic finding — requires clinician review."
              )
              tf.urgency = UrgencyLevel.SOON
              finding_db_records[idx][6] = UrgencyLevel.SOON.value
              finding_db_records[idx][10] = json.dumps({
                  "observed_features": tf.evidence.observed_features,
                  "radiographic_density": tf.evidence.radiographic_density,
              })

    # 7. Persist findings and model run record in database
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    with get_db() as conn:
      # Clear previous pending model findings for idempotency
      conn.execute(
          "DELETE FROM findings WHERE study_id = ? AND review_status = 'pending';",
          (study_id,),
      )

      # Insert new findings
      for rec in finding_db_records:
        conn.execute(
            """
            INSERT INTO findings (
                finding_id, study_id, tooth_fdi, pathology_class,
                annotation_modality, confidence, urgency, geometry_type,
                bbox_json, polygon_json, evidence_json, model_id,
                model_version, review_status, suggested_procedure, demo_cdt_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            tuple(rec),
        )

      # Record model run provenance
      conn.execute(
          """
          INSERT INTO model_runs (
              run_id, study_id, model_id, model_version,
              execution_status, execution_time_ms, findings_count, created_at
          ) VALUES (?, ?, ?, ?, 'completed', ?, ?, ?);
          """,
          (run_id, study_id, active_model_id, active_model_version, latency_ms, len(findings), now),
      )

      # Update study status
      conn.execute(
          "UPDATE studies SET status = 'analyzed', updated_at = ? WHERE study_id = ?;",
          (now, study_id),
      )

      # Audit trail
      conn.execute(
          """
          INSERT INTO audit_events (
              event_id, study_id, event_type, actor, timestamp, payload_json
          ) VALUES (?, ?, 'MODEL_INFERENCE_RUN', 'onnx_runtime', ?, ?);
          """,
          (
              f"AUD-{uuid.uuid4().hex[:8].upper()}",
              study_id,
              now,
              json.dumps({
                  "model_id": active_model_id,
                  "model_version": active_model_version,
                  "latency_ms": latency_ms,
                  "findings_count": len(findings),
                  "execution_provider": exec_provider,
              }),
          ),
      )

    return AnalysisResponse(
        study_id=study_id,
        status="completed",
        model_id=active_model_id,
        model_version=active_model_version,
        execution_time_ms=latency_ms,
        execution_provider=exec_provider,
        findings_count=len(findings),
        findings=findings,
        teeth=teeth_boxes,
        disclaimer="Draft for dentist review. Not a diagnosis.",
        notice=(
            "Academic decision-support prototype. Does not determine clinical diagnosis, "
            "treatment necessity, urgency, or automated insurance pre-authorization."
        ),
    )

  def update_study_modality(self, study_id: str, modality: str) -> bool:
    """Update persisted radiograph modality."""
    valid_modalities = {"panoramic_opg", "intraoral_periapical", "bitewing", "unknown"}
    mod_lower = modality.lower().strip()
    if mod_lower not in valid_modalities:
      raise ValueError(f"Invalid modality '{modality}'. Allowed: {sorted(valid_modalities)}")

    with get_db() as conn:
      cur = conn.execute(
          "UPDATE radiographs SET modality = ? WHERE study_id = ?;",
          (mod_lower, study_id),
      )
      # Log audit event and reset state if needed
      if cur.rowcount > 0:
        if mod_lower == "panoramic_opg":
          # Allow fresh analysis request if study was previously blocked/unsupported
          conn.execute(
              "UPDATE studies SET status = 'ingested', updated_at = ? WHERE study_id = ? AND status != 'analyzed';",
              (datetime.utcnow(), study_id),
          )
        conn.execute(
            """
            INSERT INTO audit_events (
                event_id, study_id, event_type, actor, timestamp, payload_json
            ) VALUES (?, ?, 'MODALITY_OVERRIDE', 'clinician', ?, ?);
            """,
            (
                f"AUD-{uuid.uuid4().hex[:8].upper()}",
                study_id,
                datetime.utcnow(),
                json.dumps({"modality": mod_lower}),
            ),
        )
      return cur.rowcount > 0

  def add_manual_annotation(
      self,
      study_id: str,
      tooth_fdi: Optional[int],
      pathology_class: str,
      bbox: dict,
      clinical_notes: Optional[str] = None,
      anatomical_structure: Optional[str] = None,
  ) -> PathologyFinding:
    """Create a clinician-authored manual region annotation."""
    finding_id = f"ANN-{uuid.uuid4().hex[:8].upper()}"
    obs = [clinical_notes] if clinical_notes else ["Clinician manual region annotation"]
    if anatomical_structure:
      obs.append(f"Anatomical Tissue: {anatomical_structure}")

    finding_box = FindingBoundingBox(
        x_min=float(bbox["x_min"]),
        y_min=float(bbox["y_min"]),
        x_max=float(bbox["x_max"]),
        y_max=float(bbox["y_max"]),
    )
    evidence = ClinicalEvidence(
        radiographic_density="radiolucent",
        affected_surface=None,
        observed_features=obs,
    )

    path_enum = PathologyClass.CARIES
    for pc in PathologyClass:
      if pc.value.lower() == pathology_class.lower():
        path_enum = pc
        break

    finding = PathologyFinding(
        finding_id=finding_id,
        study_id=study_id,
        tooth_fdi=tooth_fdi,
        pathology_class=path_enum,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        confidence=1.0,
        urgency=UrgencyLevel.ROUTINE,
        bbox=finding_box,
        polygon=None,
        evidence=evidence,
        suggested_procedure="Clinician Assessment & Follow-up",
        demo_cdt_code=None,
    )

    with get_db() as conn:
      conn.execute(
          """
          INSERT INTO findings (
              finding_id, study_id, tooth_fdi, pathology_class,
              annotation_modality, confidence, urgency, geometry_type,
              bbox_json, polygon_json, evidence_json, model_id,
              model_version, review_status, suggested_procedure, demo_cdt_code
          ) VALUES (?, ?, ?, ?, ?, ?, ?, 'bbox', ?, NULL, ?, 'clinician_manual', '1.0.0', 'confirmed', ?, ?);
          """,
          (
              finding_id,
              study_id,
              tooth_fdi,
              finding.pathology_class.value,
              finding.annotation_modality.value,
              1.0,
              finding.urgency.value,
              json.dumps({"x_min": finding_box.x_min, "y_min": finding_box.y_min, "x_max": finding_box.x_max, "y_max": finding_box.y_max}),
              json.dumps({"observed_features": obs, "radiographic_density": "radiolucent"}),
              finding.suggested_procedure,
              finding.demo_cdt_code,
          ),
      )
    return finding

  def delete_manual_annotation(self, study_id: str, finding_id: str) -> bool:
    """Delete a clinician-authored region annotation."""
    with get_db() as conn:
      cur = conn.execute(
          "DELETE FROM findings WHERE study_id = ? AND finding_id = ? AND model_id = 'clinician_manual';",
          (study_id, finding_id),
      )
      return cur.rowcount > 0


study_service = StudyService()

