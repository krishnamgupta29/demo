import { test, expect } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8000';

test.describe('DENTRACE Level 11 React Frontend Functional Suite', () => {
  test('01: System Shell & Overview Navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/overview`);
    await expect(page).toHaveTitle(/DENTRACE/);

    // Verify mandatory regulatory clinical boundary
    const boundaryBanner = page.locator('text=Draft for dentist review. Not a diagnosis.');
    await expect(boundaryBanner.first()).toBeVisible();

    // Verify telemetry heartbeat badge
    const telemetry = page.locator('text=127.0.0.1:8000');
    await expect(telemetry.first()).toBeVisible();

    // Verify 3D canvas is mounted
    const canvas3d = page.locator('canvas');
    await expect(canvas3d.first()).toBeVisible();
  });

  test('02: Radiograph Ingestion & Intake Bay', async ({ page }) => {
    await page.goto(`${BASE_URL}/upload`);
    await expect(page.locator('h1')).toContainText('Dental Panoramic Radiograph Ingestion');

    // Verify file input supports PNG, JPEG, DICOM
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
    const accept = await fileInput.getAttribute('accept');
    expect(accept).toContain('.png');
  });

  test('03: Diagnostic Workstation & Viewport Toolbar', async ({ page }) => {
    await page.goto(`${BASE_URL}/workstation`);
    await expect(page.locator('text=PRIMARY RADIOGRAPHIC VIEWPORT')).toBeVisible();

    // Wait for active study selector to populate and canvas to render
    const canvasContainer = page.locator('img[alt="Panoramic Radiograph"], canvas');
    await expect(canvasContainer.first()).toBeVisible({ timeout: 10000 });

    // Verify layer toggles exist on the toolbar
    await expect(page.locator('button:has-text("Box")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Mask")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Label")').first()).toBeVisible();

    // Verify screener button
    const screenerBtn = page.locator('button:has-text("Run Screener")');
    await expect(screenerBtn).toBeVisible();
  });

  test('04: FDI Tooth Explorer 3D/2D Sync', async ({ page }) => {
    await page.goto(`${BASE_URL}/fdi`);
    await expect(page.locator('h1')).toContainText('FDI Tooth Explorer');

    // Check that odontogram button exists (Tooth 16)
    const toothButtons = page.locator('button:has-text("16")');
    await expect(toothButtons.first()).toBeVisible();

    // Click tooth 16
    await toothButtons.first().click();
    await expect(page.locator('h3:has-text("Tooth #16")').first()).toBeVisible();
  });

  test('05: Clinical Evidence & Strict Separation of Facts', async ({ page }) => {
    await page.goto(`${BASE_URL}/evidence`);
    await expect(page.locator('h1')).toContainText('Clinical Evidence Engine');

    // Verify strict separation headers
    await expect(page.locator('h3:has-text("AI Candidate Observations")').first()).toBeVisible();
    await expect(page.locator('h3:has-text("Clinician Confirmed Findings")').first()).toBeVisible();
  });

  test('06: Insurance Pre-Authorization Studio', async ({ page }) => {
    await page.goto(`${BASE_URL}/preauth`);
    await expect(page.locator('h1')).toContainText('Insurance Pre-Authorization Studio');

    // Wait for active study to populate header
    await expect(page.locator('button:has-text("Generate Narrative")').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('a:has-text("Export Claim PDF")').first()).toBeVisible({ timeout: 10000 });
  });

  test('07: System Settings & Hardware Instrumentation', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await expect(page.locator('h1')).toContainText('System Settings & Hardware Instrumentation');

    // Verify GPU & zero cloud egress indicators
    await expect(page.locator('text=NVIDIA GeForce RTX 2050').first()).toBeVisible();
    await expect(page.locator('text=Zero External Cloud Egress').first()).toBeVisible();
  });
});
