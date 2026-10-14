export function Button({ children, className = '', variant = 'primary', type = 'button', ...props }) {
  return (
    <button className={`btn btn-${variant} ${className}`} type={type} {...props}>
      {children}
    </button>
  )
}
