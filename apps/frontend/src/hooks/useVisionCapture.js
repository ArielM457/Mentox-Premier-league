import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'

const CAPTURE_INTERVAL_MS = 1000

function frameBlob(video) {
  if (!video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) return Promise.resolve(null)
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82))
}

// Un solo request puede estar activo. Pause desmonta el intervalo inmediatamente;
// el backend vuelve a validar el estado para rechazar una captura que llegue tarde.
export function useVisionCapture({ matchId, playing, timeRef, videoRef }) {
  const busy = useRef(false)
  const [state, setState] = useState({ status: 'idle', processed: 0, skipped: 0, error: null })

  useEffect(() => {
    if (!playing || !videoRef.current?.src) {
      setState((current) => ({ ...current, status: 'idle' }))
      return undefined
    }
    let active = true
    const capture = async () => {
      if (!active || busy.current) return
      busy.current = true
      try {
        const image = await frameBlob(videoRef.current)
        if (!image || !active) return
        setState((current) => ({ ...current, status: 'processing', error: null }))
        const result = await api.captureVisionFrame(matchId, timeRef.current, image)
        if (!active) return
        setState((current) => ({
          status: 'live',
          processed: current.processed + Number(result.accepted),
          skipped: current.skipped + Number(!result.accepted),
          error: null,
        }))
      } catch (error) {
        if (active) setState((current) => ({ ...current, status: 'error', error: error.message }))
      } finally {
        busy.current = false
      }
    }
    capture()
    const interval = window.setInterval(capture, CAPTURE_INTERVAL_MS)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [matchId, playing, timeRef, videoRef])

  return state
}
