import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { PlaceAnnotationRecord, PlaceImageSummary, PlaceSummary } from '../lib/types'

interface PlacesResponse {
  active_target_place_id: string | null
  items: PlaceSummary[]
}

interface PlaceImagesResponse {
  items: PlaceImageSummary[]
}

interface PlaceAnnotationsResponse {
  items: PlaceAnnotationRecord[]
}

type DraftBox = {
  startX: number
  startY: number
  endX: number
  endY: number
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

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value))
}

function toOverlayBox(annotation: PlaceAnnotationRecord) {
  const left = (annotation.x_center - annotation.width / 2) * 100
  const top = (annotation.y_center - annotation.height / 2) * 100
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${annotation.width * 100}%`,
    height: `${annotation.height * 100}%`,
  }
}

function normalizeDraft(draft: DraftBox, width: number, height: number) {
  const minX = Math.min(draft.startX, draft.endX)
  const maxX = Math.max(draft.startX, draft.endX)
  const minY = Math.min(draft.startY, draft.endY)
  const maxY = Math.max(draft.startY, draft.endY)

  const boxWidth = maxX - minX
  const boxHeight = maxY - minY
  if (boxWidth < 8 || boxHeight < 8) {
    return null
  }

  return {
    x_center: clamp01((minX + boxWidth / 2) / width),
    y_center: clamp01((minY + boxHeight / 2) / height),
    width: clamp01(boxWidth / width),
    height: clamp01(boxHeight / height),
  }
}

export function PlacesPanel() {
  const [places, setPlaces] = useState<PlaceSummary[]>([])
  const [activeTargetId, setActiveTargetId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null)
  const [images, setImages] = useState<PlaceImageSummary[]>([])
  const [annotations, setAnnotations] = useState<Record<string, PlaceAnnotationRecord>>({})
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null)
  const [draftBox, setDraftBox] = useState<DraftBox | null>(null)
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadPhase, setUploadPhase] = useState<'idle' | 'preparing' | 'uploading'>('idle')
  const [showGallery, setShowGallery] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const canvasRef = useRef<HTMLDivElement | null>(null)
  const uploadInputRef = useRef<HTMLInputElement | null>(null)

  const fetchPlaces = useCallback(() => {
    fetch('/api/places')
      .then((r) => r.json())
      .then((data: PlacesResponse) => {
        setPlaces(data.items ?? [])
        setActiveTargetId(data.active_target_place_id ?? null)
      })
      .catch(() => {})
  }, [])

  const fetchPlaceAssets = useCallback((placeId: string) => {
    fetch(`/api/places/${placeId}/images`)
      .then((r) => r.json())
      .then((data: PlaceImagesResponse) => {
        const nextImages = data.items ?? []
        setImages(nextImages)
        setSelectedImageId((current) => {
          if (current && nextImages.some((image) => image.id === current)) {
            return current
          }
          return nextImages[0]?.id ?? null
        })
      })
      .catch(() => {
        setImages([])
        setSelectedImageId(null)
      })

    fetch(`/api/places/${placeId}/annotations`)
      .then((r) => r.json())
      .then((data: PlaceAnnotationsResponse) => {
        const next: Record<string, PlaceAnnotationRecord> = {}
        for (const item of data.items ?? []) {
          next[item.place_image_id] = item
        }
        setAnnotations(next)
      })
      .catch(() => setAnnotations({}))
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

  useEffect(() => {
    if (!selectedPlaceId) {
      setImages([])
      setAnnotations({})
      setSelectedImageId(null)
      return
    }
    fetchPlaceAssets(selectedPlaceId)
  }, [fetchPlaceAssets, selectedPlaceId])

  const selectedPlace = useMemo(
    () => places.find((place) => place.id === selectedPlaceId) ?? null,
    [places, selectedPlaceId],
  )

  const selectedImage = useMemo(
    () => images.find((image) => image.id === selectedImageId) ?? null,
    [images, selectedImageId],
  )

  const selectedAnnotation = selectedImageId ? annotations[selectedImageId] ?? null : null

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
    setUploading(true)
    setUploadProgress(0)
    setUploadPhase('preparing')
    setMessage(null)
    try {
      setMessage(`Preparing ${files.length} image(s)...`)
      const sourceFiles = Array.from(files)
      const items = []
      for (let index = 0; index < sourceFiles.length; index += 1) {
        const file = sourceFiles[index]
        items.push({
          filename: file.name,
          content_base64: await readFileAsBase64(file),
        })
        setUploadProgress(Math.round(((index + 1) / sourceFiles.length) * 100))
      }
      setUploadPhase('uploading')
      setMessage(`Uploading ${items.length} image(s)...`)
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
      fetchPlaceAssets(selectedPlaceId)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to upload images')
    } finally {
      setBusy(false)
      setUploading(false)
      setUploadProgress(0)
      setUploadPhase('idle')
    }
  }

  const saveAnnotation = async () => {
    if (!selectedPlaceId || !selectedImageId || !draftBox || !canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const normalized = normalizeDraft(draftBox, rect.width, rect.height)
    if (!normalized) {
      setDraftBox(null)
      setMessage('Bounding box is too small')
      return
    }

    setBusy(true)
    setMessage(null)
    try {
      const response = await fetch(`/api/places/${selectedPlaceId}/images/${selectedImageId}/annotation`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalized),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to save annotation')
      }
      setAnnotations((current) => ({ ...current, [selectedImageId]: payload }))
      setDraftBox(null)
      setMessage('Annotation saved')
      fetchPlaces()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to save annotation')
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

  const deleteImage = async (imageId: string) => {
    if (!selectedPlaceId) return
    setBusy(true)
    setMessage(null)
    try {
      const response = await fetch(`/api/places/${selectedPlaceId}/images/${imageId}`, {
        method: 'DELETE',
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to delete image')
      }
      if (selectedImageId === imageId) {
        setSelectedImageId(null)
        setDraftBox(null)
      }
      setMessage('Image deleted')
      fetchPlaces()
      fetchPlaceAssets(selectedPlaceId)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to delete image')
    } finally {
      setBusy(false)
    }
  }

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!selectedImage) return
    const rect = event.currentTarget.getBoundingClientRect()
    const startX = event.clientX - rect.left
    const startY = event.clientY - rect.top
    setDraftBox({ startX, startY, endX: startX, endY: startY })
  }

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!draftBox) return
    const rect = event.currentTarget.getBoundingClientRect()
    const endX = Math.max(0, Math.min(rect.width, event.clientX - rect.left))
    const endY = Math.max(0, Math.min(rect.height, event.clientY - rect.top))
    setDraftBox((current) => (current ? { ...current, endX, endY } : current))
  }

  const onPointerUp = () => {
    // Keep the draft visible until the user explicitly saves or resets it.
  }

  const draftStyle = useMemo(() => {
    if (!draftBox) return null
    const left = Math.min(draftBox.startX, draftBox.endX)
    const top = Math.min(draftBox.startY, draftBox.endY)
    const width = Math.abs(draftBox.endX - draftBox.startX)
    const height = Math.abs(draftBox.endY - draftBox.startY)
    return { left, top, width, height }
  }, [draftBox])

  const activeTargetName = places.find((place) => place.id === activeTargetId)?.name ?? activeTargetId

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
          style={inputStyle}
        />
        <button
          onClick={createPlace}
          disabled={busy || !name.trim()}
          style={{
            ...primaryButton,
            opacity: busy || !name.trim() ? 0.6 : 1,
            cursor: busy || !name.trim() ? 'default' : 'pointer',
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
          <div style={{ color: '#eef2ff', fontSize: 13, fontWeight: 700, marginBottom: 6 }}>{selectedPlace.name}</div>
          <div style={{ color: '#8b93bb', fontSize: 11, lineHeight: 1.5, marginBottom: 10 }}>
            Upload photos, draw one bounding box per image, then train. The current MVP saves YOLO-normalized boxes directly from this panel.
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

          <input
            ref={uploadInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={(event) => {
              void uploadImages(event.target.files)
              event.currentTarget.value = ''
            }}
            style={{ display: 'none' }}
          />
          <button
            type="button"
            onClick={() => uploadInputRef.current?.click()}
            disabled={busy || uploading}
            style={{
              ...actionButton,
              width: '100%',
              justifyContent: 'center',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 10,
              opacity: busy || uploading ? 0.6 : 1,
              cursor: busy || uploading ? 'default' : 'pointer',
            }}
          >
            {uploading && <span style={spinner} />}
            {uploading ? 'Uploading Photos...' : 'Upload Photos'}
          </button>

          {uploading && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
                <div style={{ color: '#8b93bb', fontSize: 11 }}>
                  {uploadPhase === 'preparing' ? 'Preparing files' : 'Sending request'}
                </div>
                <div style={{ color: '#c9d1ff', fontSize: 11, fontWeight: 700 }}>
                  {uploadPhase === 'preparing' ? `${uploadProgress}%` : '...'}
                </div>
              </div>
              <div style={progressTrack}>
                <div
                  style={{
                    ...progressFill,
                    width: uploadPhase === 'preparing' ? `${uploadProgress}%` : '100%',
                    opacity: uploadPhase === 'preparing' ? 1 : 0.8,
                  }}
                />
              </div>
            </div>
          )}

          {images.length > 0 && (
            <>
              <button
                type="button"
                onClick={() => setShowGallery(true)}
                style={{ ...actionButton, width: '100%', marginBottom: 10 }}
              >
                Photo Library ({images.length})
              </button>

              <div style={{ display: 'flex', gap: 6, overflowX: 'auto', marginBottom: 10, paddingBottom: 2 }}>
                {images.map((image, index) => (
                  <button
                    key={image.id}
                    onClick={() => {
                      setSelectedImageId(image.id)
                      setDraftBox(null)
                    }}
                    style={{
                      minWidth: 40,
                      padding: '6px 8px',
                      borderRadius: 8,
                      border: selectedImageId === image.id ? '1px solid #4a7dff' : '1px solid #2c3558',
                      background: image.annotated ? 'rgba(76, 175, 80, 0.12)' : '#141931',
                      color: image.annotated ? '#b8ffbf' : '#d7defe',
                      fontSize: 11,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>

              {selectedImage && (
                <>
                  <div style={{ color: '#8b93bb', fontSize: 11, marginBottom: 8 }}>
                    Draw a box around the place, then press <strong>Save Box</strong>.
                  </div>
                  <div
                    ref={canvasRef}
                    onPointerDown={onPointerDown}
                    onPointerMove={onPointerMove}
                    onPointerUp={onPointerUp}
                    onPointerLeave={onPointerUp}
                    style={{
                      position: 'relative',
                      width: '100%',
                      borderRadius: 10,
                      overflow: 'hidden',
                      border: '1px solid #2c3558',
                      background: '#0b1020',
                      marginBottom: 10,
                      cursor: 'crosshair',
                    }}
                  >
                    <img
                      src={`/api/places/${selectedPlace.id}/images/${selectedImage.id}`}
                      alt={selectedImage.filename}
                      style={{ display: 'block', width: '100%', height: 'auto' }}
                      draggable={false}
                    />

                    {selectedAnnotation && (
                      <div
                        style={{
                          ...annotationBox,
                          ...toOverlayBox(selectedAnnotation),
                        }}
                      />
                    )}

                    {draftStyle && (
                      <div
                        style={{
                          ...annotationBox,
                          left: draftStyle.left,
                          top: draftStyle.top,
                          width: draftStyle.width,
                          height: draftStyle.height,
                          borderColor: '#ffe082',
                          background: 'rgba(255, 224, 130, 0.14)',
                        }}
                      />
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={saveAnnotation}
                      disabled={busy || !draftBox}
                      style={{ ...actionButton, flex: 1, opacity: busy || !draftBox ? 0.6 : 1 }}
                    >
                      Save Box
                    </button>
                    <button
                      onClick={() => setDraftBox(null)}
                      disabled={busy || !draftBox}
                      style={{ ...actionButton, opacity: busy || !draftBox ? 0.6 : 1 }}
                    >
                      Reset
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}

      <div style={{ color: activeTargetId ? '#9fd1ff' : '#8b93bb', fontSize: 11, lineHeight: 1.5 }}>
        {activeTargetId ? `Current AI delivery target: ${activeTargetName}` : 'No active AI delivery target'}
      </div>

      {message && (
        <div style={{ marginTop: 10, color: '#c9d1ff', fontSize: 11, lineHeight: 1.5 }}>
          {message}
        </div>
      )}

      {showGallery && selectedPlace && (
        <div style={modalBackdrop} onClick={() => setShowGallery(false)}>
          <div style={modalCard} onClick={(event) => event.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
              <div>
                <div style={{ color: '#eef2ff', fontSize: 15, fontWeight: 800 }}>Photo Library</div>
                <div style={{ color: '#8b93bb', fontSize: 11, marginTop: 4 }}>
                  Click a thumbnail to switch to that frame. Delete removes the photo and its saved annotation.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowGallery(false)}
                style={{ ...actionButton, padding: '6px 10px' }}
              >
                Close
              </button>
            </div>

            <div style={galleryGrid}>
              {images.map((image, index) => (
                <div
                  key={image.id}
                  style={{
                    ...thumbnailCard,
                    borderColor: selectedImageId === image.id ? '#4a7dff' : '#232842',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedImageId(image.id)
                      setDraftBox(null)
                      setShowGallery(false)
                    }}
                    style={{ display: 'block', width: '100%', background: 'transparent', border: 0, padding: 0, cursor: 'pointer' }}
                  >
                    <div style={{ position: 'relative', aspectRatio: '1 / 1', borderRadius: 8, overflow: 'hidden', background: '#0b1020' }}>
                      <img
                        src={`/api/places/${selectedPlace.id}/images/${image.id}/thumb`}
                        alt={image.filename}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                        loading="lazy"
                      />
                      {image.annotated && <div style={thumbBadge}>Annotated</div>}
                    </div>
                  </button>

                  <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ color: '#d7defe', fontSize: 11, fontWeight: 700 }}>#{index + 1}</div>
                    <button
                      type="button"
                      onClick={() => void deleteImage(image.id)}
                      disabled={busy}
                      style={{
                        ...actionButton,
                        padding: '5px 8px',
                        fontSize: 11,
                        color: '#ffb8b8',
                        borderColor: '#5a3340',
                        background: '#2a1720',
                        opacity: busy ? 0.6 : 1,
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0,
  padding: '10px 12px',
  fontSize: 13,
  color: '#eef2ff',
  background: '#101426',
  border: '1px solid #2c3558',
  borderRadius: 10,
  outline: 'none',
}

const primaryButton: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 12,
  fontWeight: 700,
  borderRadius: 10,
  border: '1px solid #2d8cff',
  background: '#2d8cff',
  color: '#fff',
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

const annotationBox: React.CSSProperties = {
  position: 'absolute',
  border: '2px solid #4dd0e1',
  background: 'rgba(77, 208, 225, 0.12)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
}

const spinner: React.CSSProperties = {
  width: 12,
  height: 12,
  borderRadius: '50%',
  border: '2px solid rgba(215, 222, 254, 0.28)',
  borderTopColor: '#d7defe',
  animation: 'place-spin 0.8s linear infinite',
}

const progressTrack: React.CSSProperties = {
  width: '100%',
  height: 8,
  borderRadius: 999,
  overflow: 'hidden',
  background: '#141931',
  border: '1px solid #2c3558',
}

const progressFill: React.CSSProperties = {
  height: '100%',
  borderRadius: 999,
  background: 'linear-gradient(90deg, #2d8cff 0%, #59b7ff 100%)',
  transition: 'width 0.16s ease',
}

const modalBackdrop: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(3, 6, 12, 0.72)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 16,
  zIndex: 1000,
}

const modalCard: React.CSSProperties = {
  width: 'min(920px, 100%)',
  maxHeight: 'min(82vh, 900px)',
  overflow: 'auto',
  background: '#11162a',
  border: '1px solid #2a3352',
  borderRadius: 16,
  boxShadow: '0 24px 80px rgba(0, 0, 0, 0.45)',
  padding: 16,
}

const galleryGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
  gap: 12,
}

const thumbnailCard: React.CSSProperties = {
  background: '#0f1426',
  border: '1px solid #232842',
  borderRadius: 12,
  padding: 8,
}

const thumbBadge: React.CSSProperties = {
  position: 'absolute',
  top: 8,
  left: 8,
  padding: '3px 6px',
  borderRadius: 999,
  background: 'rgba(76, 175, 80, 0.85)',
  color: '#f6fff7',
  fontSize: 10,
  fontWeight: 800,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
}
