import { usePreferences } from '../../app/preferences.js'
import { formatClock } from '../../lib/overlays.js'
import { Icon } from '../ui/Icon.jsx'
import { TeamBadge } from '../ui/TeamBadge.jsx'

// status "LIVE" abre la simulación sin revelar el resultado; "FT" muestra el marcador final.
export function MatchCard({ match, status, favorite, onOpen }) {
  const { t } = usePreferences()
  const { home_team: home, away_team: away } = match.metadata
  const final = status === 'FT'
  return (
    <button className={`match-card ${status === 'LIVE' ? 'match-live' : ''}`} onClick={() => onOpen(match, status)} type="button">
      <div className="match-card-top">
        <span>{t.matches.competition} · {t.matches.scenario[match.id] ?? match.id}</span>
        <span className={`status status-${status.toLowerCase()}`}>{t.matches.status[status]}</span>
      </div>
      {favorite && (
        <span className="favorite-row">
          <span className="favorite-label">{t.matches.favorite}</span>
        </span>
      )}
      <div className="match-card-main">
        <div>
          <TeamBadge team={home} />
          <strong>{home.name}</strong>
        </div>
        <span className="card-score">
          {final ? `${match.finalScore[home.team_id] ?? 0} – ${match.finalScore[away.team_id] ?? 0}` : '0 – 0'}
          <small>{final ? t.matches.final : `${t.matches.replay} · ${formatClock(match.durationMs)}`}</small>
        </span>
        <div>
          <TeamBadge team={away} />
          <strong>{away.name}</strong>
        </div>
      </div>
      <span className="explore-label">
        {final ? t.matches.recap : t.matches.open} <Icon name="arrow" size={16} />
      </span>
    </button>
  )
}
