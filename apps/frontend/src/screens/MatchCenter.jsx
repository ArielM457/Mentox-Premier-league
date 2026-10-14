import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { playerOf, teamOf, useCatalog } from '../hooks/useCatalog.js'
import { useLiveChannel } from '../hooks/useLiveChannel.js'
import { useMatchClock } from '../hooks/useMatchClock.js'
import { formatClock, formatMatchClock, momentIdOf, pastOverlays, visibleOverlay } from '../lib/overlays.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Assistant } from '../components/match/Assistant.jsx'
import { MatchScore } from '../components/match/MatchScore.jsx'
import { OverlayCard } from '../components/match/OverlayCard.jsx'
import { LatencyPanel, MomentFeed, StatsPanel } from '../components/match/Panels.jsx'
import { Pitch } from '../components/match/Pitch.jsx'
import { Timeline } from '../components/match/Timeline.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

const TABS = ['overview', 'events', 'stats', 'tactical', 'insights']
const SPEEDS = [1, 2, 4, 8]
const notify = (promise) => promise.catch(() => {})

export function MatchCenter({ matchId }) {
  const { t } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const match = catalog?.matches.find((m) => m.id === matchId)

  return (
    <AppShell active="matches" dark>
      <section className="match-content">
        <header className="dark-header">
          <div>
            <span className="section-kicker">{t.match.kicker} · {t.matches.scenario[matchId] ?? matchId}</span>
            <h1>{t.match.title}</h1>
          </div>
          <div className="header-live">
            <span className="live-dot" /> {t.match.live}
          </div>
        </header>
        <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />
        {catalog && !match && <ErrorNotice message={`404 · ${matchId}`} />}
        {match && <LiveMatch key={match.id} match={match} />}
      </section>
    </AppShell>
  )
}

