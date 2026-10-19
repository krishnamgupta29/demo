"""Database schema migration manager."""

from datetime import datetime
import sqlite3
from backend.database.connection import get_db

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "initial_clinical_schema",
        """
        -- Core studies table
        CREATE TABLE IF NOT EXISTS studies (
            study_id TEXT PRIMARY KEY,
            patient_anonymous_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ingested',
            acquisition_date TEXT,
            clinical_indication TEXT,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0
        );

        -- Radiograph metadata and image quality screening
        CREATE TABLE IF NOT EXISTS radiographs (
            study_id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            storage_rel_path TEXT NOT NULL,
            preview_rel_path TEXT,
            file_size_bytes INTEGER NOT NULL,
            sha256_hash TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            width_px INTEGER NOT NULL,
            height_px INTEGER NOT NULL,
            aspect_ratio REAL NOT NULL,
            is_dicom INTEGER NOT NULL DEFAULT 0,
            metadata_sanitized INTEGER NOT NULL DEFAULT 1,
            blur_score REAL,
            aspect_ratio_valid INTEGER NOT NULL DEFAULT 1,
            resolution_valid INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );

        -- Tooth localizations (FDI notation 11-48)
        CREATE TABLE IF NOT EXISTS teeth (
            tooth_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            fdi_number INTEGER NOT NULL,
            x_min REAL NOT NULL,
            y_min REAL NOT NULL,
            x_max REAL NOT NULL,
            y_max REAL NOT NULL,
            confidence REAL NOT NULL,
            points_json TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_teeth_study ON teeth(study_id);
        CREATE INDEX IF NOT EXISTS idx_teeth_fdi ON teeth(fdi_number);

        -- Pathology findings (caries, periapical lesions, etc.)
        CREATE TABLE IF NOT EXISTS findings (
            finding_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            tooth_fdi INTEGER,
            pathology_class TEXT NOT NULL,
            annotation_modality TEXT NOT NULL,
            confidence REAL NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'routine',
            bbox_json TEXT,
            polygon_json TEXT,
            evidence_json TEXT,
            suggested_procedure TEXT,
            demo_cdt_code TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_findings_study ON findings(study_id);

        -- Clinician review and attestation
        CREATE TABLE IF NOT EXISTS confirmations (
            confirmation_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL UNIQUE,
            clinician_name TEXT NOT NULL,
            license_number TEXT NOT NULL,
            decision TEXT NOT NULL DEFAULT 'pending_review',
            review_timestamp TIMESTAMP NOT NULL,
            clinical_notes TEXT,
            physical_signature_status TEXT NOT NULL DEFAULT 'requires_physical_signature',
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );

        -- Audit trail ledger
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_audit_study ON audit_events(study_id);
        """,
    ),
    (
        2,
        "model_runs_and_insurance_drafts",
        """
        -- Model execution runs and provenance tracking
        CREATE TABLE IF NOT EXISTS model_runs (
            run_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            model_id TEXT NOT NULL,
            model_version TEXT NOT NULL,
            execution_status TEXT NOT NULL,
            execution_time_ms REAL,
            findings_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_model_runs_study ON model_runs(study_id);

        -- Insurance pre-authorization draft metadata
        CREATE TABLE IF NOT EXISTS insurance_drafts (
            draft_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'draft',
            narrative_summary TEXT,
            narrative_json TEXT,
            suggested_cdt_codes_json TEXT,
            regulatory_disclaimer TEXT NOT NULL DEFAULT 'Draft for dentist review. Not a diagnosis.',
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            FOREIGN KEY (study_id) REFERENCES studies(study_id) ON DELETE CASCADE
        );
        """,
    ),
]


def _ensure_finding_columns(conn: sqlite3.Connection) -> None:
  """Ensure findings table has all required clinical and provenance columns."""
  cols = {row[1] for row in conn.execute("PRAGMA table_info(findings);").fetchall()}
  if "geometry_type" not in cols:
    conn.execute("ALTER TABLE findings ADD COLUMN geometry_type TEXT DEFAULT 'bbox';")
  if "model_id" not in cols:
    conn.execute("ALTER TABLE findings ADD COLUMN model_id TEXT;")
  if "model_version" not in cols:
    conn.execute("ALTER TABLE findings ADD COLUMN model_version TEXT;")
  if "review_status" not in cols:
    conn.execute("ALTER TABLE findings ADD COLUMN review_status TEXT DEFAULT 'pending';")


def run_migrations(conn: sqlite3.Connection | None = None) -> int:
  """Apply all pending database migrations in sequential order."""
  owns_conn = conn is None
  if owns_conn:
    from backend.database.connection import get_connection

    conn = get_connection()

  try:
    # Ensure migration tracking table exists
    conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL
            );
        """)

    # Fetch applied migrations
    applied_versions = {
        row["version"]
        for row in conn.execute(
            "SELECT version FROM schema_migrations;"
        ).fetchall()
    }

    applied_count = 0
    for version, name, sql_script in MIGRATIONS:
      if version not in applied_versions:
        print(f"[DB] Applying migration {version:03d}: {name}...")
        conn.executescript(sql_script)
        conn.execute(
            """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?);
                    """,
            (version, name, datetime.utcnow()),
        )
        applied_count += 1

    # Post-migration column adjustments
    _ensure_finding_columns(conn)

    conn.commit()
    return applied_count
  finally:
    if owns_conn and conn:
      conn.close()
