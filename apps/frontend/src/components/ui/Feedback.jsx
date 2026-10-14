import { Button } from './Button.jsx'
import { Icon } from './Icon.jsx'

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
    <div className="loading-cards" aria-busy="true">
      <span />
      <span />
    </div>
  )
}
