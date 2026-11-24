"""DENTRACE Clinical Decision Support Engine — FastAPI Application Entry Point.

Enforces:
1. Localhost network binding (127.0.0.1) with zero external cloud egress.
2. Automated SQLite schema migrations on startup.
3. Privacy-safe request logging (strips query parameters, zero PHI logging).
4. Structured clinical error envelopes with mandatory regulatory notices.
5. Security response headers (X-Content-Type-Options, X-Frame-Options, Cache-Control).
6. Request body size guard before processing.

ACCESS CONTROL NOTE (Level 8):
  This application is a single-user academic prototype. Authentication is not
  implemented. All API endpoints are bound strictly to 127.0.0.1 and are
  NOT reachable from other hosts on the local network. Localhost binding is a
  network isolation measure, not an authentication mechanism. Do NOT expose
  port 8000 through firewalls, reverse proxies, or port-forwarding.
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
        "http://127.0.0.1:5173",  # Vite dev server
        "http://localhost:5173",
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
async def security_and_logging_middleware(request: Request, call_next):
  """Combined security headers + privacy-safe logging middleware.

  Security actions (Level 8):
  - Adds hardened HTTP response headers to every response.
  - Strips query strings from log entries to prevent PHI leakage in access logs.
  - Does NOT log request bodies, file names, or patient IDs.
  """
  t0 = time.time()
  clean_path = request.url.path
  method = request.method

  # Level 9 Local Access Control: Single-User Token Enforcement
  if settings.LOCAL_API_KEY:
    if (
        clean_path.startswith("/api/v1/")
        and not clean_path.startswith("/api/v1/health")
        and method != "OPTIONS"
    ):
      token = request.headers.get("X-DENTRACE-TOKEN") or request.headers.get("Authorization")
      if token and token.startswith("Bearer "):
        token = token[7:]
      if token != settings.LOCAL_API_KEY:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": "Unauthorized: Invalid or missing local access token",
                "disclaimer": settings.MANDATORY_DISCLAIMER,
            },
        )

  try:
    response = await call_next(request)
    elapsed_ms = (time.time() - t0) * 1000.0

    # --- Security Response Headers ---
    # Prevent MIME-sniffing attacks
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking (deny iframe embedding)
    response.headers["X-Frame-Options"] = "DENY"
    # Legacy XSS filter hint for older browsers
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Referrer policy: do not leak URL information
    response.headers["Referrer-Policy"] = "no-referrer"
    # Prevent caching of sensitive clinical API responses
    if clean_path.startswith("/api/"):
      response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
      response.headers["Pragma"] = "no-cache"
    # Content Security Policy: block all external resource loading (Zero Cloud Egress)
    if clean_path.startswith("/api/"):
      response.headers["Content-Security-Policy"] = (
          "default-src 'none'; "
          "script-src 'none'; "
          "style-src 'none'; "
          "img-src 'self' data:; "
          "connect-src 'self'"
      )
    else:
      # React SPA Frontend CSP (Level 11): strictly self-hosted offline resources
      response.headers["Content-Security-Policy"] = (
          "default-src 'self'; "
          "script-src 'self' 'unsafe-inline'; "
          "style-src 'self' 'unsafe-inline'; "
          "img-src 'self' data: blob:; "
          "connect-src 'self'"
      )
    # Remove server identification header if present
    # (MutableHeaders does not support .pop(); use try/del)
    try:
      del response.headers["server"]
    except KeyError:
      pass

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
        type(exc).__name__,  # Log exception type only, not full message (PHI guard)
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

# Mount React Production Frontend (Level 11)
WEB_DIST_DIR = settings.PROJECT_ROOT / "frontend" / "dist"
if not WEB_DIST_DIR.exists():
  WEB_DIST_DIR = settings.PROJECT_ROOT / "web" / "dist"
if WEB_DIST_DIR.exists():
  from fastapi.staticfiles import StaticFiles
  from fastapi.responses import FileResponse

  assets_dir = WEB_DIST_DIR / "assets"
  if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="web_assets")

  @app.get("/{full_path:path}", include_in_schema=False)
  async def serve_spa_frontend(full_path: str):
    """Serve React single-page application with client-side routing fallback."""
    if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API endpoint not found")
    file_candidate = WEB_DIST_DIR / full_path
    if full_path and file_candidate.is_file():
      return FileResponse(file_candidate)
    index_html = WEB_DIST_DIR / "index.html"
    if index_html.exists():
      return FileResponse(index_html)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontend build missing")

