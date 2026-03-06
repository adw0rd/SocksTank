import { expect, test } from '@playwright/test'

const placeId = 'place_demo'
const image1Id = 'img_1'
const image2Id = 'img_2'
const tinyPngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2nWQ0AAAAASUVORK5CYII='

test('shows loading overlay while switching annotation image', async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear())

  await page.route('**/api/**', async (route) => {
    const reqUrl = new URL(route.request().url())
    const path = reqUrl.pathname
    if (path === '/api/places') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          active_target_place_id: null,
          items: [
            {
              id: placeId,
              name: 'Washer Base',
              label: 'place_base1',
              status: 'ready',
              model_version: 'v1',
              image_count: 2,
              is_active_target: false,
              created_at: '2026-03-06T00:00:00+00:00',
              updated_at: '2026-03-06T00:00:00+00:00',
            },
          ],
        }),
      })
    }
    if (path === '/api/config') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          model_path: 'models/yolo11_best.pt',
          confidence: 0.5,
          resolution_w: 640,
          resolution_h: 480,
          camera_fps: 10,
          mock: true,
        }),
      })
    }
    if (path === '/api/gpu/servers') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ servers: [] }),
      })
    }

    if (path === `/api/places/${placeId}/images`) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            { id: image1Id, filename: 'image1.jpg', path: '', width: 1, height: 1, annotated: false, created_at: '2026-03-06T00:00:00+00:00' },
            { id: image2Id, filename: 'image2.jpg', path: '', width: 1, height: 1, annotated: false, created_at: '2026-03-06T00:00:00+00:00' },
          ],
        }),
      })
    }

    if (path === `/api/places/${placeId}/annotations`) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      })
    }

    if (path === `/api/places/${placeId}/jobs`) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          auto_accept_enabled: true,
          auto_accept_quick_check_samples: 5,
          auto_accept_place_min_hits: 4,
          auto_accept_sock_min_hits: 4,
        }),
      })
    }

    if (path === `/api/places/${placeId}/images/${image2Id}`) {
      await new Promise((resolve) => setTimeout(resolve, 900))
      return route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(tinyPngBase64, 'base64'),
      })
    }

    if (
      path === `/api/places/${placeId}/images/${image1Id}` ||
      path === `/api/places/${placeId}/images/${image1Id}/thumb` ||
      path === `/api/places/${placeId}/images/${image2Id}/thumb`
    ) {
      return route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(tinyPngBase64, 'base64'),
      })
    }

    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto('/')

  const openLibraryButton = page.getByRole('button', { name: /Open Photo Library/i })
  await expect(openLibraryButton).toBeVisible()
  await openLibraryButton.click()
  await expect(page.getByTestId('places-photo-library-modal')).toBeVisible()

  await expect(page.getByTestId('places-annotator-loading')).toBeHidden()

  await page.getByTestId(`places-thumb-${image1Id}`).click()
  await expect(page.getByTestId('places-annotator-image')).toHaveAttribute('src', new RegExp(`/api/places/${placeId}/images/${image1Id}$`))

  await page.getByTestId(`places-thumb-${image2Id}`).click()
  await expect(page.getByTestId('places-annotator-image')).toHaveAttribute('src', new RegExp(`/api/places/${placeId}/images/${image2Id}$`))
  await expect(page.getByTestId('places-annotator-image')).toHaveCSS('opacity', '0')
  await expect(page.getByTestId('places-annotator-loading')).toBeHidden({ timeout: 5000 })
  await expect(page.getByTestId('places-annotator-image')).toHaveCSS('opacity', '1')
})
