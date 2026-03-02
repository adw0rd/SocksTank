import { useCallback, useEffect, useMemo, useState } from 'react'
import type { PlaceSummary } from '../lib/types'

interface PlacesResponse {
  active_target_place_id: string | null
  items: PlaceSummary[]
}

async function readFileAsBase64(file: File) {
  const buffer = await file.arrayBuffer()
  let binary = ''
  const bytes = new Uint8Array(buffer)
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

export function PlacesPanel() {
  const [places, setPlaces] = useState<PlaceSummary[]>([])
  const [activeTargetId, setActiveTargetId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const fetchPlaces = useCallback(() => {
    fetch('/api/places')
      .then((r) => r.json())
      .then((data: PlacesResponse) => {
        setPlaces(data.items ?? [])
        setActiveTargetId(data.active_target_place_id ?? null)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchPlaces()
    const timer = setInterval(fetchPlaces, 5000)
    return () => clearInterval(timer)
  }, [fetchPlaces])

  useEffect(() => {
    if (!selectedPlaceId && places.length > 0) {
      setSelectedPlaceId(places[0].id)
    }
  }, [places, selectedPlaceId])

  const selectedPlace = useMemo(
    () => places.find((place) => place.id === selectedPlaceId) ?? null,
    [places, selectedPlaceId],
  )

  const createPlace = async () => {
    const trimmed = name.trim()
    if (!trimmed) return
    setBusy(true)
    setMessage(null)
    try {
      const response = await fetch('/api/places', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to create place')
      }
      setName('')
      setSelectedPlaceId(payload.id)
      setMessage(`Created ${payload.name}`)
      fetchPlaces()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to create place')
    } finally {
      setBusy(false)
    }
  }

  const setActiveTarget = async (placeId: string | null) => {
    setBusy(true)
    setMessage(null)
    try {
      const response = await fetch('/api/places/active', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ place_id: placeId }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to update active target')
      }
      setActiveTargetId(payload.active_target_place_id ?? null)
      fetchPlaces()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to update active target')
    } finally {
      setBusy(false)
    }
  }

  const uploadImages = async (files: FileList | null) => {
    if (!files || !selectedPlaceId || files.length === 0) return
    setBusy(true)
    setMessage(null)
    try {
      const items = await Promise.all(
        Array.from(files).map(async (file) => ({
          filename: file.name,
          content_base64: await readFileAsBase64(file),
        })),
      )
      const response = await fetch(`/api/places/${selectedPlaceId}/images`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to upload images')
      }
      setMessage(`Uploaded ${payload.items?.length ?? 0} image(s)`)
      fetchPlaces()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to upload images')
    } finally {
      setBusy(false)
    }
  }

  const triggerTrain = async () => {
    if (!selectedPlaceId) return
    setBusy(true)
    setMessage(null)
    try {
      const response = await fetch(`/api/places/${selectedPlaceId}/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to start training')
      }
      setMessage(`Training job ${payload.job_id} finished as ${payload.status}`)
      fetchPlaces()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to start training')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
        Places
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="New place name"
          style={{
            flex: 1,
            minWidth: 0,
            padding: '10px 12px',
            fontSize: 13,
            color: '#eef2ff',
            background: '#101426',
            border: '1px solid #2c3558',
            borderRadius: 10,
            outline: 'none',
          }}
        />
        <button
          onClick={createPlace}
          disabled={busy || !name.trim()}
          style={{
            padding: '10px 12px',
            fontSize: 12,
            fontWeight: 700,
            borderRadius: 10,
            border: '1px solid #2d8cff',
            background: '#2d8cff',
            color: '#fff',
            cursor: busy ? 'default' : 'pointer',
            opacity: busy || !name.trim() ? 0.6 : 1,
          }}
        >
          Add
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
        {places.length === 0 ? (
          <div style={emptyState}>No places yet</div>
        ) : (
          places.map((place) => (
            <button
              key={place.id}
              onClick={() => setSelectedPlaceId(place.id)}
              style={{
                ...placeRow,
                borderColor: selectedPlaceId === place.id ? '#4a7dff' : '#232842',
                background: selectedPlaceId === place.id ? 'rgba(45, 140, 255, 0.10)' : '#101426',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                <div style={{ color: '#eef2ff', fontSize: 13, fontWeight: 700, textAlign: 'left' }}>{place.name}</div>
                {place.is_active_target && <div style={badge}>Active</div>}
              </div>
              <div style={{ color: '#8892bf', fontSize: 11, marginTop: 4, textAlign: 'left' }}>
                {place.label} • {place.status} • {place.image_count} image(s)
              </div>
            </button>
          ))
        )}
      </div>

      {selectedPlace && (
        <div style={{ ...card, marginBottom: 10 }}>
          <div style={{ color: '#eef2ff', fontSize: 13, fontWeight: 700, marginBottom: 8 }}>{selectedPlace.name}</div>
          <div style={{ color: '#8b93bb', fontSize: 11, lineHeight: 1.5, marginBottom: 10 }}>
            Upload photos now. Box annotation UI is the next step; training requires every uploaded image to be annotated.
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <button
              onClick={() => setActiveTarget(selectedPlace.is_active_target ? null : selectedPlace.id)}
              disabled={busy}
              style={{
                ...actionButton,
                background: selectedPlace.is_active_target ? '#26324d' : '#2d8cff',
                borderColor: selectedPlace.is_active_target ? '#3a4568' : '#2d8cff',
                opacity: busy ? 0.6 : 1,
              }}
            >
              {selectedPlace.is_active_target ? 'Clear Target' : 'Set Target'}
            </button>
            <button
              onClick={triggerTrain}
              disabled={busy}
              style={{ ...actionButton, opacity: busy ? 0.6 : 1 }}
            >
              Train
            </button>
          </div>
          <label style={{ display: 'block' }}>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => {
                void uploadImages(event.target.files)
                event.currentTarget.value = ''
              }}
              style={{ display: 'none' }}
            />
            <span style={{ ...actionButton, display: 'inline-flex', width: '100%', justifyContent: 'center' }}>
              Upload Photos
            </span>
          </label>
        </div>
      )}

      <div style={{ color: activeTargetId ? '#9fd1ff' : '#8b93bb', fontSize: 11, lineHeight: 1.5 }}>
        {activeTargetId ? `Current AI delivery target: ${places.find((place) => place.id === activeTargetId)?.name ?? activeTargetId}` : 'No active AI delivery target'}
      </div>

      {message && (
        <div style={{ marginTop: 10, color: '#c9d1ff', fontSize: 11, lineHeight: 1.5 }}>
          {message}
        </div>
      )}
    </div>
  )
}

const placeRow: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid #232842',
  cursor: 'pointer',
}

const badge: React.CSSProperties = {
  padding: '2px 8px',
  borderRadius: 999,
  background: 'rgba(45, 140, 255, 0.14)',
  border: '1px solid #4a7dff',
  color: '#a9ddff',
  fontSize: 10,
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
}

const card: React.CSSProperties = {
  background: '#101426',
  border: '1px solid #232842',
  borderRadius: 10,
  padding: '10px 12px',
}

const actionButton: React.CSSProperties = {
  padding: '8px 10px',
  fontSize: 12,
  fontWeight: 700,
  color: '#d7defe',
  background: '#242b45',
  border: '1px solid #343d62',
  borderRadius: 8,
  cursor: 'pointer',
}

const emptyState: React.CSSProperties = {
  ...card,
  color: '#8b93bb',
  fontSize: 12,
  textAlign: 'center',
}
