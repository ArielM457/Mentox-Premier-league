import { usePreferences } from '../../app/preferences.js'
import { formatMatchClock } from '../../lib/overlays.js'

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
      <div className="stats-heading"><h2>{t.match.statsTitle}</h2><span><i /> {t.match.statsUpdated(formatMatchClock(snapshot ?? { clock_ms: timeMs, period: 1 }, t.match.period))}</span></div>
      <div className="stat-teams">
        <strong>{home.name}</strong>
        <strong>{away.name}</strong>
      </div>
      {METRICS.map((key) => {
        const a = metricValue(snapshot, key, home.team_id)
        const b = metricValue(snapshot, key, away.team_id)
        const percent = key === 'pass_accuracy'
        const share = percent ? a ?? 0 : a == null && b == null ? 50 : ((a ?? 0) / Math.max(1, (a ?? 0) + (b ?? 0))) * 100
        const show = (v) => (v == null ? t.match.noData : `${t.common.number(v)}${percent ? '%' : ''}`)
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
