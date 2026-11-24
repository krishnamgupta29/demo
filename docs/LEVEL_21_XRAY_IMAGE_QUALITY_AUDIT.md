# LEVEL 21 — X-RAY IMAGE QUALITY AUDIT
**Investigation of Radiograph Ingestion, Decoding, Canvas Scaling & PDF Pipeline**

---

## 1. Executive Summary & Root Cause Analysis

A core mandate of Level 21 was investigating and resolving poor X-ray rendering across the application. The audit tracked an uploaded radiograph through every stage:
```
Raw Upload → Backend Storage → DICOM Decoding → Preview Generation → Canvas Scaling → PDF Export
```

### 1.1 Identified Root Causes
1. **Initial Canvas Scale Default**: In previous versions, `RadiographCanvas` initialized with `scale = 1.0` and no auto-fit. High-resolution radiographs (e.g., 2872×1316 px) overflowed the viewport container, causing clinicians to see an arbitrary zoomed-in corner that appeared cropped and distorted.
2. **Preview Image Pipeline in PDF**: The PDF generator previously referenced downscaled 1400px web previews (`C:/mini/data/previews/{id}_preview.png`) instead of the full-resolution storage asset.
3. **Bilinear Interpolation Blur**: Deep zooming into tooth apices lacked crisp pixel rendering, leading to fuzzy edges on high-DPI displays.

---

## 2. Corrective Actions Implemented

### 2.1 Full-Resolution Storage Ingestion
- `backend/storage/file_manager.py` preserves uncompressed raw image bytes in `settings.STORAGE_DIR` (`C:/mini/data/storage`).
- DICOM files (`.dcm`) have their 16-bit or 8-bit raw pixel arrays decoded via `pydicom`, with Photometric Interpretation (`MONOCHROME1` vs `MONOCHROME2`) properly inverted and normalized without loss of diagnostic contrast.
- Web previews (`settings.PREVIEW_DIR`) are strictly used as lightweight browser thumbnails, not as master diagnostic assets.

### 2.2 Backend Original Image Endpoint
- Added `GET /api/v1/studies/{study_id}/original` in `backend/api/routes/studies.py`.
- Serves native full-resolution raster files directly to the client with correct MIME types and path traversal validation (`validate_safe_study_id`).

### 2.3 Canvas Auto-Fit & Contain Behavior
- Updated `web/src/components/workstation/RadiographCanvas.tsx`:
  - Implemented automatic viewport containment on initial load:
    ```typescript
    const s = Math.min(cw / naturalSize.w, ch / naturalSize.h, 1);
    setScale(+s.toFixed(2));
    setPan({ x: 0, y: 0 });
    ```
  - Aspect ratio is strictly preserved with `object-fit: contain` equivalent logic (`maxWidth: none` inside a transform wrapper).
  - Radiographs are never stretched or cropped.

### 2.4 Pixel Sharpness & Micro-Contrast Enhancement
- Added adaptive image rendering: `imageRendering: scale > 1.8 ? 'pixelated' : 'auto'` ensuring crisp boundaries when magnifying root canals and periodontal ligament spaces.
- Added Display Enhancement toggle (`contrast(1.32) brightness(1.04) saturate(0)`) for chairside visual enhancement while keeping diagnostic pixels unmodified.

### 2.5 PDF High-Resolution Embedding
- Updated `backend/reporting/pdf_generator.py` to scan `settings.STORAGE_DIR` for the primary high-resolution asset before falling back to previews.
- Full-resolution radiographs are embedded on Page 2 with preserved aspect ratio, high JPEG quality (94+), and complete technical metadata.
