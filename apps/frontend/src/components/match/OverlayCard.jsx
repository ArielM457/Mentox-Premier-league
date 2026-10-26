import { usePreferences } from '../../app/preferences.js'
import { kindLabel } from '../../lib/overlays.js'
import { Icon } from '../ui/Icon.jsx'

// Mensaje sincronizado que aparece sobre el campo (OverlayMessage v1). Solo uno a la vez (RNF-05).
export function OverlayCard({ overlay, time, playing, onOpen }) {
  const { t } = usePreferences()
  if (!overlay) return null
  const total = overlay.display_until_ms - overlay.video_time_ms
  const remaining = Math.max(0, Math.min(100, ((overlay.display_until_ms - time) / total) * 100))
  return (
    <article
      className={`overlay-card kind-${overlay.kind} ${overlay.priority >= 90 ? 'is-high' : ''}`}
      key={overlay.message_id}
    >
      <span className="overlay-kind">
        <Icon name="spark" size={14} /> {kindLabel(t.kinds, overlay.kind)}
        {overlay.corrected && <em> · ✓</em>}
      </span>
      <p className="overlay-headline">{overlay.headline}</p>
      {overlay.explanation && <p className="overlay-text">{overlay.explanation}</p>}
      <button className="overlay-link" onClick={() => onOpen(overlay)} type="button">
        {t.match.whyMatters} <Icon name="arrow" size={14} />
      </button>
      <span className={`overlay-timer ${playing ? '' : 'paused'}`} style={{ width: `${remaining}%` }} />
    </article>
  )
}
