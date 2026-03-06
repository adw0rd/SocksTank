import type { Page, Route } from '@playwright/test'

const tinyPngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2nWQ0AAAAASUVORK5CYII='

export interface RequestLog {
  method: string
  path: string
  body: unknown
}

interface MockTelemetry {
  type: 'telemetry'
  distance_cm: number
  ir_sensors: number[]
  fps: number
  detections: Array<{ class: string; confidence: number; bbox: [number, number, number, number] }>
  mode: string
  cpu_temp: number
  inference_mode: string
  inference_backend: string
  inference_ms: number
  inference_error: string | null
  camera_source: string
  ai_state: string
  estop: boolean
  claw_servos_enabled: boolean
  led_supported: boolean
}

interface PlaceSummary {
  id: string
  name: string
  label: string
  status: string
  model_version: string | null
  image_count: number
  is_active_target: boolean
  created_at: string
  updated_at: string
}

interface PlaceImage {
  id: string
  filename: string
  path: string
  width: number
  height: number
  annotated: boolean
  created_at: string
}

interface PlaceAnnotation {
  id: string
  place_image_id: string
  label: string
  x_center: number
  y_center: number
  width: number
  height: number
  created_at: string
  updated_at: string
}

interface PlaceJob {
  id: string
  status: string
  executor: string
  dataset_path?: string
  finished_at?: string
  result_model_version?: string
  result_model_path?: string
  result_ncnn_path?: string
  quick_check?: {
    status: 'ok' | 'failed'
    passes_threshold?: boolean
    place?: { hits: number; total: number }
    sock?: { hits: number; total: number }
  }
  dataset_summary?: {
    place_source_images?: number
    splits?: Record<string, { place_images?: number; base_sock_images?: number; total_images?: number }>
  }
  training_config?: {
    place_train_repeat?: number
    base_train_limit?: number
    base_valid_limit?: number
    base_test_limit?: number
  }
  recommendation?: string
}

export interface MockHarness {
  requests: RequestLog[]
  pushTelemetry: (telemetry: Partial<MockTelemetry>) => Promise<void>
  wsMessages: () => Promise<Array<{ cmd: string; params: Record<string, unknown> }>>
}

interface MockOptions {
  telemetry: Partial<MockTelemetry>
}

function nowIso() {
  return '2026-03-06T00:00:00+00:00'
}

function defaultTelemetry(): MockTelemetry {
  return {
    type: 'telemetry',
    distance_cm: 42,
    ir_sensors: [0, 1, 0],
    fps: 12,
    detections: [],
    mode: 'manual',
    cpu_temp: 56.4,
    inference_mode: 'auto',
    inference_backend: 'local',
    inference_ms: 71,
    inference_error: null,
    camera_source: 'mock loop',
    ai_state: 'idle',
    estop: false,
    claw_servos_enabled: true,
    led_supported: true,
  }
}

function json(route: Route, payload: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  })
}

