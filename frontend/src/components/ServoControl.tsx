import { useEffect, useState } from 'react'
import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

const SERVOS = [
  { channel: 0, label: 'Claw (grip)', min: 90, max: 150, init: 90 },
  { channel: 1, label: 'Claw (lift)', min: 80, max: 120, init: 105 },
  { channel: 2, label: 'Aux Servo (CH2)', min: 0, max: 180, init: 90 },
]

export function ServoControl({ send, telemetry }: Props) {
  const [angles, setAngles] = useState(() =>
    Object.fromEntries(SERVOS.map((s) => [s.channel, s.init]))
  )
  const [clawEnabled, setClawEnabled] = useState(true)
  const [auxExpanded, setAuxExpanded] = useState(() => {
    if (typeof window === 'undefined') {
      return false
    }
    return window.localStorage.getItem('sockstank.servo.auxExpanded') === 'true'
  })

  useEffect(() => {
    setClawEnabled(telemetry?.claw_servos_enabled ?? true)
  }, [telemetry])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    window.localStorage.setItem('sockstank.servo.auxExpanded', String(auxExpanded))
  }, [auxExpanded])

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

  const renderServoSlider = (channel: number) => {
    const servo = SERVOS.find((item) => item.channel === channel)
    if (!servo) {
      return null
    }
    return (
      <div key={servo.channel} style={{ background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aab1d6', fontSize: 13, marginBottom: 6 }}>
          <span>{servo.label}</span>
          <span style={{ fontWeight: 700 }}>{angles[servo.channel]}°</span>
        </div>
        <input
          type="range"
          min={servo.min}
          max={servo.max}
          value={angles[servo.channel]}
          onChange={(e) => setAngle(servo.channel, Number(e.target.value))}
          style={{ width: '100%' }}
        />
      </div>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        Servo Control
      </div>

      <div style={{ marginBottom: 12, background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
          <div>
            <div style={{ color: '#aab1d6', fontSize: 13, marginBottom: 4 }}>Claw Servos</div>
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
        {clawEnabled && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
            {renderServoSlider(0)}
            {renderServoSlider(1)}
          </div>
        )}
      </div>

      <div style={{ background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '10px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
          <div>
            <div style={{ color: '#aab1d6', fontSize: 13, marginBottom: 4 }}>Aux Servo</div>
            <div style={{ color: '#9aa5d8', fontSize: 12, fontWeight: 700 }}>
              {auxExpanded ? 'Expanded' : 'Collapsed'}
            </div>
          </div>
          <button
            onClick={() => setAuxExpanded((prev) => !prev)}
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
            {auxExpanded ? 'Hide' : 'Show'}
          </button>
        </div>
        {auxExpanded && (
          <>
            <div style={{ color: '#8b93bb', fontSize: 11, lineHeight: 1.4, marginTop: 8 }}>
              On some builds this servo is used for camera rotation. On fixed-camera builds it may control another auxiliary mount instead.
            </div>
            <div style={{ marginTop: 10 }}>{renderServoSlider(2)}</div>
          </>
        )}
      </div>
    </div>
  )
}
