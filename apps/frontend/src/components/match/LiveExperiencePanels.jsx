import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { usePreferences } from '../../app/preferences.js'
import { formatMatchClock } from '../../lib/overlays.js'
import { Button } from '../ui/Button.jsx'
import { Icon } from '../ui/Icon.jsx'
import { Pitch } from './Pitch.jsx'

const IMPORTANT_KINDS = new Set(['goal', 'shot'])

function eventsOf(moment, events) {
  const ids = new Set(moment?.source_event_ids ?? [])
  return events.filter((event) => ids.has(event.event_id))
}

function playerName(metadata, playerId) {
  return metadata.players.find((player) => player.player_id === playerId)?.name ?? '—'
}

function teamName(metadata, teamId) {
  if (metadata.home_team.team_id === teamId) return metadata.home_team.name
  if (metadata.away_team.team_id === teamId) return metadata.away_team.name
  return '—'
}

export function MomentSelector({ moments, selected, onSelect }) {
  const { t } = usePreferences()
  if (!moments.length) return <p className="moment-selector empty">{t.match.noMoments}</p>
  const index = Math.max(0, moments.findIndex((moment) => moment.message_id === selected?.message_id))
  const move = (amount) => onSelect(moments[(index + amount + moments.length) % moments.length])
  return (
    <div className="moment-selector" aria-label={t.match.momentSelector}>
      <button aria-label={t.match.previousMoment} onClick={() => move(-1)} type="button"><Icon name="back" size={16} /></button>
      <button className="moment-selector-current" onClick={() => onSelect(moments[index], true)} type="button">
        <span>{formatMatchClock(moments[index], t.match.period)}</span>
        <strong>{moments[index].headline}</strong>
        <small>{t.match.openInMoments}</small>
      </button>
      <button aria-label={t.match.nextMoment} onClick={() => move(1)} type="button"><Icon name="arrow" size={16} /></button>
    </div>
  )
}

export function MomentWorkspace({ moment, events, metadata, onOpen }) {
  const { t } = usePreferences()
  const [change, setChange] = useState('earlier_pass')
  if (!moment) {
    return <section className="moment-workspace empty-comments"><h2>{t.match.noMomentSelected}</h2><p>{t.match.noMoments}</p></section>
  }
  const sources = eventsOf(moment, events)
  const author = sources.slice().reverse().find((event) => event.player_id)
  const changeLabel = t.match.counterfactualOptions[change]
  return (
    <section className="moment-workspace">
      <header>
        <div>
          <span className="section-kicker">{t.match.selectedMoment}</span>
          <h2>{moment.headline}</h2>
          <p>{moment.explanation}</p>
        </div>
        <Button onClick={() => onOpen(moment)} variant="ghost">{t.match.openFullAnalysis} <Icon name="arrow" size={16} /></Button>
      </header>
      <div className="moment-workspace-grid">
        <Pitch events={sources} highlightIds={moment.source_event_ids} homeTeamId={metadata.home_team.team_id} label={moment.headline} players={metadata.players} trail={Math.max(1, sources.length)} />
        <aside className="counterfactual-panel">
          <span className="section-kicker">{t.match.counterfactualKicker}</span>
          <h3>{t.match.counterfactualTitle}</h3>
          <p>{t.match.counterfactualCopy}</p>
          <div className="counterfactual-options">
            {Object.entries(t.match.counterfactualOptions).map(([key, label]) => (
              <button className={change === key ? 'active' : ''} key={key} onClick={() => setChange(key)} type="button">{label}</button>
            ))}
          </div>
          <div className="counterfactual-result">
            <strong>{t.match.estimatedResult}</strong>
            <p>{t.match.counterfactualResult(changeLabel, playerName(metadata, author?.player_id), sources.length)}</p>
          </div>
          <small className="simulation-disclaimer">{t.match.counterfactualDisclaimer}</small>
        </aside>
      </div>
    </section>
  )
}

