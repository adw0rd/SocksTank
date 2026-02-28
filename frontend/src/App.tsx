import { useWebSocket } from './hooks/useWebSocket'
import { VideoFeed } from './components/VideoFeed'
import { StatusBar } from './components/StatusBar'
import { EmergencyStop } from './components/EmergencyStop'
import { MotorControl } from './components/MotorControl'
import { ServoControl } from './components/ServoControl'
import { LedControl } from './components/LedControl'
import { ModeSelector } from './components/ModeSelector'
import { SensorDisplay } from './components/SensorDisplay'
import { ConfigPanel } from './components/ConfigPanel'
import { InferencePanel } from './components/InferencePanel'

function formatInferenceHeader(telemetry: ReturnType<typeof useWebSocket>['telemetry']) {
  const mode = telemetry?.inference_mode ?? 'auto'
  const backend = telemetry?.inference_backend ?? 'local'

  let backendLabel = 'Local'
  if (backend === 'local:ncnn-native') {
    backendLabel = 'Local NCNN'
  } else if (backend === 'local') {
    backendLabel = 'Local YOLO'
  } else if (backend.startsWith('remote:')) {
    backendLabel = `Remote ${backend.slice('remote:'.length)}`
  }

  return `${mode.toUpperCase()} · ${backendLabel}`
}

function formatCameraHeader(cameraSource: string | undefined) {
  if (!cameraSource || cameraSource === 'camera') {
    return 'Live'
  }
  return cameraSource
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export default function App() {
  const { telemetry, status, send } = useWebSocket()
  const inferenceHeader = formatInferenceHeader(telemetry)
  const cameraHeader = formatCameraHeader(telemetry?.camera_source)
  const panelStyle = {
    background: '#15192d',
    border: '1px solid #232842',
    borderRadius: 14,
    boxShadow: '0 14px 32px rgba(0, 0, 0, 0.18)',
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(circle at top left, #1b2342 0%, #0b0f1a 46%, #070a12 100%)',
      color: '#fff',
      fontFamily: '"Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
    }}>
      <header
        style={{
          padding: '16px 18px',
          borderBottom: '1px solid #1a1f33',
          background: 'rgba(7, 10, 18, 0.72)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>SocksTank Control Surface</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 999,
              border: telemetry?.camera_source && telemetry.camera_source !== 'camera' ? '1px solid #ffcf7a' : '1px solid #2c3558',
              background: telemetry?.camera_source && telemetry.camera_source !== 'camera' ? 'rgba(255, 159, 28, 0.12)' : 'rgba(24, 30, 50, 0.88)',
              color: telemetry?.camera_source && telemetry.camera_source !== 'camera' ? '#ffcf7a' : '#9aa5d8',
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
            }}
          >
            Camera: {cameraHeader}
          </div>
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 999,
              border: telemetry?.inference_backend?.startsWith('remote:') ? '1px solid #7bc6ff' : '1px solid #2c3558',
              background: telemetry?.inference_backend?.startsWith('remote:') ? 'rgba(45, 140, 255, 0.14)' : 'rgba(24, 30, 50, 0.88)',
              color: telemetry?.inference_backend?.startsWith('remote:') ? '#a9ddff' : '#9aa5d8',
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              maxWidth: 280,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={inferenceHeader}
          >
            {inferenceHeader}
          </div>
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 999,
              border: telemetry?.estop ? '1px solid #ffcf7a' : '1px solid #2c3558',
              background: telemetry?.estop ? 'rgba(255, 159, 28, 0.14)' : 'rgba(24, 30, 50, 0.88)',
              color: telemetry?.estop ? '#ffcf7a' : '#9aa5d8',
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
            }}
          >
            {telemetry?.estop ? 'E-Stop Latched' : 'Drive Ready'}
          </div>
        </div>
      </header>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '300px minmax(0, 1fr) 320px',
        gap: 16,
        padding: 16,
        maxWidth: 1560,
        margin: '0 auto',
      }}>
        {/* Left sidebar: direct controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={panelStyle}>
            <MotorControl send={send} telemetry={telemetry} />
          </div>
          <div style={panelStyle}>
            <ServoControl send={send} />
          </div>
          <div style={panelStyle}>
            <LedControl send={send} />
          </div>
        </div>

        {/* Center column: video and live state */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={panelStyle}>
            <VideoFeed />
          </div>
          <div style={panelStyle}>
            <StatusBar telemetry={telemetry} wsStatus={status} />
          </div>
          <div style={panelStyle}>
            <SensorDisplay telemetry={telemetry} />
          </div>
        </div>

        {/* Right sidebar: system and inference */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={panelStyle}>
            <EmergencyStop send={send} telemetry={telemetry} />
          </div>
          <div style={panelStyle}>
            <ModeSelector send={send} telemetry={telemetry} />
          </div>
          <div style={panelStyle}>
            <InferencePanel telemetry={telemetry} />
          </div>
          <div style={panelStyle}>
            <ConfigPanel telemetry={telemetry} />
          </div>
        </div>
      </div>
    </div>
  )
}
