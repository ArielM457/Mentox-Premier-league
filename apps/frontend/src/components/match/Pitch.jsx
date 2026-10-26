import { Icon } from '../ui/Icon.jsx'

// Las coordenadas de la API van de 0 a 100; las líneas del campo ocupan el 90 % central.
const toPct = (value) => 5 + value * 0.9

const FORMATION = [
  [12, 50], [27, 22], [27, 50], [27, 78], [48, 28], [48, 62], [68, 42], [78, 70],
]

function positionFor(player, index, teamPlayers, homeTeamId, events, timeMs) {
  const lastEvent = [...events].reverse().find((event) => event.player_id === player.player_id && event.start)
  if (lastEvent) {
    const duration = Math.min(1_000, Math.max(350, (lastEvent.end ? 900 : 500)))
    const progress = Math.max(0, Math.min(1, (timeMs - lastEvent.video_time_ms) / duration))
    const target = lastEvent.end ?? lastEvent.start
    const point = {
      x: lastEvent.start.x + (target.x - lastEvent.start.x) * progress,
      y: lastEvent.start.y + (target.y - lastEvent.start.y) * progress,
    }
    return { x: point.x, y: point.y, event: lastEvent }
  }
  const teamIndex = teamPlayers.findIndex((candidate) => candidate.player_id === player.player_id)
  const base = FORMATION[teamIndex % FORMATION.length]
  const home = player.team_id === homeTeamId
  const phase = (timeMs / 1_500) + index * 0.8
  const driftX = Math.sin(phase) * 1.8
  const driftY = Math.cos(phase * 0.75) * 2.4
  return {
    x: Math.max(3, Math.min(97, (home ? base[0] : 100 - base[0]) + driftX)),
    y: Math.max(4, Math.min(96, base[1] + driftY)),
    event: null,
  }
}

// Dibuja las últimas acciones ocurridas con sus posiciones reales.
export function Pitch({ events, homeTeamId, players, trail = 6, playing = false, highlightIds, onSelectPlayer, label, selectedPlayerId = null, timeMs = 0 }) {
  const shown = events.slice(-trail)
  const last = shown[shown.length - 1]
  const ballAt = last?.start ? (() => {
    const target = last.end ?? last.start
    const progress = Math.max(0, Math.min(1, (timeMs - last.video_time_ms) / 900))
    return {
      x: last.start.x + (target.x - last.start.x) * progress,
      y: last.start.y + (target.y - last.start.y) * progress,
    }
  })() : null
  const playerById = new Map(players.map((p) => [p.player_id, p]))
  const isHighlighted = (event) => (highlightIds ? highlightIds.includes(event.event_id) : event === last)
  const byTeam = new Map()
  for (const player of players) {
    if (!byTeam.has(player.team_id)) byTeam.set(player.team_id, [])
    byTeam.get(player.team_id).push(player)
  }

  return (
    <div className={`pitch ${playing ? 'is-playing' : ''}`} role={onSelectPlayer ? "group" : "img"} aria-label={label}>
      <div className="pitch-lines">
        <span className="half-line" />
        <span className="center-circle" />
        <span className="box box-left" />
        <span className="box box-right" />
      </div>
      <svg className="pass-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {shown.filter((e) => e.start && e.end).map((e) => (
          <path key={e.event_id} d={`M${toPct(e.start.x)} ${toPct(e.start.y)} L${toPct(e.end.x)} ${toPct(e.end.y)}`} />
        ))}
      </svg>
      {players.map((player, index) => {
        const home = player.team_id === homeTeamId
        const position = positionFor(player, index, byTeam.get(player.team_id) ?? [], homeTeamId, shown, timeMs)
        const focused = selectedPlayerId === player.player_id
        const involved = position.event && isHighlighted(position.event)
        const Tag = onSelectPlayer ? 'button' : 'span'
        return (
          <Tag
            aria-label={onSelectPlayer ? player.name : undefined}
            aria-pressed={onSelectPlayer ? focused : undefined}
            className={`player-dot ${home ? 'home' : 'away'} ${involved ? 'involved' : ''} ${focused ? 'focused' : ''} ${selectedPlayerId && !focused ? 'dimmed' : ''}`}
            key={player.player_id}
            onClick={() => onSelectPlayer?.(player, position.event)}
            style={{ '--x': `${toPct(position.x)}%`, '--y': `${toPct(position.y)}%`, '--delay': `${(index % 5) * 0.08}s` }}
            type={onSelectPlayer ? "button" : undefined}
          >
            <span>{player.shirt_number ?? ''}</span>
            {focused && <small>{player.name}</small>}
          </Tag>
        )
      })}
      {ballAt && (
        <span className="pitch-ball" style={{ left: `${toPct(ballAt.x)}%`, top: `${toPct(ballAt.y)}%` }}>
          <Icon name="ball" size={15} />
        </span>
      )}
      {last?.player_id && ballAt && (
        <span className="player-label" style={{ left: `${Math.min(80, toPct(ballAt.x))}%`, top: `${Math.min(88, toPct(ballAt.y) + 6)}%` }}>
          {playerById.get(last.player_id)?.name}
        </span>
      )}
    </div>
  )
}
