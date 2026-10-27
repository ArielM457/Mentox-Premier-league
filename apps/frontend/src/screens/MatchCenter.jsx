import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { playerOf, teamOf, useCatalog } from '../hooks/useCatalog.js'
import { useLiveChannel } from '../hooks/useLiveChannel.js'
import { useMatchClock } from '../hooks/useMatchClock.js'
import { useTrackingFrames } from '../hooks/useTrackingFrames.js'
import { useVisionCapture } from '../hooks/useVisionCapture.js'
import { useVisionObservationChannel } from '../hooks/useVisionObservationChannel.js'
import { formatClock, formatMatchClock, momentIdOf, pastOverlays, visibleOverlay } from '../lib/overlays.js'
import { recordExperience } from '../lib/experience.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Assistant } from '../components/match/Assistant.jsx'
import { MatchScore } from '../components/match/MatchScore.jsx'
import { MomentCarousel } from '../components/match/MomentCarousel.jsx'
import { LiveTrackingPitch } from '../components/match/LiveTrackingPitch.jsx'
import { OverlayCard } from '../components/match/OverlayCard.jsx'
import { StatsPanel } from '../components/match/Panels.jsx'
import { Timeline } from '../components/match/Timeline.jsx'
import { InsightsPanel, LiveCommentsPanel, MomentSelector, MomentWorkspace, TacticalPanel, VisionCard, VisionVideoOverlay } from '../components/match/LiveExperiencePanels.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingScreen } from '../components/ui/Feedback.jsx'
import { Tabs } from '../components/ui/Tabs.jsx'
import { Icon } from '../components/ui/Icon.jsx'

const TABS = ['match', 'summary', 'stats', 'tactical']
const SPEEDS = [1, 2, 4, 8]
const notify = (promise) => promise.catch(() => {})

export function MatchCenter({ matchId }) {
  const { t } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const match = catalog?.matches.find((m) => m.id === matchId)

  return (
    <AppShell active="matches">
      <section className="match-content">
        <header className="dark-header">
          <div>
            <h1>{t.match.title}</h1>
          </div>
          <span className="replay-notice">{t.common.syntheticData}</span>
        </header>
        <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />
        {catalog && !match && <ErrorNotice message={`404 · ${matchId}`} />}
        {!catalog && !error && <LoadingScreen />}
        {match && <LiveMatch key={match.id} match={match} />}
      </section>
    </AppShell>
  )
}

