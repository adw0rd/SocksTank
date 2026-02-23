import type { Telemetry } from '../lib/types'

interface Props {
  telemetry: Telemetry | null
  wsStatus: string
}

export function StatusBar({ telemetry, wsStatus }: Props) {
  const wsColor = wsStatus === 'connected' ? '#4caf50' : wsStatus === 'connecting' ? '#ff9800' : '#f44336'

  return (
    <div style={{
      display: 'flex', gap: 16, alignItems: 'center', padding: '8px 16px',
      background: '#1a1a2e', borderRadius: 8, fontSize: 14, color: '#ccc',
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: wsColor, display: 'inline-block' }} />
        WS: {wsStatus}
      </span>
      <span>FPS: {telemetry?.fps.toFixed(1) ?? '—'}</span>
      <span>Mode: {telemetry?.mode ?? '—'}</span>
      <span>Detections: {telemetry?.detections.length ?? 0}</span>
    </div>
  )
}
