import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

test('sends motor, mode, and stop commands from UI controls', async ({ page }) => {
  const harness = await setupMockApp(page, {
    telemetry: {
      mode: 'manual',
      estop: false,
    },
  })
  await page.goto('/')

  const fwd = page.getByRole('button', { name: 'W / FWD' })
  await fwd.dispatchEvent('mousedown')
  await fwd.dispatchEvent('mouseup')

  await page.keyboard.down('w')
  await page.keyboard.down('a')
  await page.keyboard.up('a')
  await page.keyboard.up('w')

  await page.getByRole('button', { name: 'AI Hunt' }).click()
  await page.getByRole('button', { name: 'STOP' }).click()

  const ws = await harness.wsMessages()
  expect(ws.some((item) => item.cmd === 'motor' && Number(item.params.left) > 0 && Number(item.params.right) > 0)).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'motor' && item.params.left === 0 && item.params.right === 0)).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'mode' && item.params.mode === 'ai')).toBeTruthy()
  expect(ws.some((item) => item.cmd === 'stop' && item.params.active === true)).toBeTruthy()
})

test('locks manual motor controls when AI mode is active', async ({ page }) => {
  const harness = await setupMockApp(page, {
    telemetry: {
      mode: 'ai',
      estop: false,
    },
  })
  await page.goto('/')

  const fwd = page.getByRole('button', { name: 'W / FWD' })
  await expect(fwd).toBeDisabled()
  await expect(page.getByText('AI owns drive train')).toBeVisible()

  const ws = await harness.wsMessages()
  expect(ws.some((item) => item.cmd === 'motor')).toBeFalsy()
})
