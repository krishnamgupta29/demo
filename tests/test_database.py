"""Test suite verifying SQLite persistence, migrations, and SQLAlchemy ORM models."""

from datetime import datetime
import sqlite3
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_connection, get_db
from backend.database.migrations import run_migrations
from backend.database.models import (
    Base,
    StudyModel,
    RadiographModel,
    ToothModel,
    FindingModel,
    ModelRunModel,
    ConfirmationModel,
    InsuranceDraftModel,
    AuditEventModel,
)


def test_migrations_execute_cleanly():
  """Test that database schema migrations execute and track versions."""
  with get_db() as conn:
    applied = run_migrations(conn)
    # Applied count will be 0 if already applied in session setup
    assert applied >= 0

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    }

    expected_tables = {
        "studies",
        "radiographs",
        "teeth",
        "findings",
        "model_runs",
        "confirmations",
        "insurance_drafts",
        "audit_events",
        "alembic_version",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"


def test_sqlalchemy_orm_full_lifecycle():
  """Test complete study lifecycle with all related entities via SQLAlchemy ORM."""
  engine = create_engine(f"sqlite:///{settings.SQLITE_DB_PATH}")

  with Session(engine) as session:
    study_id = "CASE-TEST-001"
    now = datetime.utcnow()

    # 1. Create Study
    study = StudyModel(
        study_id=study_id,
        patient_anonymous_id="PT-ANON-99",
        status="ingested",
        clinical_indication="Routine checkup",
        created_at=now,
        updated_at=now,
    )
    session.add(study)

    # 2. Add Radiograph
    radiograph = RadiographModel(
        study_id=study_id,
        original_filename="opg_sample.png",
        storage_rel_path="data/storage/test_opg.png",
        preview_rel_path="data/previews/test_preview.png",
        file_size_bytes=102400,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="image/png",
        width_px=1000,
        height_px=500,
        aspect_ratio=2.0,
        is_dicom=0,
        metadata_sanitized=1,
        blur_score=120.5,
        aspect_ratio_valid=1,
        resolution_valid=1,
    )
    session.add(radiograph)

    # 3. Add Tooth with FDI Number
    tooth = ToothModel(
        tooth_id="TOOTH-16-001",
        study_id=study_id,
        fdi_number=16,
        x_min=100.0,
        y_min=150.0,
        x_max=160.0,
        y_max=220.0,
        confidence=0.92,
        points_json='[[100, 150], [160, 150], [160, 220], [100, 220]]',
    )
    session.add(tooth)

    # 4. Add Finding with Geometry & Model Info
    finding = FindingModel(
        finding_id="FIND-001",
        study_id=study_id,
        tooth_fdi=16,
        pathology_class="caries",
        annotation_modality="polygon",
        confidence=0.88,
        urgency="soon",
        geometry_type="polygon",
        polygon_json='{"points": [[120, 160], [140, 160], [140, 180], [120, 180]]}',
        model_id="nsitnov-dental-segmentation",
        model_version="1.0.0",
        review_status="pending",
        suggested_procedure="Resin-based composite",
        demo_cdt_code="D2391",
    )
    session.add(finding)

    # 5. Add Model Run
    model_run = ModelRunModel(
        run_id="RUN-001",
        study_id=study_id,
        model_id="nsitnov-dental-segmentation",
        model_version="1.0.0",
        execution_status="MODEL_UNAVAILABLE",
        execution_time_ms=0.0,
        findings_count=0,
        created_at=now,
    )
    session.add(model_run)

    # 6. Add Insurance Draft
    insurance_draft = InsuranceDraftModel(
        draft_id="DRAFT-001",
        study_id=study_id,
        status="draft",
        narrative_summary="Restorative treatment indicated for tooth 16 due to dental caries.",
        regulatory_disclaimer="Draft for dentist review. Not a diagnosis.",
        created_at=now,
        updated_at=now,
    )
    session.add(insurance_draft)

    # 7. Add Audit Event
    audit = AuditEventModel(
        event_id="AUD-001",
        study_id=study_id,
        event_type="STUDY_INTAKE",
        actor="system",
        timestamp=now,
        payload_json='{"action": "test_intake"}',
    )
    session.add(audit)

    session.commit()

    # Query and verify
    retrieved_study = session.execute(
        select(StudyModel).where(StudyModel.study_id == study_id)
    ).scalar_one()

    assert retrieved_study.patient_anonymous_id == "PT-ANON-99"
    assert retrieved_study.radiograph.width_px == 1000
    assert len(retrieved_study.teeth) == 1
    assert retrieved_study.teeth[0].fdi_number == 16
    assert len(retrieved_study.findings) == 1
    assert retrieved_study.findings[0].geometry_type == "polygon"
    assert retrieved_study.findings[0].model_id == "nsitnov-dental-segmentation"
    assert retrieved_study.insurance_draft.draft_id == "DRAFT-001"
    assert len(retrieved_study.model_runs) == 1
    assert len(retrieved_study.audit_events) == 1

    # Test cascade deletion
    session.delete(retrieved_study)
    session.commit()

    # Confirm cascade deleted child records
    assert session.execute(select(RadiographModel).where(RadiographModel.study_id == study_id)).scalar_one_or_none() is None
    assert session.execute(select(ToothModel).where(ToothModel.study_id == study_id)).scalar_one_or_none() is None
    assert session.execute(select(FindingModel).where(FindingModel.study_id == study_id)).scalar_one_or_none() is None
    assert session.execute(select(InsuranceDraftModel).where(InsuranceDraftModel.study_id == study_id)).scalar_one_or_none() is None
