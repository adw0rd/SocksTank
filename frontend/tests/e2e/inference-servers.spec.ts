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

  await expect(page.getByTestId('inference-backend-value')).toContainText('Remote: blackops')
  await expect(page.getByTestId('inference-latency-value')).toContainText('64 ms')

  await page.getByTestId('inference-mode-remote').click()
  await page.getByTestId('gpu-server-start-blackops').click()
  await expect(page.getByTestId('gpu-server-stop-blackops')).toBeVisible()

  await page.getByTestId('gpu-server-add').click()
  const modal = page.getByTestId('gpu-modal')
  await modal.getByTestId('gpu-modal-name').fill('Lab GPU')
  await modal.getByTestId('gpu-modal-host').fill('labgpu')
  await modal.getByTestId('gpu-modal-port').fill('8090')
  await modal.getByTestId('gpu-modal-username').fill('zeus')
  await modal.getByTestId('gpu-modal-save').click()

  await expect(page.getByText('Lab GPU')).toBeVisible()

  const requests = harness.requests
  expect(requests.some((entry) => entry.method === 'PUT' && entry.path === '/api/inference/mode')).toBeTruthy()
  expect(requests.some((entry) => entry.method === 'POST' && entry.path === '/api/gpu/servers/blackops/start')).toBeTruthy()
  expect(requests.some((entry) => entry.method === 'POST' && entry.path === '/api/gpu/servers')).toBeTruthy()
})
