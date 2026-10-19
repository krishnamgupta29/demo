"""Thread-safe SQLite database connection manager for DENTRACE.

Configured with WAL mode, foreign keys, and transaction management.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator
from backend.config import settings


def get_connection(
    db_path: Path | None = None,
) -> sqlite3.Connection:
  """Create and configure a local SQLite connection."""
  target_path = db_path or settings.SQLITE_DB_PATH
  target_path.parent.mkdir(parents=True, exist_ok=True)

  conn = sqlite3.connect(
      str(target_path),
      timeout=10.0,
      detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
      check_same_thread=False,
  )
  conn.row_factory = sqlite3.Row

  # High-reliability performance pragmas
  conn.execute("PRAGMA journal_mode = WAL;")
  conn.execute("PRAGMA foreign_keys = ON;")
  conn.execute("PRAGMA synchronous = NORMAL;")
  conn.execute("PRAGMA busy_timeout = 5000;")

  return conn


@contextmanager
def get_db(
    db_path: Path | None = None,
) -> Generator[sqlite3.Connection, None, None]:
  """Context manager providing an auto-committing / auto-rolling-back connection."""
  conn = get_connection(db_path)
  try:
    yield conn
    conn.commit()
  except Exception:
    conn.rollback()
    raise
  finally:
    conn.close()
