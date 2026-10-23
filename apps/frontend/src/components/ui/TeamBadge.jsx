import { teamBranding } from '../../data/branding.js'

export function TeamBadge({ team, size = 'md' }) {
  const brand = teamBranding(team)
  return (
    <span className={`team-badge badge-${size}`} style={{ '--team': brand.color }}>
      {brand.logo ? <img alt="" src={brand.logo} /> : brand.short}
    </span>
  )
}
