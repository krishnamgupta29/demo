"""SQLAlchemy 2.0 Declarative ORM models for DENTRACE Clinical Decision Support Engine.

Covers full clinical lifecycle:
1. Study and Radiograph metadata
2. Tooth localizations with FDI numbering (11-48)
3. Pathology findings with geometry, model attribution, and review status
4. Model prediction runs and provenance tracking
5. Clinician review attestation and physical signature requirement
6. Insurance pre-authorization draft metadata
7. Tamper-evident audit trail ledger
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
  pass


class StudyModel(Base):
  __tablename__ = "studies"

  study_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  patient_anonymous_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
  status: Mapped[str] = mapped_column(String(32), default="ingested", nullable=False)
  acquisition_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
  clinical_indication: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
  archived: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

  # Relationships
  radiograph: Mapped[Optional["RadiographModel"]] = relationship(
      "RadiographModel", back_populates="study", uselist=False, cascade="all, delete-orphan"
  )
  teeth: Mapped[List["ToothModel"]] = relationship(
      "ToothModel", back_populates="study", cascade="all, delete-orphan"
  )
  findings: Mapped[List["FindingModel"]] = relationship(
      "FindingModel", back_populates="study", cascade="all, delete-orphan"
  )
  model_runs: Mapped[List["ModelRunModel"]] = relationship(
      "ModelRunModel", back_populates="study", cascade="all, delete-orphan"
  )
  confirmation: Mapped[Optional["ConfirmationModel"]] = relationship(
      "ConfirmationModel", back_populates="study", uselist=False, cascade="all, delete-orphan"
  )
  insurance_draft: Mapped[Optional["InsuranceDraftModel"]] = relationship(
      "InsuranceDraftModel", back_populates="study", uselist=False, cascade="all, delete-orphan"
  )
  audit_events: Mapped[List["AuditEventModel"]] = relationship(
      "AuditEventModel", back_populates="study", cascade="all, delete-orphan"
  )


class RadiographModel(Base):
  __tablename__ = "radiographs"

  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), primary_key=True
  )
  original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
  storage_rel_path: Mapped[str] = mapped_column(String(255), nullable=False)
  preview_rel_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
  sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
  mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
  width_px: Mapped[int] = mapped_column(Integer, nullable=False)
  height_px: Mapped[int] = mapped_column(Integer, nullable=False)
  aspect_ratio: Mapped[float] = mapped_column(Float, nullable=False)
  is_dicom: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
  metadata_sanitized: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
  blur_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
  aspect_ratio_valid: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
  resolution_valid: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
  modality: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="radiograph")


class ToothModel(Base):
  __tablename__ = "teeth"

  tooth_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), nullable=False, index=True
  )
  fdi_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
  x_min: Mapped[float] = mapped_column(Float, nullable=False)
  y_min: Mapped[float] = mapped_column(Float, nullable=False)
  x_max: Mapped[float] = mapped_column(Float, nullable=False)
  y_max: Mapped[float] = mapped_column(Float, nullable=False)
  confidence: Mapped[float] = mapped_column(Float, nullable=False)
  points_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="teeth")


class FindingModel(Base):
  __tablename__ = "findings"

  finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), nullable=False, index=True
  )
  tooth_fdi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
  pathology_class: Mapped[str] = mapped_column(String(64), nullable=False)
  annotation_modality: Mapped[str] = mapped_column(String(32), nullable=False)
  confidence: Mapped[float] = mapped_column(Float, nullable=False)
  urgency: Mapped[str] = mapped_column(String(32), default="routine", nullable=False)
  geometry_type: Mapped[str] = mapped_column(String(32), default="bbox", nullable=False)
  bbox_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  polygon_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  model_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
  model_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
  review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
  suggested_procedure: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  demo_cdt_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="findings")


class ModelRunModel(Base):
  __tablename__ = "model_runs"

  run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), nullable=False, index=True
  )
  model_id: Mapped[str] = mapped_column(String(64), nullable=False)
  model_version: Mapped[str] = mapped_column(String(32), nullable=False)
  execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
  execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
  findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="model_runs")


class ConfirmationModel(Base):
  __tablename__ = "confirmations"

  confirmation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), unique=True, nullable=False
  )
  clinician_name: Mapped[str] = mapped_column(String(128), nullable=False)
  license_number: Mapped[str] = mapped_column(String(64), nullable=False)
  decision: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False)
  review_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
  clinical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  physical_signature_status: Mapped[str] = mapped_column(
      String(64), default="requires_physical_signature", nullable=False
  )

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="confirmation")


class InsuranceDraftModel(Base):
  __tablename__ = "insurance_drafts"

  draft_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), unique=True, nullable=False
  )
  status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
  narrative_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  narrative_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  suggested_cdt_codes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  regulatory_disclaimer: Mapped[str] = mapped_column(
      Text, default="Draft for dentist review. Not a diagnosis.", nullable=False
  )
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="insurance_draft")


class AuditEventModel(Base):
  __tablename__ = "audit_events"

  event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
  study_id: Mapped[str] = mapped_column(
      String(64), ForeignKey("studies.study_id", ondelete="CASCADE"), nullable=False, index=True
  )
  event_type: Mapped[str] = mapped_column(String(64), nullable=False)
  actor: Mapped[str] = mapped_column(String(64), nullable=False)
  timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
  payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

  study: Mapped["StudyModel"] = relationship("StudyModel", back_populates="audit_events")
