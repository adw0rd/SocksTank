import { useState } from 'react'

interface Props {
  onClose: () => void
  onAdded: () => void
}

export function AddGpuServerModal({ onClose, onAdded }: Props) {
  const [host, setHost] = useState('')
  const [port, setPort] = useState(8090)
  const [username, setUsername] = useState('')
  const [authType, setAuthType] = useState<'key' | 'password'>('key')
  const [password, setPassword] = useState('')
  const [keyPath, setKeyPath] = useState('~/.ssh/id_rsa')
  const [testResult, setTestResult] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const save = () => {
    setSaving(true)
    fetch('/api/gpu/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host, port, username, auth_type: authType,
        ...(authType === 'password' ? { password } : { key_path: keyPath }),
      }),
    })
      .then((r) => r.json())
      .then(() => onAdded())
      .catch((e) => setTestResult(`Error: ${e}`))
      .finally(() => setSaving(false))
  }

  const test = () => {
    setTestResult('Testing...')
    // Сначала сохраняем, потом тестируем
    fetch('/api/gpu/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host, port, username, auth_type: authType,
        ...(authType === 'password' ? { password } : { key_path: keyPath }),
      }),
    })
      .then(() => fetch(`/api/gpu/servers/${host}/test`, { method: 'POST' }))
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) {
          setTestResult(`OK — GPU: ${data.gpu ?? 'CPU'}, model: ${data.model ?? 'n/a'}`)
        } else {
          setTestResult(`Error: ${data.error}`)
        }
      })
      .catch((e) => setTestResult(`Error: ${e}`))
  }

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        background: '#1a1a2e', borderRadius: 12, padding: 24, width: 360,
        border: '1px solid #252545',
      }}>
        <div style={{ fontSize: 16, color: '#fff', marginBottom: 16 }}>Add GPU Server</div>

        <label style={labelStyle}>Host</label>
        <input
          value={host} onChange={(e) => setHost(e.target.value)}
          placeholder="192.168.0.188"
          style={inputStyle}
        />

        <label style={labelStyle}>Port</label>
        <input
          type="number" value={port} onChange={(e) => setPort(Number(e.target.value))}
          style={inputStyle}
        />

        <label style={labelStyle}>Username</label>
        <input
          value={username} onChange={(e) => setUsername(e.target.value)}
          placeholder="user"
          style={inputStyle}
        />

        <label style={labelStyle}>Auth</label>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          {(['key', 'password'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setAuthType(t)}
              style={{
                flex: 1, padding: '6px', fontSize: 12,
                background: authType === t ? '#1976d2' : '#37474f',
                color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              {t === 'key' ? 'SSH Key' : 'Password'}
            </button>
          ))}
        </div>

        {authType === 'password' ? (
          <>
            <label style={labelStyle}>Password</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
            />
          </>
        ) : (
          <>
            <label style={labelStyle}>Key Path</label>
            <input
              value={keyPath} onChange={(e) => setKeyPath(e.target.value)}
              style={inputStyle}
            />
          </>
        )}

        {testResult && (
          <div style={{
            fontSize: 11, padding: 8, borderRadius: 4, marginBottom: 10,
            background: '#252545',
            color: testResult.startsWith('OK') ? '#4caf50' : testResult === 'Testing...' ? '#ff9800' : '#ef5350',
          }}>
            {testResult}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button onClick={test} disabled={!host || !username} style={{ ...actionBtn, background: '#37474f', flex: 1 }}>
            Test
          </button>
          <button onClick={save} disabled={!host || !username || saving} style={{ ...actionBtn, background: '#1976d2', flex: 1 }}>
            {saving ? '...' : 'Save'}
          </button>
          <button onClick={onClose} style={{ ...actionBtn, background: '#37474f', flex: 0 }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 11, color: '#999', marginBottom: 4 }
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px', marginBottom: 10, fontSize: 13,
  background: '#252545', color: '#fff', border: '1px solid #37474f',
  borderRadius: 6, boxSizing: 'border-box', outline: 'none',
}
const actionBtn: React.CSSProperties = {
  padding: '8px 14px', fontSize: 13, color: '#fff',
  border: 'none', borderRadius: 6, cursor: 'pointer',
}
