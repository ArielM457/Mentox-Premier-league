import { usePreferences } from '../../app/preferences.js'
import { formatMatchClock } from '../../lib/overlays.js'
import { Icon } from '../ui/Icon.jsx'

const METRICS = ['goals', 'shots', 'passes_attempted', 'pass_accuracy', 'recoveries', 'pressures']

function metricValue(snapshot, key, teamId) {
  const metric = snapshot?.metrics.find((m) => m.key === key && m.team_id === teamId)
  if (!metric || !metric.available || metric.value == null) return null
  return metric.value
}

// Estadísticas del MatchSnapshot v1. Una métrica sin datos se muestra como tal, nunca como cero.
export function StatsPanel({ snapshot, metadata, timeMs = 0 }) {
  const { t } = usePreferences()
  const home = metadata.home_team
  const away = metadata.away_team
  const possession = [home, away].find((team) => team.team_id === snapshot?.possession_team_id)
  return (
    <div className="stats-panel">
      <div className="stats-heading"><h2>{t.match.statsTitle}</h2><span><i /> {t.match.statsUpdated(formatMatchClock({ clock_ms: timeMs, period: snapshot?.period ?? 1 }, t.match.period))}</span></div>
      <div className="stat-teams">
        <strong>{home.name}</strong>
        <strong>{away.name}</strong>
      </div>
      {METRICS.map((key) => {
        const a = metricValue(snapshot, key, home.team_id)
        const b = metricValue(snapshot, key, away.team_id)
        const percent = key === 'pass_accuracy'
        const share = percent ? a ?? 0 : a == null && b == null ? 50 : ((a ?? 0) / Math.max(1, (a ?? 0) + (b ?? 0))) * 100
        const show = (v) => (v == null ? t.match.noData : percent ? `${v}%` : v)
        return (
          <div className="stat-row" key={key}>
            <b>{show(a)}</b>
            <div>
              <span>{t.match.metrics[key]}</span>
              <i className="stat-balance" style={{ '--home-share': `${share}%` }}>
                <em />
                <b />
              </i>
            </div>
            <b>{show(b)}</b>
          </div>
        )
      })}
      <p className="stat-footnote">{t.match.possession}: {possession?.name ?? t.match.noData}</p>
    </div>
  )
}

// Momentos ya mostrados, del más reciente al más antiguo.
export function MomentFeed({ items, onOpen, detailed = false }) {
  const { t } = usePreferences()
  if (!items.length) {
    return (
      <div className="event-feed">
        <p className="feed-empty">{t.match.noMoments}</p>
      </div>
    )
  }
  return (
    <div className="event-feed">
      {items.map((m) => (
        <button key={m.message_id} onClick={() => onOpen(m)} type="button">
          <span>{formatMatchClock(m, t.match.period)}</span>
          <div>
            <strong>
              {t.kinds[m.kind] ?? m.kind} · {m.headline}
            </strong>
            {detailed && m.explanation && <small>{m.explanation}</small>}
            <span className="feed-badges">
              <i>{m.priority}</i>
              {m.suppressed && <i className="muted">{m.language === 'es' ? 'en cola' : 'queued'}</i>}
              {m.replaces_message_id && <i className="muted">↺</i>}
              {m.corrected && <i className="warn">✓</i>}
            </span>
          </div>
          <Icon name="arrow" />
        </button>
      ))}
    </div>
  )
}

export function LatencyPanel({ samples }) {
  const { t } = usePreferences()
  const summary = (key) => {
    const values = samples.map((s) => s[key])
    return { avg: Math.round(values.reduce((a, b) => a + b, 0) / values.length), max: Math.round(Math.max(...values)) }
  }
  return (
    <div className="latency-card">
      <h3>{t.match.latency}</h3>
      {!samples.length ? (
        <p>{t.match.latencyEmpty}</p>
      ) : (
        <dl>
          {[['transportMs', t.match.transport], ['pipelineMs', t.match.pipeline], ['leadMs', t.match.lead]].map(([key, label]) => {
            const s = summary(key)
            return (
              <div key={key}>
                <dt>{label}</dt>
                <dd>
                  {s.avg} ms <small>{t.match.avg} · {s.max} ms {t.match.max}</small>
                </dd>
              </div>
            )
          })}
        </dl>
      )}
    </div>
  )
}
