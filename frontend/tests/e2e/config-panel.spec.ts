import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

test('updates confidence in config panel', async ({ page }) => {
  const harness = await setupMockApp(page, {
    telemetry: {
      camera_source: 'mock loop',
      detections: [],
    },
  })
  await page.goto('/')

  const confidenceSlider = page.getByTestId('config-confidence-slider')
  await confidenceSlider.fill('0.65')
  await page.getByTestId('config-save').click()

  const saveRequest = harness.requests.find((entry) => entry.method === 'PUT' && entry.path === '/api/config')
  expect(saveRequest).toBeDefined()
  expect((saveRequest?.body as { confidence?: number }).confidence).toBe(0.65)
  await expect(page.getByText('Confidence: 0.65')).toBeVisible()
})