function LiveMatch({ match }) {
  const { t, preferences, apiPreferences, update } = usePreferences()
  const { data: catalog } = useCatalog()
  const matchId = match.id
  const metadata = match.metadata
  const videoRef = useRef(null)
  const matchViewRef = useRef(null)
  const liveDurationMs = match.durationMs
  const clock = useMatchClock(liveDurationMs, videoRef, matchId)
  const [seekVersion, setSeekVersion] = useState(0)
  const [snapshot, setSnapshot] = useState(null)
  const [tab, setTab] = useState('match')
  const [popover, setPopover] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [preparingVision, setPreparingVision] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [simulationStarted, setSimulationStarted] = useState(() => clock.time > 0)
  const [assistantOpen, setAssistantOpen] = useState(() => window.localStorage.getItem('itg:match-agent-open') !== 'false')
  const [fullscreen, setFullscreen] = useState(false)
  const [selectedPlayerId, setSelectedPlayerId] = useState(null)
  const [selectedMomentId, setSelectedMomentId] = useState(null)
  const [visionOpen, setVisionOpen] = useState(false)
  const activeTab = TABS.includes(tab) ? tab : 'match'
  const hasVideoSource = match.video?.kind === 'file' && Boolean(match.video.url)
  const matchAgentOpen = activeTab === 'match' && assistantOpen && !hasVideoSource

  useEffect(() => {
    recordExperience(matchId)
  }, [matchId])

  useEffect(() => {
    window.localStorage.setItem('itg:match-agent-open', String(assistantOpen))
  }, [assistantOpen])

  useEffect(() => {
    const syncFullscreen = () => setFullscreen(document.fullscreenElement === matchViewRef.current)
    document.addEventListener('fullscreenchange', syncFullscreen)
    return () => document.removeEventListener('fullscreenchange', syncFullscreen)
  }, [])

  const live = useLiveChannel({
    matchId,
    prefs: apiPreferences,
    playing: clock.playing,
    speed: clock.speed,
    timeRef: clock.timeRef,
    seekVersion,
  })
  const tracking = useTrackingFrames({
    durationMs: liveDurationMs,
    matchId,
    seekVersion,
    timeMs: clock.time,
  })
  const visionChannel = useVisionObservationChannel(matchId, seekVersion)
  const visionCapture = useVisionCapture({
    matchId,
    playing: clock.playing,
    timeRef: clock.timeRef,
    videoRef,
  })

  const crossed = live.events.filter((event) => event.video_time_ms <= clock.time).length
  const pastEvents = useMemo(() => live.events.slice(0, crossed), [live.events, crossed])
  useEffect(() => {
    let active = true
    api.state(matchId, clock.timeRef.current)
      .then((s) => active && setSnapshot(s))
      .catch((err) => active && setActionError(err.message))
    return () => { active = false }
  }, [matchId, crossed, seekVersion, clock.timeRef])

  const seek = useCallback((value) => {
    const next = Math.min(Math.max(0, value), liveDurationMs)
    clock.seek(next)
    if (next > 0) setSimulationStarted(true)
    setSeekVersion((v) => v + 1)
    notify(api.playback(matchId, 'seek', next))
    notify(api.visionPlayback('seek', next, matchId))
  }, [clock, liveDurationMs, matchId])

  const play = async () => {
    if (preparingVision) return
    setSimulationStarted(true)
    setActionError(null)
    if (hasVideoSource) {
      setPreparingVision(true)
      try {
        await api.prepareVisionModels()
      } catch (err) {
        setActionError(err.message)
        setPreparingVision(false)
        return
      }
      setPreparingVision(false)
    }
    clock.play()
    notify(api.playback(matchId, 'play', clock.timeRef.current))
    notify(api.visionPlayback('play', clock.timeRef.current, matchId))
  }
  const pause = () => {
    clock.pause()
    notify(api.playback(matchId, 'pause', clock.timeRef.current))
    notify(api.visionPlayback('pause', clock.timeRef.current, matchId))
  }
  const replay = async () => {
    setSimulationStarted(true)
    clock.seek(0)
    setSeekVersion((v) => v + 1)
    notify(api.playback(matchId, 'restart'))
    notify(api.visionPlayback('restart', 0, matchId))
    await play()
  }

  const overlay = visibleOverlay(live.overlays, clock.time)
  const history = pastOverlays(live.overlays, clock.time)
  const current = overlay ?? history[0] ?? null
  const moments = history.filter((moment) => !moment.suppressed)
  const timelineMoments = moments.filter((moment) => ['goal', 'shot', 'recovery', 'turnover'].includes(moment.kind) || moment.priority >= 70)
  const selectedMoment = moments.find((moment) => moment.message_id === selectedMomentId) ?? current
  const finished = clock.time >= liveDurationMs
  const minute = snapshot
    ? `${t.match.period(snapshot.period)} · ${formatClock(Math.max(0, snapshot.clock_ms + (clock.time - snapshot.video_time_ms)))}`
    : '—'

  function openMoment(item) {
    pause()
    navigate(paths.moment(matchId, momentIdOf(item)))
  }

  async function startSimulation() {
    setSimulating(true)
    setActionError(null)
    if (finished) seek(0)
    pause()
    try {
      await api.simulate(matchId, apiPreferences)
      play()
      live.resync()
    } catch (error) {
      setActionError(error.message)
    } finally {
      setSimulating(false)
    }
  }

  function selectMoment(moment, openTab = false) {
    setSelectedMomentId(moment.message_id)
    if (openTab) setTab('summary')
  }

  function changeMode(mode) {
    update({ mode })
  }

  async function toggleFullscreen() {
    setActionError(null)
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
      else await matchViewRef.current?.requestFullscreen()
    } catch {
      setActionError(t.match.fullscreenUnavailable)
    }
  }

  function onKeyDown(event) {
    if (event.target.closest('input, textarea, select, button, [role="slider"]')) return
    if (event.key === ' ' || event.key === 'k') {
      event.preventDefault()
      if (clock.playing) pause()
      else play()
    }
  }

  const selectPlayer = (player, event) => {
    const next = selectedPlayerId === player.player_id ? null : player.player_id
    setSelectedPlayerId(next)
    setPopover(next ? { player, event } : null)
  }

  return (
    <div onKeyDown={onKeyDown}>
      <MatchScore metadata={metadata} minute={minute} score={snapshot?.score} status={finished ? "FT" : "LIVE"} statusLabel={finished ? t.matches.status.FT : t.matches.status.LIVE} />
      <div className="simulation-toolbar">
        <div>
          <strong>{t.match.liveExperienceTitle}</strong>
          <span>{simulating ? t.common.loading : simulationStarted ? (clock.playing ? t.match.playingState : t.match.pauseState) : t.match.liveExperienceCopy}</span>
        </div>
        <div className="live-toolbar-actions">
          <div className="live-mode-switch" aria-label={t.match.viewMode} role="group">
            {['casual', 'analyst'].map((mode) => <button aria-pressed={preferences.mode === mode} className={preferences.mode === mode ? 'active' : ''} key={mode} onClick={() => changeMode(mode)} type="button">{t.modes[mode].name}</button>)}
          </div>
          {!simulationStarted ? (
            <Button disabled={simulating} onClick={startSimulation} variant="lime"><Icon name="play" size={17} /> {simulating ? t.common.loading : t.match.startLive}</Button>
          ) : (
            <>
              <Button disabled={preparingVision} onClick={clock.playing ? pause : play} variant="lime"><Icon name={clock.playing ? 'pause' : 'play'} size={17} /> {preparingVision ? t.match.preparingVision : (clock.playing ? t.match.pauseLive : t.match.resumeLive)}</Button>
              <Button onClick={replay} variant="ghost"><Icon name="replay" size={17} /> {t.match.restartLive}</Button>
            </>
          )}
        </div>
      </div>
      {simulating && <LoadingScreen message={t.common.loading} compact />}
      <Tabs items={TABS.map((key) => [key, t.match.tabs[key]])} value={activeTab} onChange={setTab} label={t.match.viewTabs} id="match-view" />

      <ErrorNotice message={actionError || live.error || tracking.error} onRetry={() => { setActionError(null); live.resync(); setSeekVersion((value) => value + 1) }} retryLabel={t.common.retry} />

      {finished && (
        <div className="finished-banner" role="status">
          <span>
            <Icon name="flag" size={18} /> {t.match.finished}
          </span>
          <Button variant="lime" onClick={() => navigate(paths.recap(matchId))}>
            {t.match.goRecap} <Icon name="arrow" size={17} />
          </Button>
        </div>
      )}

      <div aria-labelledby={`match-view-${activeTab}`} className={`match-layout ${matchAgentOpen ? 'agent-open' : 'agent-closed'}`} id="match-view-panel" role="tabpanel">
        <div className="pitch-column" ref={matchViewRef}>
          {activeTab === 'stats' ? (
            <StatsPanel metadata={metadata} snapshot={snapshot} timeMs={clock.time} />
          ) : activeTab === 'summary' ? (
            <div className="match-summary">
              <MomentWorkspace events={pastEvents} matchId={matchId} metadata={metadata} moment={selectedMoment} onOpen={openMoment} />
              <InsightsPanel events={pastEvents} metadata={metadata} moments={history} onOpen={openMoment} />
            </div>
          ) : activeTab === 'tactical' ? (
            <TacticalPanel compact={false} events={pastEvents} matchId={matchId} metadata={metadata} />
          ) : (
            <>
              <div className="pitch-wrap">
                <div className="match-view-controls">
                  {!hasVideoSource && (
                    <>
                      <label className="view-switch">
                        <span>{t.match.liveCommentsToggle}</span>
                        <input checked={preferences.liveComments} onChange={(event) => update({ liveComments: event.target.checked })} type="checkbox" />
                        <span aria-hidden="true" className="switch-track"><span /></span>
                      </label>
                      <label className="view-switch">
                        <span><Icon name="spark" size={15} /> {t.match.assistantToggle}</span>
                        <input aria-controls="match-agent-panel" checked={assistantOpen} onChange={(event) => setAssistantOpen(event.target.checked)} type="checkbox" />
                        <span aria-hidden="true" className="switch-track"><span /></span>
                      </label>
                    </>
                  )}
                  <Button
                    aria-label={fullscreen ? t.match.exitFullscreen : t.match.enterFullscreen}
                    className="match-fullscreen-toggle"
                    onClick={toggleFullscreen}
                    title={fullscreen ? t.match.exitFullscreen : t.match.enterFullscreen}
                    variant="ghost"
                  >
                    <Icon name={fullscreen ? 'fullscreenExit' : 'fullscreen'} size={18} />
                  </Button>
                </div>
                <div className="pitch-meta">
                  <span><Icon name="spark" size={16} /> {t.match.selected}</span>
                  <strong>{hasVideoSource ? t.match.visionVideoAnalysis : current ? `${formatMatchClock(current, t.match.period)} · ${current.headline}` : t.match.waiting}</strong>
                  <span className={`channel-pill channel-${live.status}`}>{t.match.channel[live.status]}</span>
                </div>
                {hasVideoSource ? (
                  <div className="match-video-stage">
                    <video
                      className="match-source-video"
                      crossOrigin="anonymous"
                      onEnded={pause}
                      playsInline
                      preload="metadata"
                      ref={videoRef}
                      src={match.video.url}
                    />
                    <VisionVideoOverlay matchId={matchId} observations={visionChannel.observations} timeMs={clock.time} />
                  </div>
                ) : <LiveTrackingPitch
                  events={pastEvents}
                  eventTypeLabels={t.moment.eventTypes}
                  frames={tracking.frames}
                  homeTeamId={metadata.home_team.team_id}
                  label={t.match.timeline}
                  loading={tracking.loading}
                  onSelectPlayer={selectPlayer}
                  pitchLengthM={metadata.pitch_length_m}
                  pitchWidthM={metadata.pitch_width_m}
                  players={metadata.players}
                  playing={clock.playing}
                  selectedPlayerId={selectedPlayerId}
                  situationLabels={t.match.situations}
                  sourceLabel={tracking.source === 'video_model' ? t.match.trackingVideo : t.match.trackingSynthetic}
                  speed={clock.speed}
                  timeMs={clock.time}
                />}
                {!hasVideoSource && <div className="overlay-zone" aria-live="assertive" aria-atomic="true"><OverlayCard onOpen={openMoment} overlay={overlay} playing={clock.playing} time={clock.time} /></div>}
                {popover?.player && (
                  <button className="player-popover" onClick={() => setPopover(null)} type="button">
                    <strong>
                      {popover.player.shirt_number ? `${popover.player.shirt_number} · ` : ''}
                      {popover.player.name}
                    </strong>
                    <span>
                      {popover.event ? `${t.moment.eventTypes[popover.event.type] ?? popover.event.type} · ${formatClock(popover.event.video_time_ms)}` : t.match.playerReady} — {t.match.tapToClose}
                    </span>
                    <Icon name="close" size={15} />
                  </button>
                )}
                {!hasVideoSource && <MomentSelector moments={moments} onSelect={selectMoment} selected={selectedMoment} />}
              </div>
              {!hasVideoSource && preferences.liveComments && <LiveCommentsPanel compact events={pastEvents} metadata={metadata} moments={history} timeMs={clock.time} />}
            </>
          )}
          <section className="replay-controls" aria-label={t.match.timeline}>
          <div className="timeline-heading"><strong>{t.match.timelineTitle}</strong><span>{timelineMoments.length || t.match.timelineEmpty}</span></div>
          <div className="playback">
            <Button aria-label={clock.playing ? t.match.pause : t.match.play} className="play-main" disabled={preparingVision} onClick={clock.playing ? pause : play}>
              {clock.playing ? <Icon name="pause" /> : <Icon name="play" />}
            </Button>
            <Timeline durationMs={liveDurationMs} label={t.match.timeline} moments={timelineMoments.slice().reverse()} onSeek={seek} selectedId={selectedMoment?.message_id} time={clock.time} />
            <div className="playback-tools">
              <span className="playback-time">{formatClock(clock.time)} / {formatClock(liveDurationMs)}</span>
              <label className="speed-select">
                <span className="sr-only">{t.match.speed}</span>
                <select onChange={(event) => clock.setSpeed(Number(event.target.value))} value={clock.speed}>
                  {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
                </select>
              </label>
              <Button variant="ghost" onClick={replay}>
                <Icon name="replay" /> {t.match.replay}
              </Button>
            </div>
          </div>
          </section>
          {activeTab === 'match' && (
            <>
              {!hasVideoSource && <MomentCarousel currentId={current?.message_id} moments={moments.slice(0, 8)} onOpen={openMoment} />}
              {hasVideoSource ? (
                <VisionCard capture={visionCapture} liveChannel={visionChannel} matchId={matchId} seekVersion={seekVersion} timeMs={clock.time} videoMode />
              ) : (
                <details className="vision-details" open={visionOpen} onToggle={(event) => setVisionOpen(event.currentTarget.open)}>
                  <summary>{t.match.visionDetails}</summary>
                  <p>{t.match.visionDescription}</p>
                  {visionOpen && <VisionCard capture={visionCapture} liveChannel={visionChannel} matchId={matchId} seekVersion={seekVersion} timeMs={clock.time} videoMode={false} />}
                </details>
              )}
            </>
          )}
        </div>
        {matchAgentOpen && (
          <div className="match-agent-rail" id="match-agent-panel">
            <Assistant canExplore={Boolean(current)} favoriteClub={teamOf(catalog, preferences.favoriteTeamId)} favoritePlayer={playerOf(catalog, preferences.favoritePlayerId)} matchId={matchId} onExplore={() => current && openMoment(current)} timeRef={clock.timeRef} />
          </div>
        )}
      </div>
    </div>
  )
}
