import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'

const MAX_CHAT = 200

// Sala de un resumen: estado inicial por HTTP y cambios en tiempo real por SSE.
// Si el canal se reconecta (el navegador lo hace solo), se vuelve a pedir el estado
// para no perder lo que pasó mientras estuvo desconectado.
export function useCommunityRoom(matchId, draftId, clientId) {
  const [room, setRoom] = useState(null)
  const [status, setStatus] = useState('connecting')
  const [error, setError] = useState(null)
  const [lastEvent, setLastEvent] = useState(null)
  const request = useRef(0)

  const load = useCallback(async () => {
    if (!matchId || !draftId) return
    const id = ++request.current
    try {
      const data = await api.communityRoom(matchId, draftId, clientId)
      if (id === request.current) {
        setRoom(data)
        setError(null)
      }
    } catch (err) {
      if (id === request.current) setError(err.message)
    }
  }, [matchId, draftId, clientId])

  useEffect(() => {
    if (!matchId || !draftId) return undefined
    const source = new EventSource(api.communityStreamUrl(matchId, draftId))
    source.addEventListener('ready', () => {
      setStatus('live')
      load()
    })
    source.addEventListener('vote', (message) => {
      const event = JSON.parse(message.data)
      setRoom((current) => (current ? { ...current, tally: event.tally } : current))
      setLastEvent({ type: 'vote', ...event, at: Date.now() })
    })
    source.addEventListener('message', (message) => {
      const { message: item } = JSON.parse(message.data)
      setRoom((current) => {
        if (!current) return current
        const list = item.kind === 'suggestion' ? 'suggestions' : 'chat'
        if (current[list].some((m) => m.message_id === item.message_id)) return current
        return { ...current, [list]: [...current[list], item].slice(-MAX_CHAT) }
      })
    })
    source.onerror = () => setStatus(source.readyState === EventSource.CLOSED ? 'closed' : 'reconnecting')
    return () => {
      source.close()
      setStatus('connecting')
    }
  }, [matchId, draftId, load])

  const vote = useCallback(async (author, choice) => {
    const tally = await api.communityVote(matchId, draftId, { client_id: clientId, author, vote: choice })
    setRoom((current) => (current ? { ...current, tally, my_vote: choice } : current))
  }, [matchId, draftId, clientId])

  const send = useCallback(async (author, kind, text) => {
    const item = await api.communityPost(matchId, draftId, { client_id: clientId, author, kind, text })
    // El mismo mensaje llega por el canal; se agrega aquí también por si el canal va atrasado.
    setRoom((current) => {
      if (!current) return current
      const list = kind === 'suggestion' ? 'suggestions' : 'chat'
      if (current[list].some((m) => m.message_id === item.message_id)) return current
      return { ...current, [list]: [...current[list], item].slice(-MAX_CHAT) }
    })
    return item
  }, [matchId, draftId, clientId])

  return { room, status, error, lastEvent, vote, send, reload: load }
}
