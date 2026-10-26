import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client.js'
import { usePreferences } from '../../app/preferences.js'
import { formatMatchClock } from '../../lib/overlays.js'
import { Button } from '../ui/Button.jsx'
import { Icon } from '../ui/Icon.jsx'
import { TeamBadge } from '../ui/TeamBadge.jsx'
import { Pitch } from './Pitch.jsx'
import { TacticalSimulationPitch } from './TacticalSimulationPitch.jsx'

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

function replayTitle(sequence, t) {
  if (sequence.some((event) => event.type === 'recovery')) return t.match.replayPatterns.recovery
  if (sequence.filter((event) => event.type === 'pass').length >= 3) return t.match.replayPatterns.circulation
  if (sequence.some((event) => event.type === 'pressure')) return t.match.replayPatterns.pressure
  return t.match.replayPatterns.attack
}

function replayFrames(sequence, homePlayers, awayPlayers, t) {
  const current = new Map([...homePlayers, ...awayPlayers].map((player) => [player.player_id, { ...player, position: { ...player.position } }]))
  const basePositions = new Map([...current].map(([playerId, player]) => [playerId, { ...player.position }]))
  const goalkeepers = new Set([homePlayers[0]?.player_id, awayPlayers[0]?.player_id].filter(Boolean))
  const frames = []
  const players = () => [...current.values()].map((item) => ({ ...item, position: { ...item.position } }))
  const step = (value, target, amount) => value + Math.max(-amount, Math.min(amount, target - value))
  const movePlayer = (playerId, point) => {
    const player = current.get(playerId)
    if (playerId && player && point) current.set(playerId, { ...player, position: { ...point } })
  }
  const moveBlocks = (attackingTeamId, point) => {
    current.forEach((player, playerId) => {
      const base = basePositions.get(playerId)
      const attacking = player.team_id === attackingTeamId
      const intensity = goalkeepers.has(playerId) ? .6 : attacking ? 2.5 : 2.1
      const horizontalShift = (point.x - 50) * (attacking ? .18 : .12)
      const verticalShift = (point.y - 50) * (attacking ? .16 : .2)
      const target = {
        x: Math.max(4, Math.min(96, base.x + horizontalShift)),
        y: Math.max(7, Math.min(93, base.y + verticalShift)),
      }
      current.set(playerId, {
        ...player,
        position: {
          x: Number(step(player.position.x, target.x, intensity).toFixed(2)),
          y: Number(step(player.position.y, target.y, intensity).toFixed(2)),
        },
      })
    })
  }
  const closestDefenders = (attackingTeamId, point) => [...current.values()]
    .filter((player) => player.team_id !== attackingTeamId)
    .sort((left, right) => (
      ((left.position.x - point.x) ** 2 + (left.position.y - point.y) ** 2)
      - ((right.position.x - point.x) ** 2 + (right.position.y - point.y) ** 2)
    ))
    .slice(0, 2)
    .map((player) => player.player_id)
  const addFrame = (event, ball, ownerId, action, involvedPlayerIds) => {
    const defenders = closestDefenders(event.team_id, ball)
    frames.push({
      at_ms: frames.length * 900,
      phase: t.moment.eventTypes[event.type] ?? event.type,
      action,
      ball,
      ball_owner_id: ownerId,
      involved_player_ids: [...new Set([...involvedPlayerIds, ...defenders].filter(Boolean))],
      players: players(),
    })
  }

  sequence.forEach((event, index) => {
    const start = event.start ?? event.end ?? { x: 50, y: 50 }
    moveBlocks(event.team_id, start)
    movePlayer(event.player_id, start)
    addFrame(
      event,
      start,
      event.player_id,
      t.match.recordedAction(t.moment.eventTypes[event.type] ?? event.type, formatMatchClock(event, t.match.period)),
      [event.player_id],
    )

    if (!event.end) return
    if (event.type === 'shot') {
      moveBlocks(event.team_id, event.end)
      addFrame(event, event.end, null, t.match.recordedShotPath, [event.player_id])
      return
    }
    if (event.type === 'pass') {
      const receiverEvent = sequence.slice(index + 1).find((candidate) => (
        candidate.team_id === event.team_id
        && candidate.player_id
        && candidate.player_id !== event.player_id
        && candidate.start
      ))
      const receiver = current.get(receiverEvent?.player_id)
      moveBlocks(event.team_id, event.end)
      movePlayer(receiver?.player_id, event.end)
      addFrame(
        event,
        event.end,
        receiver?.player_id ?? null,
        t.match.recordedReception(receiver?.name ?? '—'),
        [event.player_id, receiver?.player_id],
      )
      return
    }
    moveBlocks(event.team_id, event.end)
    movePlayer(event.player_id, event.end)
    addFrame(event, event.end, event.player_id, t.match.recordedMove, [event.player_id])
  })

  return frames
}

