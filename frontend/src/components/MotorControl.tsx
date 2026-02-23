import { useState } from 'react'
import type { WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
}

export function MotorControl({ send }: Props) {
  const [speed, setSpeed] = useState(2000)

  const move = (left: number, right: number) => {
    send({ cmd: 'motor', params: { left, right } })
  }

  const stop = () => move(0, 0)

  const btnStyle = (bg: string): React.CSSProperties => ({
    padding: '14px 0', fontSize: 16, fontWeight: 'bold',
    background: bg, color: '#fff', border: 'none', borderRadius: 6,
    cursor: 'pointer', minWidth: 60,
  })

  return (
    <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 16 }}>
      <div style={{ color: '#ccc', fontSize: 14, marginBottom: 8 }}>Motor Control</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ color: '#999', fontSize: 13 }}>Speed: {speed}</span>
        <input
          type="range" min={500} max={4095} value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
          style={{ flex: 1 }}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
        <button style={btnStyle('#455a64')} onClick={() => move(speed, -speed)}>TL</button>
        <button style={btnStyle('#1976d2')} onClick={() => move(speed, speed)}>FWD</button>
        <button style={btnStyle('#455a64')} onClick={() => move(-speed, speed)}>TR</button>

        <button style={btnStyle('#546e7a')} onClick={() => move(-speed, speed)}>LEFT</button>
        <button style={btnStyle('#e65100')} onClick={stop}>STOP</button>
        <button style={btnStyle('#546e7a')} onClick={() => move(speed, -speed)}>RIGHT</button>

        <button style={btnStyle('#455a64')} onClick={() => move(-speed, speed)}>BL</button>
        <button style={btnStyle('#1976d2')} onClick={() => move(-speed, -speed)}>BWD</button>
        <button style={btnStyle('#455a64')} onClick={() => move(speed, -speed)}>BR</button>
      </div>
    </div>
  )
}
