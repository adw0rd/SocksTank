import { useState } from 'react'
import type { WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
}

const SERVOS = [
  { channel: 0, label: 'Claw (grip)', min: 90, max: 150, init: 90 },
  { channel: 1, label: 'Claw (lift)', min: 90, max: 150, init: 140 },
  { channel: 2, label: 'Camera (pan)', min: 0, max: 180, init: 90 },
]

export function ServoControl({ send }: Props) {
  const [angles, setAngles] = useState(() =>
    Object.fromEntries(SERVOS.map((s) => [s.channel, s.init]))
  )

  const setAngle = (channel: number, angle: number) => {
    setAngles((prev) => ({ ...prev, [channel]: angle }))
    send({ cmd: 'servo', params: { channel, angle } })
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        Servo Control
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
          />
        </div>
      ))}
    </div>
  )
}
