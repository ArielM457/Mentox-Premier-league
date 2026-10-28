export function Spinner({ size = 'medium' }) {
  return <span className={`loading-spinner spinner-${size}`} aria-hidden="true" />
}

export function Button({ busy = false, busyLabel, children, className = '', disabled = false, variant = 'primary', type = 'button', ...props }) {
  return (
    <button aria-busy={busy || undefined} className={`btn btn-${variant} ${className}`} disabled={disabled || busy} type={type} {...props}>
      {busy && <Spinner size="small" />}
      {busy && busyLabel ? busyLabel : children}
    </button>
  )
}
