import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

export function EmergencyStop({ send, telemetry }: Props) {
  const active = telemetry?.estop ?? false

  return (
    <div style={{ padding: 16 }}>
      <button
        onClick={() => send({ cmd: 'stop', params: { active: !active } })}
        style={{
          width: '100%',
          padding: '16px',
          fontSize: 20,
          fontWeight: 'bold',
          background: active ? '#ff9f1c' : '#d32f2f',
          color: '#fff',
          border: active ? '1px solid #ffcf7a' : '1px solid transparent',
          borderRadius: 10,
          cursor: 'pointer',
          textTransform: 'uppercase',
          letterSpacing: 2,
          boxShadow: active ? '0 0 0 3px rgba(255, 159, 28, 0.22)' : 'none',
        }}
      >
        {active ? 'Release Stop' : 'STOP'}
      </button>
      <div
        style={{
          marginTop: 10,
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          color: active ? '#ffcf7a' : '#7f88b8',
        }}
      >
        {active ? 'E-STOP latched: drive is locked until released' : 'Ready: press once to latch emergency stop'}
      </div>
    </div>
  )
}
