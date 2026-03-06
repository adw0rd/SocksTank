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

  await page.getByRole('button', { name: 'Disable' }).click()
  await expect(page.getByText('Disabled')).toBeVisible()
  await page.getByRole('button', { name: 'Enable' }).click()
  await expect(page.getByText('Enabled')).toBeVisible()

  await page.getByRole('button', { name: 'Show' }).nth(0).click()
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

  const colorPicker = page.locator('input[type="color"]')
  await colorPicker.fill('#ff0000')
  await page.getByRole('button', { name: 'Apply Color' }).click()
  await page.getByRole('button', { name: 'Rainbow' }).click()
  await page.getByRole('button', { name: 'Breathing' }).click()

  const ws = await harness.wsMessages()
  expect(ws.some((item) => item.cmd === 'led' && item.params.r === 255 && item.params.g === 0 && item.params.b === 0)).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'led' && item.params.effect === 'rainbow')).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'led' && item.params.effect === 'breathing')).toBeTruthy()
})