function LiveMatch({ match }) {
  const { t, preferences, apiPreferences } = usePreferences()
  const { data: catalog } = useCatalog()
  const matchId = match.id
  const metadata = match.metadata
  const videoRef = useRef(null)
  const clock = useMatchClock(match.durationMs, videoRef)
  const [seekVersion, setSeekVersion] = useState(0)
  const [snapshot, setSnapshot] = useState(null)
  const [tab, setTab] = useState('overview')
  const [popover, setPopover] = useState(null)
  const [actionError, setActionError] = useState(null)

  const live = useLiveChannel({
    matchId,
    prefs: apiPreferences,
    playing: clock.playing,
    speed: clock.speed,
    timeRef: clock.timeRef,
    seekVersion,
  })

  const pastEvents = live.events.filter((e) => e.video_time_ms <= clock.time)
  const crossed = pastEvents.length
  useEffect(() => {
    let active = true
    api.state(matchId, clock.timeRef.current)
      .then((s) => active && setSnapshot(s))
      .catch((err) => active && setActionError(err.message))
    return () => { active = false }
  }, [matchId, crossed, seekVersion, clock.timeRef])

  const seek = useCallback((value) => {
    const next = Math.min(Math.max(0, value), match.durationMs)
    clock.seek(next)
    setSeekVersion((v) => v + 1)
    notify(api.playback(matchId, 'seek', next))
  }, [clock, match.durationMs, matchId])

  const play = () => {
    clock.play()
    notify(api.playback(matchId, 'play', clock.timeRef.current))
  }
  const pause = () => {
    clock.pause()
    notify(api.playback(matchId, 'pause', clock.timeRef.current))
  }
  const replay = () => {
    clock.seek(0)
    setSeekVersion((v) => v + 1)
    notify(api.playback(matchId, 'restart'))
    clock.play()
  }

  const overlay = visibleOverlay(live.overlays, clock.time)
  const history = pastOverlays(live.overlays, clock.time)
  const current = overlay ?? history[0] ?? null
  const finished = clock.time >= match.durationMs
  const minute = snapshot
    ? `${t.match.period(snapshot.period)} · ${formatClock(Math.max(0, snapshot.clock_ms + (clock.time - snapshot.video_time_ms)))}`
    : '—'

  function openMoment(item) {
    pause()
    navigate(paths.moment(matchId, momentIdOf(item)))
  }

  function onKeyDown(event) {
    if (event.target.closest('input, textarea, select, button, [role="slider"]')) return
    if (event.key === ' ' || event.key === 'k') {
      event.preventDefault()
      if (clock.playing) pause()
      else play()
    }
  }

  const pitchProps = {
    homeTeamId: metadata.home_team.team_id,
    players: metadata.players,
    playing: clock.playing,
    onSelectPlayer: (player, event) => setPopover({ player, event }),
    label: t.match.timeline,
  }

  return (
    <div onKeyDown={onKeyDown}>
      <MatchScore metadata={metadata} minute={minute} score={snapshot?.score} status="LIVE" statusLabel={t.matches.status.LIVE} />
      <nav className="match-tabs" role="tablist">
        {TABS.map((item) => (
          <button aria-selected={tab === item} className={tab === item ? 'active' : ''} key={item} onClick={() => setTab(item)} role="tab" type="button">
            {t.match.tabs[item]}
          </button>
        ))}
      </nav>

      <ErrorNotice message={actionError || live.error} onRetry={() => { setActionError(null); live.resync() }} retryLabel={t.common.retry} />

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

      <div className="match-layout">
        <div className="pitch-column">
          {tab === 'stats' ? (
            <StatsPanel metadata={metadata} snapshot={snapshot} />
          ) : tab === 'events' ? (
            <MomentFeed items={history} onOpen={openMoment} />
          ) : tab === 'insights' ? (
            <div className="insights-panel">
              <LatencyPanel samples={live.latency} />
              <MomentFeed detailed items={history.filter((m) => !m.suppressed)} onOpen={openMoment} />
            </div>
          ) : (
            <div className="pitch-wrap">
              <div className="pitch-meta">
                <span>
                  <Icon name="spark" size={16} /> {tab === 'tactical' ? t.match.tacticalCopy : t.match.selected}
                </span>
                <strong>{current ? `${formatMatchClock(current, t.match.period)} · ${current.headline}` : t.match.waiting}</strong>
                <span className={`channel-pill channel-${live.status}`}>{t.match.channel[live.status]}</span>
              </div>
              <Pitch {...pitchProps} events={pastEvents} trail={tab === 'tactical' ? 15 : 6} />
              {tab === 'overview' && (
                <div className="overlay-zone" aria-live="assertive" aria-atomic="true">
                  <OverlayCard onOpen={openMoment} overlay={overlay} playing={clock.playing} time={clock.time} />
                </div>
              )}
              {popover?.player && (
                <button className="player-popover" onClick={() => setPopover(null)} type="button">
                  <strong>
                    {popover.player.shirt_number ? `${popover.player.shirt_number} · ` : ''}
                    {popover.player.name}
                  </strong>
                  <span>
                    {t.moment.eventTypes[popover.event.type] ?? popover.event.type} · {formatClock(popover.event.video_time_ms)} — {t.match.tapToClose}
                  </span>
                  <Icon name="close" size={15} />
                </button>
              )}
            </div>
          )}

          <div className="playback">
            <Button aria-label={clock.playing ? t.match.pause : t.match.play} className="play-main" onClick={clock.playing ? pause : play}>
              {clock.playing ? <Icon name="pause" /> : <Icon name="play" />}
            </Button>
            <Timeline durationMs={match.durationMs} label={t.match.timeline} moments={history.filter((m) => !m.suppressed).slice().reverse()} onSeek={seek} selectedId={current?.message_id} time={clock.time} />
            <div className="playback-tools">
              <span className="playback-time">{formatClock(clock.time)} / {formatClock(match.durationMs)}</span>
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
          <div className="event-chips">
            {history.filter((m) => !m.suppressed).slice(0, 8).map((m) => (
              <button className={current?.message_id === m.message_id ? 'active' : ''} key={m.message_id} onClick={() => openMoment(m)} type="button">
                {formatMatchClock(m, t.match.period)} · {t.kinds[m.kind] ?? m.kind}
              </button>
            ))}
          </div>
        </div>
        <Assistant
          canExplore={Boolean(current)}
          favoriteClub={teamOf(catalog, preferences.favoriteTeamId)}
          favoritePlayer={playerOf(catalog, preferences.favoritePlayerId)}
          matchId={matchId}
          onExplore={() => current && openMoment(current)}
          timeRef={clock.timeRef}
        />
      </div>
    </div>
  )
}
