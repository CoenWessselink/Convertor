import { test, expect } from '@playwright/test';
import path from 'node:path';

const stepFixture = path.resolve(process.cwd(), 'tests/fixtures/sample.step');
const invalidFixture = path.resolve(process.cwd(), 'tests/fixtures/invalid.txt');

async function login(page) {
  await page.goto('/login');
  await page.getByPlaceholder('Tenant').fill('demo');
  await page.getByPlaceholder('E-mail').fill('admin@demo.com');
  await page.getByPlaceholder('Wachtwoord').fill('Admin123!');
  await page.getByRole('button', { name: 'Inloggen' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText('Convertor')).toBeVisible();
}

test('login, upload, jobs en viewer-flow', async ({ page }) => {
  await login(page);
  await page.getByRole('link', { name: 'Upload' }).click();
  await expect(page.getByRole('heading', { name: 'Upload' })).toBeVisible();

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(stepFixture);

  await expect(page).toHaveURL(/\/jobs$/);
  await expect(page.getByRole('heading', { name: 'Jobs' })).toBeVisible();
  await expect(page.getByText('sample.step')).toBeVisible();

  await page.getByRole('link', { name: 'Openen' }).first().click();
  await expect(page.getByRole('heading', { name: 'Jobdetail' })).toBeVisible();
  await page.getByRole('link', { name: 'Open viewer' }).click();
  await expect(page.getByText('DXF downloaden')).toBeVisible();
  await page.getByRole('button', { name: 'front' }).click();
  await expect(page.getByText('Projectie')).toBeVisible();
});

test('ongeldig bestand geeft foutmelding', async ({ page }) => {
  await login(page);
  await page.getByRole('link', { name: 'Upload' }).click();
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(invalidFixture);
  await expect(page.getByText(/Niet toegestaan:/)).toBeVisible();
});
