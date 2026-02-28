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

export default function App() {
  const { telemetry, status, send } = useWebSocket()

  return (
    <div style={{
      minHeight: '100vh', background: '#0f0f23', color: '#fff',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      <header style={{ padding: '12px 16px', borderBottom: '1px solid #1a1a2e' }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>SocksTank Control Panel</h1>
      </header>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 360px',
        gap: 16, padding: 16, maxWidth: 1200, margin: '0 auto',
      }}>
        {/* Left column: video and status */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <VideoFeed />
          <StatusBar telemetry={telemetry} wsStatus={status} />
          <SensorDisplay telemetry={telemetry} />
        </div>

        {/* Right column: controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <EmergencyStop send={send} />
          <ModeSelector send={send} telemetry={telemetry} />
          <InferencePanel telemetry={telemetry} />
          <ConfigPanel />
          <MotorControl send={send} />
          <ServoControl send={send} />
          <LedControl send={send} />
        </div>
      </div>
    </div>
  )
}
