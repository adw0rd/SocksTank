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
    <div style={{ padding: '12px 14px' }}>
      <div style={{ color: '#cbd3ff', fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
        Sensors
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
        <div style={metricCard}>
          <span style={{ color: '#6e78a8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>CPU Temp</span>
          <span style={{ color: tempColor, fontSize: 18, fontWeight: 'bold' }}>{temp.toFixed(1)}°C</span>
        </div>
        <div style={metricCard}>
          <span style={{ color: '#6e78a8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Distance</span>
          <span style={{ color: distColor, fontSize: 18, fontWeight: 'bold' }}>{dist.toFixed(1)} cm</span>
        </div>
      </div>

      <div style={{ background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '8px 10px' }}>
        <span style={{ color: '#6e78a8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>IR Sensors</span>
        <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
          {['L', 'C', 'R'].map((label, i) => (
            <div key={label} style={{
              flex: 1, textAlign: 'center', padding: '6px',
              background: ir[i] ? '#4caf50' : '#242b45',
              borderRadius: 8, color: '#fff', fontSize: 12, fontWeight: 700,
            }}>
              {label}: {ir[i]}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const metricCard: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 3,
  background: '#101426',
  border: '1px solid #232842',
  borderRadius: 10,
  padding: '8px 10px',
}