function parseBody(route: Route): unknown {
  const raw = route.request().postData()
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export async function setupMockApp(page: Page, options?: Partial<MockOptions>): Promise<MockHarness> {
  const telemetry = { ...defaultTelemetry(), ...(options?.telemetry ?? {}) }
  const requests: RequestLog[] = []

  let config = {
    model_path: 'models/yolo11_best.pt',
    confidence: 0.5,
    resolution_w: 640,
    resolution_h: 480,
    camera_fps: 10,
    mock: true,
  }

  let inferenceMode = 'auto'

  let servers = [
    {
      name: 'blackops',
      host: 'blackops',
      port: 8090,
      username: 'zeus',
      auth_type: 'key' as const,
      key_path: '~/.ssh/id_rsa',
      status: 'offline',
      gpu: 'NVIDIA GeForce RTX 4070 SUPER',
    },
  ]

  let placeCounter = 1
  let imageCounter = 1
  let annotationCounter = 1
  let jobCounter = 1
  let activeTargetPlaceId: string | null = null

  const places: PlaceSummary[] = [
    {
      id: 'place_1',
      name: 'Laundry Machine',
      label: 'place_laundry_machine',
      status: 'collecting',
      model_version: null,
      image_count: 1,
      is_active_target: false,
      created_at: nowIso(),
      updated_at: nowIso(),
    },
  ]

  const imagesByPlace = new Map<string, PlaceImage[]>([
    [
      'place_1',
      [
        {
          id: 'img_1',
          filename: 'washer.jpg',
          path: '',
          width: 1280,
          height: 720,
          annotated: false,
          created_at: nowIso(),
        },
      ],
    ],
  ])
  const annotationsByPlace = new Map<string, PlaceAnnotation[]>([['place_1', []]])
  const jobsByPlace = new Map<string, PlaceJob[]>([['place_1', []]])

  await page.addInitScript((initialTelemetry: MockTelemetry) => {
    localStorage.clear()
    const wsMessages: Array<{ cmd: string; params: Record<string, unknown> }> = []
    let latestTelemetry = initialTelemetry

    class MockWebSocket {
      static instances: MockWebSocket[] = []
      static OPEN = 1
      static CLOSED = 3

      readyState = MockWebSocket.OPEN
      onopen: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent<string>) => void) | null = null
      onclose: ((event: CloseEvent) => void) | null = null
      onerror: ((event: Event) => void) | null = null

      constructor() {
        MockWebSocket.instances.push(this)
        setTimeout(() => {
          this.onopen?.(new Event('open'))
          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify(latestTelemetry),
            }),
          )
        }, 0)
      }

      send(data: string) {
        try {
          wsMessages.push(JSON.parse(data))
        } catch {
          // noop
        }
      }

      close() {
        this.readyState = MockWebSocket.CLOSED
        this.onclose?.(new CloseEvent('close'))
      }
    }

    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      writable: true,
      value: MockWebSocket,
    })

    ;(window as typeof window & { __pushTelemetry: (payload: MockTelemetry) => void }).__pushTelemetry = (payload: MockTelemetry) => {
      latestTelemetry = payload
      for (const ws of MockWebSocket.instances) {
        ws.onmessage?.(
          new MessageEvent('message', {
            data: JSON.stringify(payload),
          }),
        )
      }
    }

    ;(window as typeof window & { __getWsMessages: () => Array<{ cmd: string; params: Record<string, unknown> }> }).__getWsMessages = () =>
      wsMessages
  }, telemetry)

  await page.route('**/api/**', async (route) => {
    const method = route.request().method()
    const url = new URL(route.request().url())
    const path = url.pathname
    const body = parseBody(route)
    requests.push({ method, path, body })

    if (path === '/api/config' && method === 'GET') {
      return json(route, config)
    }
    if (path === '/api/config' && method === 'PUT') {
      config = { ...config, ...(typeof body === 'object' && body ? (body as Record<string, unknown>) : {}) }
      return json(route, config)
    }

    if (path === '/api/inference/mode' && method === 'PUT') {
      const next = (body as { mode?: string } | null)?.mode ?? inferenceMode
      inferenceMode = next
      return json(route, { ok: true, mode: inferenceMode })
    }

    if (path === '/api/gpu/servers' && method === 'GET') {
      return json(route, { servers })
    }
    if (path === '/api/gpu/servers' && method === 'POST') {
      const payload = (body as Record<string, unknown>) ?? {}
      servers.push({
        name: (payload.name as string) || '',
        host: (payload.host as string) || 'unknown',
        port: Number(payload.port ?? 8090),
        username: (payload.username as string) || 'user',
        auth_type: (payload.auth_type as 'key' | 'password') || 'key',
        password: payload.password as string | undefined,
        key_path: payload.key_path as string | undefined,
        status: 'offline',
      })
      return json(route, { ok: true })
    }

    const serverPathMatch = path.match(/^\/api\/gpu\/servers\/([^/]+)$/)
    if (serverPathMatch && method === 'PUT') {
      const host = decodeURIComponent(serverPathMatch[1])
      const payload = (body as Record<string, unknown>) ?? {}
      servers = servers.map((server) =>
        server.host === host
          ? {
              ...server,
              ...payload,
              host: server.host,
            }
          : server,
      )
      return json(route, { ok: true })
    }
    if (serverPathMatch && method === 'DELETE') {
      const host = decodeURIComponent(serverPathMatch[1])
      servers = servers.filter((server) => server.host !== host)
      return json(route, { ok: true })
    }

    const serverActionMatch = path.match(/^\/api\/gpu\/servers\/([^/]+)\/(start|stop|test)$/)
    if (serverActionMatch) {
      const host = decodeURIComponent(serverActionMatch[1])
      const action = serverActionMatch[2]
      if (action === 'start') {
        servers = servers.map((server) => (server.host === host ? { ...server, status: 'online' } : server))
        return json(route, { ok: true })
      }
      if (action === 'stop') {
        servers = servers.map((server) => (server.host === host ? { ...server, status: 'offline' } : server))
        return json(route, { ok: true })
      }
      return json(route, { ok: true, gpu: 'NVIDIA GeForce RTX 4070 SUPER', model: 'yolo11_best.pt' })
    }

    if (path === '/api/places' && method === 'GET') {
      const normalizedPlaces = places.map((place) => ({ ...place, is_active_target: place.id === activeTargetPlaceId }))
      return json(route, { active_target_place_id: activeTargetPlaceId, items: normalizedPlaces })
    }
    if (path === '/api/places' && method === 'POST') {
      const payload = (body as { name?: string } | null) ?? {}
      const id = `place_${++placeCounter}`
      const name = payload.name?.trim() || `Place ${placeCounter}`
      const created: PlaceSummary = {
        id,
        name,
        label: `place_${name.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`,
        status: 'collecting',
        model_version: null,
        image_count: 0,
        is_active_target: false,
        created_at: nowIso(),
        updated_at: nowIso(),
      }
      places.unshift(created)
      imagesByPlace.set(id, [])
      annotationsByPlace.set(id, [])
      jobsByPlace.set(id, [])
      return json(route, created, 201)
    }

    if (path === '/api/places/active' && method === 'PUT') {
      const payload = (body as { place_id?: string | null } | null) ?? {}
      activeTargetPlaceId = payload.place_id ?? null
      return json(route, { active_target_place_id: activeTargetPlaceId })
    }

    const placeImagesMatch = path.match(/^\/api\/places\/([^/]+)\/images$/)
    if (placeImagesMatch && method === 'GET') {
      const placeId = decodeURIComponent(placeImagesMatch[1])
      return json(route, { items: imagesByPlace.get(placeId) ?? [] })
    }
    if (placeImagesMatch && method === 'POST') {
      const placeId = decodeURIComponent(placeImagesMatch[1])
      const payload = (body as { items?: Array<{ filename?: string }> } | null) ?? {}
      const list = imagesByPlace.get(placeId) ?? []
      const created = (payload.items ?? []).map((item) => ({
        id: `img_${++imageCounter}`,
        filename: item.filename || `upload_${imageCounter}.jpg`,
        path: '',
        width: 1280,
        height: 720,
        annotated: false,
        created_at: nowIso(),
      }))
      imagesByPlace.set(placeId, [...list, ...created])
      const place = places.find((entry) => entry.id === placeId)
      if (place) {
        place.image_count = (imagesByPlace.get(placeId) ?? []).length
      }
      return json(route, { items: created })
    }

    const placeAnnotationsMatch = path.match(/^\/api\/places\/([^/]+)\/annotations$/)
    if (placeAnnotationsMatch && method === 'GET') {
      const placeId = decodeURIComponent(placeAnnotationsMatch[1])
      return json(route, { items: annotationsByPlace.get(placeId) ?? [] })
    }

    const imageAnnotationMatch = path.match(/^\/api\/places\/([^/]+)\/images\/([^/]+)\/annotation$/)
    if (imageAnnotationMatch && method === 'PUT') {
      const placeId = decodeURIComponent(imageAnnotationMatch[1])
      const imageId = decodeURIComponent(imageAnnotationMatch[2])
      const payload = (body as Partial<PlaceAnnotation>) ?? {}
      const annotation: PlaceAnnotation = {
        id: `ann_${++annotationCounter}`,
        place_image_id: imageId,
        label: 'place',
        x_center: Number(payload.x_center ?? 0.5),
        y_center: Number(payload.y_center ?? 0.5),
        width: Number(payload.width ?? 0.4),
        height: Number(payload.height ?? 0.4),
        created_at: nowIso(),
        updated_at: nowIso(),
      }
      const existing = annotationsByPlace.get(placeId) ?? []
      const filtered = existing.filter((entry) => entry.place_image_id !== imageId)
      annotationsByPlace.set(placeId, [...filtered, annotation])
      const images = imagesByPlace.get(placeId) ?? []
      for (const image of images) {
        if (image.id === imageId) {
          image.annotated = true
        }
      }
      return json(route, annotation)
    }

    const imageMatch = path.match(/^\/api\/places\/([^/]+)\/images\/([^/]+)$/)
    if (imageMatch && method === 'DELETE') {
      const placeId = decodeURIComponent(imageMatch[1])
      const imageId = decodeURIComponent(imageMatch[2])
      const images = (imagesByPlace.get(placeId) ?? []).filter((image) => image.id !== imageId)
      imagesByPlace.set(placeId, images)
      annotationsByPlace.set(
        placeId,
        (annotationsByPlace.get(placeId) ?? []).filter((annotation) => annotation.place_image_id !== imageId),
      )
      const place = places.find((entry) => entry.id === placeId)
      if (place) {
        place.image_count = images.length
      }
      return json(route, { ok: true })
    }
    if (imageMatch && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(tinyPngBase64, 'base64'),
      })
    }

    const thumbMatch = path.match(/^\/api\/places\/([^/]+)\/images\/([^/]+)\/thumb$/)
    if (thumbMatch) {
      return route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(tinyPngBase64, 'base64'),
      })
    }

    const placeJobsMatch = path.match(/^\/api\/places\/([^/]+)\/jobs$/)
    if (placeJobsMatch && method === 'GET') {
      const placeId = decodeURIComponent(placeJobsMatch[1])
      return json(route, {
        items: jobsByPlace.get(placeId) ?? [],
        auto_accept_enabled: true,
        auto_accept_quick_check_samples: 5,
        auto_accept_place_min_hits: 4,
        auto_accept_sock_min_hits: 4,
      })
    }

    const placeTrainMatch = path.match(/^\/api\/places\/([^/]+)\/train$/)
    if (placeTrainMatch && method === 'POST') {
      const placeId = decodeURIComponent(placeTrainMatch[1])
      const jobId = `job_${++jobCounter}`
      const job: PlaceJob = {
        id: jobId,
        status: 'ready',
        executor: 'remote:blackops',
        dataset_path: `/tmp/${placeId}/${jobId}`,
        finished_at: nowIso(),
        result_model_version: `v${jobCounter}`,
        result_model_path: `~/sockstank/models/${placeId}/weights/best.pt`,
        result_ncnn_path: `~/sockstank/models/${placeId}/ncnn`,
        quick_check: {
          status: 'ok',
          passes_threshold: true,
          place: { hits: 5, total: 5 },
          sock: { hits: 5, total: 5 },
        },
        dataset_summary: {
          place_source_images: (imagesByPlace.get(placeId) ?? []).length,
          splits: {
            train: { place_images: 6, base_sock_images: 40, total_images: 46 },
            valid: { place_images: 2, base_sock_images: 10, total_images: 12 },
            test: { place_images: 2, base_sock_images: 10, total_images: 12 },
          },
        },
        training_config: {
          place_train_repeat: 6,
          base_train_limit: 40,
          base_valid_limit: 10,
          base_test_limit: 10,
        },
        recommendation: 'Good fit for current scene. Increase place photos if lighting changes.',
      }
      const nextJobs = [job, ...(jobsByPlace.get(placeId) ?? [])]
      jobsByPlace.set(placeId, nextJobs)
      const place = places.find((entry) => entry.id === placeId)
      if (place) {
        place.status = 'ready'
        place.model_version = job.result_model_version ?? null
      }
      return json(route, {
        job_id: jobId,
        status: 'ready',
        executor: job.executor,
      })
    }

    const jobMatch = path.match(/^\/api\/places\/jobs\/([^/]+)$/)
    if (jobMatch && method === 'GET') {
      const jobId = decodeURIComponent(jobMatch[1])
      for (const jobs of jobsByPlace.values()) {
        const job = jobs.find((entry) => entry.id === jobId)
        if (job) {
          return json(route, job)
        }
      }
      return json(route, { detail: 'Job not found' }, 404)
    }
    if (jobMatch && method === 'DELETE') {
      const jobId = decodeURIComponent(jobMatch[1])
      for (const [placeId, jobs] of jobsByPlace.entries()) {
        jobsByPlace.set(
          placeId,
          jobs.filter((job) => job.id !== jobId),
        )
      }
      return json(route, { ok: true })
    }

    if (path === '/api/places/quick-check' && method === 'POST') {
      return json(route, {
        model_path: '~/sockstank/models/active.pt',
        model_version: 'v-demo',
        place_id: 'place_1',
        place_label: 'place_laundry_machine',
        place: { hits: 5, total: 5 },
        sock: { hits: 5, total: 5 },
        place_images: [],
        sock_images: [],
      })
    }

    return json(route, {})
  })

  return {
    requests,
    pushTelemetry: (nextTelemetry) =>
      page.evaluate((payload) => {
        const api = window as typeof window & { __pushTelemetry: (value: MockTelemetry) => void }
        api.__pushTelemetry(payload as MockTelemetry)
      }, { ...telemetry, ...nextTelemetry }),
    wsMessages: () =>
      page.evaluate(() => {
        const api = window as typeof window & { __getWsMessages: () => Array<{ cmd: string; params: Record<string, unknown> }> }
        return api.__getWsMessages()
      }),
  }
}
