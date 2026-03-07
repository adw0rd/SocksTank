import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

test('toggles claw servo power and auxiliary servo panel', async ({ page }) => {
  const harness = await setupMockApp(page, {
    telemetry: {
      claw_servos_enabled: true,
      led_supported: true,
    },
  })
  await page.goto('/')

  await page.getByTestId('servo-claw-toggle').click()
  await expect(page.getByText('Disabled')).toBeVisible()
  await page.getByTestId('servo-claw-toggle').click()
  await expect(page.getByText('Enabled')).toBeVisible()

  await page.getByTestId('servo-aux-toggle').click()
  await expect(page.getByText('On some builds this servo is used for camera rotation.')).toBeVisible()

  const ws = await harness.wsMessages()
  expect(ws.some((item) => item.cmd === 'servo_power' && item.params.enabled === false)).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'servo_power' && item.params.enabled === true)).toBeTruthy()
})

test('applies led color and preset effects', async ({ page }) => {
  const harness = await setupMockApp(page, {
    telemetry: {
      led_supported: true,
    },
  })
  await page.goto('/')

  const colorPicker = page.getByTestId('led-color-input')
  await colorPicker.fill('#ff0000')
  await page.getByTestId('led-apply-color').click()
  await page.getByTestId('led-preset-rainbow').click()
  await page.getByTestId('led-preset-breathing').click()

  const ws = await harness.wsMessages()
  expect(ws.some((item) => item.cmd === 'led' && item.params.r === 255 && item.params.g === 0 && item.params.b === 0)).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'led' && item.params.effect === 'rainbow')).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'led' && item.params.effect === 'breathing')).toBeTruthy()
})
