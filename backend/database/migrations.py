"""Canonical Database Schema Migration Manager using Alembic.

Unifies database schema management under Alembic as the single canonical mechanism:
1. Eliminates redundant custom DDL scripts.
2. Programmatically executes `alembic upgrade head` on application lifespan startup.
3. Completely preserves existing records and supports SQLite batch migrations.
"""

from pathlib import Path
import sqlite3
from alembic import command
from alembic.config import Config
from backend.config import settings


def run_migrations(conn: sqlite3.Connection | None = None) -> int:
  """Apply all pending Alembic database migrations up to head.

  Operates as the canonical schema migration manager across all environments.
  """
  alembic_ini_path = settings.PROJECT_ROOT / "alembic.ini"
  if not alembic_ini_path.exists():
    raise FileNotFoundError(f"Alembic configuration not found at {alembic_ini_path}")

  alembic_cfg = Config(str(alembic_ini_path))
  # Enforce runtime sqlite db path
  alembic_cfg.set_main_option(
      "sqlalchemy.url", f"sqlite:///{settings.SQLITE_DB_PATH.resolve().as_posix()}"
  )

  try:
    command.upgrade(alembic_cfg, "head")
    return 1
  except Exception as exc:
    print(f"[Alembic] Error applying migrations: {exc}")
    raise