function patternsFor(teamId, events, t) {
  const teamEvents = events.filter((event) => !teamId || event.team_id === teamId)
  const patterns = []
  if (teamEvents.filter((event) => event.type === 'pressure').length >= 2) patterns.push(t.match.patterns.pressure)
  if (teamEvents.filter((event) => event.type === 'pass').length >= 3) patterns.push(t.match.patterns.circulation)
  if (teamEvents.some((event) => event.type === 'recovery') && teamEvents.some((event) => event.type === 'pass' && event.end?.x > event.start?.x)) patterns.push(t.match.patterns.transition)
  if (teamEvents.some((event) => event.type === 'shot' && event.start?.x >= 70)) patterns.push(t.match.patterns.finalThird)
  return patterns.length ? patterns : [t.match.patterns.unconfirmed]
}

export function TacticalPanel({ events, metadata, timeMs, playing }) {
  const { t } = usePreferences()
  const [teamId, setTeamId] = useState('')
  const options = [{ team_id: '', name: t.match.bothTeams }, metadata.home_team, metadata.away_team]
  const visible = teamId ? events.filter((event) => event.team_id === teamId) : events
  const patterns = patternsFor(teamId, events, t)
  return (
    <section className="tactical-panel">
      <header>
        <div><span className="section-kicker">{t.match.tacticalKicker}</span><h2>{t.match.tacticalTitle}</h2></div>
        <label>{t.match.focusTeam}<select onChange={(event) => setTeamId(event.target.value)} value={teamId}>{options.map((team) => <option key={team.team_id || 'both'} value={team.team_id}>{team.name}</option>)}</select></label>
      </header>
      <div className="tactical-patterns">{patterns.map((pattern) => <span key={pattern}>{pattern}</span>)}</div>
      <Pitch events={visible} homeTeamId={metadata.home_team.team_id} label={t.match.tacticalTitle} players={metadata.players} playing={playing} timeMs={timeMs} trail={15} />
      <p className="panel-note">{t.match.patternEvidence}</p>
    </section>
  )
}

export function InsightsPanel({ moments, events, metadata, onOpen }) {
  const { t } = usePreferences()
  const important = moments.filter((moment) => !moment.suppressed && (IMPORTANT_KINDS.has(moment.kind) || moment.priority >= 70))
  if (!important.length) return <section className="insight-list empty-comments"><h2>{t.match.importantMoments}</h2><p>{t.match.noImportantMoments}</p></section>
  return (
    <section className="insight-list">
      <header><span className="section-kicker">{t.match.aiExplanations}</span><h2>{t.match.importantMoments}</h2></header>
      {important.map((moment) => {
        const sources = eventsOf(moment, events)
        const author = sources.slice().reverse().find((event) => event.player_id)
        return (
          <button key={moment.message_id} onClick={() => onOpen(moment)} type="button">
            <div className="insight-mini-pitch"><Pitch events={sources} highlightIds={moment.source_event_ids} homeTeamId={metadata.home_team.team_id} label={moment.headline} players={metadata.players} trail={Math.max(1, sources.length)} /></div>
            <div><span>{formatMatchClock(moment, t.match.period)} · {t.kinds[moment.kind] ?? moment.kind}</span><strong>{moment.headline}</strong><p>{moment.explanation}</p><small>{t.match.author}: {playerName(metadata, author?.player_id)} · {t.match.viewAnalysis}</small></div>
            <Icon name="arrow" />
          </button>
        )
      })}
    </section>
  )
}

export function LiveCommentsPanel({ moments, events, metadata, timeMs }) {
  const { t } = usePreferences()
  const visible = moments.filter((moment) => !moment.suppressed).slice(0, 8)
  const recentEvents = events.filter((event) => event.video_time_ms <= timeMs)
  return (
    <section className="commentary-stage">
      <div className="commentary-preview">
        <span className="section-kicker">{t.match.matchPreview}</span>
        <Pitch events={recentEvents} homeTeamId={metadata.home_team.team_id} label={t.match.matchPreview} players={metadata.players} playing timeMs={timeMs} trail={6} />
      </div>
      <div className="commentary-flow" aria-live="polite">
        <header><span className="live-dot" /><div><strong>{t.match.liveCommentsTitle}</strong><small>{t.match.liveCommentsCopy}</small></div></header>
        {visible.length ? visible.map((moment) => <article key={moment.message_id}><time>{formatMatchClock(moment, t.match.period)}</time><div><strong>{moment.headline}</strong><p>{moment.explanation}</p></div></article>) : <p className="feed-empty">{t.match.waitingCommentary}</p>}
      </div>
    </section>
  )
}

