import { useState } from 'react'
import type { WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
}

const PRESETS = [
  { label: 'Off', effect: 'off' },
  { label: 'Rainbow', effect: 'rainbow' },
  { label: 'Breathing', effect: 'breathing' },
]

export function LedControl({ send }: Props) {
  const [color, setColor] = useState('#0064ff')

  const applyColor = () => {
    const r = parseInt(color.slice(1, 3), 16)
    const g = parseInt(color.slice(3, 5), 16)
    const b = parseInt(color.slice(5, 7), 16)
    send({ cmd: 'led', params: { r, g, b } })
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        LED Control
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          type="color" value={color}
          onChange={(e) => setColor(e.target.value)}
          style={{ width: 48, height: 36, border: 'none', cursor: 'pointer' }}
        />
        <button
          onClick={applyColor}
          style={{
            flex: 1, padding: '8px', background: '#2d8cff', color: '#fff',
            border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 700,
          }}
        >
          Apply Color
        </button>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        {PRESETS.map((p) => (
          <button
            key={p.effect}
            onClick={() => send({ cmd: 'led', params: { effect: p.effect } })}
            style={{
              flex: 1, padding: '8px', background: '#242b45', color: '#fff',
              border: '1px solid #343d62', borderRadius: 8, cursor: 'pointer', fontSize: 13,
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}
