# DENTRACE Level 8 — Security Audit Report

> **DOCUMENT ID:** DOC-SEC-008
> **STATUS:** COMPLETE
> **DATE:** 2026-10-22
> **SCOPE:** Academic single-user prototype — not a certified medical device

---

## Executive Summary

Level 8 security audit reviewed the complete DENTRACE application stack. Critical hardening was applied to the API middleware layer. No critical vulnerabilities requiring immediate escalation were found. All findings are documented with mitigations appropriate for an academic prototype.

---

## 1. Attack Surface Inventory

| Surface | Implementation | Risk Level |
|---|---|---|
| File upload endpoint | Magic byte validation + extension allowlist + size cap | Medium → Mitigated |
| File storage paths | `sanitize_filename()` + `is_relative_to()` secondary check | Medium → Mitigated |
| Study ID path parameters | FastAPI routing + parameterized SQL | Low |
| SQL queries | SQLite parameterized queries throughout | Low |
| CORS policy | Explicit localhost-only origins, no wildcard | Low |
| Network binding | 127.0.0.1 only — not 0.0.0.0 | Low |
| API response headers | Security headers added at Level 8 | Low after fix |
| Ollama prompt injection | Fixed Pydantic schema validation on LLM output | Low |
| PDF generation | ReportLab canvas (no HTML rendering) | Low |
| Error responses | Stack trace suppressed; type-only logging | Low |

---

## 2. Findings and Remediations

### SEC-01: Missing Security Response Headers (FIXED)

**Severity:** Medium  
**Description:** The FastAPI middleware did not add security response headers, allowing potential browser-side MIME sniffing, clickjacking, and information leakage.  
**Fix Applied (`backend/main.py`):**
```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
response.headers["Referrer-Policy"] = "no-referrer"
response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"  # API routes
response.headers["Content-Security-Policy"] = "default-src 'none'; ..."
```

### SEC-02: `response.headers.pop()` API Error (FIXED)

**Severity:** Critical (crashed entire application middleware)  
**Description:** FastAPI/Starlette `MutableHeaders` does not support `.pop()`. Using `response.headers.pop("Server", None)` raised `AttributeError` on every request, making the application unusable.  
**Fix Applied:**
```python
try:
    del response.headers["server"]
except KeyError:
    pass
```

### SEC-03: Path Traversal Defense (VERIFIED ADEQUATE)

**Mechanism:** `sanitize_filename()` uses `Path(filename).name` (extracts basename only) + regex `[^a-zA-Z0-9_\-\.]` replacement. The secondary `is_relative_to()` check in `save_upload()` provides defense-in-depth.

**Coverage:**
- `../../../etc/passwd` → `passwd` ✅
- `../../Windows/evil.exe` → `evil.exe` ✅  
- `/absolute/evil.dcm` → `evil.dcm` ✅
- URL-encoded (`%2F`) traversal: Decoded by HTTP framework (FastAPI) before reaching storage layer ✅

### SEC-04: Content Validation (VERIFIED ADEQUATE)

| Check | Mechanism | Status |
|---|---|---|
| File size | `MAX_UPLOAD_SIZE_BYTES = 50 MB` | ✅ |
| Extension allowlist | `.png .jpg .jpeg .bmp .tiff .tif .dcm` | ✅ |
| Magic byte validation | Custom MIME detector on first 136 bytes | ✅ |
| DICOM pixel validation | `dcm.pixel_array` + `img.verify()` + `img.load()` | ✅ |

### SEC-05: SQL Injection (VERIFIED NOT VULNERABLE)

All database queries use SQLite parameterized placeholders (`?`). No string interpolation in SQL. Path parameter values are treated as strings and looked up against indexed primary keys. Injection patterns return 404 without error.

### SEC-06: Localhost Binding (VERIFIED)

`settings.HOST = "127.0.0.1"`. FastAPI/Uvicorn cannot accept connections from non-loopback interfaces. CORS origins explicitly enumerate `localhost` and `127.0.0.1` variants only — no wildcard.

### SEC-07: Error Message Leakage (MITIGATED)

Global exception handler logs `type(exc).__name__` only (not full message). API error responses return structured envelopes without internal paths, stack traces, or patient data. Middleware logging strips query strings.

### SEC-08: Model Checkpoint Integrity

SHA-256 hashes computed on model load. Verification available via `model_registry.list_models()`. Hashes are not compared against a reference manifest (tracking issue for Level 9).

---

## 3. Access Control Statement

> **IMPORTANT:** This application does not implement authentication or authorization.
> 
> Localhost binding (`127.0.0.1:8000`) is a **network isolation measure**, not an authentication mechanism. Any process running on the same machine can connect to the API.
>
> **Mitigating factors for academic prototype use:**
> - Single-user workstation deployment
> - No multi-user or multi-tenant requirement  
> - No internet exposure intended
> - Firewall should block port 8000 from LAN
>
> **Do NOT** expose port 8000 via reverse proxy, port-forwarding, or firewall rules without adding authentication.

---

## 4. Prompt Injection Defense

Ollama LLM responses are validated through the `FaithfulnessChecker` before persistence. The checker:
1. Validates output against a Pydantic JSON schema
2. Detects prohibited autonomous diagnosis terms
3. Falls back to deterministic template if output fails schema validation

Malformed or injection-laden LLM outputs cannot corrupt clinical records.

---

## 5. Remaining Non-Critical Issues

| Issue | Severity | Action |
|---|---|---|
| No API authentication | Info (academic scope) | Document; Level 9 scope |
| Checkpoint hash not compared to reference manifest | Info | Level 9 scope |
| Streamlit UI has no CSRF token | Info | Not applicable (same-origin localhost only) |
| `httpx2` deprecation warning from TestClient | Info | Library migration; future |

---

## 6. Compliance Disclaimer

> This security audit was conducted by the development team for academic quality assurance purposes. It is **not** a formal penetration test, security certification, or HIPAA/GDPR compliance assessment.
>
> The system is designated as an **academic college decision-support prototype** and is not intended for clinical deployment, multi-user production use, or submission to regulatory bodies without further professional security review.
