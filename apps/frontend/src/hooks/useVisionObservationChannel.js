import { useEffect, useState } from 'react'

export function useVisionObservationChannel(matchId, resetToken) {
  const connectionKey = `${matchId}:${resetToken}`
  const [state, setState] = useState({ connectionKey, status: 'connecting', observations: [], error: null })

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/integration/live/ws`)
    socket.onopen = () => setState({ connectionKey, status: 'live', observations: [], error: null })
    socket.onmessage = (message) => {
      const payload = JSON.parse(message.data)
      if (payload.type !== 'observation') return
      setState((current) => ({
        connectionKey,
        status: 'live',
        error: null,
        observations: [...(current.connectionKey === connectionKey ? current.observations : []).slice(-299), payload.observation],
      }))
    }
    socket.onerror = () => setState((current) => ({ ...current, status: 'error', error: 'Canal de visión no disponible' }))
    socket.onclose = () => setState((current) => ({ ...current, status: current.status === 'error' ? 'error' : 'closed' }))
    return () => socket.close()
  }, [connectionKey])

  return state
}
