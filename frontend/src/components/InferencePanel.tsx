import { useState, useEffect, useCallback } from 'react'
import type { Telemetry, GPUServer } from '../lib/types'
import { AddGpuServerModal } from './AddGpuServerModal'

interface Props {
  telemetry: Telemetry | null
}

const MODES = ['auto', 'local', 'remote'] as const

export function InferencePanel({ telemetry }: Props) {
  const [servers, setServers] = useState<GPUServer[]>([])
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const currentMode = telemetry?.inference_mode ?? 'auto'
  const backend = telemetry?.inference_backend ?? 'local'
  const inferenceMs = telemetry?.inference_ms ?? 0
  const inferenceError = telemetry?.inference_error ?? null

  const fetchServers = useCallback(() => {
    fetch('/api/gpu/servers')
      .then((r) => r.json())
      .then((data) => setServers(data.servers ?? []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchServers()
    const interval = setInterval(fetchServers, 5000)
    return () => clearInterval(interval)
  }, [fetchServers])

  const setMode = (mode: string) => {
    fetch('/api/inference/mode', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    }).catch(() => {})
  }

  const startServer = (host: string) => {
    setLoading((prev) => ({ ...prev, [host]: true }))
    fetch(`/api/gpu/servers/${host}/start`, { method: 'POST' })
      .then(() => setTimeout(fetchServers, 2000))
      .catch(() => {})
      .finally(() => setLoading((prev) => ({ ...prev, [host]: false })))
  }

  const stopServer = (host: string) => {
    fetch(`/api/gpu/servers/${host}/stop`, { method: 'POST' })
      .then(() => setTimeout(fetchServers, 1000))
      .catch(() => {})
  }

  const removeServer = (host: string) => {
    fetch(`/api/gpu/servers/${host}`, { method: 'DELETE' })
      .then(() => fetchServers())
      .catch(() => {})
  }

  const statusColor = (status: string) => {
    if (status === 'online') return '#4caf50'
    if (status === 'starting') return '#ff9800'
    return '#666'
  }

  return (
    <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 16 }}>
      <div style={{ color: '#ccc', fontSize: 14, marginBottom: 8 }}>Inference</div>

      {/* Режим инференса */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        {MODES.map((mode) => (
          <button
            key={mode}
            onClick={() => setMode(mode)}
            style={{
              flex: 1, padding: '8px', fontSize: 13,
              background: mode === currentMode ? '#1976d2' : '#37474f',
              color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {mode}
          </button>
        ))}
      </div>

      {/* Статус */}
      <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
        <span>Backend: <strong style={{ color: '#ccc' }}>{backend}</strong></span>
        {inferenceMs > 0 && <span> | {inferenceMs.toFixed(0)} ms</span>}
      </div>
      {inferenceError && (
        <div style={{ fontSize: 11, color: '#ef5350', marginBottom: 8 }}>{inferenceError}</div>
      )}

      {/* Список GPU-серверов */}
      {servers.map((s) => (
        <div
          key={s.host}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 0', borderTop: '1px solid #252545',
          }}
        >
          <span
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: statusColor(s.status), flexShrink: 0,
            }}
          />
          <span style={{ flex: 1, fontSize: 12, color: '#ccc' }}>
            {s.host}:{s.port}
            {s.gpu && <span style={{ color: '#666' }}> ({s.gpu})</span>}
          </span>
          {s.status === 'online' ? (
            <button onClick={() => stopServer(s.host)} style={btnSmall}>Stop</button>
          ) : (
            <button
              onClick={() => startServer(s.host)}
              disabled={loading[s.host]}
              style={{ ...btnSmall, opacity: loading[s.host] ? 0.5 : 1 }}
            >
              {loading[s.host] ? '...' : 'Start'}
            </button>
          )}
          <button onClick={() => removeServer(s.host)} style={{ ...btnSmall, color: '#ef5350' }}>
            ×
          </button>
        </div>
      ))}

      {/* Кнопка "Добавить" */}
      <button
        onClick={() => setShowModal(true)}
        style={{
          marginTop: 8, padding: '6px 12px', fontSize: 12,
          background: '#37474f', color: '#ccc', border: 'none',
          borderRadius: 6, cursor: 'pointer', width: '100%',
        }}
      >
        + Add GPU Server
      </button>

      {showModal && (
        <AddGpuServerModal
          onClose={() => setShowModal(false)}
          onAdded={() => { setShowModal(false); fetchServers() }}
        />
      )}
    </div>
  )
}

const btnSmall: React.CSSProperties = {
  padding: '3px 8px', fontSize: 11, background: '#37474f',
  color: '#ccc', border: 'none', borderRadius: 4, cursor: 'pointer',
}
