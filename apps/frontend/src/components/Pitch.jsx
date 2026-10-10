// "Vídeo" sintético: dibuja en el campo los eventos ya ocurridos.
const LENGTH = 105
const WIDTH = 68
const TRAIL = 5

const px = (p) => ({ x: (p.x / 100) * LENGTH, y: (p.y / 100) * WIDTH })

export function Pitch({ events, time, homeTeamId, players, label }) {
  const past = events.filter((e) => e.video_time_ms <= time)
  const trail = past.slice(-TRAIL)
  const last = trail[trail.length - 1]
  const ball = last ? px(last.end ?? last.start ?? { x: 50, y: 50 }) : { x: LENGTH / 2, y: WIDTH / 2 }
  const name = (id) => players.find((p) => p.player_id === id)?.name ?? ''

  return (
    <svg className="pitch" viewBox={`-2 -2 ${LENGTH + 4} ${WIDTH + 4}`} role="img" aria-label={label}>
      <rect x="0" y="0" width={LENGTH} height={WIDTH} className="pitch-grass" />
      <g className="pitch-lines">
        <rect x="0" y="0" width={LENGTH} height={WIDTH} />
        <line x1={LENGTH / 2} y1="0" x2={LENGTH / 2} y2={WIDTH} />
        <circle cx={LENGTH / 2} cy={WIDTH / 2} r="9.15" />
        <rect x="0" y={(WIDTH - 40.3) / 2} width="16.5" height="40.3" />
        <rect x={LENGTH - 16.5} y={(WIDTH - 40.3) / 2} width="16.5" height="40.3" />
        <rect x="0" y={(WIDTH - 18.3) / 2} width="5.5" height="18.3" />
        <rect x={LENGTH - 5.5} y={(WIDTH - 18.3) / 2} width="5.5" height="18.3" />
      </g>
      {trail.map((e, i) => {
        const home = e.team_id === homeTeamId
        const opacity = 0.25 + (0.75 * (i + 1)) / trail.length
        const start = e.start && px(e.start)
        const end = e.end && px(e.end)
        return (
          <g key={e.event_id} opacity={opacity} className={home ? 'team-home' : 'team-away'}>
            {start && end && <line x1={start.x} y1={start.y} x2={end.x} y2={end.y} className="pass-line" />}
            {start && <circle cx={start.x} cy={start.y} r="1.8" className="player-dot" />}
            {start && i === trail.length - 1 && (
              <text x={start.x} y={start.y - 3} className="player-label">
                {name(e.player_id)} · {e.type}
              </text>
            )}
          </g>
        )
      })}
      <circle cx={ball.x} cy={ball.y} r="1" className="ball" />
    </svg>
  )
}
