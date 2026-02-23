export function VideoFeed() {
  return (
    <div style={{ position: 'relative', background: '#111', borderRadius: 8, overflow: 'hidden' }}>
      <img
        src="/api/video/stream"
        alt="Camera"
        style={{ width: '100%', display: 'block' }}
      />
    </div>
  )
}
