import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

function mergeObservations(current, incoming) {
  const values = new Map(current.map((item) => [`${item.source}:${item.observation_id}`, item]))
  for (const item of incoming) values.set(`${item.source}:${item.observation_id}`, item)
  return [...values.values()]
    .sort((left, right) => left.timestamp_ms - right.timestamp_ms)
    .slice(-5000)
}

export function useVisionObservationChannel(matchId, resetToken, timeMs = 0) {
  const connectionKey = `${matchId}:${resetToken}`
  const [state, setState] = useState({ connectionKey, status: 'connecting', observations: [], error: null })

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/integration/live/ws`)
    let active = true
    socket.onopen = () => {
      if (active) setState((current) => ({ connectionKey, status: 'live', observations: current.connectionKey === connectionKey ? current.observations : [], error: null }))
    }
    socket.onmessage = (message) => {
      if (!active) return
      let payload
      try { payload = JSON.parse(message.data) } catch { return }
      if (payload.type !== 'observation') return
      if (payload.observation?.payload?.match_id !== matchId) return
      setState((current) => ({
        connectionKey,
        status: 'live',
        error: null,
        observations: mergeObservations(
          current.connectionKey === connectionKey ? current.observations : [],
          [payload.observation],
        ),
      }))
    }
    socket.onerror = () => { if (active) setState((current) => ({ ...current, status: 'error', error: 'Canal de visión no disponible' })) }
    socket.onclose = () => { if (active) setState((current) => ({ ...current, status: current.status === 'error' ? 'error' : 'closed' })) }
    return () => { active = false; socket.close() }
  }, [connectionKey, matchId])

  const second = Math.floor(timeMs / 1000)
  useEffect(() => {
    let active = true
    const start = Math.max(0, second * 1000 - 30000)
    const end = second * 1000 + 3000
    api.visionObservations(matchId, start, end)
      .then((payload) => {
        if (!active) return
        setState((current) => ({
          ...current, connectionKey,
          observations: mergeObservations(current.connectionKey === connectionKey ? current.observations : [], payload.observations ?? []),
        }))
      })
      .catch((error) => {
        if (active) setState((current) => ({ ...current, error: error.message }))
      })
    return () => { active = false }
  }, [matchId, second, resetToken, connectionKey])

  return state
}
