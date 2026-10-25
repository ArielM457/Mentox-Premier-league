import { Icon } from './Icon.jsx'

export function Brand({ light = false }) {
  return (
    <div className={`brand ${light ? 'brand-light' : ''}`} aria-label="The Prime Moment">
      <span className="brand-mark">
        <Icon name="ball" size={22} />
      </span>
      <span>
        The Prime
        <br />
        Moment
      </span>
    </div>
  )
}
