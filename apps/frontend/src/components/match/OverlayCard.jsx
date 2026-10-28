import { usePreferences } from '../../app/preferences.js'
import { kindLabel } from '../../lib/overlays.js'
import { Icon } from '../ui/Icon.jsx'
import { matchMinute } from '../../lib/commentary.js'

// Mensaje sincronizado que aparece sobre el campo (OverlayMessage v1). Solo uno a la vez (RNF-05).
export function OverlayCard({ overlay, time, playing, onClose, onOpen }) {
  const { t } = usePreferences()
  if (!overlay) return null
  const total = overlay.display_until_ms - overlay.video_time_ms
  const remaining = Math.max(0, Math.min(100, ((overlay.display_until_ms - time) / total) * 100))
  return (
    <article
      className={`overlay-card kind-${overlay.kind} ${overlay.priority >= 90 ? 'is-high' : ''}`}
      key={overlay.message_id}
    >
      <button aria-label={t.common.close} className="overlay-close" onClick={onClose} type="button"><Icon name="close" size={15} /></button>
      <span className="overlay-kind">
        <Icon name="spark" size={14} /> {matchMinute(overlay.clock_ms)} · {kindLabel(t.kinds, overlay.kind)}
        {overlay.corrected && <em> · ✓</em>}
      </span>
      <p className="overlay-headline">{overlay.headline}</p>
      {overlay.explanation && <p className="overlay-text">{overlay.explanation.split(/\s(?:Datos|Data):/)[0]}</p>}
      <button aria-label={`${overlay.call_to_action || t.match.viewAnalysis}. ${t.match.viewAnalysis}`} className="overlay-link" onClick={() => onOpen(overlay)} type="button">
        <strong>{overlay.call_to_action || t.match.viewAnalysis}</strong>
      </button>
      <span className={`overlay-timer ${playing ? '' : 'paused'}`} style={{ width: `${remaining}%` }} />
    </article>
  )
}
