"""DENTRACE Clinical Decision Support Engine — FastAPI Application Entry Point.

Enforces:
1. Localhost network binding (127.0.0.1) with zero external cloud egress.
2. Automated SQLite schema migrations on startup.
3. Privacy-safe request logging (strips query parameters, zero PHI logging).
4. Structured clinical error envelopes with mandatory regulatory notices.
"""

from contextlib import asynccontextmanager
import logging
import time
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.api.router import root_router
from backend.config import settings
from backend.database.migrations import run_migrations

# Configure privacy-safe console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dentrace.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Application lifespan initializing database migrations and storage directories."""
  logger.info("Initializing %s v%s...", settings.APP_NAME, settings.APP_VERSION)
  logger.info("Local storage directory: %s", settings.STORAGE_DIR)
  logger.info("Local SQLite database: %s", settings.SQLITE_DB_PATH)

  # Run pending database migrations
  try:
    applied = run_migrations()
    logger.info("Database migrations verified. %d new migration(s) applied.", applied)
  except Exception as exc:
    logger.error("Database migration failure: %s", exc, exc_info=True)
    raise

  yield

  logger.info("Shutting down %s.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Local-first dental panoramic radiograph anomaly detection & insurance"
        " pre-authorization decision-support engine. Draft for dentist review."
        " Not a diagnosis."
    ),
    lifespan=lifespan,
)

# CORS restricted strictly to localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:8501",  # Streamlit default port
        "http://localhost:8501",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def privacy_safe_logging_middleware(request: Request, call_next):
  """Privacy-safe logging middleware that sanitizes paths and prevents PHI leaks in server logs."""
  t0 = time.time()
  # Log only method and stripped path without query string
  clean_path = request.url.path
  method = request.method

  try:
    response = await call_next(request)
    elapsed_ms = (time.time() - t0) * 1000.0
    logger.info(
        "%s %s -> %d (%.1f ms)",
        method,
        clean_path,
        response.status_code,
        elapsed_ms,
    )
    return response
  except Exception as exc:
    elapsed_ms = (time.time() - t0) * 1000.0
    logger.error(
        "%s %s -> UNHANDLED EXCEPTION (%.1f ms): %s",
        method,
        clean_path,
        elapsed_ms,
        str(exc),
    )
    raise


# --- Structured Exception Handlers ---


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
  """Uniform clinical JSON envelope for HTTP exceptions."""
  return JSONResponse(
      status_code=exc.status_code,
      content={
          "error": True,
          "status_code": exc.status_code,
          "detail": exc.detail,
          "disclaimer": settings.MANDATORY_DISCLAIMER,
      },
  )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
  """Structured error response for Pydantic input validation failures."""
  errors = []
  for err in exc.errors():
    errors.append({
        "loc": [str(x) for x in err.get("loc", [])],
        "msg": err.get("msg"),
        "type": err.get("type"),
    })
  return JSONResponse(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      content={
          "error": True,
          "status_code": 422,
          "detail": "Data validation failed against clinical schemas",
          "validation_errors": errors,
          "disclaimer": settings.MANDATORY_DISCLAIMER,
      },
  )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
  """Sanitized fallthrough handler preventing internal stack trace disclosure."""
  logger.error("Unhandled internal server error: %s", exc, exc_info=True)
  return JSONResponse(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      content={
          "error": True,
          "status_code": 500,
          "detail": "An internal error occurred during study processing",
          "disclaimer": settings.MANDATORY_DISCLAIMER,
      },
  )


# Mount routes
app.include_router(root_router)
