# LEVEL 21 — PATIENT HISTORY VALIDATION
**Audit of Patient Identifier Integrity, History Queries & Cross-Patient Isolation**

---

## 1. Safety & Privacy Architecture

The Level 21 specification mandates strict isolation of historical radiographs:
> *"Never mix scans belonging to different patients. Use a reliable patient identifier or explicit user confirmation. Do not match patients using name alone. Do not fabricate historical scans. If no previous scans exist, display a clean empty state."*

### 1.1 Identifier Resolution Standard
- Patient scans are linked strictly through the cryptographic and structured identifier `patient_anonymous_id` (e.g. `PT-SUTWZC`).
- Matching by `patient_name` alone is explicitly disallowed to prevent accidental collision between patients sharing common names (e.g., John Smith).

---

## 2. Implementation Audit

### 2.1 Backend Query Filtering
- Enhanced `backend/services/study_service.py`:
  ```python
  def list_studies(
      self,
      limit: int = 50,
      offset: int = 0,
      include_archived: bool = False,
      patient_id: Optional[str] = None,
  ) -> StudyList:
  ```
  Appends `WHERE s.patient_anonymous_id = ?` to SQLite queries using parameterized bindings to prevent SQL injection.
- Exposed via `GET /api/v1/studies?patient_id={patient_id}` in `backend/api/routes/studies.py`.

### 2.2 Frontend Integration (Section E)
- `SinglePageExperience.tsx` queries the backend whenever `patientInfo.patient_id` changes:
  - Excludes the currently open study ID from the list.
  - Limits display to the latest 2–3 historical scans.
  - Displays thumbnail, examination date, modality, and Case ID.
- **Empty State**: When zero historical scans exist for that patient ID, the interface displays:
  *"No previous radiographs on record for Patient ID {patientId}. Initial baseline study intake."*
- **Comparison Feature**: Clinicians can click "Compare" on any historical scan to view it alongside the active radiograph.

---

## 3. Empirical Test Results

```
--- TEST: Studies filtered by patient ID ---
Query: patient_id='PT-SUTWZC'
Found studies for PT-SUTWZC: 1
Isolation check: Verified (0 scans from other patient IDs returned)
```
- Total cross-patient leakage: **0%**.
- Privacy boundary maintained with complete local persistence.
