import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'

const BUCKET_MS = 10_000
const LOOK_BEHIND_MS = 2_000
const LOOK_AHEAD_MS = 28_000

// Mantiene una ventana pequeña de TrackingFrame v1 alrededor del reloj.
// El backend añade los cuadros limítrofes para interpolar sin descargar el partido completo.
export function useTrackingFrames({ durationMs, matchId, seekVersion, timeMs }) {
  const [state, setState] = useState({ frames: [], source: null, loading: true, error: null })
  const requestId = useRef(0)
  const bucket = Math.floor(timeMs / BUCKET_MS) * BUCKET_MS

  useEffect(() => {
    if (!matchId) return undefined
    const id = ++requestId.current
    const from = Math.max(0, bucket - LOOK_BEHIND_MS)
    const to = Math.min(durationMs, from + LOOK_AHEAD_MS)
    api.tracking(matchId, from, to)
      .then((payload) => {
        if (id !== requestId.current) return
        setState({ frames: payload.frames, source: payload.source, loading: false, error: null })
      })
      .catch((error) => {
        if (id !== requestId.current) return
        setState((current) => ({ ...current, loading: false, error: error.message }))
      })
    return () => { requestId.current += 1 }
  }, [bucket, durationMs, matchId, seekVersion])

  return state
}
