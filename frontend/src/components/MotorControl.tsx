import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import type { ButtonHTMLAttributes } from 'react'
import type { Telemetry, WsCommand } from '../lib/types'

interface Props {
  send: (cmd: WsCommand) => void
  telemetry: Telemetry | null
}

const ROBOT_PHRASES = ['Привет!', 'Как дела?', 'Где носки!?', 'А если найду?', 'Sock my tank!', "I'll be back"]
const SPEECH_COLORS = ['#231b11', '#b3261e', '#0d47a1', '#5d4037']
const SPEECH_SIZE_MULTIPLIERS = [1.05, 1.1, 1.15, 1.2, 1.25, 1.3]
const HOTKEY_CODES = ['KeyQ', 'KeyW', 'KeyE', 'KeyA', 'KeyS', 'KeyD', 'KeyZ', 'KeyX', 'KeyC']
const HOTKEY_VECTORS: Record<string, [number, number]> = {
  KeyQ: [0, 1],
  KeyW: [1, 1],
  KeyE: [1, 0],
  KeyA: [-1, 1],
  KeyS: [-1, -1],
  KeyD: [1, -1],
  KeyZ: [0, -1],
  KeyX: [-1, -1],
  KeyC: [-1, 0],
}
const BUBBLE_PRESETS = [
  {
    container: { top: 14, right: 12 } as CSSProperties,
    tail: { right: 22, bottom: -8 } as CSSProperties,
  },
  {
    container: { top: 18, left: 12 } as CSSProperties,
    tail: { left: 26, bottom: -8 } as CSSProperties,
  },
  {
    container: { top: 86, right: 16 } as CSSProperties,
    tail: { right: 28, bottom: -8 } as CSSProperties,
  },
  {
    container: { top: 80, left: 16 } as CSSProperties,
    tail: { left: 28, bottom: -8 } as CSSProperties,
  },
  {
    container: { top: 44, left: '50%', transform: 'translateX(-50%)' } as CSSProperties,
    tail: { left: '50%', bottom: -8, transform: 'translateX(-50%) rotate(45deg)' } as CSSProperties,
  },
]

