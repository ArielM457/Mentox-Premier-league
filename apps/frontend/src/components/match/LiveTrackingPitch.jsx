import { useEffect, useMemo, useRef } from 'react'
import { Spinner } from '../ui/Button.jsx'
import { Icon } from '../ui/Icon.jsx'

const FALLBACK_433 = [
  [7, 50], [22, 15], [18, 38], [18, 62], [22, 85],
  [39, 50], [49, 33], [49, 67], [68, 17], [73, 50], [68, 83],
]

const toPitchPct = (value) => 5 + value * 0.9

function preparedFrame(frame) {
  const players = new Map()
  let ball = null
  for (const item of frame.objects) {
    if (item.kind === 'ball') ball = item
    else if (item.player_id) players.set(item.player_id, item)
  }
  return { ...frame, players, ball }
}

function framePair(frames, timeMs) {
  if (!frames.length) return [null, null, 0]
  let low = 0
  let high = frames.length - 1
  while (low < high) {
    const middle = Math.ceil((low + high) / 2)
    if ((frames[middle].video_time_ms ?? 0) <= timeMs) low = middle
    else high = middle - 1
  }
  const left = frames[low]
  const right = frames[Math.min(low + 1, frames.length - 1)]
  const start = left.video_time_ms ?? 0
  const end = right.video_time_ms ?? start
  const progress = end === start ? 0 : Math.max(0, Math.min(1, (timeMs - start) / (end - start)))
  return [left, right, progress]
}

function between(left, right, progress) {
  const a = left ?? right
  const b = right ?? left
  if (!a || !b) return null
  return {
    x_m: a.x_m + (b.x_m - a.x_m) * progress,
    y_m: a.y_m + (b.y_m - a.y_m) * progress,
  }
}

export function LiveTrackingPitch({
  events,
  eventTypeLabels,
  frames,
  homeTeamId,
  label,
  loading,
  onSelectPlayer,
  pitchLengthM,
  pitchWidthM,
  players,
  playing,
  selectedPlayerId,
  situationLabels,
  sourceLabel,
  speed,
  timeMs,
}) {
  const pitchRef = useRef(null)
  const playerNodes = useRef(new Map())
  const ballRef = useRef(null)
  const boundsRef = useRef({ width: 1, height: 1 })
  const animationRef = useRef({ timeMs, wall: 0, playing, speed })
  const framesRef = useRef([])
  const reducedMotion = useRef(false)
  const prepared = useMemo(() => frames.map(preparedFrame), [frames])
  const recentEvents = events.slice(-3)
  const latestEvent = events.at(-1) ?? null
  const situationVisibleFor = latestEvent
    ? Math.max(4_000, latestEvent.stoppage_ms ?? 0)
    : 0
  const activeSituation = latestEvent
    && timeMs - latestEvent.video_time_ms <= situationVisibleFor
    ? latestEvent
    : null
  const lastEventByPlayer = useMemo(() => {
    const result = new Map()
    for (const event of events) if (event.player_id) result.set(event.player_id, event)
    return result
  }, [events])

  useEffect(() => {
    framesRef.current = prepared
  }, [prepared])

  useEffect(() => {
    animationRef.current = { timeMs, wall: performance.now(), playing, speed }
  }, [playing, speed, timeMs])

  useEffect(() => {
    reducedMotion.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const pitch = pitchRef.current
    if (!pitch) return undefined
    const updateBounds = () => {
      const bounds = pitch.getBoundingClientRect()
      boundsRef.current = { width: bounds.width, height: bounds.height }
    }
    updateBounds()
    const observer = new ResizeObserver(updateBounds)
    observer.observe(pitch)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let animationId = 0
    const draw = (now) => {
      const anchor = animationRef.current
      const displayTime = anchor.playing
        ? anchor.timeMs + (now - anchor.wall) * anchor.speed
        : anchor.timeMs
      const [left, right, rawProgress] = framePair(framesRef.current, displayTime)
      const progress = reducedMotion.current ? 0 : rawProgress
      if (left && right) {
        const { width, height } = boundsRef.current
        for (const player of players) {
          const point = between(left.players.get(player.player_id), right.players.get(player.player_id), progress)
          const node = playerNodes.current.get(player.player_id)
          if (!point || !node) continue
          const x = toPitchPct(point.x_m / pitchLengthM * 100) / 100 * width
          const y = toPitchPct(point.y_m / pitchWidthM * 100) / 100 * height
          node.style.left = '0'
          node.style.top = '0'
          node.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`
          node.dataset.positioned = 'true'
        }
        const ball = between(left.ball, right.ball, progress)
        if (ball && ballRef.current) {
          const x = toPitchPct(ball.x_m / pitchLengthM * 100) / 100 * width
          const y = toPitchPct(ball.y_m / pitchWidthM * 100) / 100 * height
          ballRef.current.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`
          ballRef.current.dataset.positioned = 'true'
        }
      }
      animationId = requestAnimationFrame(draw)
    }
    animationId = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(animationId)
  }, [pitchLengthM, pitchWidthM, players])

  const byTeam = new Map()
  for (const player of players) {
    if (!byTeam.has(player.team_id)) byTeam.set(player.team_id, [])
    byTeam.get(player.team_id).push(player)
  }

  return (
    <div aria-label={label} className={`pitch live-tracking-pitch ${playing ? 'is-playing' : ''}`} ref={pitchRef}>
      <div className="pitch-lines">
        <span className="half-line" />
        <span className="center-circle" />
        <span className="box box-left" />
        <span className="box box-right" />
      </div>
      <svg className="pass-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {recentEvents.filter((event) => event.start && event.end).map((event) => (
          <path key={event.event_id} d={`M${toPitchPct(event.start.x)} ${toPitchPct(event.start.y)} L${toPitchPct(event.end.x)} ${toPitchPct(event.end.y)}`} />
        ))}
      </svg>
      <span aria-busy={loading || undefined} className="tracking-source">{loading ? <><Spinner size="small" /> {sourceLabel}</> : sourceLabel}</span>
      {activeSituation && (
        <span className={`live-situation situation-${activeSituation.type}`} role="status">
          {situationLabels?.[activeSituation.situation]
            ?? eventTypeLabels?.[activeSituation.type]
            ?? activeSituation.type}
        </span>
      )}
      {players.map((player) => {
        const teamPlayers = byTeam.get(player.team_id) ?? []
        const index = teamPlayers.findIndex((candidate) => candidate.player_id === player.player_id)
        const fallback = FALLBACK_433[index % FALLBACK_433.length]
        const home = player.team_id === homeTeamId
        const focused = selectedPlayerId === player.player_id
        return (
          <button
            aria-label={player.name}
            aria-pressed={focused}
            className={`live-player-dot ${home ? 'home' : 'away'} ${focused ? 'focused' : ''} ${selectedPlayerId && !focused ? 'dimmed' : ''}`}
            key={player.player_id}
            onClick={() => onSelectPlayer?.(player, lastEventByPlayer.get(player.player_id) ?? null)}
            ref={(node) => {
              if (node) playerNodes.current.set(player.player_id, node)
              else playerNodes.current.delete(player.player_id)
            }}
            style={{ left: `${toPitchPct(home ? fallback[0] : 100 - fallback[0])}%`, top: `${toPitchPct(fallback[1])}%` }}
            type="button"
          >
            <span>{player.shirt_number ?? ''}</span>
            {focused && <small>{player.name}</small>}
          </button>
        )
      })}
      <span aria-label="Balón" className="live-pitch-ball" ref={ballRef} role="img">
        <Icon name="ball" size={15} />
      </span>
    </div>
  )
}
