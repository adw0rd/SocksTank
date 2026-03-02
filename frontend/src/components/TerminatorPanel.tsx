import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'

const ROBOT_PHRASES = ['Привет!', 'Как дела?', 'Где носки!?', 'А если найду?', 'Sock my tank!', "I'll be back"]
const SPEECH_COLORS = ['#231b11', '#b3261e', '#0d47a1', '#5d4037']
const SPEECH_SIZE_MULTIPLIERS = [1.05, 1.1, 1.15, 1.2, 1.25, 1.3]
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

export function TerminatorPanel() {
  const [speech, setSpeech] = useState<string | null>(null)
  const [speechColor, setSpeechColor] = useState(SPEECH_COLORS[0])
  const [speechScale, setSpeechScale] = useState(SPEECH_SIZE_MULTIPLIERS[0])
  const [bubblePresetIndex, setBubblePresetIndex] = useState(0)
  const bubblePreset = BUBBLE_PRESETS[bubblePresetIndex]
  const lastPresetIndexRef = useRef(0)
  const lastColorIndexRef = useRef(0)

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

  return (
    <div style={{ padding: 16 }}>
      <div
        style={{
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
    </div>
  )
}
