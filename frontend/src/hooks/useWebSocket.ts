import { useEffect, useRef, useState, useCallback } from 'react'
import type { Telemetry, WsCommand } from '../lib/types'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

export function useWebSocket() {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null)
  const [status, setStatus] = useState<WsStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const connect = useCallback(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/ws/control`

    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as Telemetry
        if (data.type === 'telemetry') {
          setTelemetry(data)
        }
      } catch { /* ignore */ }
    }

    ws.onclose = () => {
      setStatus('disconnected')
      reconnectRef.current = setTimeout(connect, 2000)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((cmd: WsCommand) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(cmd))
    }
  }, [])

  return { telemetry, status, send }
}
