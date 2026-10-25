import { Icon } from '../ui/Icon.jsx'

export function TacticalSimulationPitch({ homePlayers, awayPlayers, frame, previousFrame, homeId, label }) {
  const byId = new Map(frame?.players.map((player) => [player.player_id, player]) ?? [])
  const involvedIds = new Set(frame?.involved_player_ids ?? [])
  const players = [...homePlayers, ...awayPlayers].map((player) => byId.get(player.player_id) ?? player)

  return (
    <div className="preview-pitch" role="img" aria-label={label}>
      <div className="pitch-lines">
        <span className="half-line" />
        <span className="center-circle" />
        <span className="box box-left" />
        <span className="box box-right" />
      </div>
      {frame && previousFrame && (
        <svg className="tactical-pass-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <line x1={previousFrame.ball.x} y1={previousFrame.ball.y} x2={frame.ball.x} y2={frame.ball.y} />
        </svg>
      )}
      {players.map((player) => (
        <span
          className={`preview-player ${player.team_id === homeId ? 'home' : 'away'} ${frame && involvedIds.has(player.player_id) ? 'involved' : ''} ${frame && !involvedIds.has(player.player_id) ? 'supporting' : ''} ${frame?.ball_owner_id === player.player_id ? 'has-ball' : ''}`}
          key={player.player_id}
          style={{ left: `${player.position.x}%`, top: `${player.position.y}%` }}
          title={player.name}
        >
          {player.shirt_number}
          <small>{player.name}</small>
        </span>
      ))}
      {frame && (
        <span className={`preview-ball ${frame.ball_owner_id ? 'controlled' : 'in-flight'}`} style={{ left: `${frame.ball.x}%`, top: `${frame.ball.y}%` }}>
          <Icon name="ball" size={14} />
        </span>
      )}
      {frame && <strong className="simulation-phase">{frame.phase}</strong>}
    </div>
  )
}
