import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { api } from './api/client.js'
import {
  DemoTools,
  EditorialPanel,
  HistoryPanel,
  LatencyPanel,
  MomentDialog,
  PreferencesPanel,
  QuestionPanel,
  StatsPanel,
  SummaryPanel,
} from './components/Panels.jsx'
import { Player } from './components/Player.jsx'
import { useLiveChannel } from './hooks/useLiveChannel.js'
import { useMatchClock } from './hooks/useMatchClock.js'
import { strings } from './i18n.js'
import { pastOverlays, visibleOverlay } from './lib/overlays.js'

const DEFAULT_MATCH = 'synthetic-acceptance-001'
const PREFS_KEY = 'match-intelligence:prefs'
const DEFAULT_PREFS = { language: 'es', mode: 'casual', level: 'normal', favoriteTeamId: '', favoritePlayerId: '' }

function loadPrefs() {
  try {
    return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY) ?? '{}') }
  } catch {
    return DEFAULT_PREFS
  }
}

const notify = (promise) => promise.catch(() => {})

function App() {
  const [apiOk, setApiOk] = useState(null)
  const [match, setMatch] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [prefs, setPrefs] = useState(loadPrefs)
  const t = strings[prefs.language]

  useEffect(() => {
    document.documentElement.lang = prefs.language
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
    } catch {
      // Sin almacenamiento local las preferencias solo duran la sesión.
    }
  }, [prefs])

  const loadMatch = useCallback(async () => {
    try {
      await api.health()
      setApiOk(true)
      setMatch(await api.match(DEFAULT_MATCH))
      setLoadError(null)
    } catch (err) {
      setApiOk(false)
      setLoadError(err.message)
    }
  }, [])

  useEffect(() => {
    loadMatch()
  }, [loadMatch])

  if (!match) {
    return (
      <main className="page">
        <p className="eyebrow">{t.eyebrow}</p>
        <h1>{t.loading}</h1>
        {loadError && (
          <div className="panel" role="alert">
            <p className="error">{t.apiDown}: {loadError}</p>
            <button type="button" onClick={loadMatch}>{t.retry}</button>
          </div>
        )}
      </main>
    )
  }

  return <MatchView key={match.metadata.match_id + match.loadedAt} match={match} setMatch={setMatch} apiOk={apiOk} prefs={prefs} setPrefs={setPrefs} t={t} />
}

function MatchView({ match, setMatch, apiOk, prefs, setPrefs, t }) {
  const matchId = match.metadata.match_id
  const videoRef = useRef(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [seekVersion, setSeekVersion] = useState(0)
  const [snapshot, setSnapshot] = useState(null)
  const [moment, setMoment] = useState(null)
  const [editorialKey, setEditorialKey] = useState(0)
  const [actionError, setActionError] = useState(null)
  const clock = useMatchClock(match.duration_ms, videoRef)

  // Con preferencias incompletas se sigue mostrando el modo casual en vez de bloquear la pantalla.
  const apiPrefs = useMemo(
    () => (prefs.mode === 'player' && !prefs.favoritePlayerId ? { ...prefs, mode: 'casual' } : prefs),
    [prefs],
  )

  const live = useLiveChannel({
    matchId,
    prefs: apiPrefs,
    playing: clock.playing,
    speed: clock.speed,
    timeRef: clock.timeRef,
    seekVersion,
  })

  const crossed = live.events.filter((e) => e.video_time_ms <= clock.time).length
  useEffect(() => {
    let active = true
    api.state(matchId, clock.timeRef.current)
      .then((s) => active && setSnapshot(s))
      .catch((err) => active && setActionError(err.message))
    return () => { active = false }
  }, [matchId, crossed, seekVersion, clock.timeRef])

  const displaySnapshot = snapshot && {
    ...snapshot,
    clock_ms: Math.max(0, snapshot.clock_ms + (clock.time - snapshot.video_time_ms)),
  }

  const seek = useCallback((value) => {
    const next = Math.min(Math.max(0, value), match.duration_ms)
    clock.seek(next)
    setSeekVersion((v) => v + 1)
    notify(api.playback(matchId, 'seek', next))
  }, [clock, match.duration_ms, matchId])

  const controls = {
    ...clock,
    play: () => {
      clock.play()
      notify(api.playback(matchId, 'play', clock.timeRef.current))
    },
    pause: () => {
      clock.pause()
      notify(api.playback(matchId, 'pause', clock.timeRef.current))
    },
  }

  const restart = () => {
    clock.pause()
    clock.seek(0)
    setSeekVersion((v) => v + 1)
    notify(api.playback(matchId, 'restart'))
  }

  async function reload(injectErrorIn) {
    setActionError(null)
    try {
      const detail = await api.loadMatch({ match_id: matchId, inject_error_in: injectErrorIn })
      clock.pause()
      setMatch({ ...detail, loadedAt: Date.now() })
    } catch (err) {
      setActionError(err.message)
    }
  }

  const overlay = visibleOverlay(live.overlays, clock.time)
  const history = pastOverlays(live.overlays, clock.time)
  const finished = clock.time >= match.duration_ms
  const error = actionError || live.error

  return (
    <main className="page">
      <header className="top">
        <div>
          <p className="eyebrow">{t.eyebrow}</p>
          <h1>{match.metadata.home_team.name} <span className="vs">vs</span> {match.metadata.away_team.name}</h1>
        </div>
        <p className={apiOk ? 'api ok' : 'api down'} role="status">
          {apiOk ? t.apiOk : t.apiDown} · <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">Swagger</a>
        </p>
      </header>

      {error && (
        <div className="banner" role="alert">
          <span>{error}</span>
          <button type="button" className="ghost" onClick={() => { setActionError(null); live.resync() }}>{t.retry}</button>
        </div>
      )}

      <div className="layout">
        <div className="main-column">
          <Player
            t={t}
            match={match}
            clock={controls}
            snapshot={displaySnapshot}
            overlay={overlay}
            events={live.events}
            channelStatus={live.status}
            videoRef={videoRef}
            videoUrl={videoUrl}
            onVideoUrl={setVideoUrl}
            onSeek={seek}
            onRestart={restart}
            onOpenMoment={(m) => { controls.pause(); setMoment(m) }}
          />
          <HistoryPanel t={t} items={history} onOpen={setMoment} />
          <QuestionPanel t={t} matchId={matchId} prefs={apiPrefs} time={clock.time} metadata={match.metadata} />
        </div>
        <aside className="side-column">
          <PreferencesPanel t={t} prefs={prefs} onChange={setPrefs} metadata={match.metadata} />
          <StatsPanel t={t} snapshot={snapshot} metadata={match.metadata} />
          <SummaryPanel key={JSON.stringify(apiPrefs)} t={t} matchId={matchId} prefs={apiPrefs} finished={finished} onCreated={() => setEditorialKey((k) => k + 1)} />
          <EditorialPanel t={t} matchId={matchId} refreshKey={editorialKey} onChanged={() => setEditorialKey((k) => k + 1)} />
          <LatencyPanel t={t} samples={live.latency} />
          <DemoTools t={t} onReload={reload} />
        </aside>
      </div>

      {moment && (
        <MomentDialog
          t={t}
          matchId={matchId}
          overlay={moment}
          metadata={match.metadata}
          onClose={() => setMoment(null)}
          onReported={() => { live.resync(); setEditorialKey((k) => k + 1) }}
        />
      )}
    </main>
  )
}

export default App
