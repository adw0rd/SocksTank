import { expect, test } from '@playwright/test'
import { setupMockApp } from './support/mockApp'

test('renders empty state for places and supports empty gpu list', async ({ page }) => {
  await setupMockApp(page)

  await page.route('**/api/places', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ active_target_place_id: null, items: [] }),
      })
    }
    return route.fallback()
  })
  await page.route('**/api/gpu/servers', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ servers: [] }),
      })
    }
    return route.fallback()
  })

  await page.goto('/')

  await expect(page.getByText('No places yet')).toBeVisible()
  await expect(page.getByTestId('gpu-server-add')).toBeVisible()
})

test('shows error when creating place fails', async ({ page }) => {
  await setupMockApp(page)

  await page.route('**/api/places', async (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Place creation failed in backend' }),
      })
    }
    return route.fallback()
  })

  await page.goto('/')
  await page.getByTestId('places-new-name').fill('Broken Place')
  await page.getByTestId('places-add').click()
  await expect(page.getByText('Place creation failed in backend')).toBeVisible()
})

test('shows explicit errors for quick-check and training failures', async ({ page }) => {
  await setupMockApp(page)

  await page.route('**/api/places/quick-check', async (route) => {
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Quick check crashed' }),
    })
  })
  await page.route('**/api/places/*/train', async (route) => {
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Training start failed' }),
    })
  })

  await page.goto('/')
  await page.getByTestId('places-quick-check-run').click()
  await expect(page.getByText('Quick check crashed')).toBeVisible()

  await page.getByTestId('places-train').click()
  await expect(page.getByText('Training start failed')).toBeVisible()
})
