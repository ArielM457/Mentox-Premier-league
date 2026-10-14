import { useState } from 'react'
import { formatClock } from '../lib/overlays.js'
import { Pitch } from './Pitch.jsx'

const SPEEDS = [0.5, 1, 2, 4]

export function Player({ t, match, clock, snapshot, overlay, events, channelStatus, videoRef, videoUrl, onVideoUrl, onSeek, onRestart, onOpenMoment }) {
  const [urlDraft, setUrlDraft] = useState(videoUrl)
  const { metadata, duration_ms: duration } = match
  const home = metadata.home_team
  const away = metadata.away_team
  const score = snapshot?.score ?? {}

  function onKeyDown(event) {
    if (event.target.closest('input, select, textarea, button')) return
    if (event.key === ' ' || event.key === 'k') {
      event.preventDefault()
      if (clock.playing) clock.pause()
      else clock.play()
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      onSeek(clock.time + 5000)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      onSeek(clock.time - 5000)
    }
  }

  const pastEvents = events.filter((e) => e.video_time_ms <= clock.time)

  return (
    <section className="player" aria-label={t.timeline} onKeyDown={onKeyDown}>
      <div className="stage" tabIndex={0}>
        <video ref={videoRef} src={videoUrl || undefined} className={videoUrl ? 'video' : 'video hidden'} muted playsInline />
        {!videoUrl && (
          <Pitch events={events} time={clock.time} homeTeamId={home.team_id} players={metadata.players} label={t.syntheticVideo} />
        )}

        <div className="scoreboard" aria-live="polite">
          <span className="team-name home">{home.name}</span>
          <span className="score">{score[home.team_id] ?? 0} – {score[away.team_id] ?? 0}</span>
          <span className="team-name away">{away.name}</span>
          <span className="match-clock">{formatClock(snapshot?.clock_ms ?? 0)}</span>
        </div>

        <span className={`channel channel-${channelStatus}`}>{t.channel[channelStatus]}</span>

        <div className="overlay-zone" aria-live="assertive" aria-atomic="true">
          {overlay && (
            <article key={overlay.message_id} className={`overlay overlay-${overlay.kind} ${overlay.priority >= 90 ? 'overlay-high' : ''}`}>
              <p className="overlay-headline">{overlay.headline}</p>
              {overlay.explanation && <p className="overlay-text">{overlay.explanation}</p>}
              <button type="button" className="link-button" onClick={() => onOpenMoment(overlay)}>
                {t.whyMatters}
              </button>
              <span
                className="overlay-timer"
                style={{ width: `${Math.max(0, Math.min(100, ((overlay.display_until_ms - clock.time) / (overlay.display_until_ms - overlay.video_time_ms)) * 100))}%` }}
              />
            </article>
          )}
        </div>
      </div>

      <div className="controls">
        <button type="button" onClick={clock.playing ? clock.pause : clock.play} aria-label={clock.playing ? t.pause : t.play}>
          {clock.playing ? '❚❚' : '▶'} <span className="sr-label">{clock.playing ? t.pause : t.play}</span>
        </button>
        <button type="button" className="ghost" onClick={() => onSeek(clock.time - 5000)} aria-label={t.back5}>−5s</button>
        <button type="button" className="ghost" onClick={() => onSeek(clock.time + 5000)} aria-label={t.fwd5}>+5s</button>
        <button type="button" className="ghost" onClick={onRestart}>{t.restart}</button>
        <div className="seek">
          <input
            type="range"
            min="0"
            max={duration}
            step="100"
            value={Math.round(clock.time)}
            onChange={(e) => onSeek(Number(e.target.value))}
            aria-label={t.timeline}
            aria-valuetext={formatClock(clock.time)}
          />
          <div className="ticks" aria-hidden="true">
            {pastEvents.map((e) => (
              <span key={e.event_id} className={e.team_id === home.team_id ? 'tick home' : 'tick away'} style={{ left: `${(e.video_time_ms / duration) * 100}%` }} />
            ))}
          </div>
        </div>
        <span className="time">{formatClock(clock.time)} / {formatClock(duration)}</span>
        <label className="speed">
          <span>{t.speed}</span>
          <select value={clock.speed} onChange={(e) => clock.setSpeed(Number(e.target.value))}>
            {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
          </select>
        </label>
      </div>

      <form
        className="video-url"
        onSubmit={(e) => {
          e.preventDefault()
          onVideoUrl(urlDraft.trim())
        }}
      >
        <label htmlFor="video-url">{t.videoUrl}</label>
        <input id="video-url" type="url" value={urlDraft} onChange={(e) => setUrlDraft(e.target.value)} placeholder="https://…/demo.mp4" />
        <button type="submit" className="ghost">{t.useVideo}</button>
        {videoUrl && (
          <button type="button" className="ghost" onClick={() => { setUrlDraft(''); onVideoUrl('') }}>
            {t.removeVideo}
          </button>
        )}
      </form>
    </section>
  )
}
