import { useState, useEffect } from 'react'
import type { Config, Telemetry } from '../lib/types'

interface Props {
  telemetry: Telemetry | null
}

export function ConfigPanel({ telemetry }: Props) {
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
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        Config
      </div>

      {config && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
          <InfoChip label='Model' value={config.model_path.split('/').pop() ?? config.model_path} />
          <InfoChip label='Camera' value={telemetry?.camera_source ?? (config.mock ? 'mock' : 'live')} />
          <InfoChip label='Resolution' value={`${config.resolution_w}x${config.resolution_h}`} />
          <InfoChip label='Detect' value={telemetry?.detections.length ? `${telemetry.detections.length} target(s)` : 'No target'} />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: '#aab1d6', fontSize: 13, marginBottom: 6 }}>Confidence: {confidence.toFixed(2)}</div>
          <input
            type="range" min={0.1} max={1} step={0.05} value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            style={{ width: '100%' }}
          />
        </div>
        <button
          onClick={save}
          style={{
            padding: '8px 12px', background: '#2d8cff', color: '#fff',
            border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 700,
            whiteSpace: 'nowrap',
          }}
        >
          Save
        </button>
      </div>
    </div>
  )
}

function InfoChip({ label, value }: { label: string, value: string }) {
  return (
    <div style={{ background: '#101426', border: '1px solid #232842', borderRadius: 10, padding: '9px 10px' }}>
      <div style={{ color: '#6e78a8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ color: '#eef2ff', fontSize: 12, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</div>
    </div>
  )
}
