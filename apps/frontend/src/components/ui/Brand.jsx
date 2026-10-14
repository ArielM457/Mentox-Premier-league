import { Icon } from './Icon.jsx'

export function Brand({ light = false }) {
  return (
    <div className={`brand ${light ? 'brand-light' : ''}`} aria-label="Inside the Game">
      <span className="brand-mark">
        <Icon name="ball" size={22} />
      </span>
      <span>
        Inside
        <br />
        the Game
      </span>
    </div>
  )
}
