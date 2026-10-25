import { formatClock } from '../../lib/overlays.js'

const SYMBOL = { goal: '⚽', shot: '◎', recovery: '✦', turnover: '✦', pressure: '✦', progressive_pass: '→', foul: '!', yellow_card: '■', red_card: '■', injury_stoppage: '+', player_quiet: '·' }

// Solo muestra momentos ya ocurridos para no adelantar el partido.
export function Timeline({ moments, durationMs, time, selectedId, onSeek, label }) {
  const pct = (ms) => `${Math.min(100, Math.max(0, (ms / durationMs) * 100))}%`

  function seekFromClick(event) {
    if (event.target.closest('.timeline-event')) return
    const rect = event.currentTarget.getBoundingClientRect()
    onSeek(((event.clientX - rect.left) / rect.width) * durationMs)
  }

  function onKeyDown(event) {
    if (event.key === 'ArrowRight') onSeek(time + 5000)
    else if (event.key === 'ArrowLeft') onSeek(time - 5000)
    else return
    event.preventDefault()
  }

  return (
    <div
      aria-label={label}
      aria-valuemax={Math.round(durationMs / 1000)}
      aria-valuemin={0}
      aria-valuenow={Math.round(time / 1000)}
      aria-valuetext={formatClock(time)}
      className="timeline"
      onClick={seekFromClick}
      onKeyDown={onKeyDown}
      role="slider"
      style={{ '--progress': pct(time) }}
      tabIndex={0}
    >
      <div className="timeline-line" />
      {moments.map((m) => (
        <button
          aria-label={`${formatClock(m.video_time_ms)} ${m.headline}`}
          className={`timeline-event type-${m.kind} ${selectedId === m.message_id ? 'selected' : ''}`}
          key={m.message_id}
          onClick={() => onSeek(m.video_time_ms)}
          style={{ left: pct(m.video_time_ms) }}
          type="button"
        >
          <span aria-hidden="true">{SYMBOL[m.kind] ?? '•'}</span>
          <small>{formatClock(m.video_time_ms)}</small>
        </button>
      ))}
    </div>
  )
}
