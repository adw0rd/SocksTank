import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

test('manages inference mode and remote gpu servers', async ({ page }) => {
  const harness = await setupMockApp(page, {
    telemetry: {
      inference_mode: 'auto',
      inference_backend: 'remote:blackops:8090',
      inference_ms: 64,
    },
  })
  await page.goto('/')

  await expect(page.getByText('Backend').first()).toBeVisible()
  await expect(page.getByText('Remote: blackops').first()).toBeVisible()
  await expect(page.getByText('64 ms').first()).toBeVisible()

  await page.getByRole('button', { name: 'Remote' }).click()
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByRole('button', { name: 'Stop' })).toBeVisible()

  await page.getByRole('button', { name: '+ Add GPU Server' }).click()
  const modal = page.getByText('Add GPU Server').locator('..')
  const modalInputs = modal.locator('input')
  await modalInputs.nth(0).fill('Lab GPU')
  await modalInputs.nth(1).fill('labgpu')
  await modalInputs.nth(2).fill('8090')
  await modalInputs.nth(3).fill('zeus')
  await modal.getByRole('button', { name: 'Save', exact: true }).click()

  await expect(page.getByText('Lab GPU')).toBeVisible()

  const requests = harness.requests
  expect(requests.some((entry) => entry.method === 'PUT' && entry.path === '/api/inference/mode')).toBeTruthy()
  expect(requests.some((entry) => entry.method === 'POST' && entry.path === '/api/gpu/servers/blackops/start')).toBeTruthy()
  expect(requests.some((entry) => entry.method === 'POST' && entry.path === '/api/gpu/servers')).toBeTruthy()
})
