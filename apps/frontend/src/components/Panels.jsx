import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { formatClock } from '../lib/overlays.js'

export function PreferencesPanel({ t, prefs, onChange, metadata }) {
  const set = (key) => (e) => onChange({ ...prefs, [key]: e.target.value })
  const teams = [metadata.home_team, metadata.away_team]
  const needsPlayer = prefs.mode === 'player' && !prefs.favoritePlayerId
  return (
    <section className="panel" aria-labelledby="prefs-title">
      <h2 id="prefs-title">{t.preferences}</h2>
      <div className="field-grid">
        <label>
          <span>{t.language}</span>
          <select value={prefs.language} onChange={set('language')}>
            <option value="es">Español</option>
            <option value="en">English</option>
          </select>
        </label>
        <label>
          <span>{t.mode}</span>
          <select value={prefs.mode} onChange={set('mode')}>
            {Object.entries(t.modes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label>
          <span>{t.level}</span>
          <select value={prefs.level} onChange={set('level')}>
            {Object.entries(t.levels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label>
          <span>{t.favoriteTeam}</span>
          <select value={prefs.favoriteTeamId} onChange={set('favoriteTeamId')}>
            <option value="">{t.none}</option>
            {teams.map((team) => <option key={team.team_id} value={team.team_id}>{team.name}</option>)}
          </select>
        </label>
        <label>
          <span>{t.favoritePlayer}</span>
          <select value={prefs.favoritePlayerId} onChange={set('favoritePlayerId')} aria-invalid={needsPlayer}>
            <option value="">{t.none}</option>
            {teams.map((team) => (
              <optgroup key={team.team_id} label={team.name}>
                {metadata.players.filter((p) => p.team_id === team.team_id).map((p) => (
                  <option key={p.player_id} value={p.player_id}>{p.shirt_number ? `${p.shirt_number} · ` : ''}{p.name}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
      </div>
      {needsPlayer && <p className="warning" role="alert">{t.playerModeNeedsPlayer}</p>}
    </section>
  )
}

const MAIN_METRICS = ['goals', 'shots', 'passes_attempted', 'pass_accuracy', 'recoveries', 'pressures']

export function StatsPanel({ t, snapshot, metadata }) {
  const teams = [metadata.home_team, metadata.away_team]
  const value = (key, teamId) => {
    const metric = snapshot?.metrics.find((m) => m.key === key && m.team_id === teamId)
    if (!metric || !metric.available || metric.value == null) return <span className="muted">{t.noData}</span>
    return metric.unit === 'percent' ? `${metric.value}%` : metric.value
  }
  const possession = teams.find((team) => team.team_id === snapshot?.possession_team_id)
  return (
    <section className="panel" aria-labelledby="stats-title">
      <h2 id="stats-title">{t.stats}</h2>
      <table className="stats">
        <thead>
          <tr><th scope="col"><span className="sr-label">{t.stats}</span></th>{teams.map((team) => <th key={team.team_id} scope="col">{team.name}</th>)}</tr>
        </thead>
        <tbody>
          {MAIN_METRICS.map((key) => (
            <tr key={key}>
              <th scope="row">{t.metrics[key]}</th>
              {teams.map((team) => <td key={team.team_id}>{value(key, team.team_id)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted">{t.possession}: {possession?.name ?? t.noData}</p>
    </section>
  )
}

export function HistoryPanel({ t, items, onOpen }) {
  return (
    <section className="panel" aria-labelledby="history-title">
      <h2 id="history-title">{t.history}</h2>
      {items.length === 0 ? (
        <p className="muted">{t.historyEmpty}</p>
      ) : (
        <ol className="history">
          {items.map((m) => (
            <li key={m.message_id}>
              <button type="button" className="history-item" onClick={() => onOpen(m)}>
                <span className="history-time">{formatClock(m.clock_ms)}</span>
                <span className="history-text">{m.headline}</span>
                <span className="badges">
                  <span className={`badge kind-${m.kind}`}>{m.kind}</span>
                  <span className="badge">{m.priority}</span>
                  {m.suppressed && <span className="badge muted-badge">{t.suppressed}</span>}
                  {m.replaces_message_id && <span className="badge muted-badge">↺ {t.replaced}</span>}
                  {m.corrected && <span className="badge warn-badge">{t.corrected}</span>}
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export function MomentDialog({ t, matchId, overlay, metadata, onClose, onReported }) {
  const dialog = useRef(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [reason, setReason] = useState('')
  const [report, setReport] = useState(null)
  const [sending, setSending] = useState(false)

  useEffect(() => {
    dialog.current?.showModal()
    let active = true
    api.sources(matchId, overlay.draft_id)
      .then((d) => active && setData(d))
      .catch((e) => active && setError(e.message))
    return () => { active = false }
  }, [matchId, overlay.draft_id])

  const name = (id) => metadata.players.find((p) => p.player_id === id)?.name ?? id ?? '—'

  async function sendReport(e) {
    e.preventDefault()
    setSending(true)
    try {
      const result = await api.report(matchId, overlay.draft_id, overlay.message_id, reason)
      setReport(result)
      onReported()
    } catch (err) {
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <dialog ref={dialog} className="dialog" onClose={onClose} aria-labelledby="moment-title">
      <header className="dialog-header">
        <h2 id="moment-title">{t.detail}</h2>
        <button type="button" className="ghost" onClick={() => dialog.current?.close()}>{t.close}</button>
      </header>
      <p className="dialog-headline">{overlay.headline}</p>
      <p>{data?.draft.explanation ?? overlay.explanation}</p>
      {error && <p className="error" role="alert">{error}</p>}
      <h3>{t.sourceEvents}</h3>
      {overlay.source_event_ids.length === 0 ? (
        <p className="muted">{t.noSources}</p>
      ) : !data ? (
        <p className="muted">{t.loading}</p>
      ) : (
        <div className="table-scroll">
          <table className="events-table">
            <thead><tr><th>ID</th><th>{t.eventTime}</th><th>{t.eventType}</th><th>{t.eventPlayer}</th><th>{t.eventOutcome}</th></tr></thead>
            <tbody>
              {data.events.map((e) => (
                <tr key={e.event_id}>
                  <td><code>{e.event_id}</code></td>
                  <td>{formatClock(e.clock_ms)}</td>
                  <td>{e.type}</td>
                  <td>{name(e.player_id)}</td>
                  <td>{e.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data?.draft.applied_preferences?.length > 0 && (
        <p className="muted small">{data.draft.applied_preferences.join(' · ')}</p>
      )}

      <form className="report-form" onSubmit={sendReport}>
        <label htmlFor="report-reason">{t.reportReason}</label>
        <textarea id="report-reason" rows="2" value={reason} onChange={(e) => setReason(e.target.value)} required maxLength={500} />
        <button type="submit" disabled={sending || !reason.trim()}>{t.sendReport}</button>
      </form>
      {report && (
        <div className={`report-result ${report.outcome}`} role="status">
          <p>{report.outcome === 'withdrawn' ? t.reportWithdrawn : t.reportConfirmed}</p>
          {report.issues.map((issue) => <p key={issue} className="small">{issue}</p>)}
          {report.corrected_draft && <p><strong>{report.corrected_draft.headline}</strong></p>}
        </div>
      )}
    </dialog>
  )
}

export function QuestionPanel({ t, matchId, prefs, time, metadata }) {
  const [question, setQuestion] = useState('')
  const [answers, setAnswers] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const players = metadata.players

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const result = await api.ask(matchId, question, time, prefs)
      setAnswers((current) => [{ question, ...result.answer, at: time }, ...current].slice(0, 6))
      setQuestion('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" aria-labelledby="questions-title">
      <h2 id="questions-title">{t.questions}</h2>
      <form className="inline-form" onSubmit={submit}>
        <label htmlFor="question" className="sr-label">{t.questions}</label>
        <input id="question" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t.questionPlaceholder} maxLength={500} required />
        <button type="submit" disabled={busy || !question.trim()}>{busy ? t.asking : t.ask}</button>
      </form>
      <p className="muted small">{players.slice(0, 3).map((p) => p.name).join(', ')}…</p>
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="answers" aria-live="polite">
        {answers.map((a) => (
          <li key={a.draft_id + a.at}>
            <p className="muted small">{formatClock(a.at)} · {a.question}</p>
            <p className="answer-headline">{a.headline}</p>
            <p className="small">{a.explanation}</p>
            <p className="muted small">{t.sources}: {a.source_event_ids.length ? a.source_event_ids.join(', ') : t.noSources}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function SummaryPanel({ t, matchId, prefs, finished, onCreated }) {
  const [record, setRecord] = useState(null)
  const [published, setPublished] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  async function generate() {
    setBusy(true)
    setError(null)
    try {
      const result = await api.summary(matchId, prefs)
      setRecord(result)
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function checkPublication() {
    setError(null)
    try {
      setPublished(await api.published(matchId, record.draft.draft_id))
    } catch (err) {
      setPublished(null)
      setError(err.status === 409 ? `${t.publishBlocked} (${err.message})` : err.message)
    }
    // El estado editorial puede haber cambiado desde el panel de revisión.
    api.summary(matchId, prefs).then(setRecord).catch(() => {})
  }

  return (
    <section className="panel" aria-labelledby="summary-title">
      <h2 id="summary-title">{t.summary}</h2>
      {!finished && <p className="muted">{t.summaryWait}</p>}
      <div className="button-row">
        <button type="button" onClick={generate} disabled={!finished || busy}>{t.generateSummary}</button>
        {record && <button type="button" className="ghost" onClick={checkPublication}>{t.publish}</button>}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {record && (
        <article className="summary">
          <span className={`badge status-${record.status}`}>{t.status[record.status]}</span>
          <h3>{record.draft.headline}</h3>
          <p>{record.draft.explanation}</p>
        </article>
      )}
      {published && <p className="success" role="status">✓ {published.headline}</p>}
    </section>
  )
}

export function EditorialPanel({ t, matchId, refreshKey, onChanged }) {
  const [queue, setQueue] = useState([])
  const [reports, setReports] = useState([])
  const [reviewer, setReviewer] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    Promise.all([api.editorial(matchId), api.reports(matchId)])
      .then(([q, r]) => {
        if (!active) return
        setQueue(q)
        setReports(r)
      })
      .catch((e) => active && setError(e.message))
    return () => { active = false }
  }, [matchId, refreshKey])

  async function decide(draftId, decision) {
    setError(null)
    try {
      await api.review(matchId, draftId, decision, reviewer, note)
      setNote('')
      onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section className="panel" aria-labelledby="editorial-title">
      <h2 id="editorial-title">{t.editorial}</h2>
      <div className="field-grid two">
        <label><span>{t.reviewer}</span><input value={reviewer} onChange={(e) => setReviewer(e.target.value)} maxLength={80} /></label>
        <label><span>{t.note}</span><input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} /></label>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {queue.length === 0 ? (
        <p className="muted">{t.editorialEmpty}</p>
      ) : (
        <ul className="review-list">
          {queue.map((r) => (
            <li key={r.draft.draft_id}>
              <div>
                <span className={`badge status-${r.status}`}>{t.status[r.status]}</span>
                <p className="answer-headline">{r.draft.headline}</p>
                <p className="small">{r.draft.explanation}</p>
                <p className="muted small">{r.draft.language} · {r.draft.applied_preferences.join(' · ')}</p>
                {r.reviewer && <p className="muted small">{r.reviewer}{r.note ? ` — ${r.note}` : ''}</p>}
              </div>
              {r.status === 'pending' && (
                <div className="button-row">
                  <button type="button" disabled={!reviewer.trim()} onClick={() => decide(r.draft.draft_id, 'approve')}>{t.approve}</button>
                  <button type="button" className="danger" disabled={!reviewer.trim()} onClick={() => decide(r.draft.draft_id, 'reject')}>{t.reject}</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <h3>{t.reports}</h3>
      {reports.length === 0 ? (
        <p className="muted">{t.reportsEmpty}</p>
      ) : (
        <ul className="review-list">
          {reports.map((r) => (
            <li key={r.report_id}>
              <div>
                <span className={`badge report-${r.outcome}`}>{r.outcome}</span>
                <p className="small"><code>{r.draft_id}</code> — {r.reason}</p>
                {r.issues.map((issue) => <p key={issue} className="muted small">{issue}</p>)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function LatencyPanel({ t, samples }) {
  const stats = (key) => {
    if (!samples.length) return null
    const values = samples.map((s) => s[key])
    return { avg: Math.round(values.reduce((a, b) => a + b, 0) / values.length), max: Math.round(Math.max(...values)) }
  }
  const rows = [['transportMs', t.transport], ['pipelineMs', t.pipeline], ['leadMs', t.lead]]
  return (
    <section className="panel" aria-labelledby="latency-title">
      <h2 id="latency-title">{t.latency}</h2>
      {!samples.length ? (
        <p className="muted">{t.latencyEmpty}</p>
      ) : (
        <dl className="latency">
          {rows.map(([key, label]) => {
            const s = stats(key)
            return (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{s.avg} ms <span className="muted small">{t.avg} · {s.max} ms {t.max}</span></dd>
              </div>
            )
          })}
        </dl>
      )}
    </section>
  )
}

export function DemoTools({ t, onReload }) {
  const [inject, setInject] = useState(false)
  return (
    <details className="panel demo-tools">
      <summary>{t.demoTools}</summary>
      <label className="checkbox">
        <input type="checkbox" checked={inject} onChange={(e) => setInject(e.target.checked)} />
        <span>{t.injectError}</span>
      </label>
      <button type="button" className="ghost" onClick={() => onReload(inject ? 'goal' : null)}>{t.reloadMatch}</button>
    </details>
  )
}
