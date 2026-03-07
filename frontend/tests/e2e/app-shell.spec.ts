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
  await expect(page.getByTestId('header-camera-chip')).toContainText('Camera: Mock Loop')
  await expect(page.getByTestId('header-inference-chip')).toContainText('REMOTE · Remote blackops:8090')
  await expect(page.getByTestId('header-estop-chip')).toContainText('E-Stop Latched')

  await expect(page.getByTestId('panel-sensors').getByText('Sensors', { exact: true })).toBeVisible()
  await expect(page.getByText('CPU Temp')).toBeVisible()
  await expect(page.getByText('Distance')).toBeVisible()

  await expect(page.getByTestId('panel-status').getByText('WS')).toBeVisible()
  await expect(page.getByText('Detections')).toBeVisible()

  await expect(page.getByTestId('video-fullscreen-toggle')).toBeVisible()
  await expect(page.getByTestId('video-stream')).toBeVisible()
})
