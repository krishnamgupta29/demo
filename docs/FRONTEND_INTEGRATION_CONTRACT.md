# DENTRACE — Streamlit-to-FastAPI Frontend Integration Contract

> **DOCUMENT ID:** DOC-INT-012  
> **STATUS:** SPECIFICATION & CONTRACT (LEVEL 1)  
> **COMPANION:** `docs/FRONTEND_DESIGN_SYSTEM.md` (Curie-Nordic Radiography Workstation)  
> **AUTHORITY:** Antigravity Principal Architecture Team  

---

## 1. Architectural Separation & Transport Layer

DENTRACE strictly decouples the presentation workstation (Streamlit) from the clinical backend core (FastAPI):

```
+-----------------------------------------------------------+
|          STREAMLIT CLINICAL WORKSTATION (PORT 8501)       |
|  - Curie-Nordic Darkroom UI        - FDI Interactive Grid |
|  - Medical Viewer & Polygon Canvas - Pre-Auth Narrative   |
+-----------------------------------------------------------+
                             |
         REST / JSON over loopback (127.0.0.1:8000)
         Strictly Zero Telemetry / Zero External Cloud
                             v
+-----------------------------------------------------------+
|               FASTAPI CORE BACKEND (PORT 8000)            |
|  - /api/v1/health & readiness     - Storage Manager       |
|  - /api/v1/studies (Upload/CRUD)  - SQLite WAL Database   |
|  - /api/v1/models (Registry)      - Quality Screening     |
+-----------------------------------------------------------+
```

### Transport Protocol
- **Base URL:** `http://127.0.0.1:8000/api/v1`
- **Transport Client:** `httpx.Client(timeout=10.0)`
- **Authentication:** Local session token (Prototype local boundary)
- **Error Handling:** Standardized clinical error envelope:
  ```json
  {
    "error": true,
    "status_code": 400,
    "detail": "Description of clinical or validation error",
    "disclaimer": "Draft for dentist review. Not a diagnosis."
  }
  ```

---

## 2. API Endpoint Contracts

### A. Health & Readiness Diagnostics
| Endpoint | Method | Response Payload | Frontend Workstation Behavior |
|---|---|---|---|
| `/health` | `GET` | `{"status": "healthy", "version": "0.1.0", "disclaimer": "..."}` | Heartbeat pulse badge in top status bar (Quiet green `#10B981`) |
| `/readiness` | `GET` | `{"status": "ready", "checks": {"database": true, "storage": true}}` | Blocks study upload modal if `database` or `storage` is false |

### B. Study Intake & Storage
| Endpoint | Method | Request Type | Success Code | Response Payload |
|---|---|---|---|---|
| `/studies` / `/studies/upload` | `POST` | `multipart/form-data` (`file`, `patient_anonymous_id`, `clinical_indication`) | `201 Created` | `StudyResponse` JSON with `study_id`, `radiograph` metadata, `quality` assessment |
| `/studies` | `GET` | Query params: `limit`, `offset`, `include_archived` | `200 OK` | `StudyList` JSON with `total` and array of `StudyResponse` items |
| `/studies/{study_id}` | `GET` | Path parameter `study_id` | `200 OK` | `StudyDetail` JSON with complete teeth, findings, review confirmations |
| `/studies/{study_id}/preview` | `GET` | Path parameter `study_id` | `200 OK` | Binary `image/png` raster stream |
| `/studies/{study_id}` | `DELETE` | Path parameter `study_id`, query `hard_delete=true` | `204 No Content` | Removes active study, clears viewer canvas, refreshes study list |

### C. Model Registry & Availability
| Endpoint | Method | Response Payload | Frontend Behavior |
|---|---|---|---|
| `/models` | `GET` | `{"total": 4, "models": [...], "notice": "..."}` | Renders Model Inventory drawer; uninstalled models flagged as `MODEL_UNAVAILABLE` |
| `/models/{model_id}/status` | `GET` | Specific model provenance & SHA-256 | Displays provenance card with execution provider and license |

---

## 3. Workstation State Management (`st.session_state`)

Streamlit manages clinical session state with explicit, predictable keys:

```python
st.session_state.current_study_id: Optional[str]        # Currently active study
st.session_state.active_fdi_tooth: Optional[int]         # Tooth selected in odontogram (e.g. 16)
st.session_state.active_pathology_filter: set[str]      # Active anomaly filter tags
st.session_state.viewer_zoom_level: float               # Zoom multiplier (1.0 to 4.0)
st.session_state.viewer_pan_offset: tuple[int, int]     # (x, y) pan coordinates
st.session_state.clinician_attestation: dict            # Clinician review status
```

---

## 4. Canvas Coordinate Mapping & Overlay Rendering

### Diagnostic Integrity Guardrails
1. **Never mutate source pixels:** The original radiograph is displayed via the web preview raster (`/preview`), maintaining exact 1:1 pixel coordinates mapped from the original resolution.
2. **Absolute coordinate translation:**
   ```
   Normalized X = (bbox_x / original_width) * rendered_canvas_width
   Normalized Y = (bbox_y / original_height) * rendered_canvas_height
   ```
3. **No distracting pulsing/flashing:** All pathology overlays are static semi-transparent polygons (opacity `0.35`–`0.45`) with crisp 2px solid boundaries according to `docs/FRONTEND_DESIGN_SYSTEM.md`. Flashing, pulsing, or animated hazard glows are strictly prohibited over clinical imagery.

---

## 5. Accessibility & Reduced Motion

- **Keyboard Navigation:**
  - `Key 1`–`Key 4`: Select dental quadrants 1, 2, 3, or 4.
  - `Tab` / `Shift+Tab`: Cycle through identified teeth in anatomical order.
  - `Escape`: Clear active tooth filter and reset canvas zoom.
- **Reduced Motion:**
  - When `prefers-reduced-motion` is active, all pane transitions, drawer expansions, and zoom interpolations resolve instantly (0ms duration).
