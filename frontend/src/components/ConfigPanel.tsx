import { useState, useEffect } from 'react'
import type { Config } from '../lib/types'

export function ConfigPanel() {
  const [config, setConfig] = useState<Config | null>(null)
  const [confidence, setConfidence] = useState(0.5)

  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((data: Config) => {
        setConfig(data)
        setConfidence(data.confidence)
      })
      .catch(() => {})
  }, [])

  const save = () => {
    fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confidence }),
    })
      .then((r) => r.json())
      .then((data: Config) => setConfig(data))
      .catch(() => {})
  }

  return (
    <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 16 }}>
      <div style={{ color: '#ccc', fontSize: 14, marginBottom: 8 }}>Config</div>

      {config && (
        <div style={{ color: '#666', fontSize: 12, marginBottom: 8 }}>
          Model: {config.model_path} | {config.resolution_w}x{config.resolution_h} | {config.mock ? 'MOCK' : 'LIVE'}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ color: '#999', fontSize: 13 }}>Confidence: {confidence.toFixed(2)}</span>
        <input
          type="range" min={0.1} max={1} step={0.05} value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          style={{ flex: 1 }}
        />
        <button
          onClick={save}
          style={{
            padding: '6px 12px', background: '#1976d2', color: '#fff',
            border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13,
          }}
        >
          Save
        </button>
      </div>
    </div>
  )
}
