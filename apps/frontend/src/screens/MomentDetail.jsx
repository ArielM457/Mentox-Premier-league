import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { formatClock, formatMatchClock, momentIdOf } from '../lib/overlays.js'
import { Pitch } from '../components/match/Pitch.jsx'
import { Brand } from '../components/ui/Brand.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

const STEP_MS = 900

export function MomentDetail({ matchId, momentId }) {
  const { t, apiPreferences } = usePreferences()
  const { data: catalog } = useCatalog()
  const match = catalog?.matches.find((m) => m.id === matchId)
  const [overlay, setOverlay] = useState(null)
  const [sources, setSources] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('explanation')
  // Se guarda aquí porque un mensaje corregido vuelve a montar el contenido.
  const [lastReport, setLastReport] = useState(null)

  // Se busca el momento con las preferencias actuales: si cambias de idioma, cambia el texto.
  const load = useCallback(async () => {
    if (!match) return
    try {
      const batch = await api.overlays(matchId, apiPreferences, match.durationMs)
      const found = batch.overlays.find((o) => momentIdOf(o) === momentId)
      if (!found) {
        setError(t.moment.notFound)
        return
      }
      setOverlay(found)
      setSources(await api.sources(matchId, found.draft_id))
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [apiPreferences, match, matchId, momentId, t.moment.notFound])

  useEffect(() => {
    load()
  }, [load])

  const back = () => navigate(paths.match(matchId))

  return (
    <main className="detail-page">
      <header className="detail-header">
        <Button variant="ghost" onClick={back}>
          <Icon name="back" /> {t.moment.back}
        </Button>
        <Brand light />
        <span className="share-label">{t.common.syntheticData}</span>
      </header>
      <ErrorNotice message={error} onRetry={error === t.moment.notFound ? back : load} retryLabel={error === t.moment.notFound ? t.moment.back : t.common.retry} />
      {overlay && sources && match && (
        <MomentContent key={overlay.draft_id} lastReport={lastReport} match={match} overlay={overlay} sources={sources} tab={tab} setTab={setTab} onReported={(report) => { setLastReport(report); if (report.outcome === 'withdrawn') load() }} />
      )}
    </main>
  )
}

function MomentContent({ match, overlay, sources, tab, setTab, lastReport, onReported }) {
  const { t } = usePreferences()
  const events = sources.events
  const metadata = match.metadata
  const [step, setStep] = useState(events.length)
  const playing = step < events.length

  useEffect(() => {
    if (!playing) return undefined
    const id = setTimeout(() => setStep((s) => s + 1), STEP_MS)
    return () => clearTimeout(id)
  }, [playing, step])

  const playerName = (id) => metadata.players.find((p) => p.player_id === id)?.name ?? id ?? '—'
  const involved = [...new Map(events.filter((e) => e.player_id).map((e) => [e.player_id, e])).values()]
  const authorEvent = events.slice().reverse().find((event) => event.player_id)
  const author = playerName(authorEvent?.player_id)
  const team = authorEvent?.team_id === metadata.home_team.team_id ? metadata.home_team.name : authorEvent?.team_id === metadata.away_team.team_id ? metadata.away_team.name : '—'
  const span = events.length > 1 ? (events[events.length - 1].clock_ms - events[0].clock_ms) / 1000 : 0
  const passes = events.filter((e) => e.type === 'pass').length
  const explanation = sources.draft.explanation || overlay.explanation || overlay.headline
  const conciseExplanation = explanation.length > 260 ? `${explanation.slice(0, 257)}…` : explanation

  return (
    <div className="detail-grid">
      <section className="detail-main">
        <span className="moment-pill">
          <Icon name="spark" size={16} /> {t.moment.pill(formatMatchClock(overlay, t.match.period))} · {t.kinds[overlay.kind] ?? overlay.kind}
        </span>
        <h1>{overlay.headline}</h1>
        <p>{conciseExplanation}</p>
        <div className="moment-context">
          <span><small>{t.moment.author}</small><strong>{author}</strong></span>
          <span><small>{t.moment.situation}</small><strong>{t.kinds[overlay.kind] ?? overlay.kind}</strong></span>
          <span><small>{t.moment.team}</small><strong>{team}</strong></span>
          <span><small>{t.moment.minute}</small><strong>{formatMatchClock(overlay, t.match.period)}</strong></span>
        </div>
        <div className="detail-pitch">
          <Pitch
            events={events.slice(0, Math.max(1, step))}
            highlightIds={events.slice(0, Math.max(1, step)).map((e) => e.event_id)}
            homeTeamId={metadata.home_team.team_id}
            label={overlay.headline}
            players={metadata.players}
            playing={playing}
            trail={events.length || 1}
          />
        </div>
        <div className="video-controls">
          <Button aria-label={playing ? t.match.pause : t.match.play} className="play-main" onClick={() => setStep(playing ? events.length : 1)}>
            {playing ? <Icon name="pause" /> : <Icon name="play" />}
          </Button>
          <div>
            <span style={{ width: `${(Math.min(step, events.length) / Math.max(1, events.length)) * 100}%` }} />
          </div>
          <small>{Math.min(step, events.length)} / {events.length}</small>
          <Button variant="ghost" onClick={() => setStep(1)}>
            <Icon name="replay" /> {t.match.replay}
          </Button>
        </div>
      </section>

      <aside className="detail-insight">
        <nav role="tablist">
          {Object.entries(t.moment.tabs).map(([key, label]) => (
            <button aria-selected={tab === key} className={tab === key ? 'active' : ''} key={key} onClick={() => setTab(key)} role="tab" type="button">
              {label}
            </button>
          ))}
        </nav>

        {tab === 'explanation' && (
          <div className="tab-copy">
            <span className="big-spark">
              <Icon name="spark" size={26} />
            </span>
            <h2>{t.moment.why}</h2>
            <p>{conciseExplanation}</p>
            <div className="takeaway">
              <strong>{t.moment.takeaway}</strong>
              <span>{t.moment.takeawayCopy(events.length)}</span>
            </div>
            {sources.draft.applied_preferences.length > 0 && (
              <p className="applied-preferences">
                {t.moment.applied}: {sources.draft.applied_preferences.join(' · ')}
              </p>
            )}
          </div>
        )}

        {tab === 'stats' && (
          <div className="moment-stats">
            <h2>{t.moment.numbers}</h2>
            <div>
              <strong>{span.toFixed(1)} s</strong>
              <span>{t.moment.duration}</span>
            </div>
            <div>
              <strong>{events.length}</strong>
              <span>{t.moment.events}</span>
            </div>
            <div>
              <strong>{involved.length}</strong>
              <span>{t.moment.playersInvolved}</span>
            </div>
            <div>
              <strong>{passes}</strong>
              <span>{t.moment.passes}</span>
            </div>
            <table className="source-table">
              <caption>{t.moment.sourceEvents}</caption>
              <tbody>
                {events.map((e) => (
                  <tr key={e.event_id}>
                    <td><code>{e.event_id}</code></td>
                    <td>{formatClock(e.clock_ms)}</td>
                    <td>{t.moment.eventTypes[e.type] ?? e.type}</td>
                    <td>{playerName(e.player_id)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'players' && (
          <div className="player-list">
            <h2>{t.moment.involved}</h2>
            {involved.map((e, index) => (
              <div key={e.player_id}>
                <span>{index + 1}</span>
                <div>
                  <strong>{playerName(e.player_id)}</strong>
                  <small>{events.filter((x) => x.player_id === e.player_id).map((x) => t.moment.eventTypes[x.type] ?? x.type).join(' · ')}</small>
                </div>
              </div>
            ))}
          </div>
        )}

        <ReportForm lastReport={lastReport} matchId={match.id} overlay={overlay} onReported={onReported} />
      </aside>
    </div>
  )
}

// Reporte de error y resultado de la verificación (RF-39).
function ReportForm({ matchId, overlay, lastReport, onReported }) {
  const { t } = usePreferences()
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const report = await api.report(matchId, overlay.draft_id, overlay.message_id, reason)
      setReason('')
      onReported(report)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="report-form" onSubmit={submit}>
      <label htmlFor="report-reason">
        <Icon name="flag" size={15} /> {t.moment.report}
      </label>
      <textarea id="report-reason" maxLength={500} onChange={(event) => setReason(event.target.value)} placeholder={t.moment.reportReason} required rows={2} value={reason} />
      <Button variant="secondary" disabled={busy || !reason.trim()} type="submit">
        {t.moment.sendReport}
      </Button>
      {error && <p className="report-error" role="alert">{error}</p>}
      {lastReport && (
        <div className={`report-result ${lastReport.outcome}`} role="status">
          <strong>{lastReport.outcome === 'withdrawn' ? t.moment.withdrawn : t.moment.confirmed}</strong>
          {lastReport.issues.map((issue) => <small key={issue}>{issue}</small>)}
          {lastReport.corrected_draft && <span>{lastReport.corrected_draft.headline}</span>}
        </div>
      )}
    </form>
  )
}
