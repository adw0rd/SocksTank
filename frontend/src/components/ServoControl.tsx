import { useEffect, useState } from 'react'
import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

const SERVOS = [
  { channel: 0, label: 'Claw (grip)', min: 90, max: 150, init: 90 },
  { channel: 1, label: 'Claw (lift)', min: 80, max: 120, init: 105 },
  { channel: 2, label: 'Camera (pan)', min: 0, max: 180, init: 90 },
]

export function ServoControl({ send, telemetry }: Props) {
  const [angles, setAngles] = useState(() =>
    Object.fromEntries(SERVOS.map((s) => [s.channel, s.init]))
  )
  const [clawEnabled, setClawEnabled] = useState(true)

  useEffect(() => {
    setClawEnabled(telemetry?.claw_servos_enabled ?? true)
  }, [telemetry])

  const setAngle = (channel: number, angle: number) => {
    if (channel !== 2 && !clawEnabled) return
    setAngles((prev) => ({ ...prev, [channel]: angle }))
    send({ cmd: 'servo', params: { channel, angle } })
  }

  const toggleClawPower = () => {
    const next = !clawEnabled
    setClawEnabled(next)
    send({ cmd: 'servo_power', params: { enabled: next } })
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        Servo Control
      </div>

      <div style={{ marginBottom: 12, background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
          <div>
            <div style={{ color: '#aab1d6', fontSize: 13, marginBottom: 4 }}>Claw Servo Power</div>
            <div style={{ color: clawEnabled ? '#7ad38b' : '#ffcf7a', fontSize: 12, fontWeight: 700 }}>
              {clawEnabled ? 'Enabled' : 'Disabled'}
            </div>
          </div>
          <button
            onClick={toggleClawPower}
            style={{
              padding: '9px 12px',
              background: clawEnabled ? '#5a2b2b' : '#1f5c3b',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {clawEnabled ? 'Disable' : 'Enable'}
          </button>
        </div>
      </div>

      {SERVOS.map((s) => (
        <div key={s.channel} style={{ marginBottom: 12, background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '10px 12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aab1d6', fontSize: 13, marginBottom: 6 }}>
            <span>{s.label}</span>
            <span style={{ fontWeight: 700 }}>{angles[s.channel]}°</span>
          </div>
          <input
            type="range" min={s.min} max={s.max} value={angles[s.channel]}
            onChange={(e) => setAngle(s.channel, Number(e.target.value))}
            style={{ width: '100%' }}
            disabled={s.channel !== 2 && !clawEnabled}
          />
        </div>
      ))}
    </div>
  )
}
