import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { describePreferences, usePreferences } from '../app/preferences.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

// Revisión editorial (RF-38) y reportes de error (RF-39).
export function Editorial() {
  const { t } = usePreferences()
  const { data: catalog, error: catalogError, reload } = useCatalog()
  const copy = t.editorial
  const [matchId, setMatchId] = useState('')
  const [queue, setQueue] = useState([])
  const [reports, setReports] = useState([])
  const [reviewer, setReviewer] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [inject, setInject] = useState(false)
  const selected = matchId || catalog?.matches[0]?.id || ''
  const selectedMatch = catalog?.matches.find((m) => m.id === selected)

  const refresh = useCallback(async () => {
    if (!selected) return
    try {
      const [q, r] = await Promise.all([api.editorial(selected), api.reports(selected)])
      setQueue(q)
      setReports(r)
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [selected])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function decide(draftId, decision) {
    try {
      await api.review(selected, draftId, decision, reviewer, note)
      setNote('')
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  async function reloadMatch() {
    try {
      const scenario = selected === 'synthetic-analytics-001' ? 'analytics' : 'acceptance'
      await api.loadMatch({ scenario, match_id: selected, inject_error_in: inject ? 'goal' : null })
      setNotice(copy.reloaded)
      await reload()
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <AppShell active="editorial">
      <section className="profile-content editorial-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>
        </header>
        <ErrorNotice message={(catalogError && t.common.apiDown) || error} onRetry={catalogError ? reload : refresh} retryLabel={t.common.retry} />

        <div className="profile-card">
          <div className="editorial-fields">
            <label>
              <span>{copy.match}</span>
              <select onChange={(event) => setMatchId(event.target.value)} value={selected}>
                {catalog?.matches.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.metadata.home_team.name} – {m.metadata.away_team.name} · {t.matches.scenario[m.id] ?? m.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{copy.reviewer}</span>
              <input maxLength={80} onChange={(event) => setReviewer(event.target.value)} value={reviewer} />
            </label>
            <label>
              <span>{copy.note}</span>
              <input maxLength={500} onChange={(event) => setNote(event.target.value)} value={note} />
            </label>
          </div>

          <div className="preference-block">
            <h3>{copy.queue}</h3>
            {queue.length === 0 ? (
              <p className="muted-copy">{copy.empty}</p>
            ) : (
              <ul className="review-list">
                {queue.map((record) => (
                  <li key={record.draft.draft_id}>
                    <div>
                      <span className={`editorial-status status-${record.status}`}>{t.recap.status[record.status]}</span>
                      <strong>{record.draft.headline}</strong>
                      <p>{record.draft.explanation}</p>
                      <small>
                        {describePreferences(record.draft.applied_preferences, t, selectedMatch?.metadata)}
                        {record.reviewer && ` — ${record.reviewer}${record.note ? `: ${record.note}` : ''}`}
                      </small>
                    </div>
                    {record.status === 'pending' && (
                      <div className="review-actions">
                        <Button disabled={!reviewer.trim()} onClick={() => decide(record.draft.draft_id, 'approve')}>
                          <Icon name="check" size={17} /> {copy.approve}
                        </Button>
                        <Button variant="ghost" className="danger" disabled={!reviewer.trim()} onClick={() => decide(record.draft.draft_id, 'reject')}>
                          <Icon name="close" size={17} /> {copy.reject}
                        </Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="preference-block">
            <h3>{copy.reports}</h3>
            {reports.length === 0 ? (
              <p className="muted-copy">{copy.noReports}</p>
            ) : (
              <ul className="review-list">
                {reports.map((report) => (
                  <li key={report.report_id}>
                    <div>
                      <span className={`editorial-status report-${report.outcome}`}>{copy.outcomes[report.outcome]}</span>
                      <strong>{report.reason}</strong>
                      <small><code>{report.draft_id}</code></small>
                      {report.issues.map((issue) => <p key={issue}>{issue}</p>)}
                      {report.corrected_draft && <p>✓ {report.corrected_draft.headline}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <details className="preference-block demo-tools">
            <summary>{copy.demo}</summary>
            <p className="muted-copy">{copy.demoCopy}</p>
            <label className="checkbox">
              <input checked={inject} onChange={(event) => setInject(event.target.checked)} type="checkbox" />
              <span>{copy.inject}</span>
            </label>
            <Button variant="ghost" disabled={!selectedMatch} onClick={reloadMatch}>
              <Icon name="replay" size={17} /> {copy.reload}
            </Button>
            {notice && <p className="success-copy" role="status">{notice}</p>}
          </details>
        </div>
      </section>
    </AppShell>
  )
}