function usedTactics(team, events, homePlayers, awayPlayers, t) {
  const teamEvents = events.filter((event) => event.team_id === team.team_id && event.start)
  if (!teamEvents.length) return []
  const finishes = teamEvents.filter((event) => event.type === 'shot')
  const ends = finishes.length ? finishes.slice(-3) : [teamEvents[teamEvents.length - 1]]
  return ends.map((ending) => {
    const endIndex = teamEvents.findIndex((event) => event.event_id === ending.event_id)
    const sequence = teamEvents.slice(Math.max(0, endIndex - 5), endIndex + 1)
    const title = replayTitle(sequence, t)
    return {
      simulation_id: `recorded-${team.team_id}-${ending.event_id}`,
      team_id: team.team_id,
      title: `${title} · ${formatMatchClock(ending, t.match.period)}`,
      summary: t.match.recordedSummary(sequence.length),
      result: ending.type === 'shot' ? t.match.recordedFinish : t.match.recordedSequence,
      frames: replayFrames(sequence, homePlayers, awayPlayers, t),
      source_event_ids: sequence.map((event) => event.event_id),
    }
  })
}

function TacticalChoiceCard({ team, options, selectedId, onSelect, onPlay, activeId, copy, mode }) {
  const selected = options.find((option) => option.simulation_id === selectedId) ?? options[0]
  return (
    <article className={`live-tactic-card ${activeId === selected?.simulation_id ? 'active' : ''}`}>
      <header><TeamBadge team={team} /><div><span>{team.role}</span><h3>{team.team_name}</h3></div></header>
      {selected ? (
        <>
          <label>{mode === 'replay' ? copy.usedTactics : copy.possibleTactics}</label>
          <select onChange={(event) => onSelect(event.target.value)} value={selected.simulation_id}>
            {options.map((option) => <option key={option.simulation_id} value={option.simulation_id}>{option.title}</option>)}
          </select>
          <p>{selected.summary}</p>
          <Button onClick={() => onPlay(selected.simulation_id)}>
            <Icon name={activeId === selected.simulation_id ? 'replay' : 'play'} size={15} />
            {mode === 'replay' ? copy.replayMode : copy.simulateMode}
          </Button>
        </>
      ) : <p className="no-used-tactic">{copy.noUsedTactics}</p>}
    </article>
  )
}

