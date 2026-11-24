# DENTRACE Level 9: Security Review & Privacy Hardening Report

## 1. Security Architecture & Threat Model

DENTRACE operates in a single-workstation, offline clinical environment. While network exposure to the wider internet is strictly zero, local workstations introduce specific security vectors:
1. **Localhost Cross-Service Hijacking**: Other local applications or untrusted browser tabs could attempt to query or manipulate clinical endpoints on `127.0.0.1:8000`.
2. **DICOM Metadata PHI Leakage**: Incoming DICOM files frequently carry sensitive patient identifiers in standard and vendor-private tags.
3. **Burned-In Annotation Pixel Leakage**: Some legacy OPG scanners hardcode patient names directly into the pixel frame.
4. **File System Permission Violations**: Applications attempting to write patient data to `Program Files` or shared directories violate Windows User Account Control (UAC) and multi-user privacy.

---

## 2. Implemented Security Controls

### 2.1 Single-User Local Access Token Authentication
- **Mechanism**: The supervisor launcher generates a cryptographically strong 256-bit random token (`secrets.token_urlsafe(32)`) upon launch.
- **Enforcement**: FastAPI middleware inspects the `X-DENTRACE-TOKEN` header on every incoming HTTP request.
- **Behavior**: Any request without the valid header (or with an invalid token) is immediately rejected with `401 Unauthorized`, preventing unauthorized local processes or browser tabs from probing patient records or triggering model inference.
- **Exemptions**: Only public read-only health probe `/health` is exempted to enable service liveness verification.

### 2.2 Comprehensive DICOM PHI De-Identification
The ingestion pipeline in `backend/storage/file_manager.py` implements an 18-tag anonymization scrub before saving any study:
1. `PatientName` -> Replaced with anonymous pseudorandom study hash
2. `PatientID` -> Anonymized
3. `PatientBirthDate` -> Blanked
4. `PatientSex` -> Blanked
5. `PatientAge` -> Blanked
6. `PatientAddress` -> Stripped
7. `InstitutionName` -> Stripped
8. `InstitutionAddress` -> Stripped
9. `ReferringPhysicianName` -> Stripped
10. `PerformingPhysicianName` -> Stripped
11. `PhysiciansOfRecord` -> Stripped
12. `OperatorsName` -> Stripped
13. `StudyDate` -> Generalized
14. `SeriesDate` -> Generalized
15. `AcquisitionDate` -> Generalized
16. `AccessionNumber` -> Blanked
17. `OtherPatientIDs` -> Stripped
18. `EthnicGroup` -> Stripped

**Private Tag Removal**: In compliance with DICOM PS 3.15 Annex E, all vendor-specific private tags (identified by odd group numbers `0x0009`, `0x0019`, `0x0029`, etc.) are removed recursively.

### 2.3 Burned-In Annotation Detection
- **Metadata Check**: Reads tag `(0x0028, 0x0301) BurnedInAnnotation`. If `'YES'`, flags an advisory warning.
- **Pixel Heuristic Inspection**: Scans image peripheral borders (top/bottom 5% margin) for high-contrast alphanumeric clusters typical of patient name overlays.
- **Safety Directive**: To protect diagnostic validity, pixel values are **not** blindly blurred or cropped, as indiscriminate cropping could eliminate upper alveolar crest or mandibular border anatomy needed for pathology detection. Instead, a clinical warning flag is logged and displayed in the review interface.

### 2.4 User-Isolated Local Storage
- Clinical databases, DICOM stores, and exported pre-authorization claims are placed strictly in the current user's profile:
  `%LOCALAPPDATA%\DENTRACE\data\`
- Complies with Windows UAC standards, requiring no administrative privileges during daily clinical operation.
- Multi-user workstations ensure Patient A's dental records are inaccessible to other Windows accounts.

---

## 3. Residual Risk Assessment

| Risk Vector | Likelihood | Impact | Implemented Mitigation | Residual Level |
|:---|:---:|:---:|:---|:---:|
| Unauthorized local network access | Low | High | Ephemeral `X-DENTRACE-TOKEN` + `127.0.0.1` binding | Low |
| DICOM PHI leakage in metadata | Low | High | 18 standard tags cleared + private tags stripped | Negligible |
| Burned-in text on legacy scans | Medium | Medium | Automated border inspection + clinical notification | Low (Clinical review required) |
| Cloud egress or telemetry leak | Very Low | Critical | Hardcoded localhost URLs + zero external CDNs | Negligible |
