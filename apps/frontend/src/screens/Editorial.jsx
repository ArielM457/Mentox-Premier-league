import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { describePreferences, usePreferences } from '../app/preferences.js'
import { CommunityPanel } from '../components/community/CommunityPanel.jsx'
import { useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

// Revisión editorial (RF-38), reportes de error (RF-39) y revisión de la comunidad.
export function Editorial() {
  const { t, apiPreferences } = usePreferences()
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
  const [tab, setTab] = useState('review')
  const [tallies, setTallies] = useState({})
  const [communityDraft, setCommunityDraft] = useState('')
  const selected = matchId || catalog?.matches[0]?.id || ''
  const selectedMatch = catalog?.matches.find((m) => m.id === selected)
  const communityRecord = queue.find((record) => record.draft.draft_id === communityDraft) ?? queue[0] ?? null

  const refresh = useCallback(async () => {
    if (!selected) return
    try {
      const [q, r, votes] = await Promise.all([
        api.editorial(selected),
        api.reports(selected),
        api.communityTallies(selected).catch(() => []),
      ])
      setQueue(q)
      setReports(r)
      setTallies(Object.fromEntries(votes.map((item) => [item.draft_id, item.tally])))
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

  async function generateSummary() {
    try {
      await api.summary(selected, apiPreferences)
      setNotice(copy.generated)
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

        <nav className="editorial-tabs" role="tablist" aria-label={copy.kicker}>
          {['review', 'community'].map((key) => (
            <button aria-selected={tab === key} className={tab === key ? 'active' : ''} key={key} onClick={() => { setTab(key); if (key === 'review') refresh() }} role="tab" type="button">
              <Icon name={key === 'review' ? 'shield' : 'user'} size={17} /> {copy.tabs[key]}
            </button>
          ))}
        </nav>

        <div className="profile-card">
          <div className="editorial-fields">
            <label>
              <span>{copy.match}</span>
              <select onChange={(event) => { setMatchId(event.target.value); setCommunityDraft('') }} value={selected}>
                {catalog?.matches.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.metadata.home_team.name} – {m.metadata.away_team.name} · {t.matches.scenario[m.id] ?? m.id}
                  </option>
                ))}
              </select>
            </label>
            {tab === 'review' ? (
              <>
              <label>
                <span>{copy.reviewer}</span>
                <input maxLength={80} onChange={(event) => setReviewer(event.target.value)} value={reviewer} />
              </label>
              <label>
                <span>{copy.note}</span>
                <input maxLength={500} onChange={(event) => setNote(event.target.value)} value={note} />
              </label>
              </>
            ) : (
              <label className="wide">
                <span>{copy.community.pick}</span>
                <select disabled={!queue.length} onChange={(event) => setCommunityDraft(event.target.value)} value={communityRecord?.draft.draft_id ?? ''}>
                  {queue.map((record) => (
                    <option key={record.draft.draft_id} value={record.draft.draft_id}>
                      {record.draft.headline} · {t.recap.status[record.status]}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {notice && <p className="success-copy" role="status">{notice}</p>}

          {tab === 'review' ? (
            <>
            <div className="preference-block">
              <div className="queue-heading">
                <h3>{copy.queue}</h3>
                <Button variant="ghost" disabled={!selectedMatch} onClick={generateSummary}>
                  <Icon name="spark" size={17} /> {copy.generate}
                </Button>
              </div>
              <p className="muted-copy">{copy.whereFrom}</p>
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
                        <span className="community-signal">
                          <Icon name="user" size={14} />
                          {copy.communitySignal(tallies[record.draft.draft_id]?.approve_pct, tallies[record.draft.draft_id]?.total ?? 0)}
                        </span>
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
            </details>
            </>
          ) : communityRecord ? (
            <CommunityPanel key={`${selected}/${communityRecord.draft.draft_id}`} matchId={selected} record={communityRecord} />
          ) : (
            <p className="muted-copy community-empty">{copy.community.none}</p>
          )}
        </div>
      </section>
    </AppShell>
  )
}
