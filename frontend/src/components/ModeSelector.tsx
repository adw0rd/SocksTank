import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

const MODES = ['manual', 'ultrasonic', 'infrared']

export function ModeSelector({ send, telemetry }: Props) {
  const current = telemetry?.mode ?? 'manual'

  return (
    <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 16 }}>
      <div style={{ color: '#ccc', fontSize: 14, marginBottom: 8 }}>Mode</div>
      <div style={{ display: 'flex', gap: 6 }}>
        {MODES.map((mode) => (
          <button
            key={mode}
            onClick={() => send({ cmd: 'mode', params: { mode } })}
            style={{
              flex: 1, padding: '10px', fontSize: 14,
              background: mode === current ? '#1976d2' : '#37474f',
              color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {mode}
          </button>
        ))}
      </div>
    </div>
  )
}
