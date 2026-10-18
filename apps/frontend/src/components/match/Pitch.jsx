import { Icon } from '../ui/Icon.jsx'

// Las coordenadas de la API van de 0 a 100; las líneas del campo ocupan el 90 % central.
const toPct = (value) => 5 + value * 0.9

// Dibuja las últimas acciones ocurridas con sus posiciones reales.
export function Pitch({ events, homeTeamId, players, trail = 6, playing = false, highlightIds, onSelectPlayer, label }) {
  const shown = events.slice(-trail)
  const last = shown[shown.length - 1]
  const ballAt = last ? (last.end ?? last.start) : null
  const playerById = new Map(players.map((p) => [p.player_id, p]))
  const isHighlighted = (event) => (highlightIds ? highlightIds.includes(event.event_id) : event === last)

  return (
    <div className={`pitch ${playing ? 'is-playing' : ''}`} role="img" aria-label={label}>
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
      {shown.filter((e) => e.start).map((e, index) => {
        const player = playerById.get(e.player_id)
        const home = e.team_id === homeTeamId
        return (
          <button
            aria-label={player?.name ?? e.team_id}
            className={`player-dot ${home ? 'home' : 'away'} ${isHighlighted(e) ? 'involved' : ''}`}
            key={e.event_id}
            onClick={() => onSelectPlayer?.(player, e)}
            style={{ '--x': `${toPct(e.start.x)}%`, '--y': `${toPct(e.start.y)}%`, '--delay': `${(index % 5) * 0.08}s`, opacity: 0.45 + (0.55 * (index + 1)) / shown.length }}
            type="button"
          >
            <span>{player?.shirt_number ?? ''}</span>
          </button>
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