export function TacticalPanel({ compact = false, events, matchId, metadata }) {
  const { t } = usePreferences()
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [mode, setMode] = useState('replay')
  const [selected, setSelected] = useState({})
  const [playingId, setPlayingId] = useState(null)
  const [frameIndex, setFrameIndex] = useState(0)
  const [runToken, setRunToken] = useState(0)

  useEffect(() => {
    let active = true
    api.preview(matchId).then((data) => active && setPreview(data)).catch((reason) => active && setError(reason.message))
    return () => { active = false }
  }, [matchId])

  const homeFormation = preview?.home.formations[0]
  const awayFormation = preview?.away.formations[0]
  const recorded = useMemo(() => {
    if (!preview || !homeFormation || !awayFormation) return []
    return [
      ...usedTactics(preview.home, events, homeFormation.players, awayFormation.players, t),
      ...usedTactics(preview.away, events, homeFormation.players, awayFormation.players, t),
    ]
  }, [events, preview, homeFormation, awayFormation, t])
  const options = mode === 'replay' ? recorded : preview?.simulations ?? []
  const active = options.find((option) => option.simulation_id === playingId) ?? null
  const frame = active?.frames[frameIndex] ?? null
  const previousFrame = active && frameIndex > 0 ? active.frames[frameIndex - 1] : null

  useEffect(() => {
    if (!active) return undefined
    const timer = window.setInterval(() => {
      setFrameIndex((current) => {
        if (current >= active.frames.length - 1) {
          window.clearInterval(timer)
          return current
        }
        return current + 1
      })
    }, 950)
    return () => window.clearInterval(timer)
  }, [active, runToken])

  function changeMode(nextMode) {
    setMode(nextMode)
    setPlayingId(null)
    setFrameIndex(0)
  }

  function play(optionId) {
    setPlayingId(optionId)
    setFrameIndex(0)
    setRunToken((value) => value + 1)
  }

  return (
    <section className={`tactical-panel live-tactical-lab ${compact ? 'agent-open' : ''}`}>
      <header>
        <div><span className="section-kicker">{t.match.tacticalKicker}</span><h2>{t.match.liveTacticalTitle}</h2><p>{t.match.liveTacticalCopy}</p></div>
        <div className="tactical-mode-switch" aria-label={t.match.tacticalMode} role="group">
          <button aria-pressed={mode === 'replay'} className={mode === 'replay' ? 'active' : ''} onClick={() => changeMode('replay')} type="button">{t.match.replayMode}</button>
          <button aria-pressed={mode === 'simulate'} className={mode === 'simulate' ? 'active' : ''} onClick={() => changeMode('simulate')} type="button">{t.match.simulateMode}</button>
        </div>
      </header>
      {error && <p className="panel-note">{error}</p>}
      {preview && homeFormation && awayFormation && (
        <>
          <div className="initial-lineup-bar">
            <div><TeamBadge team={metadata.home_team} size="sm" /><span><strong>{metadata.home_team.name} · {homeFormation.name}</strong><small>{homeFormation.players.map((player) => player.name).join(' · ')}</small></span></div>
            <span className="lineup-lock"><Icon name="shield" size={14} /> {t.match.lineupUntilHalftime}</span>
            <div><TeamBadge team={metadata.away_team} size="sm" /><span><strong>{metadata.away_team.name} · {awayFormation.name}</strong><small>{awayFormation.players.map((player) => player.name).join(' · ')}</small></span></div>
          </div>
          <div className="live-tactical-grid">
            <div className="live-tactic-choices">
              {[preview.home, preview.away].map((team) => (
                <TacticalChoiceCard
                  activeId={playingId}
                  copy={t.match}
                  key={`${mode}-${team.team_id}`}
                  mode={mode}
                  onPlay={play}
                  onSelect={(optionId) => setSelected((current) => ({ ...current, [`${mode}-${team.team_id}`]: optionId }))}
                  options={options.filter((option) => option.team_id === team.team_id)}
                  selectedId={selected[`${mode}-${team.team_id}`]}
                  team={team}
                />
              ))}
            </div>
            <div className="live-tactical-stage">
              <TacticalSimulationPitch
                awayPlayers={awayFormation.players}
                frame={frame}
                homeId={preview.home.team_id}
                homePlayers={homeFormation.players}
                label={t.match.liveTacticalTitle}
                previousFrame={previousFrame}
              />
              <div className="live-tactical-status">
                <span>{frame ? `${frameIndex + 1}/${active.frames.length}` : mode === 'replay' ? t.match.recordedReady : t.match.simulationReady}</span>
                <strong>{frame?.phase ?? (mode === 'replay' ? t.match.chooseRecorded : t.match.choosePossible)}</strong>
                <p>{frameIndex === active?.frames.length - 1 ? active.result : frame?.action ?? t.match.lineupBaseCopy}</p>
              </div>
            </div>
          </div>
          <p className="panel-note">{mode === 'replay' ? t.match.recordedEvidence : t.match.simulatedEvidence}</p>
        </>
      )}
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

export function LiveCommentsPanel({ moments, events, metadata, timeMs, compact = false }) {
  const { t } = usePreferences()
  const visible = moments.filter((moment) => !moment.suppressed).slice(0, 8)
  const recentEvents = events.filter((event) => event.video_time_ms <= timeMs)
  const comments = (
    <div className={`commentary-flow ${compact ? 'commentary-inline' : ''}`} aria-live="polite">
      <header><span className="live-dot" /><div><strong>{t.match.liveCommentsTitle}</strong><small>{t.match.liveCommentsCopy}</small></div></header>
      {visible.length ? visible.map((moment) => <article key={moment.message_id}><time>{formatMatchClock(moment, t.match.period)}</time><div><strong>{moment.headline}</strong><p>{moment.explanation}</p></div></article>) : <p className="feed-empty">{t.match.waitingCommentary}</p>}
    </div>
  )

  if (compact) return comments

  return (
    <section className="commentary-stage">
      <div className="commentary-preview">
        <span className="section-kicker">{t.match.matchPreview}</span>
        <Pitch events={recentEvents} homeTeamId={metadata.home_team.team_id} label={t.match.matchPreview} players={metadata.players} playing timeMs={timeMs} trail={6} />
      </div>
      {comments}
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

function visionLabel(t, label) {
  return t.match.visionObjectLabels[label] ?? label ?? t.match.visionObject
}

function observationsForFrame(observations, matchId, timeMs) {
  const candidates = observations.filter((item) => (
    item.kind === 'spatial_detection'
    && item.payload?.match_id === matchId
    && Array.isArray(item.payload?.bounding_box)
    && Math.abs(item.timestamp_ms - timeMs) <= 2500
  ))
  const latestTimestamp = Math.max(-1, ...candidates.map((item) => item.timestamp_ms))
  return candidates.filter((item) => item.timestamp_ms === latestTimestamp)
}

function groupLiveObservations(observations) {
  const groups = new Map()
  for (const item of observations) {
    const group = groups.get(item.timestamp_ms) ?? []
    group.push(item)
    groups.set(item.timestamp_ms, group)
  }
  return [...groups.entries()]
    .sort(([left], [right]) => right - left)
    .slice(0, 6)
    .map(([timestamp, items]) => ({ timestamp, items }))
}

function detectionSummary(t, observations) {
  const counts = new Map()
  for (const item of observations) {
    const label = item.payload?.label ?? 'other'
    counts.set(label, (counts.get(label) ?? 0) + 1)
  }
  return [...counts.entries()].map(([label, count]) => {
    const copy = t.match.visionObjectCountLabels[label] ?? t.match.visionObjectCountLabels.other
    return `${count} ${count === 1 ? copy.one : copy.many}`
  }).join(' · ')
}

export function VisionVideoOverlay({ observations, matchId, timeMs }) {
  const { t } = usePreferences()
  const detections = observationsForFrame(observations, matchId, timeMs)
  return (
    <div className="vision-box-layer" aria-label="Detecciones de visión sobre el vídeo">
      {detections.map((item) => {
        const [x1, y1, x2, y2] = item.payload.bounding_box
        const label = visionLabel(t, item.payload.label)
        return (
          <span
            className={`vision-box vision-box-${item.payload.label ?? 'other'}`}
            key={item.observation_id}
            style={{ '--box-x': `${x1 * 100}%`, '--box-y': `${y1 * 100}%`, '--box-width': `${(x2 - x1) * 100}%`, '--box-height': `${(y2 - y1) * 100}%` }}
          >
            <small>{label} · {(item.payload.confidence * 100).toFixed(0)}%</small>
          </span>
        )
      })}
    </div>
  )
}

export function VisionPanel({ timeMs, seekVersion, capture, liveChannel, matchId }) {
  const { t } = usePreferences()
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const second = Math.floor(timeMs / 1000)

  useEffect(() => {
    let active = true
    Promise.allSettled([
      api.visionLiveStatus(),
      api.visionStatus(),
    ]).then(([liveResult, integrationResult]) => {
      if (!active) return
      const liveReady = liveResult.status === 'fulfilled'
      const integrationReady = integrationResult.status === 'fulfilled'
      setStatus(integrationReady ? integrationResult.value : {
        ready: liveReady,
        fusion: { match_events_published: 0 },
      })
      setError(liveReady || integrationReady ? null : t.match.visionUnavailable)
    })
    return () => { active = false }
  }, [second, seekVersion, t.match.visionUnavailable])

  if (error) return (
    <section className="vision-panel vision-panel-inline" aria-live="polite">
      <header><div><span className="section-kicker">{t.match.visionKicker}</span><h2>{t.match.visionTitle}</h2></div><span className="channel-pill channel-error">{t.match.visionUnavailable}</span></header>
      <p className="vision-empty">{error}</p>
    </section>
  )
  if (!status) return (
    <section className="vision-panel vision-panel-inline" aria-busy="true">
      <header><div><span className="section-kicker">{t.match.visionKicker}</span><h2>{t.match.visionTitle}</h2></div><span className="channel-pill">{t.common.loading}</span></header>
    </section>
  )
  const liveObservations = (liveChannel?.observations ?? [])
    .filter((item) => item.payload?.match_id === matchId && Math.abs(item.timestamp_ms - timeMs) <= 5000)
  const liveFrames = groupLiveObservations(liveObservations)
  const captureLive = capture?.status === 'live'
  const sessionObservations = (liveChannel?.observations ?? []).filter((item) => item.payload?.match_id === matchId)
  const spatialCount = sessionObservations.filter((item) => item.kind === 'spatial_detection').length
  const actionCount = sessionObservations.filter((item) => item.kind === 'temporal_action').length

  return (
    <section className="vision-panel vision-panel-inline" aria-live="polite">
      <header>
        <div><span className="section-kicker">{t.match.visionKicker}</span><h2>{t.match.visionTitle}</h2></div>
        <div className="vision-statuses">
          <span className={`channel-pill ${captureLive ? 'channel-live' : ''}`}>{captureLive ? t.match.visionCapturing : t.match.visionWaiting}</span>
          <span className={`channel-pill ${liveChannel?.status === 'live' ? 'channel-live' : ''}`}>{liveChannel?.status === 'live' ? t.match.visionConnected : t.match.visionDisconnected}</span>
        </div>
      </header>
      <div className="vision-summary">
        <p>{t.match.visionNotice}</p>
        <div className="vision-counters">
          <span><strong>{capture?.processed ?? 0}</strong>{t.match.visionFrames}</span>
          <span><strong>{spatialCount}</strong>{t.match.visionDetections}</span>
          <span><strong>{actionCount}</strong>{t.match.visionActions}</span>
          <span><strong>{status.fusion.match_events_published}</strong>MatchEvent</span>
        </div>
      </div>
      <div className="vision-feed">
        {liveFrames.length ? liveFrames.map((frame) => (
          <article className="vision-event-live" key={frame.timestamp}>
            <time>{(frame.timestamp / 1000).toFixed(2)} s</time>
            <div><strong>{t.match.visionLive} · {detectionSummary(t, frame.items)}</strong><small>{t.match.visionFrameEvidence(frame.items.length)}</small></div>
          </article>
        )) : <p className="vision-empty">{t.match.visionPlayPrompt}</p>}
      </div>
      {capture?.error && <p className="vision-error">{capture.error}</p>}
    </section>
  )
}
