import { test, expect } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8000';

test.describe('DENTRACE Level 12 Single-Page Premium Visual Experience Suite', () => {
  test('01: Pure White Single-Page Shell & Elimination of Multi-Page Dashboard', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/DENTRACE/);

    // Verify brand wordmark
    await expect(page.locator('text=DENTRACE').first()).toBeVisible();
    await expect(page.locator('text=Clinical Panoramic Radiograph Analysis').first()).toBeVisible();

    // Verify regulatory clinical boundary
    const boundaryBanner = page.locator('text=Draft for dentist review. Not a diagnosis.');
    await expect(boundaryBanner.first()).toBeVisible();

    // Verify localhost loopback badge
    await expect(page.locator('text=127.0.0.1:8000').first()).toBeVisible();

    // Verify sidebar and 7-page navigation are REMOVED from the DOM
    const sidebar = page.locator('aside');
    await expect(sidebar).toHaveCount(0);
    const navLinks = page.locator('a[href="/workstation"], a[href="/evidence"], a[href="/settings"]');
    await expect(navLinks).toHaveCount(0);
  });

  test('02: Before-Upload Intake Bay & 3D Reference Model Preview', async ({ page }) => {
    await page.goto(BASE_URL);

    // Verify heading
    await expect(page.locator('h1')).toContainText('Dental Panoramic Radiograph Anomaly Detection');

    // Verify file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
    const accept = await fileInput.getAttribute('accept');
    expect(accept).toContain('.png');

    // Verify 3D reference model is mounted
    const canvas3d = page.locator('canvas');
    await expect(canvas3d.first()).toBeVisible();

    // Verify non-diagnostic watermark
    await expect(page.locator('text=Reference 3D Model — Not Patient Scan').first()).toBeVisible();

    // Verify NO fake analysis findings before upload
    await expect(page.locator('text=Detected Anomalies')).toHaveCount(0);
  });

  test('03: Transformation to Analysis Workspace & Radiograph Preview', async ({ page }) => {
    await page.goto(BASE_URL);

    // Click quick verified case button
    const loadSampleBtn = page.locator('button:has-text("Load Verified Case")');
    await expect(loadSampleBtn).toBeVisible();
    await loadSampleBtn.click();

    // Verify transformation into analysis workspace
    await expect(page.locator('text=Detected Anomalies').first()).toBeVisible({ timeout: 12000 });

    // Verify radiograph preview image rendered
    const radiographImg = page.locator('img[alt="Panoramic Dental Radiograph"]');
    await expect(radiographImg.first()).toBeVisible();

    // Verify overlay visibility toggle
    await expect(page.locator('button:has-text("Detection Overlays Active")').first()).toBeVisible();
  });

  test('04: Interactive Radiograph Viewport & Overlay Controls', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('button:has-text("Load Verified Case")').click();
    await expect(page.locator('text=Detected Anomalies').first()).toBeVisible({ timeout: 12000 });

    // Test overlay toggle button
    const toggleBtn = page.locator('button:has-text("Detection Overlays Active")');
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();
    await expect(page.locator('button:has-text("Overlays Hidden")')).toBeVisible();

    // Re-enable
    await page.locator('button:has-text("Overlays Hidden")').click();
    await expect(page.locator('button:has-text("Detection Overlays Active")')).toBeVisible();

    // Test zoom controls
    await expect(page.locator('button[title="Zoom In"]')).toBeVisible();
    await expect(page.locator('button[title="Zoom Out"]')).toBeVisible();
    await expect(page.locator('button[title="Fit to Window"]')).toBeVisible();
  });

  test('05: 3D Anatomical Dental Model Synchronization & Camera Presets', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('button:has-text("Load Verified Case")').click();
    await expect(page.locator('text=Detected Anomalies').first()).toBeVisible({ timeout: 12000 });

    // Verify 3D canvas is active
    const canvas3d = page.locator('canvas');
    await expect(canvas3d.first()).toBeVisible();

    // Click camera angle presets
    const maxillaBtn = page.locator('button:has-text("maxilla")');
    if (await maxillaBtn.isVisible()) {
      await maxillaBtn.click();
    }

    const fullArchBtn = page.locator('button:has-text("Full Arch")');
    if (await fullArchBtn.isVisible()) {
      await fullArchBtn.click();
    }

    // Verify tooth telemetry pill is present
    await expect(page.locator('text=FDI #').first()).toBeVisible();
  });

  test('06: Real Analysis Results Dossier & New Scan Action', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('button:has-text("Load Verified Case")').click();
    await expect(page.locator('text=Detected Anomalies').first()).toBeVisible({ timeout: 12000 });

    // Verify real detections list is populated
    await expect(page.locator('text=Actual Model Detections')).toBeVisible();

    // Verify PDF claim export button
    const pdfLink = page.locator('a:has-text("Export Claim PDF")');
    await expect(pdfLink).toBeVisible();
    const href = await pdfLink.getAttribute('href');
    expect(href).toContain('/claim-pack/pdf');

    // Click "Upload Another Radiograph" to return to upload state
    const resetBtn = page.locator('button:has-text("Upload Another Radiograph")');
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    // Verify return to clean upload state
    await expect(page.locator('h1')).toContainText('Dental Panoramic Radiograph Anomaly Detection');
    await expect(page.locator('text=Drag & Drop Panoramic Dental Radiograph')).toBeVisible();
  });
});

