import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { usePreferences } from '../../app/preferences.js'
import { formatClock, formatMatchClock } from '../../lib/overlays.js'
import { ErrorNotice } from '../ui/Feedback.jsx'
import { Icon } from '../ui/Icon.jsx'

const SECTIONS = ['commentary', 'moments', 'events']

// Consola del analista profesional: todo lo que el sistema generó hasta el tiempo actual del vídeo.
// Se vuelve a pedir cada vez que el vídeo cruza un evento o se adelanta, así que nunca muestra el futuro.
export function AnalystConsole({ matchId, metadata, timeRef, crossed, seekVersion, onOpenMoment }) {
  const { t, apiPreferences } = usePreferences()
  const copy = t.console
  const [section, setSection] = useState('commentary')
  const [feed, setFeed] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    api.analystFeed(matchId, apiPreferences, timeRef.current)
      .then((data) => {
        if (!active) return
        setFeed(data)
        setError(null)
      })
      .catch((err) => active && setError(err.message))
    return () => { active = false }
  }, [matchId, apiPreferences, timeRef, crossed, seekVersion])

  const playerName = (id) => metadata.players.find((p) => p.player_id === id)?.name ?? id ?? '—'
  const teamName = (id) => [metadata.home_team, metadata.away_team].find((team) => team.team_id === id)?.name ?? id
  const counts = {
    commentary: feed?.commentary.length ?? 0,
    moments: feed?.moments.length ?? 0,
    events: feed?.events.length ?? 0,
  }

  return (
    <div className="analyst-console">
      <header className="console-header">
        <div>
          <strong>
            <Icon name="chart" size={17} /> {copy.tab}
          </strong>
          <span>{copy.intro}</span>
        </div>
        {feed && (
          <small>
            {copy.counts(counts.events, counts.moments, counts.commentary)} · {copy.pipeline} {feed.pipeline_ms} ms
          </small>
        )}
      </header>
      <ErrorNotice message={error} />
      <nav className="console-tabs" role="tablist">
        {SECTIONS.map((key) => (
          <button aria-selected={section === key} className={section === key ? 'active' : ''} key={key} onClick={() => setSection(key)} role="tab" type="button">
            {copy[key]} <i>{counts[key]}</i>
          </button>
        ))}
      </nav>

      {feed && counts[section] === 0 && <p className="console-empty">{copy.empty}</p>}

      {feed && section === 'commentary' && (
        <ol className="console-list">
          {[...feed.commentary].reverse().map((m) => (
            <li className={m.suppressed ? 'is-muted' : ''} key={m.message_id}>
              <span className="console-time">{formatMatchClock(m, t.match.period)}</span>
              <div>
                <p className="console-title">
                  <b>{t.kinds[m.kind] ?? m.kind}</b> {m.headline}
                </p>
                {m.explanation && <p className="console-text">{m.explanation}</p>}
                <span className="console-badges">
                  <i>{copy.priority} {m.priority}</i>
                  <i>{formatClock(m.video_time_ms)} → {formatClock(m.display_until_ms)}</i>
                  {m.suppressed && <i className="warn">{copy.queued}</i>}
                  {m.replaces_message_id && <i>{copy.replaces}</i>}
                  {m.corrected && <i className="ok">{copy.corrected}</i>}
                </span>
              </div>
              <button aria-label={t.match.whyMatters} onClick={() => onOpenMoment(m)} type="button">
                <Icon name="arrow" size={16} />
              </button>
            </li>
          ))}
        </ol>
      )}

      {feed && section === 'moments' && (
        <ol className="console-list moments">
          {[...feed.moments].reverse().map(({ candidate, drafts, shown_in: shownIn }) => (
            <li key={candidate.candidate_id}>
              <span className="console-time">{formatMatchClock(candidate, t.match.period)}</span>
              <div>
                <p className="console-title">
                  <b>{t.kinds[candidate.kind] ?? candidate.kind}</b> {teamName(candidate.team_id)}
                  {candidate.player_ids.length > 0 && ` · ${candidate.player_ids.map(playerName).join(', ')}`}
                </p>
                <span className="console-badges">
                  <i>{copy.priority} {candidate.priority}</i>
                  {shownIn.length ? (
                    <i className="ok">{copy.shownIn}: {shownIn.map((mode) => copy.modes[mode]).join(' · ')}</i>
                  ) : (
                    <i className="warn">{copy.notShown}</i>
                  )}
                </span>
                <div className="console-facts">
                  <small>{copy.facts}</small>
                  {candidate.facts.map((fact) => (
                    <code key={fact.key + (fact.player_id ?? '')}>
                      {fact.key}={fact.value ?? '—'}{fact.unit === 'count' ? '' : ` ${fact.unit}`}
                    </code>
                  ))}
                  <code>{candidate.source_event_ids.join(', ')}</code>
                </div>
                {candidate.evidence_limits.length > 0 && (
                  <p className="console-limits">
                    {copy.limits}: {candidate.evidence_limits.join('; ')}
                  </p>
                )}
                <div className="console-drafts">
                  {['casual', 'analyst'].map((mode) => (
                    <div key={mode}>
                      <small>{copy.modes[mode]}</small>
                      <strong>{drafts[mode].headline}</strong>
                      <p>{drafts[mode].explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
              <button aria-label={t.match.whyMatters} onClick={() => onOpenMoment({ candidate_id: candidate.candidate_id })} type="button">
                <Icon name="arrow" size={16} />
              </button>
            </li>
          ))}
        </ol>
      )}

      {feed && section === 'events' && counts.events > 0 && (
        <div className="console-table">
          <table>
            <thead>
              <tr>
                {['time', 'type', 'player', 'team', 'outcome', 'id'].map((key) => (
                  <th key={key} scope="col">{copy.columns[key]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...feed.events].reverse().map((e) => (
                <tr key={e.event_id}>
                  <td>{formatMatchClock(e, t.match.period)}</td>
                  <td>{t.moment.eventTypes[e.type] ?? e.type}</td>
                  <td>{playerName(e.player_id)}</td>
                  <td>{teamName(e.team_id)}</td>
                  <td>{e.outcome}</td>
                  <td><code>{e.event_id}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
