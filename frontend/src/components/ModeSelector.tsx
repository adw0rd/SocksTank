import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

const MODES = [
  { value: 'manual', label: 'Manual', accent: '#2d8cff' },
  { value: 'ai', label: 'AI Hunt', accent: '#ff7a18' },
  { value: 'ultrasonic', label: 'Ultrasonic', accent: '#26a69a' },
  { value: 'infrared', label: 'Infrared', accent: '#7e57c2' },
]

export function ModeSelector({ send, telemetry }: Props) {
  const current = telemetry?.mode ?? 'manual'
  const aiState = telemetry?.ai_state ?? 'idle'

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          Mode
        </div>
        <div style={{ color: current === 'ai' ? '#ffb36b' : '#7f88b8', fontSize: 12 }}>
          {current === 'ai' ? `AI: ${aiState}` : 'Operator control'}
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {MODES.map((mode) => (
          <button
            key={mode.value}
            data-testid={`mode-btn-${mode.value}`}
            onClick={() => send({ cmd: 'mode', params: { mode: mode.value } })}
            style={{
              padding: '12px 10px',
              fontSize: 13,
              fontWeight: 700,
              background: mode.value === current ? mode.accent : '#242b45',
              color: '#fff',
              border: mode.value === current ? '1px solid transparent' : '1px solid #343d62',
              borderRadius: 10,
              cursor: 'pointer',
            }}
          >
            {mode.label}
          </button>
        ))}
      </div>
      <div style={{ marginTop: 10, color: '#7f88b8', fontSize: 12, lineHeight: 1.5 }}>
        AI mode searches for a sock, aligns, approaches, grabs it, then backs off and drops the payload.
      </div>
    </div>
  )
}
