import { usePreferences } from '../../app/preferences.js'
import { eventCommentary, matchMinute } from '../../lib/commentary.js'

export function LiveNarrator({ events, metadata }) {
  const { t, preferences } = usePreferences()
  if (!events.length) return null
  return (
    <section className="live-narrator" aria-label={t.match.liveCommentsTitle} aria-live="polite">
      <header><span className="live-dot" /><strong>{t.match.liveCommentsTitle}</strong></header>
      <div className="live-narrator-feed">
        {events.slice().reverse().map((event) => (
          <article key={event.event_id}>
            <time>{matchMinute(event.clock_ms)}</time>
            <p>{eventCommentary(event, metadata, preferences.language)}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
