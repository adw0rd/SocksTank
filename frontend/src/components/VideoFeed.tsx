import { useEffect, useRef, useState } from 'react'

export function VideoFeed() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    const onChange = () => {
      setIsFullscreen(document.fullscreenElement === containerRef.current)
    }
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggleFullscreen = async () => {
    const node = containerRef.current
    if (!node) return
    if (document.fullscreenElement === node) {
      await document.exitFullscreen()
      return
    }
    await node.requestFullscreen()
  }

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        background: '#060913',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      <button
        data-testid="video-fullscreen-toggle"
        onClick={() => { void toggleFullscreen() }}
        style={{
          position: 'absolute',
          top: 12,
          right: 12,
          zIndex: 2,
          padding: '8px 10px',
          fontSize: 12,
          fontWeight: 700,
          color: '#eef2ff',
          background: 'rgba(11, 15, 26, 0.78)',
          border: '1px solid rgba(122, 136, 184, 0.45)',
          borderRadius: 8,
          cursor: 'pointer',
          backdropFilter: 'blur(6px)',
        }}
      >
        {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
      </button>
      <img
        data-testid="video-stream"
        src="/api/video/stream"
        alt="Camera"
        style={{
          width: '100%',
          display: 'block',
          minHeight: isFullscreen ? '100vh' : undefined,
          objectFit: 'contain',
          background: '#05070d',
        }}
      />
    </div>
  )
}
