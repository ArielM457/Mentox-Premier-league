import { TeamBadge } from '../ui/TeamBadge.jsx'

export function MatchScore({ metadata, score, status, statusLabel, minute }) {
  const home = metadata.home_team
  const away = metadata.away_team
  return (
    <div className="match-score">
      <div className="score-team">
        <TeamBadge team={home} />
        <strong>{home.name}</strong>
      </div>
      <div className="score-center" aria-live="polite">
        <span className={`status status-${status.toLowerCase()}`}>{statusLabel}</span>
        <b>
          {score?.[home.team_id] ?? 0} <em>–</em> {score?.[away.team_id] ?? 0}
        </b>
        <small>{minute}</small>
      </div>
      <div className="score-team away">
        <TeamBadge team={away} />
        <strong>{away.name}</strong>
      </div>
    </div>
  )
}
