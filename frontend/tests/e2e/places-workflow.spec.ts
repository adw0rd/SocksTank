import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

const tinyPngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2nWQ0AAAAASUVORK5CYII='

test('creates place, uploads photos, annotates, quick-checks, and trains', async ({ page }) => {
  const harness = await setupMockApp(page)
  await page.goto('/')

  await page.getByTestId('places-new-name').fill('Base 1')
  await page.getByTestId('places-add').click()
  await expect(page.getByText('Created Base 1')).toBeVisible()

  await page.getByTestId('places-upload-input').setInputFiles([
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

  await page.getByTestId('places-open-library').click()
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
  await page.getByTestId('places-annotator-save').click()
  await expect(page.getByText('Annotation saved')).toBeVisible()

  await page.getByTestId('places-library-close').click()
  await page.getByTestId('places-quick-check-run').click()
  await expect(page.getByText(/Quick check done:/)).toBeVisible()

  await page.getByTestId('places-train').click()
  await expect(page.getByText(/Training job .* started on/)).toBeVisible()
  await expect(page.getByText('Training Job', { exact: true })).toBeVisible()
  await expect(page.getByText('Recent Training Jobs')).toBeVisible()
  await expect(page.getByText(/Used images: train/).first()).toBeVisible()

  const trainRequest = harness.requests.find((entry) => entry.method === 'POST' && entry.path.endsWith('/train'))
  expect(trainRequest).toBeDefined()
  expect(harness.requests.some((entry) => entry.method === 'POST' && entry.path === '/api/places/quick-check')).toBeTruthy()
})
