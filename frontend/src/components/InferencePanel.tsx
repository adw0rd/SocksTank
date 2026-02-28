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
  const [editingServer, setEditingServer] = useState<GPUServer | null>(null)
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const currentMode = telemetry?.inference_mode ?? 'auto'
  const backend = telemetry?.inference_backend ?? 'local'
  const inferenceMs = telemetry?.inference_ms ?? 0
  const inferenceError = telemetry?.inference_error ?? null
  const backendLabel = formatBackendLabel(backend, servers)

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

  const openAdd = () => {
    setEditingServer(null)
    setShowModal(true)
  }

  const openEdit = (server: GPUServer) => {
    setEditingServer(server)
    setShowModal(true)
  }

  const statusColor = (status: string) => {
    if (status === 'online') return '#4caf50'
    if (status === 'starting') return '#ff9800'
    return '#666'
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        Inference
      </div>

      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        {MODES.map((mode) => (
          <button
            key={mode}
            onClick={() => setMode(mode)}
            style={{
              flex: 1, padding: '10px 8px', fontSize: 13,
              background: mode === currentMode ? '#2d8cff' : '#242b45',
              color: '#fff', border: mode === currentMode ? '1px solid transparent' : '1px solid #343d62', borderRadius: 10, cursor: 'pointer',
              textTransform: 'capitalize',
              fontWeight: 700,
            }}
          >
            {mode}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
        <div style={statCard}>
          <div style={statLabel}>Backend</div>
          <div style={statValue}>{backendLabel}</div>
        </div>
        <div style={statCard}>
          <div style={statLabel}>Latency</div>
          <div style={statValue}>{inferenceMs > 0 ? `${inferenceMs.toFixed(0)} ms` : 'Idle'}</div>
        </div>
      </div>
      {inferenceError && (
        <div style={{ fontSize: 11, color: '#ef5350', marginBottom: 8, lineHeight: 1.4 }}>{inferenceError}</div>
      )}

      {servers.map((s) => (
        <div
          key={s.host}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 0', borderTop: '1px solid #252545',
          }}
        >
          <span
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: statusColor(s.status), flexShrink: 0,
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, color: '#eef2ff', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {s.name || s.host}
            </div>
            <div style={{ fontSize: 11, color: '#8b93bb', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {s.host}:{s.port}
              {s.gpu && <span style={{ color: '#666' }}> • {s.gpu}</span>}
            </div>
          </div>
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
          <button onClick={() => openEdit(s)} style={btnSmall}>Edit</button>
          <button onClick={() => removeServer(s.host)} style={{ ...btnSmall, color: '#ef5350' }}>
            ×
          </button>
        </div>
      ))}

      <button
        onClick={openAdd}
        style={{
          marginTop: 8, padding: '8px 12px', fontSize: 12,
          background: '#242b45', color: '#d7defe', border: '1px solid #343d62',
          borderRadius: 8, cursor: 'pointer', width: '100%', fontWeight: 700,
        }}
      >
        + Add GPU Server
      </button>

      {showModal && (
        <AddGpuServerModal
          onClose={() => setShowModal(false)}
          onSaved={() => { setShowModal(false); setEditingServer(null); fetchServers() }}
          server={editingServer}
        />
      )}
    </div>
  )
}

function formatBackendLabel(backend: string, servers: GPUServer[]) {
  if (!backend) return 'Idle'
  if (backend === 'local') return 'Local YOLO'
  if (backend === 'local:ncnn-native') return 'Local NCNN'
  if (backend.startsWith('remote:')) {
    const remoteTarget = backend.slice('remote:'.length)
    const [host] = remoteTarget.split(':')
    const match = servers.find((server) => server.host === host)
    if (match?.name) {
      return `Remote: ${match.name}`
    }
    return `Remote: ${remoteTarget}`
  }
  return backend
}

const btnSmall: React.CSSProperties = {
  padding: '4px 8px', fontSize: 11, background: '#2a324f',
  color: '#d7defe', border: '1px solid #343d62', borderRadius: 6, cursor: 'pointer',
}

const statCard: React.CSSProperties = {
  background: '#101426',
  border: '1px solid #232842',
  borderRadius: 10,
  padding: '8px 10px',
}

const statLabel: React.CSSProperties = {
  color: '#6e78a8',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
}

const statValue: React.CSSProperties = {
  color: '#eef2ff',
  fontSize: 12,
  fontWeight: 700,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
}
