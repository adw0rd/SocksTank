import type { WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
}

export function EmergencyStop({ send }: Props) {
  return (
    <button
      onClick={() => send({ cmd: 'stop', params: {} })}
      style={{
        width: '100%', padding: '16px', fontSize: 20, fontWeight: 'bold',
        background: '#d32f2f', color: '#fff', border: 'none', borderRadius: 8,
        cursor: 'pointer', textTransform: 'uppercase', letterSpacing: 2,
      }}
    >
      STOP
    </button>
  )
}
