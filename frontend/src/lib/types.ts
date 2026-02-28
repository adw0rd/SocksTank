export interface Detection {
  class: string
  confidence: number
  bbox: [number, number, number, number]
}

export interface Telemetry {
  type: 'telemetry'
  distance_cm: number
  ir_sensors: number[]
  fps: number
  detections: Detection[]
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

export interface WsCommand {
  cmd: string
  params: Record<string, unknown>
}

export interface Config {
  model_path: string
  confidence: number
  resolution_w: number
  resolution_h: number
  camera_fps: number
  mock: boolean
}

export interface Status {
  fps: number
  mode: string
  mock: boolean
  detections: number
  motor_left: number
  motor_right: number
  distance_cm: number
  ir_sensors: number[]
}

export interface GPUServer {
  name?: string
  host: string
  port: number
  username: string
  auth_type: 'key' | 'password'
  password?: string
  key_path?: string
  status: string
  gpu?: string
}
