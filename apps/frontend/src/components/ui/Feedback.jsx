import { Button, Spinner } from './Button.jsx'
import { Icon } from './Icon.jsx'
import { usePreferences } from '../../app/preferences.js'

export function LoadingScreen({ message, compact = false }) {
  const { t } = usePreferences()
  return <div aria-busy="true" className={`loading-screen ${compact ? 'compact-loading' : ''}`} role="status" aria-live="polite"><Spinner /><strong>{message || t.common.loading}</strong><p>{t.common.loadingCopy}</p></div>
}

export function InlineLoading({ message }) {
  const { t } = usePreferences()
  return <span aria-busy="true" className="inline-loading" role="status"><Spinner size="small" /> {message || t.common.loading}</span>
}

export function ErrorNotice({ message, onRetry, retryLabel }) {
  if (!message) return null
  return (
    <div className="error-notice" role="alert">
      <Icon name="flag" size={18} />
      <span>{message}</span>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}

export function LoadingCards() {
  return (
    <div aria-busy="true">
      <LoadingScreen compact />
      <div className="loading-cards" aria-hidden="true">
      <span />
      <span />
      </div>
    </div>
  )
}