export function AnnouncerPanel({ current, metadata, snapshot, timeMs }) {
  const { t } = usePreferences()
  const factIndex = Math.floor(timeMs / 10_000) % 3
  const facts = [
    t.match.contextFacts.players(metadata.players.length),
    t.match.contextFacts.pitch,
    snapshot?.possession_team_id ? t.match.contextFacts.possession(teamName(metadata, snapshot.possession_team_id)) : t.match.contextFacts.level,
  ]
  return (
    <aside className="announcer-panel">
      <header><span className="announcer-avatar"><Icon name="spark" /></span><div><strong>{t.match.announcer}</strong><small>{t.match.announcerLive}</small></div></header>
      <div className="announcer-message">
        <span>{current ? formatMatchClock(current, t.match.period) : t.match.deadTime}</span>
        <h3>{current?.headline ?? t.match.contextFact}</h3>
        <p>{current?.explanation ?? facts[factIndex]}</p>
      </div>
      {!current && <small className="context-badge">{t.match.deadTimeContext}</small>}
    </aside>
  )
}

export function VisionPanel({ timeMs, seekVersion }) {
  const { t } = usePreferences()
  const [status, setStatus] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [error, setError] = useState(null)
  const second = Math.floor(timeMs / 1000)

  useEffect(() => {
    let active = true
    Promise.all([
      api.visionStatus(),
      api.visionTimeline(Math.max(0, second * 1000 - 1000), second * 1000 + 1000),
    ]).then(([nextStatus, nextTimeline]) => {
      if (!active) return
      setStatus(nextStatus)
      setTimeline(nextTimeline)
      setError(null)
    }).catch((reason) => active && setError(reason.message))
    return () => { active = false }
  }, [second, seekVersion])

  if (error) {
    return <section className="vision-panel empty-comments"><h2>{t.match.visionTitle}</h2><p>{t.match.visionUnavailable}: {error}</p></section>
  }
  if (!status || !timeline) {
    return <section className="vision-panel empty-comments"><h2>{t.match.visionTitle}</h2><p>{t.common.loading}</p></section>
  }
  const observations = [
    ...timeline.temporal_actions.map((item) => ({ ...item, category: t.match.visionAction })),
    ...timeline.spatial_observations.map((item) => ({ ...item, category: t.match.visionDetection })),
  ].sort((a, b) => a.timestamp_ms - b.timestamp_ms).slice(0, 40)

  return (
    <section className="vision-panel">
      <header><div><span className="section-kicker">{t.match.visionKicker}</span><h2>{t.match.visionTitle}</h2></div><span className="channel-pill channel-live">{status.ready ? t.match.visionReady : t.match.visionUnavailable}</span></header>
      <p className="panel-note">{t.match.visionNotice}</p>
      <div className="vision-counters">
        <span><strong>{timeline.spatial_total}</strong>{t.match.visionDetections}</span>
        <span><strong>{timeline.temporal_actions.length}</strong>{t.match.visionActions}</span>
        <span><strong>{timeline.fusion_candidates.length}</strong>{t.match.visionCandidates}</span>
        <span><strong>{status.fusion.match_events_published}</strong>MatchEvent</span>
      </div>
      <div className="vision-feed">
        {observations.length ? observations.map((item) => (
          <article key={item.prediction_id}>
            <time>{(item.timestamp_ms / 1000).toFixed(2)} s</time>
            <div><strong>{item.category} · {item.label}</strong><small>{t.match.visionConfidence}: {(item.confidence * 100).toFixed(1)}% · track_id: {item.track_id ?? '—'}</small></div>
          </article>
        )) : <p>{t.match.visionEmpty}</p>}
      </div>
    </section>
  )
}
