import { formatClock } from '../../lib/overlays.js'

const SYMBOL = { goal: '⚽', shot: '◎', recovery: '◆', turnover: '◆', pressure: '◆', progressive_pass: '→', foul: '!', yellow_card: '■', red_card: '■', injury_stoppage: '+', player_quiet: '·' }

export function Timeline({ moments, durationMs, time, selectedId, onSeek, label }) {
  const visible = moments.filter((moment) => !moment.suppressed && (['goal', 'shot', 'recovery', 'turnover'].includes(moment.kind) || moment.priority >= 70))
  const progress = Math.min(100, Math.max(0, time / durationMs * 100))
  return (
    <div className="timeline" style={{ '--progress': `${progress}%` }}>
      <div className="timeline-track" aria-hidden="true"><span /></div>
      <input type="range" min="0" max={durationMs} step="100" value={Math.round(time)} aria-label={label} aria-valuetext={formatClock(time)} onChange={(event) => onSeek(Number(event.target.value))} onKeyDown={(event) => {
        const targets = { ArrowRight: time + 5000, ArrowLeft: time - 5000, Home: 0, End: durationMs }
        if (event.key in targets) { event.preventDefault(); onSeek(targets[event.key]) }
      }} />
      <div className="timeline-markers">
        {visible.map((moment) => <button key={moment.message_id} type="button" className={`timeline-event type-${moment.kind} ${selectedId === moment.message_id ? 'selected' : ''}`} style={{ left: `${Math.min(97, Math.max(3, moment.video_time_ms / durationMs * 100))}%` }} aria-label={`${formatClock(moment.video_time_ms)} · ${moment.headline}`} title={`${formatClock(moment.video_time_ms)} · ${moment.headline}`} onClick={() => onSeek(moment.video_time_ms)}><span aria-hidden="true">{SYMBOL[moment.kind] || '◆'}</span><small>{formatClock(moment.video_time_ms)}</small></button>)}
      </div>
    </div>
  )
}
