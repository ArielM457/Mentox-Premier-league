import { NarrativeCopy } from '../components/ui/NarrativeCopy.jsx'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { usePreferences } from '../app/preferences.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingScreen } from '../components/ui/Feedback.jsx'
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
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [inject, setInject] = useState(false)
  const selected = matchId || catalog?.matches[0]?.id || ''
  const selectedMatch = catalog?.matches.find((m) => m.id === selected)

  const refresh = useCallback(async () => {
    if (!selected) return
    setLoading(true)
    try {
      const [q, r] = await Promise.all([api.editorial(selected), api.reports(selected)])
      setQueue(q)
      setReports(r)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally { setLoading(false) }
  }, [selected])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function decide(draftId, decision) {
    setBusy(true)
    try {
      await api.review(selected, draftId, decision, reviewer, note)
      setNote('')
      await refresh()
      setNotice(copy.decisionSaved)
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
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
          <div className="editorial-intro"><span className="empty-icon"><Icon name="shield" size={24} /></span><div><h2>{copy.workspace}</h2><p>{copy.workspaceCopy}</p></div></div>
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
              <input maxLength={80} onChange={(event) => setReviewer(event.target.value)} placeholder={copy.reviewerPlaceholder} value={reviewer} />
            </label>
            <label>
              <span>{copy.note}</span>
              <input maxLength={500} onChange={(event) => setNote(event.target.value)} value={note} />
            </label>
          </div>

          <div className="preference-block">
            <div className="editorial-section-title"><h3>{copy.queue}</h3><span className="count-badge">{queue.length}</span></div>
            {!reviewer.trim() && <p className="muted-copy">{copy.reviewerHint}</p>}
            {loading && <LoadingScreen compact />}
            {notice && <p role="status" className="success-copy">{notice}</p>}
            {!loading && queue.length === 0 ? (
              <p className="muted-copy">{copy.empty}</p>
            ) : (
              <ul className="review-list">
                {queue.map((record) => (
                  <li key={record.draft.draft_id}>
                    <div>
                      <span className={`editorial-status status-${record.status}`}>{t.recap.status[record.status]}</span>
                      <strong>{record.draft.headline}</strong>
                      <NarrativeCopy text={record.draft.explanation} />
                      <small>
                        {record.draft.applied_preferences.map((item) => { const [key, value] = item.split(':'); return key === 'language' ? (value === 'es' ? 'Español' : 'English') : key === 'mode' ? t.modes[value]?.name : key === 'level' ? t.levels[value]?.name : catalog?.players.find((player) => player.player_id === value)?.name || catalog?.clubs.find((club) => club.team_id === value)?.name }).filter(Boolean).join(' · ')}
                        {record.reviewer && ` — ${record.reviewer}${record.note ? `: ${record.note}` : ''}`}
                      </small>
                    </div>
                    {record.status === 'pending' && (
                      <div className="review-actions">
                        <Button disabled={busy || !reviewer.trim()} onClick={() => decide(record.draft.draft_id, 'approve')}>
                          <Icon name="check" size={17} /> {copy.approve}
                        </Button>
                        <Button variant="secondary" className="review-reject" disabled={busy || !reviewer.trim()} onClick={() => decide(record.draft.draft_id, 'reject')}>
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
