import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { mergeOverlay, overlayMap } from '../lib/overlays.js'

// Une el historial (al cargar o adelantar) con el canal en directo (SSE).
// Al pausar se cierra el canal; al reanudar o adelantar se abre desde la nueva posición.
// `prefs` debe ser estable (useMemo) para no reabrir el canal en cada render.
export function useLiveChannel({ matchId, prefs, playing, speed, timeRef, seekVersion }) {
  const [overlays, setOverlays] = useState(() => new Map())
  const [events, setEvents] = useState([])
  const [channel, setChannel] = useState({ key: null, status: 'connecting' })
  const [error, setError] = useState(null)
  const [latency, setLatency] = useState([])
  const request = useRef(0)
  const prefsKey = JSON.stringify(prefs)
  const streamKey = `${matchId}|${prefsKey}|${speed}|${seekVersion}`

  const resync = useCallback(async () => {
    if (!matchId) return
    const id = ++request.current
    const t = timeRef.current
    try {
      const [history, past] = await Promise.all([
        api.overlays(matchId, prefs, t),
        api.events(matchId, t),
      ])
      if (id !== request.current) return
      setOverlays((current) => {
        // Conserva lo que el canal ya entregó después de t con estas mismas preferencias.
        let next = overlayMap(history.overlays.map((m) => ({ ...m, prefsKey })))
        for (const m of current.values()) {
          if (m.video_time_ms > t && m.prefsKey === prefsKey) next = mergeOverlay(next, m)
        }
        return next
      })
      setEvents((current) => {
        const ids = new Set(past.events.map((e) => e.event_id))
        return [...past.events, ...current.filter((e) => !ids.has(e.event_id) && e.video_time_ms > t)]
      })
      setError(null)
    } catch (err) {
      if (id === request.current) setError(err.message)
    }
  }, [matchId, prefs, prefsKey, timeRef])

  useEffect(() => {
    resync()
  }, [resync, seekVersion])

  useEffect(() => {
    if (!matchId || !playing) return undefined
    const source = new EventSource(api.streamUrl(matchId, prefs, timeRef.current, speed))
    const status = (value) => setChannel({ key: streamKey, status: value })
    source.addEventListener('ready', () => status('live'))
    source.addEventListener('match_event', (message) => {
      const event = JSON.parse(message.data)
      setEvents((current) => (current.some((e) => e.event_id === event.event_id) ? current : [...current, event]))
    })
    source.addEventListener('overlay', (message) => {
      const payload = JSON.parse(message.data)
      const received = Date.now()
      setOverlays((current) => mergeOverlay(current, { ...payload.overlay, prefsKey }))
      setLatency((current) => [
        ...current.slice(-49),
        {
          messageId: payload.overlay.message_id,
          transportMs: Math.max(0, received - payload.emitted_at_ms),
          pipelineMs: payload.pipeline_ms,
          leadMs: payload.overlay.video_time_ms - timeRef.current,
        },
      ])
    })
    source.addEventListener('end', () => {
      status('ended')
      source.close()
    })
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) return
      status('error')
      setError('Se perdió el canal en directo. Pausa y vuelve a reproducir para reconectar.')
      source.close()
    }
    return () => source.close()
  }, [matchId, prefs, prefsKey, playing, speed, streamKey, timeRef])

  const status = !playing ? 'idle' : channel.key === streamKey ? channel.status : 'connecting'
  return { overlays, events, status, error, latency, resync }
}