export function MotorControl({ send, telemetry }: Props) {
  const [speed, setSpeed] = useState(2000)
  const [speech, setSpeech] = useState<string | null>(null)
  const [speechColor, setSpeechColor] = useState(SPEECH_COLORS[0])
  const [speechScale, setSpeechScale] = useState(SPEECH_SIZE_MULTIPLIERS[0])
  const [bubblePresetIndex, setBubblePresetIndex] = useState(0)
  const aiMode = telemetry?.mode === 'ai'
  const estop = telemetry?.estop ?? false
  const locked = aiMode || estop
  const bubblePreset = BUBBLE_PRESETS[bubblePresetIndex]
  const lastPresetIndexRef = useRef(0)
  const lastColorIndexRef = useRef(0)
  const activeHotkeysRef = useRef<Set<string>>(new Set())
  const speedRef = useRef(speed)
  const lockedRef = useRef(locked)

  useEffect(() => {
    speedRef.current = speed
  }, [speed])

  useEffect(() => {
    lockedRef.current = locked
  }, [locked])

  useEffect(() => {
    let showTimer: ReturnType<typeof setTimeout> | undefined
    let hideTimer: ReturnType<typeof setTimeout> | undefined
    let cancelled = false

    const runCycle = () => {
      const nextSpeech = ROBOT_PHRASES[Math.floor(Math.random() * ROBOT_PHRASES.length)]
      const nextPresetIndex =
        BUBBLE_PRESETS.length > 1
          ? (lastPresetIndexRef.current + 1 + Math.floor(Math.random() * (BUBBLE_PRESETS.length - 1))) % BUBBLE_PRESETS.length
          : 0
      const nextColorIndex =
        SPEECH_COLORS.length > 1
          ? (lastColorIndexRef.current + 1 + Math.floor(Math.random() * (SPEECH_COLORS.length - 1))) % SPEECH_COLORS.length
          : 0
      const nextColor = SPEECH_COLORS[nextColorIndex]
      const nextScale = SPEECH_SIZE_MULTIPLIERS[Math.floor(Math.random() * SPEECH_SIZE_MULTIPLIERS.length)]
      lastPresetIndexRef.current = nextPresetIndex
      lastColorIndexRef.current = nextColorIndex
      setBubblePresetIndex(nextPresetIndex)
      setSpeechColor(nextColor)
      setSpeechScale(nextScale)
      setSpeech(nextSpeech)

      hideTimer = setTimeout(() => {
        setSpeech(null)
        if (!cancelled) {
          showTimer = setTimeout(runCycle, 3000)
        }
      }, 10000)
    }

    runCycle()

    return () => {
      cancelled = true
      if (showTimer) clearTimeout(showTimer)
      if (hideTimer) clearTimeout(hideTimer)
    }
  }, [])

  const sendRawMotor = (left: number, right: number) => {
    if (locked) return
    send({ cmd: 'motor', params: { left, right } })
  }

  const stop = () => sendRawMotor(0, 0)
  const driveProfiles = {
    tl: { left: 0, right: speed },
    fwd: { left: speed, right: speed },
    tr: { left: speed, right: 0 },
    left: { left: -speed, right: speed },
    right: { left: speed, right: -speed },
    bl: { left: 0, right: -speed },
    bwd: { left: -speed, right: -speed },
    br: { left: -speed, right: 0 },
  }

  const holdToDrive = (leftTrack: number, rightTrack: number): ButtonHTMLAttributes<HTMLButtonElement> => ({
    onMouseDown: () => sendRawMotor(leftTrack, rightTrack),
    onMouseUp: stop,
    onMouseLeave: stop,
    onTouchStart: (event) => {
      event.preventDefault()
      sendRawMotor(leftTrack, rightTrack)
    },
    onTouchEnd: (event) => {
      event.preventDefault()
      stop()
    },
    onTouchCancel: (event) => {
      event.preventDefault()
      stop()
    },
  })

  useEffect(() => {
    const clampUnit = (value: number) => Math.max(-1, Math.min(1, value))

    const commandFromActiveKeys = (value: number) => {
      let left = 0
      let right = 0

      for (const code of activeHotkeysRef.current) {
        const vector = HOTKEY_VECTORS[code]
        if (!vector) continue
        left += vector[0]
        right += vector[1]
      }

      return {
        left: clampUnit(left) * value,
        right: clampUnit(right) * value,
      }
    }

    const isTypingTarget = (eventTarget: EventTarget | null) => {
      const element = eventTarget as HTMLElement | null
      if (!element) return false
      const tag = element.tagName
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || element.isContentEditable
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (!HOTKEY_CODES.includes(event.code) || event.repeat || isTypingTarget(event.target)) {
        return
      }
      if (lockedRef.current) {
        return
      }
      event.preventDefault()
      activeHotkeysRef.current.add(event.code)
      const command = commandFromActiveKeys(speedRef.current)
      sendRawMotor(command.left, command.right)
    }

    const onKeyUp = (event: KeyboardEvent) => {
      if (!HOTKEY_CODES.includes(event.code) || isTypingTarget(event.target)) {
        return
      }
      if (lockedRef.current) {
        return
      }
      event.preventDefault()
      activeHotkeysRef.current.delete(event.code)
      const command = commandFromActiveKeys(speedRef.current)
      sendRawMotor(command.left, command.right)
    }

    const onWindowBlur = () => {
      activeHotkeysRef.current.clear()
      if (!lockedRef.current) {
        sendRawMotor(0, 0)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    window.addEventListener('blur', onWindowBlur)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      window.removeEventListener('blur', onWindowBlur)
      activeHotkeysRef.current.clear()
    }
  }, [send, locked])

  const btnStyle = (bg: string): React.CSSProperties => ({
    padding: '14px 0', fontSize: 16, fontWeight: 'bold',
    background: bg, color: '#fff', border: 'none', borderRadius: 6,
    cursor: 'pointer', minWidth: 60,
  })

  return (
    <div style={{ padding: 16 }}>
      <div
        style={{
          marginBottom: 12,
          borderRadius: 10,
          overflow: 'hidden',
          border: '1px solid #232842',
          background: '#0d1120',
          position: 'relative',
        }}
      >
        {speech && (
          <div
            style={{
              position: 'absolute',
              ...bubblePreset.container,
              maxWidth: 150,
              padding: '10px 12px',
              background: '#fff8e7',
              color: speechColor,
              borderRadius: 14,
              fontSize: `${12 * speechScale}px`,
              fontWeight: 700,
              lineHeight: 1.3,
              boxShadow: '0 10px 24px rgba(0, 0, 0, 0.25)',
              zIndex: 1,
              animation: 'speechBubbleFade 10s ease-in-out forwards',
            }}
          >
            {speech}
            <div
              style={{
                position: 'absolute',
                ...bubblePreset.tail,
                width: 14,
                height: 14,
                background: '#fff8e7',
                transform: bubblePreset.tail.transform || 'rotate(45deg)',
                borderBottomRightRadius: 4,
              }}
            />
          </div>
        )}
        <img
          src="/term.jpg"
          alt="Tank controller diagram"
          style={{ display: 'block', width: '100%', height: 'auto' }}
        />
      </div>
      <style>
        {`
          @keyframes speechBubbleFade {
            0% { opacity: 0; }
            10% { opacity: 1; }
            82% { opacity: 1; }
            100% { opacity: 0; }
          }
        `}
      </style>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ color: '#cbd3ff', fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          Motor Control
        </div>
        <div style={{ color: estop ? '#ffcf7a' : aiMode ? '#ffb36b' : '#7f88b8', fontSize: 12 }}>
          {estop ? 'Locked by E-STOP' : aiMode ? 'AI owns drive train' : 'Manual drive'}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ color: '#aab1d6', fontSize: 13, minWidth: 90 }}>Speed: {speed}</span>
        <input
          type="range" min={500} max={4095} value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
          style={{ flex: 1 }}
          disabled={locked}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, opacity: locked ? 0.55 : 1 }}>
        <button disabled={locked} style={btnStyle('#32414a')} {...holdToDrive(driveProfiles.tl.left, driveProfiles.tl.right)}>Q / TL</button>
        <button disabled={locked} style={btnStyle('#2d8cff')} {...holdToDrive(driveProfiles.fwd.left, driveProfiles.fwd.right)}>W / FWD</button>
        <button disabled={locked} style={btnStyle('#32414a')} {...holdToDrive(driveProfiles.tr.left, driveProfiles.tr.right)}>E / TR</button>

        <button disabled={locked} style={btnStyle('#3d5361')} {...holdToDrive(driveProfiles.left.left, driveProfiles.left.right)}>A / LEFT</button>
        <div
          style={{
            borderRadius: 6,
            border: '1px dashed #39415f',
            color: '#7f88b8',
            fontSize: 12,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '0 8px',
          }}
        >
          Hold to drive
        </div>
        <button disabled={locked} style={btnStyle('#3d5361')} {...holdToDrive(driveProfiles.right.left, driveProfiles.right.right)}>D / RIGHT</button>

        <button disabled={locked} style={btnStyle('#32414a')} {...holdToDrive(driveProfiles.bl.left, driveProfiles.bl.right)}>Z / BL</button>
        <button disabled={locked} style={btnStyle('#2d8cff')} {...holdToDrive(driveProfiles.bwd.left, driveProfiles.bwd.right)}>X / BWD</button>
        <button disabled={locked} style={btnStyle('#32414a')} {...holdToDrive(driveProfiles.br.left, driveProfiles.br.right)}>C / BR</button>
      </div>
    </div>
  )
}
