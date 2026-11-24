# LEVEL 20 — OPG MODALITY AUTO-DETECTION & PERSISTENCE DEBUGGING REPORT

> **DOCUMENT ID:** DOC-L20-DEBUG-002  
> **TOPIC:** Root-Cause Analysis of OPG→IOPA Misclassification & Modality Lifecycles  
> **DATE:** 2026-11-21  

---

## 1. Defect Description & Symptoms

When users uploaded standard Panoramic OPG radiographs captured via digital cameras or smartphones, the application exhibited the following defects:
1. Ingested radiographs were assigned `intraoral_periapical` modality.
2. The radiograph workspace rendered an orange/yellow IOPA warning banner: *"IOPA Limited-Field Workflow — 4-Tooth Focus Strip"*.
3. Model inference was permanently blocked with notice: *"MODALITY_SAFETY_GUARD: AI model is trained and validated strictly on Panoramic OPG images. Automated AI detection is NOT AVAILABLE for Intraoral Periapical (IOPA) radiographs."*
4. The user could not trigger neural screener or segmentation models, even though the image was physically a panoramic radiograph.

---

## 2. Technical Investigation & Root Cause

### 2.1 Database Audit of Existing Records
An inspection of the local SQLite database (`data/dentrace.db`) revealed that almost all historical studies were tagged with `modality = 'intraoral_periapical'`:
- Image file: `eeb89254...jpg` -> Dimensions: $1200 \times 1600$ (Aspect ratio: $0.75$) -> Tagged: `intraoral_periapical`
- Image file: `38588d53...jpg` -> Dimensions: $1200 \times 1600$ (Aspect ratio: $0.75$) -> Tagged: `intraoral_periapical`
- Image file: `4570e919...jpg` -> Dimensions: $1200 \times 1600$ (Aspect ratio: $0.75$) -> Tagged: `intraoral_periapical`

### 2.2 The Ingestion Code Flaw
In `backend/services/study_service.py`, `create_study()` computed:
$$\text{aspect\_ratio} = \frac{\text{width}}{\text{height}} = \frac{1200}{1600} = 0.75$$
The heuristic logic evaluated:
```python
if metadata.aspect_ratio <= 1.4:
    persisted_modality = "intraoral_periapical"
```
Because standard intraoral radiographs typically have aspect ratios around $1.0$ to $1.33$ (e.g. Size 2 sensor $31 \times 41$ mm $\approx 1.32$), the rule assumed anything $\le 1.4$ was an IOPA! However, users frequently take portrait-mode smartphone photos of printed panoramic films or panoramic monitor displays, yielding vertical orientations ($\text{aspect\_ratio} < 1.0$).

---

## 3. The Resolution

### 3.1 Strict Heuristic Boundary (`study_service.py`)
The ingestion logic was updated to eliminate speculative classification:
```python
valid_modalities = {"panoramic_opg", "intraoral_periapical", "bitewing", "unknown"}
if modality and modality.lower() in valid_modalities:
    persisted_modality = modality.lower()
else:
    # A new study must NEVER silently default to IOPA.
    # When modality is uncertain (e.g. portrait photo of OPG or non-panoramic ratio),
    # set to 'unknown' so the clinician confirms modality instead of silently guessing.
    if metadata.aspect_ratio >= 1.5:
        persisted_modality = "panoramic_opg"
    else:
        persisted_modality = "unknown"
```

### 3.2 Dynamic State Reset on Modality Update
When a user updates a study's modality via `PATCH /api/v1/studies/{study_id}/modality`, the backend now resets the study lifecycle:
```python
with get_db() as conn:
    conn.execute(
        "UPDATE radiographs SET modality = ? WHERE study_id = ?;",
        (target_modality, study_id),
    )
    if target_modality == "panoramic_opg":
        # Reset study status so fresh analysis can execute
        conn.execute(
            "UPDATE studies SET status = 'ingested', updated_at = ? WHERE study_id = ? AND status != 'reviewed';",
            (datetime.utcnow(), study_id),
        )
```

### 3.3 Frontend Interactive Confirmation
In `web/src/views/SinglePageExperience.tsx`:
1. Uploading a portrait OPG now displays the high-contrast yellow alert banner:
   *"Modality Confirmation Required — Radiograph modality is unconfirmed. AI inference is disabled until confirmed."*
2. Clicking `[Confirm Panoramic (OPG)]` instantly updates the database, updates local state, clears the banner, and triggers the local AI screener.

---

## 4. Verification

This behavior was validated with unit tests:
- `test_portrait_or_square_study_defaults_to_unknown_never_silently_iopa` (PASSED)
- `test_switching_from_iopa_to_opg_permits_fresh_analysis` (PASSED)
- `test_aspect_ratio_threshold_boundary` (PASSED)
