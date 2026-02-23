import type { Telemetry } from '../lib/types'

interface Props {
  telemetry: Telemetry | null
}

export function SensorDisplay({ telemetry }: Props) {
  const dist = telemetry?.distance_cm ?? 0
  const ir = telemetry?.ir_sensors ?? [0, 0, 0]
  const temp = telemetry?.cpu_temp ?? 0

  const distColor = dist < 20 ? '#f44336' : dist < 50 ? '#ff9800' : '#4caf50'
  const tempColor = temp > 80 ? '#f44336' : temp > 65 ? '#ff9800' : '#4caf50'

  return (
    <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 16 }}>
      <div style={{ color: '#ccc', fontSize: 14, marginBottom: 8 }}>Sensors</div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ color: '#999', fontSize: 13 }}>CPU Temp</span>
        <span style={{ color: tempColor, fontSize: 20, fontWeight: 'bold' }}>{temp.toFixed(1)}°C</span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ color: '#999', fontSize: 13 }}>Distance</span>
        <span style={{ color: distColor, fontSize: 20, fontWeight: 'bold' }}>{dist.toFixed(1)} cm</span>
      </div>

      <div>
        <span style={{ color: '#999', fontSize: 13 }}>IR Sensors</span>
        <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
          {['L', 'C', 'R'].map((label, i) => (
            <div key={label} style={{
              flex: 1, textAlign: 'center', padding: '8px',
              background: ir[i] ? '#4caf50' : '#37474f',
              borderRadius: 6, color: '#fff', fontSize: 13,
            }}>
              {label}: {ir[i]}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
