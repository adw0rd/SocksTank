import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

const tinyPngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2nWQ0AAAAASUVORK5CYII='

test('creates place, uploads photos, annotates, quick-checks, and trains', async ({ page }) => {
  const harness = await setupMockApp(page)
  await page.goto('/')

  await page.getByPlaceholder('New place name').fill('Base 1')
  await page.getByRole('button', { name: 'Add', exact: true }).click()
  await expect(page.getByText('Created Base 1')).toBeVisible()

  await page.locator('input[type="file"]').setInputFiles([
    {
      name: 'base1_1.png',
      mimeType: 'image/png',
      buffer: Buffer.from(tinyPngBase64, 'base64'),
    },
    {
      name: 'base1_2.png',
      mimeType: 'image/png',
      buffer: Buffer.from(tinyPngBase64, 'base64'),
    },
  ])
  await expect(page.getByText('Uploaded 2 image(s)')).toBeVisible()

  await page.getByRole('button', { name: /Open Photo Library/ }).click()
  await expect(page.getByTestId('places-photo-library-modal')).toBeVisible()
  await expect(page.getByTestId('places-annotator-image')).toBeVisible()

  const canvas = page.getByTestId('places-annotator-canvas')
  const box = await canvas.boundingBox()
  if (!box) {
    throw new Error('Annotator canvas not available')
  }
  await page.mouse.move(box.x + 30, box.y + 30)
  await page.mouse.down()
  await page.mouse.move(box.x + 220, box.y + 170)
  await page.mouse.up()
  await page.getByRole('button', { name: 'Save Box' }).click()
  await expect(page.getByText('Annotation saved')).toBeVisible()

  await page.getByRole('button', { name: 'Close' }).click()
  await page.getByRole('button', { name: 'Run Check' }).click()
  await expect(page.getByText(/Quick check done:/)).toBeVisible()

  await page.getByRole('button', { name: 'Train' }).click()
  await expect(page.getByText(/Training job .* started on/)).toBeVisible()
  await expect(page.getByText('Training Job', { exact: true })).toBeVisible()
  await expect(page.getByText('Recent Training Jobs')).toBeVisible()
  await expect(page.getByText(/Used images: train/).first()).toBeVisible()

  const trainRequest = harness.requests.find((entry) => entry.method === 'POST' && entry.path.endsWith('/train'))
  expect(trainRequest).toBeDefined()
  expect(harness.requests.some((entry) => entry.method === 'POST' && entry.path === '/api/places/quick-check')).toBeTruthy()
})
