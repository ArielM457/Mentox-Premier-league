import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { preferencesForMatch, usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { playerOf, teamOf, useCatalog } from '../hooks/useCatalog.js'
import { useLiveChannel } from '../hooks/useLiveChannel.js'
import { useMatchClock } from '../hooks/useMatchClock.js'
import { useTrackingFrames } from '../hooks/useTrackingFrames.js'
import { useVisionCapture } from '../hooks/useVisionCapture.js'
import { useVisionObservationChannel } from '../hooks/useVisionObservationChannel.js'
import { formatClock, formatMatchClock, momentIdOf, pastOverlays, visibleOverlay } from '../lib/overlays.js'
import { recordExperience } from '../lib/experience.js'
import { readMatchSession, saveMatchSession } from '../lib/matchSession.js'
import { filterSummaryMoments, SUMMARY_TYPES } from '../lib/summaryMoments.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Assistant } from '../components/match/Assistant.jsx'
import { MatchScore } from '../components/match/MatchScore.jsx'
import { LiveSummarySelector } from '../components/match/LiveSummarySelector.jsx'
import { MomentCarousel } from '../components/match/MomentCarousel.jsx'
import { LiveTrackingPitch } from '../components/match/LiveTrackingPitch.jsx'
import { OverlayCard } from '../components/match/OverlayCard.jsx'
import { StatsPanel } from '../components/match/Panels.jsx'
import { Timeline } from '../components/match/Timeline.jsx'
import { InsightsPanel, MomentSelector, MomentWorkspace, TacticalPanel, VisionCard, VisionVideoOverlay } from '../components/match/LiveExperiencePanels.jsx'
import { LiveNarrator } from '../components/match/LiveNarrator.jsx'
import { Button, Spinner } from '../components/ui/Button.jsx'
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
  const matchApiPreferences = useMemo(
    () => preferencesForMatch(apiPreferences, metadata),
    [apiPreferences, metadata],
  )
  const videoRef = useRef(null)
  const matchViewRef = useRef(null)
  const liveDurationMs = match.durationMs
  const clock = useMatchClock(liveDurationMs, videoRef, matchId)
  const [restoredSession] = useState(() => readMatchSession(matchId))
  const [seekVersion, setSeekVersion] = useState(0)
  const [snapshot, setSnapshot] = useState(null)
  const [tab, setTab] = useState(() => restoredSession.tab ?? 'match')
  const [popover, setPopover] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [preparingVision, setPreparingVision] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [simulationStarted, setSimulationStarted] = useState(() => restoredSession.simulationStarted || clock.time > 0)
  const [assistantOpen, setAssistantOpen] = useState(() => window.localStorage.getItem('itg:match-agent-open') !== 'false')
  const [fullscreen, setFullscreen] = useState(false)
  const [selectedPlayerId, setSelectedPlayerId] = useState(() => restoredSession.selectedPlayerId ?? null)
  const [selectedMomentId, setSelectedMomentId] = useState(() => restoredSession.selectedMomentId ?? null)
  const [summaryType, setSummaryType] = useState(() => SUMMARY_TYPES.includes(restoredSession.summaryType) ? restoredSession.summaryType : 'short')
  const [summaryPlayerId, setSummaryPlayerId] = useState(() => restoredSession.summaryPlayerId ?? '')
  const [visionOpen, setVisionOpen] = useState(() => Boolean(restoredSession.visionOpen))
  const [dismissedOverlays, setDismissedOverlays] = useState(() => new Set())
  const activeTab = TABS.includes(tab) ? tab : 'match'
  const hasVideoSource = match.video?.kind === 'file' && Boolean(match.video.url)
  const matchAgentOpen = activeTab === 'match' && assistantOpen && !hasVideoSource
  const analystPerspective = ['analyst', 'professional_analyst'].includes(preferences.mode)
  const liveCommentsEnabled = preferences.mode === 'professional_analyst' || preferences.liveComments
  const preferredSummaryPlayerId = metadata.players.some((player) => player.player_id === preferences.favoritePlayerId)
    ? preferences.favoritePlayerId
    : metadata.players[0]?.player_id ?? ''
  const selectedSummaryPlayerId = metadata.players.some((player) => player.player_id === summaryPlayerId)
    ? summaryPlayerId
    : preferredSummaryPlayerId

  useEffect(() => {
    recordExperience(matchId)
  }, [matchId])

  useEffect(() => {
    window.localStorage.setItem('itg:match-agent-open', String(assistantOpen))
  }, [assistantOpen])

  useEffect(() => {
    saveMatchSession(matchId, {
      tab: activeTab,
      selectedMomentId,
      selectedPlayerId,
      summaryPlayerId: selectedSummaryPlayerId,
      summaryType,
      simulationStarted,
      visionOpen,
    })
  }, [activeTab, matchId, selectedMomentId, selectedPlayerId, selectedSummaryPlayerId, simulationStarted, summaryType, visionOpen])

  useEffect(() => {
    const restore = window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => window.scrollTo({ top: Number(restoredSession.scrollY) || 0 }))
    })
    const rememberScroll = () => saveMatchSession(matchId, { scrollY: window.scrollY })
    window.addEventListener('pagehide', rememberScroll)
    return () => {
      window.cancelAnimationFrame(restore)
      rememberScroll()
      window.removeEventListener('pagehide', rememberScroll)
    }
  }, [matchId, restoredSession.scrollY])

  useEffect(() => {
    const syncFullscreen = () => setFullscreen(document.fullscreenElement === matchViewRef.current)
    document.addEventListener('fullscreenchange', syncFullscreen)
    return () => document.removeEventListener('fullscreenchange', syncFullscreen)
  }, [])

  const live = useLiveChannel({
    matchId,
    prefs: matchApiPreferences,
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
  const displayedOverlay = overlay && !dismissedOverlays.has(overlay.message_id) ? overlay : null
  const history = pastOverlays(live.overlays, clock.time)
  const current = overlay ?? history[0] ?? null
  const moments = history.filter((moment) => !moment.suppressed)
  const timelineMoments = moments.filter((moment) => ['goal', 'shot', 'recovery', 'turnover'].includes(moment.kind) || moment.priority >= 70)
  const selectedMoment = moments.find((moment) => moment.message_id === selectedMomentId) ?? current
  const summaryMoments = filterSummaryMoments({
    events: pastEvents,
    moments: history,
    playerId: selectedSummaryPlayerId,
    type: summaryType,
  })
  const summarySelectedMoment = summaryMoments.find((moment) => moment.message_id === selectedMomentId) ?? summaryMoments[0] ?? null
  const finished = clock.time >= liveDurationMs
  const behindLive = !finished && clock.time < clock.liveEdge - 750
  const timelineDurationMs = finished ? liveDurationMs : Math.max(100, clock.liveEdge)
  const clockSpeed = clock.speed
  const setClockSpeed = clock.setSpeed
  useEffect(() => {
    if (!behindLive && clockSpeed !== 1) setClockSpeed(1)
  }, [behindLive, clockSpeed, setClockSpeed])
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
      await api.simulate(matchId, matchApiPreferences)
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

  const playbackControls = (
    <section className="replay-controls pitch-replay-controls" aria-label={t.match.timeline}>
      <div className="playback">
        <Button aria-label={clock.playing ? t.match.pause : t.match.play} className="play-main" disabled={preparingVision} onClick={clock.playing ? pause : play}>
          {clock.playing ? <Icon name="pause" /> : <Icon name="play" />}
        </Button>
        <Timeline durationMs={timelineDurationMs} label={t.match.timeline} moments={timelineMoments.slice().reverse()} onSeek={seek} selectedId={selectedMoment?.message_id} time={clock.time} />
        <div className="playback-tools">
          {behindLive && <label className="speed-select"><span className="sr-only">{t.match.speed}</span><select onChange={(event) => clock.setSpeed(Number(event.target.value))} value={clock.speed}>{SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}</select></label>}
          <button className={`live-edge-control ${behindLive ? 'is-behind' : ''}`} onClick={() => seek(clock.liveEdge)} type="button"><span aria-hidden="true" />{t.match.channel.live}</button>
        </div>
      </div>
    </section>
  )

  return (
    <div className={analystPerspective ? 'analyst-pitch-view' : undefined} onKeyDown={onKeyDown}>
      <MatchScore metadata={metadata} minute={minute} score={snapshot?.score} status={finished ? "FT" : "LIVE"} statusLabel={finished ? t.matches.status.FT : t.matches.status.LIVE} />
      <div className="simulation-toolbar">
        <div>
          <strong>{t.match.liveExperienceTitle}</strong>
          <span>{simulating ? t.common.processing : simulationStarted ? (clock.playing ? t.match.playingState : t.match.pauseState) : t.match.liveExperienceCopy}</span>
        </div>
        <div className="live-toolbar-actions">
          {!simulationStarted ? (
            <Button busy={simulating} busyLabel={t.common.processing} onClick={startSimulation} variant="lime"><Icon name="play" size={17} /> {t.match.startLive}</Button>
          ) : (
            <>
              <Button busy={preparingVision} busyLabel={t.match.preparingVision} onClick={clock.playing ? pause : play} variant="lime"><Icon name={clock.playing ? 'pause' : 'play'} size={17} /> {clock.playing ? t.match.pauseLive : t.match.resumeLive}</Button>
              <Button onClick={replay} variant="ghost"><Icon name="replay" size={17} /> {t.match.restartLive}</Button>
            </>
          )}
        </div>
      </div>
      {simulating && <LoadingScreen message={t.common.processing} compact />}
      <div className={`match-tabs-row ${!hasVideoSource && activeTab === 'match' ? 'with-agent-control' : ''}`}>
        <Tabs items={TABS.map((key) => [key, t.match.tabs[key]])} value={activeTab} onChange={setTab} label={t.match.viewTabs} id="match-view" />
        {!hasVideoSource && activeTab === 'match' && (
          <button
            aria-controls="match-agent-panel"
            aria-expanded={assistantOpen}
            aria-label={assistantOpen ? t.match.closeAssistant : t.match.openAssistant}
            className="match-agent-arrow"
            onClick={() => setAssistantOpen((value) => !value)}
            title={assistantOpen ? t.match.closeAssistant : t.match.openAssistant}
            type="button"
          >
            <Icon name={assistantOpen ? 'arrow' : 'back'} size={18} />
          </button>
        )}
      </div>

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
              <LiveSummarySelector onPlayerChange={setSummaryPlayerId} onTypeChange={setSummaryType} playerId={selectedSummaryPlayerId} players={metadata.players} type={summaryType} />
              <MomentWorkspace events={pastEvents} matchId={matchId} metadata={metadata} moment={summarySelectedMoment} moments={summaryMoments} onOpen={openMoment} onSelect={selectMoment} />
              <InsightsPanel events={pastEvents} metadata={metadata} moments={summaryMoments} onSelect={selectMoment} selectedId={summarySelectedMoment?.message_id} />
            </div>
          ) : activeTab === 'tactical' ? (
            <TacticalPanel compact={false} events={pastEvents} matchId={matchId} metadata={metadata} />
          ) : (
            <>
              <div className="pitch-wrap">
                <div className="match-view-controls">
                  {!hasVideoSource && (
                    <label className="view-switch">
                      <span>{t.match.liveCommentsToggle}</span>
                      <input checked={preferences.mode === 'professional_analyst' || preferences.liveComments} disabled={preferences.mode === 'professional_analyst'} onChange={(event) => update({ liveComments: event.target.checked })} type="checkbox" />
                      <span aria-hidden="true" className="switch-track"><span /></span>
                    </label>
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
                  <span aria-busy={live.status === 'connecting' || undefined} className={`channel-pill channel-${live.status}`}>
                    {live.status === 'connecting' && <Spinner size="small" />} {t.match.channel[live.status]}
                  </span>
                </div>
                <div className={`match-stage-layout ${hasVideoSource ? 'video-only' : ''}`}>
                  <div className="match-stage-main">
                    <div className="match-playback-stage">
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
                      {playbackControls}
                    </div>
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
                  </div>
                  {!hasVideoSource && (
                    <aside className="match-commentary-rail">
                      <div className="match-commentary-slot">
                        {liveCommentsEnabled && pastEvents.length ? (
                          <LiveNarrator events={pastEvents} metadata={metadata} />
                        ) : (
                          <section className="live-narrator live-narrator-empty" aria-label={t.match.liveCommentsTitle}>
                            <header><span className="live-dot" /><strong>{t.match.liveCommentsTitle}</strong></header>
                            <p>{liveCommentsEnabled ? t.match.waitingCommentary : t.match.liveCommentsCopy}</p>
                          </section>
                        )}
                      </div>
                      <section className="match-moment-panel" aria-label={t.match.momentSelector}>
                        <header><span><Icon name="spark" size={14} /> {t.match.selected}</span></header>
                        {displayedOverlay ? (
                          <div className="match-current-moment" aria-live="assertive" aria-atomic="true">
                            <OverlayCard onClose={() => setDismissedOverlays((currentIds) => new Set(currentIds).add(displayedOverlay.message_id))} onOpen={openMoment} overlay={displayedOverlay} playing={clock.playing} time={clock.time} />
                          </div>
                        ) : (
                          <p className="match-moment-empty">{t.match.waiting}</p>
                        )}
                        <MomentSelector moments={moments} onSelect={selectMoment} selected={selectedMoment} />
                        <MomentCarousel currentId={current?.message_id} moments={moments.slice(0, 8)} onOpen={openMoment} />
                      </section>
                    </aside>
                  )}
                </div>
              </div>
            </>
          )}
          {activeTab === 'match' && (
            <>
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
