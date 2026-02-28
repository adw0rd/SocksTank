import { useState } from 'react'
import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

export function MotorControl({ send, telemetry }: Props) {
  const [speed, setSpeed] = useState(2000)
  const aiMode = telemetry?.mode === 'ai'
  const estop = telemetry?.estop ?? false
  const locked = aiMode || estop

  const move = (left: number, right: number) => {
    if (locked) return
    send({ cmd: 'motor', params: { left, right } })
  }

  const stop = () => move(0, 0)

  const btnStyle = (bg: string): React.CSSProperties => ({
    padding: '14px 0', fontSize: 16, fontWeight: 'bold',
    background: bg, color: '#fff', border: 'none', borderRadius: 6,
    cursor: 'pointer', minWidth: 60,
  })

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          Motor Control
        </div>
        <div style={{ color: estop ? '#ffcf7a' : aiMode ? '#ffb36b' : '#7f88b8', fontSize: 12 }}>
          {estop ? 'Locked by E-STOP' : aiMode ? 'AI owns drive train' : 'Manual drive'}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ color: '#aab1d6', fontSize: 13, minWidth: 90 }}>Speed: {speed}</span>
        <input
          type="range" min={500} max={4095} value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
          style={{ flex: 1 }}
          disabled={locked}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, opacity: locked ? 0.55 : 1 }}>
        <button disabled={locked} style={btnStyle('#32414a')} onClick={() => move(speed, -speed)}>Q / TL</button>
        <button disabled={locked} style={btnStyle('#2d8cff')} onClick={() => move(speed, speed)}>W / FWD</button>
        <button disabled={locked} style={btnStyle('#32414a')} onClick={() => move(-speed, speed)}>E / TR</button>

        <button disabled={locked} style={btnStyle('#3d5361')} onClick={() => move(-speed, speed)}>A / LEFT</button>
        <button disabled={locked} style={btnStyle('#f0622d')} onClick={stop}>S / STOP</button>
        <button disabled={locked} style={btnStyle('#3d5361')} onClick={() => move(speed, -speed)}>D / RIGHT</button>

        <button disabled={locked} style={btnStyle('#32414a')} onClick={() => move(-speed, speed)}>Z / BL</button>
        <button disabled={locked} style={btnStyle('#2d8cff')} onClick={() => move(-speed, -speed)}>X / BWD</button>
        <button disabled={locked} style={btnStyle('#32414a')} onClick={() => move(speed, -speed)}>C / BR</button>
      </div>
    </div>
  )
}
