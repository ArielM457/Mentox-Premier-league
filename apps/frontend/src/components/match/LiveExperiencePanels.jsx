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

const WHAT_IF_ORDER = ['earlier_pass', 'keeper_steps', 'supporting_run', 'early_shot']

// Análisis de Persona 2 para el momento: motivos, hechos, posiciones y lecturas alternativas.
function useMomentAnalysis(matchId, moment, prefs) {
  const [state, setState] = useState({ key: null, data: null, error: null })
  const key = moment && matchId
    ? [matchId, moment.candidate_id, prefs.language, prefs.mode, prefs.favoriteTeamId, prefs.favoritePlayerId].join('|')
    : null
  useEffect(() => {
    if (!key) return undefined
    let active = true
    api.momentAnalysis(matchId, moment.candidate_id, prefs, moment.source_event_ids?.at(-1))
      .then((data) => { if (active) setState({ key, data, error: null }) })
      .catch((error) => { if (active) setState({ key, data: null, error: error.message }) })
    return () => { active = false }
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!key || state.key !== key) return { loading: Boolean(key), data: null, error: null }
  return { loading: false, data: state.data, error: state.error }
}

// Pasa un TrackingFrame (metros) a porcentajes de la cancha para ``Pitch``.
function snapshotOf(frame, metadata) {
  if (!frame) return null
  const toPct = (value, size) => Math.max(0, Math.min(100, (value / size) * 100))
  const players = new Map()
  let ball = null
  for (const item of frame.objects) {
    const point = { x: toPct(item.x_m, metadata.pitch_length_m), y: toPct(item.y_m, metadata.pitch_width_m) }
    if (item.kind === 'ball') ball = point
    else if (item.player_id) players.set(item.player_id, point)
  }
  return { players, ball }
}

function formatValue(value, unit, t) {
  if (value === null || value === undefined) return t.match.analysis.noData
  const shown = Number(value).toLocaleString(t.match.analysis.locale, { maximumFractionDigits: 1 })
  return `${shown}${t.match.analysis.units[unit] ?? ''}`
}

// El avance también llega en metros: se omite su versión en porcentaje del campo.
const HIDDEN_FACTS = new Set(['forward_progress'])

function WhatIfResult({ reading, metadata, t }) {
  if (!reading) return null
  if (!reading.available) {
    return (
      <div className="counterfactual-result unavailable">
        <strong>{t.match.analysis.notApplicable}</strong>
        <p>{t.match.analysis.unavailable(reading.unavailable_reason)}</p>
      </div>
    )
  }
  const name = (id) => playerName(metadata, id)
  return (
    <div className="counterfactual-result">
      <strong>{t.match.estimatedResult}</strong>
      <p>{t.match.analysis.whatIfSummary[reading.scenario](reading.comparisons, name)}</p>
      <table className="what-if-table">
        <thead>
          <tr><th>{t.match.analysis.measure}</th><th>{t.match.analysis.actual}</th><th>{t.match.analysis.alternative[reading.scenario]}</th></tr>
        </thead>
        <tbody>
          {reading.comparisons.map((item) => {
            const delta = item.actual !== null && item.alternative !== null ? item.alternative - item.actual : null
            return (
              <tr key={item.key}>
                <th scope="row">{t.match.analysis.comparisonLabels[item.key] ?? item.key}</th>
                <td>{formatValue(item.actual, item.unit, t)}</td>
                <td>
                  {formatValue(item.alternative, item.unit, t)}
                  {delta !== null && Math.abs(delta) >= 0.05 && (
                    <small className={delta > 0 ? 'up' : 'down'}> {delta > 0 ? '+' : '−'}{formatValue(Math.abs(delta), item.unit, t)}</small>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function MomentWorkspace({ matchId, moment, events, metadata, onOpen }) {
  const { t, apiPreferences } = usePreferences()
  const [change, setChange] = useState('earlier_pass')
  const { loading, data: analysis, error } = useMomentAnalysis(matchId, moment, apiPreferences)
  const snapshot = useMemo(() => snapshotOf(analysis?.frame, metadata), [analysis, metadata])
  if (!moment) {
    return <section className="moment-workspace empty-comments"><h2>{t.match.noMomentSelected}</h2><p>{t.match.noMoments}</p></section>
  }
  const sources = eventsOf(moment, events)
  const reading = analysis?.what_if.find((item) => item.scenario === change) ?? null
  const marked = reading?.available
    ? [reading.player_id, ...reading.comparisons.flatMap((item) => [item.player_id, item.alternative_player_id])].filter(Boolean)
    : []
  const simulated = analysis?.frame?.source !== 'video_model'
  const reasons = analysis?.reasons.filter((reason) => reason.points !== 0 || reason.code === 'decisive_fact') ?? []
  const facts = analysis?.facts.filter((fact) => fact.available && !HIDDEN_FACTS.has(fact.key)).slice(0, 6) ?? []
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
        <div className="moment-main">
          <Pitch events={sources} highlightIds={moment.source_event_ids} homeTeamId={metadata.home_team.team_id} label={moment.headline} markedPlayerIds={marked} players={metadata.players} snapshot={snapshot} trail={Math.max(1, sources.length)} />
          {snapshot && <small className="pitch-caption">{simulated ? t.match.analysis.positionsSimulated : t.match.analysis.positionsVideo}</small>}
          <div className="moment-evidence">
            {loading && <p className="moment-evidence-status">{t.match.analysis.loading}</p>}
            {error && <p className="moment-evidence-status">{t.match.analysis.error}</p>}
            {analysis && !analysis.found_in_engine && <p className="moment-evidence-status">{t.match.analysis.notInEngine}</p>}
            {analysis?.found_in_engine && (
              <div className="moment-why">
                <h3>{t.match.analysis.whyKicker}</h3>
                <div className="moment-priority">
                  <strong>{analysis.priority}</strong>
                  <span>{t.match.analysis.priority(analysis.threshold)}</span>
                </div>
                <ul className="reason-chips">
                  {reasons.map((reason) => (
                    <li key={reason.code} title={reason.detail}>
                      {t.match.analysis.reasonLabels[reason.code] ?? reason.code}
                      {reason.points !== 0 && <b>{reason.points > 0 ? `+${reason.points}` : reason.points}</b>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {facts.length > 0 && (
              <div className="moment-facts">
                <h3>{t.match.analysis.factsKicker}</h3>
                <dl>
                  {facts.map((fact, index) => (
                    <div key={`${fact.key}-${fact.team_id}-${fact.player_id}-${index}`}>
                      <dt>
                        {t.match.analysis.factLabels[fact.key] ?? fact.key}
                        {fact.player_id ? ` · ${playerName(metadata, fact.player_id)}` : fact.team_id ? ` · ${teamName(metadata, fact.team_id)}` : ''}
                      </dt>
                      <dd>{formatValue(fact.value, fact.unit, t)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>
        </div>
        <aside className="counterfactual-panel">
          <span className="section-kicker">{t.match.counterfactualKicker}</span>
          <h3>{t.match.counterfactualTitle}</h3>
          <p>{t.match.counterfactualCopy}</p>
          <div className="counterfactual-options">
            {WHAT_IF_ORDER.map((key) => {
              const option = analysis?.what_if.find((item) => item.scenario === key)
              return (
                <button className={[change === key ? 'active' : '', option && !option.available ? 'muted' : ''].join(' ').trim()} key={key} onClick={() => setChange(key)} type="button">
                  {t.match.counterfactualOptions[key]}
                </button>
              )
            })}
          </div>
          {loading ? <p className="moment-evidence-status">{t.match.analysis.loading}</p> : <WhatIfResult metadata={metadata} reading={reading} t={t} />}
          <small className="simulation-disclaimer">{simulated ? t.match.counterfactualDisclaimer : t.match.counterfactualDisclaimerVideo}</small>
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
