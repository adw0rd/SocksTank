import type { Telemetry } from '../lib/types'

interface Props {
  telemetry: Telemetry | null
  wsStatus: string
}

export function StatusBar({ telemetry, wsStatus }: Props) {
  const wsColor = wsStatus === 'connected' ? '#4caf50' : wsStatus === 'connecting' ? '#ff9800' : '#f44336'
  const items = [
    { label: 'WS', value: wsStatus, tone: wsColor },
    { label: 'E-Stop', value: telemetry?.estop ? 'Latched' : 'Ready', tone: telemetry?.estop ? '#ff9f1c' : '#89d185' },
    { label: 'Camera', value: telemetry?.camera_source ?? '—' },
    { label: 'FPS', value: telemetry ? telemetry.fps.toFixed(1) : '—' },
    { label: 'Mode', value: telemetry?.mode ?? '—' },
    { label: 'AI', value: telemetry?.ai_state ?? 'idle' },
    { label: 'Backend', value: telemetry?.inference_backend ?? '—' },
    { label: 'Latency', value: telemetry ? `${telemetry.inference_ms.toFixed(0)} ms` : '—' },
    { label: 'Detections', value: String(telemetry?.detections.length ?? 0) },
  ]

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
      gap: 10,
      padding: '12px 14px',
      fontSize: 13,
    }}>
      {items.map((item) => (
        <div
          key={item.label}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 12px',
            background: '#101426',
            border: '1px solid #232842',
            borderRadius: 10,
            minWidth: 0,
          }}
        >
          <div style={{ color: '#6e78a8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {item.label}
          </div>
          <div
            style={{
              color: item.tone ?? '#e7ebff',
              fontWeight: 700,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {item.label === 'WS' && (
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: wsColor,
                  display: 'inline-block',
                  marginRight: 6,
                }}
              />
            )}
            {item.value}
          </div>
        </div>
      ))}
    </div>
  )
}
