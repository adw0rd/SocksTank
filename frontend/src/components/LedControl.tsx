import { useEffect, useState } from 'react'
import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

const PRESETS = [
  { label: 'Off', effect: 'off' },
  { label: 'Rainbow', effect: 'rainbow' },
  { label: 'Breathing', effect: 'breathing' },
]

export function LedControl({ send, telemetry }: Props) {
  const [color, setColor] = useState('#0064ff')
  const [expanded, setExpanded] = useState(() => {
    if (typeof window === 'undefined') {
      return true
    }
    const saved = window.localStorage.getItem('sockstank.led.expanded')
    if (saved === null) {
      return true
    }
    return saved === 'true'
  })
  const supported = telemetry?.led_supported ?? true

  useEffect(() => {
    if (!supported) {
      setExpanded(false)
    }
  }, [supported])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    window.localStorage.setItem('sockstank.led.expanded', String(expanded))
  }, [expanded])

  const applyColor = () => {
    if (!supported) return
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

      <div style={{ background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
          <div>
            <div style={{ color: '#aab1d6', fontSize: 13, marginBottom: 4 }}>LED State</div>
            <div style={{ color: supported ? '#7ad38b' : '#ffcf7a', fontSize: 12, fontWeight: 700 }}>
              {supported ? (expanded ? 'Expanded' : 'Collapsed') : 'Disabled'}
            </div>
          </div>
          <button
            onClick={() => setExpanded((prev) => !prev)}
            style={{
              padding: '9px 12px',
              background: '#242b45',
              color: '#fff',
              border: '1px solid #343d62',
              borderRadius: 8,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {expanded ? 'Hide' : 'Show'}
          </button>
        </div>

        {expanded && !supported && (
          <div
            style={{
              marginTop: 10,
              marginBottom: 10,
              padding: '9px 10px',
              background: '#1a1420',
              border: '1px solid #43324f',
              borderRadius: 8,
              color: '#ffcf7a',
              fontSize: 12,
              lineHeight: 1.4,
            }}
          >
            LED is not supported on PCB v1 + Raspberry Pi 5. It works on RPi 4, or on PCB v2 via SPI.
          </div>
        )}

        {expanded && (
          <>
            <div style={{ display: 'flex', gap: 8, marginBottom: 10, marginTop: 10 }}>
              <input
                type="color" value={color}
                onChange={(e) => setColor(e.target.value)}
                style={{ width: 48, height: 36, border: 'none', cursor: 'pointer' }}
                disabled={!supported}
              />
              <button
                onClick={applyColor}
                disabled={!supported}
                style={{
                  flex: 1, padding: '8px', background: '#2d8cff', color: '#fff',
                  border: 'none', borderRadius: 8, cursor: supported ? 'pointer' : 'not-allowed', fontWeight: 700,
                  opacity: supported ? 1 : 0.45,
                }}
              >
                Apply Color
              </button>
            </div>

            <div style={{ display: 'flex', gap: 6 }}>
              {PRESETS.map((p) => (
                <button
                  key={p.effect}
                  onClick={() => supported && send({ cmd: 'led', params: { effect: p.effect } })}
                  disabled={!supported}
                  style={{
                    flex: 1, padding: '8px', background: '#242b45', color: '#fff',
                    border: '1px solid #343d62', borderRadius: 8, cursor: supported ? 'pointer' : 'not-allowed', fontSize: 13,
                    opacity: supported ? 1 : 0.45,
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
