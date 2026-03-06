import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

test('renders main control surface and live status blocks', async ({ page }) => {
  await setupMockApp(page, {
    telemetry: {
      camera_source: 'mock loop',
      inference_mode: 'remote',
      inference_backend: 'remote:blackops:8090',
      mode: 'manual',
      estop: true,
      ai_state: 'tracking_target',
      detections: [{ class: 'sock', confidence: 0.91, bbox: [0.2, 0.2, 0.5, 0.5] }],
      distance_cm: 18,
      cpu_temp: 69.7,
      inference_ms: 83,
    },
  })

  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'SocksTank Control Surface' })).toBeVisible()
  await expect(page.getByText('Camera: Mock Loop')).toBeVisible()
  await expect(page.getByText('REMOTE · Remote blackops:8090')).toBeVisible()
  await expect(page.getByText('E-Stop Latched').first()).toBeVisible()

  await expect(page.getByText('Sensors', { exact: true })).toBeVisible()
  await expect(page.getByText('CPU Temp')).toBeVisible()
  await expect(page.getByText('Distance')).toBeVisible()

  await expect(page.getByText('WS')).toBeVisible()
  await expect(page.getByText('Detections')).toBeVisible()

  await expect(page.getByRole('button', { name: 'Fullscreen' })).toBeVisible()
  await expect(page.getByRole('img', { name: 'Camera' })).toBeVisible()
})
