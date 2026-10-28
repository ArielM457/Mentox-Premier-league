import { useEffect, useMemo, useState } from "react"

type Screen = "landing" | "onboarding" | "discover" | "matches" | "match" | "moment" | "recap" | "profile"
type Mode = "Casual Fan" | "Football Expert" | "Player Focus"
type MatchFilter = "LIVE" | "UPCOMING" | "FT"

type EventData = {
  id: string
  minute: number
  label: string
  type: "goal" | "press" | "shot" | "pass"
  player: string
  title: string
  detail: string
}

type MatchData = {
  id: string
  home: string
  away: string
  homeShort: string
  awayShort: string
  homeScore: number
  awayScore: number
  status: "LIVE" | "FT" | "UPCOMING"
  minute: string
  homeColor: string
  awayColor: string
}

const matches: MatchData[] = [
  {
    id: "mci-ars",
    home: "Manchester City",
    away: "Arsenal",
    homeShort: "MCI",
    awayShort: "ARS",
    homeScore: 2,
    awayScore: 1,
    status: "LIVE",
    minute: "62:18",
    homeColor: "#78b9eb",
    awayColor: "#ef3340",
  },
  {
    id: "liv-che",
    home: "Liverpool",
    away: "Chelsea",
    homeShort: "LIV",
    awayShort: "CHE",
    homeScore: 1,
    awayScore: 1,
    status: "LIVE",
    minute: "48:02",
    homeColor: "#e31b23",
    awayColor: "#2864dc",
  },
  {
    id: "bar-int",
    home: "Barcelona",
    away: "Inter Milan",
    homeShort: "BAR",
    awayShort: "INT",
    homeScore: 3,
    awayScore: 2,
    status: "FT",
    minute: "Full time",
    homeColor: "#3c50a2",
    awayColor: "#111f62",
  },
  {
    id: "rma-bay",
    home: "Real Madrid",
    away: "Bayern Munich",
    homeShort: "RMA",
    awayShort: "BAY",
    homeScore: 0,
    awayScore: 0,
    status: "UPCOMING",
    minute: "20:00",
    homeColor: "#d7cfff",
    awayColor: "#dc1732",
  },
  {
    id: "north-riverside",
    home: "North City",
    away: "Riverside United",
    homeShort: "NC",
    awayShort: "RU",
    homeScore: 2,
    awayScore: 1,
    status: "LIVE",
    minute: "67:14",
    homeColor: "#d8ff65",
    awayColor: "#6539d5",
  },
  {
    id: "aurora-harbor",
    home: "Aurora Athletic",
    away: "Harborline FC",
    homeShort: "AA",
    awayShort: "HF",
    homeScore: 0,
    awayScore: 0,
    status: "UPCOMING",
    minute: "19:30",
    homeColor: "#963879",
    awayColor: "#205664",
  },
  {
    id: "ember-summit",
    home: "Ember Borough",
    away: "Summit Vale",
    homeShort: "EB",
    awayShort: "SV",
    homeScore: 3,
    awayScore: 2,
    status: "FT",
    minute: "Full time",
    homeColor: "#963653",
    awayColor: "#404b8d",
  },
]

const events: EventData[] = [
  {
    id: "kickoff",
    minute: 1,
    label: "Kick-off",
    type: "pass",
    player: "Rodri",
    title: "City establish their passing rhythm",
    detail:
      "City open with a patient circulation, pulling Arsenal's midfield narrow before switching play.",
  },
  {
    id: "goal-1",
    minute: 24,
    label: "Goal · Haaland",
    type: "goal",
    player: "Erling Haaland",
    title: "Haaland opens the scoring",
    detail:
      "A quick transition ends with De Bruyne releasing Haaland into the left channel for a precise finish.",
  },
  {
    id: "shot",
    minute: 39,
    label: "Shot · Saka",
    type: "shot",
    player: "Bukayo Saka",
    title: "Saka tests the near post",
    detail:
      "Saka isolates the full-back and creates Arsenal's clearest opening of the first half.",
  },
  {
    id: "ars-goal",
    minute: 51,
    label: "Goal · Ødegaard",
    type: "goal",
    player: "Martin Ødegaard",
    title: "Arsenal find the equalizer",
    detail:
      "A compact combination around the box gives Ødegaard the half-yard needed to finish.",
  },
  {
    id: "press",
    minute: 58,
    label: "Goal · De Bruyne",
    type: "goal",
    player: "Kevin De Bruyne",
    title: "De Bruyne restores City's lead",
    detail:
      "Haaland pins both center-backs before laying the ball into De Bruyne's path for a composed finish.",
  },
  {
    id: "press-sequence",
    minute: 62,
    label: "High press",
    type: "press",
    player: "Phil Foden",
    title: "City recover and create a dangerous chance",
    detail:
      "A coordinated high press traps Arsenal near the touchline and turns a recovery into a shot in six seconds.",
  },
]

const teams = [
  { name: "Manchester City", short: "MCI", color: "#78b9eb" },
  { name: "Arsenal", short: "ARS", color: "#ef3340" },
  { name: "Liverpool", short: "LIV", color: "#e31b23" },
  { name: "Barcelona", short: "BAR", color: "#3c50a2" },
  { name: "Inter Milan", short: "INT", color: "#111f62" },
  {
    name: "North City",
    short: "NC",
    color: "#d8ff65",
    logo: "/images/clubs/north-city.png",
  },
  {
    name: "Riverside United",
    short: "RU",
    color: "#6539d5",
    logo: "/images/clubs/riverside-united.png",
  },
  {
    name: "Aurora Athletic",
    short: "AA",
    color: "#963879",
    logo: "/images/clubs/aurora-athletic.png",
  },
  {
    name: "Harborline FC",
    short: "HF",
    color: "#205664",
    logo: "/images/clubs/harborline-fc.png",
  },
  {
    name: "Summit Vale",
    short: "SV",
    color: "#404b8d",
    logo: "/images/clubs/summit-vale.png",
  },
  {
    name: "Ember Borough",
    short: "EB",
    color: "#963653",
    logo: "/images/clubs/ember-borough.png",
  },
]

const preferenceClubs = [
  {
    name: "North City",
    short: "NC",
    logo: "/images/clubs/north-city.png",
    players: [
      { name: "Milo Arden", role: "Arquero", image: "/assets/4e09b.png" },
      { name: "Teo Varin", role: "Mediocampista", image: "/assets/3d38e.png" },
      { name: "Cael Norr", role: "Delantero", image: "/assets/4c136.png" },
    ],
  },
  {
    name: "Riverside United",
    short: "RU",
    logo: "/images/clubs/riverside-united.png",
    players: [
      { name: "Riven Solan", role: "Arquero", image: "/assets/5176b.png" },
      {
        name: "Nilo Verdan",
        role: "Mediocampista",
        image: "/assets/45201.png",
      },
      { name: "Kenji Morita", role: "Extremo", image: "/assets/e5f99.png" },
    ],
  },
  {
    name: "Aurora Athletic",
    short: "AA",
    logo: "/images/clubs/aurora-athletic.png",
    players: [
      { name: "Eren Solis", role: "Arquero", image: "/assets/03798.png" },
      { name: "Luka Savic", role: "Mediocampista", image: "/assets/45eb0.png" },
      { name: "Ivo Darsen", role: "Delantero", image: "/assets/7b273.png" },
    ],
  },
  {
    name: "Harborline FC",
    short: "HF",
    logo: "/images/clubs/harborline-fc.png",
    players: [
      { name: "Samir Dax", role: "Arquero", image: "/assets/c7efd.png" },
      { name: "Arin Solt", role: "Mediocampista", image: "/assets/5ed57.png" },
      { name: "Tomas Vey", role: "Delantero", image: "/assets/c2752.png" },
    ],
  },
  {
    name: "Summit Vale",
    short: "SV",
    logo: "/images/clubs/summit-vale.png",
    players: [
      { name: "Oskar Venn", role: "Arquero", image: "/assets/a64b8.png" },
      { name: "Mateo Brin", role: "Mediocampista", image: "/assets/4d3b4.png" },
      { name: "Soren Vale", role: "Delantero", image: "/assets/c6e56.png" },
    ],
  },
  {
    name: "Ember Borough",
    short: "EB",
    logo: "/images/clubs/ember-borough.png",
    players: [
      { name: "Idris Kellan", role: "Arquero", image: "/assets/48744.png" },
      { name: "Pavel Orin", role: "Mediocampista", image: "/assets/fcfef.png" },
      { name: "Rafael Miro", role: "Delantero", image: "/assets/92e53.png" },
    ],
  },
]

const preferencePlayers = preferenceClubs.flatMap((club) =>
  club.players.map((player) => ({ ...player, club: club.name })),
)

const favoritePlayers = preferencePlayers.map((player) => player.name)

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m14 7 5 5-5 5" />
      </>
    ),
    back: (
      <>
        <path d="m15 18-6-6 6-6" />
      </>
    ),
    home: (
      <>
        <path d="m3 11 9-8 9 8" />
        <path d="M5 10v10h14V10M9 20v-6h6v6" />
      </>
    ),
    match: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="3" />
        <path d="M12 4v16M3 12h18" />
        <circle cx="12" cy="12" r="2.5" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" />
        <path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c.7-4.4 3.4-6.5 8-6.5s7.3 2.1 8 6.5" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    play: <path d="m9 7 9 5-9 5V7Z" />,
    pause: (
      <>
        <path d="M9 7v10M15 7v10" />
      </>
    ),
    replay: (
      <>
        <path d="M20 7v5h-5" />
        <path d="M19 12a7 7 0 1 0-2 5" />
      </>
    ),
    chart: (
      <>
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
      </>
    ),
    close: (
      <>
        <path d="m6 6 12 12M18 6 6 18" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    ball: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m9 9 3-2 3 2-1 4h-4L9 9ZM6 5l3 4M15 9l3-4M10 13l-3 5M14 13l3 5" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
      </>
    ),
    menu: (
      <>
        <path d="M4 7h16M4 12h16M4 17h16" />
      </>
    ),
  }
  return (
    <svg
      aria-hidden="true"
      className="icon"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
    >
      <g
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      >
        {paths[name]}
      </g>
    </svg>
  )
}

function Button({
  children,
  className = "",
  onClick,
  variant = "primary",
  disabled = false,
}: {
  children: React.ReactNode
  className?: string
  onClick?: () => void
  variant?: "primary" | "secondary" | "ghost" | "lime"
  disabled?: boolean
}) {
  return (
    <button
      className={`btn btn-${variant} ${className}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function Brand({ light = false }: { light?: boolean }) {
  return (
    <div
      className={`brand ${light ? "brand-light" : ""}`}
      aria-label="Inside the Game"
    >
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

function Badge({
  team,
  size = "md",
}: {
  team: typeof teams[number]
  size?: "sm" | "md" | "lg"
}) {
  return (
    <span
      className={`team-badge badge-${size}`}
      style={{ "--team": team.color } as React.CSSProperties}
    >
      {"logo" in team ? <img alt="" src={team.logo} /> : team.short}
    </span>
  )
}

function getTeam(name: string) {
  return teams.find((team) => team.name === name) ?? teams[0]
}

function PlayerIllustration({ compact = false }: { compact?: boolean }) {
  return (
    <svg
      className={`player-illustration ${compact ? "compact" : ""}`}
      viewBox="0 0 560 560"
      role="img"
      aria-label="Illustrated footballer striking a ball"
    >
      <defs>
        <linearGradient id="violetBrush" x1="0" x2="1">
          <stop stopColor="#8257F5" />
          <stop offset="1" stopColor="#5431c9" />
        </linearGradient>
        <linearGradient id="limeBrush" x1="0" x2="1">
          <stop stopColor="#D8FF65" />
          <stop offset="1" stopColor="#b6ed3f" />
        </linearGradient>
      </defs>
      <path
        className="brush brush-one"
        d="M35 370C110 210 173 105 380 32L511 116C337 163 242 307 179 507Z"
        fill="url(#limeBrush)"
      />
      <path
        className="brush brush-two"
        d="M97 465C199 356 286 272 530 214L504 393C326 401 241 468 174 534Z"
        fill="url(#violetBrush)"
      />
      <path
        d="m330 180 135-73 15 30-124 99Z"
        fill="#f2b090"
        stroke="#151329"
        strokeWidth="6"
      />
      <path
        d="m465 106 40-6 16 20-41 17Z"
        fill="#f2b090"
        stroke="#151329"
        strokeWidth="6"
      />
      <path
        d="M232 170c41-37 97-27 135 28l-44 121-139-39Z"
        fill="#f8f7fc"
        stroke="#151329"
        strokeWidth="8"
      />
      <path
        d="m228 201-95 94-26-23 73-110Z"
        fill="#f2b090"
        stroke="#151329"
        strokeWidth="7"
      />
      <path
        d="m114 268-46 10 9 32 53-15Z"
        fill="#f2b090"
        stroke="#151329"
        strokeWidth="6"
      />
      <path
        d="M260 155c-10-21-2-62 28-76 40-18 72 5 78 38 6 36-31 68-65 63Z"
        fill="#f2b090"
        stroke="#151329"
        strokeWidth="7"
      />
      <path
        d="M271 117c-18-27 20-60 49-47 24-22 59 7 47 33 20 3 19 31-5 42-3-25-18-32-30-39-18 21-40 20-61 11Z"
        fill="#151329"
      />
      <path
        d="M312 126c12 7 25 5 36 1"
        fill="none"
        stroke="#151329"
        strokeWidth="5"
      />
      <circle cx="329" cy="114" r="3" fill="#151329" />
      <path
        d="m216 274 107 31-17 105-92-3-58-90Z"
        fill="#28204f"
        stroke="#151329"
        strokeWidth="8"
      />
      <path
        d="m230 397-23 99-49 1 6-126Z"
        fill="#f8f7fc"
        stroke="#151329"
        strokeWidth="8"
      />
      <path
        d="m305 398 87 72-27 37-114-78Z"
        fill="#f8f7fc"
        stroke="#151329"
        strokeWidth="8"
      />
      <path
        d="m157 495-46 12 6 24 90-4v-31Z"
        fill="#8257F5"
        stroke="#151329"
        strokeWidth="7"
      />
      <path
        d="m391 468 61 36-9 27-80-24Z"
        fill="#8257F5"
        stroke="#151329"
        strokeWidth="7"
      />
      <circle
        cx="462"
        cy="387"
        r="67"
        fill="#f8f7fc"
        stroke="#151329"
        strokeWidth="8"
      />
      <path d="m440 364 34-8 22 26-19 32-37-7-10-26Z" fill="#151329" />
      <path
        d="m462 320 12 36M508 348l-25 18M515 408l-38 6M466 454l11-40M410 428l30-21M400 371l31 10"
        fill="none"
        stroke="#151329"
        strokeWidth="6"
      />
      <path
        d="m421 88 18-30M450 83l8-31M477 93l23-25"
        stroke="#8257F5"
        strokeLinecap="round"
        strokeWidth="9"
      />
    </svg>
  )
}

function Landing({
  language,
  mode,
  setLanguage,
  navigate,
}: {
  language: string
  mode: Mode
  setLanguage: (language: string) => void
  navigate: (screen: Screen) => void
}) {
  const spanish = language === "Español"
  const [selectedDiscovery, setSelectedDiscovery] = useState(0)
  const [examplePlaying, setExamplePlaying] = useState(true)
  const copy = spanish
    ? {
        eyebrow: "El fútbol, explicado para ti",
        title: "Ve el partido. Entiende cada momento.",
        intro:
          "Una plataforma que convierte jugadas y datos del encuentro en explicaciones fáciles de explorar.",
        start: "Iniciar",
        discoverKicker: "Qué puedes descubrir",
        discoverTitle: "Todo el partido, en una historia que puedes explorar.",
        liveTitle: "Sigue el partido",
        liveCopy: "Explora sus eventos mientras ocurre.",
        playTitle: "Entiende las jugadas",
        playCopy: "Mira el recorrido y los datos detrás de cada momento.",
        recapTitle: "Revive la historia",
        recapCopy: "Consulta un resumen claro cuando termina.",
        exampleKicker: "Ejemplo de explicación",
        exampleTitle: "67′ · Un pase cambió el partido",
        exampleCopy:
          "Superó a dos defensores y dejó al atacante frente al arco.",
        evidence: "La evidencia detrás del momento",
        modesKicker: "Una experiencia a tu medida",
        modesTitle: "Elige cómo quieres entender el juego.",
        close: "Elige cómo quieres vivir el fútbol.",
        explore: "Empezar a explorar",
      }
    : {
        eyebrow: "Football, explained for you",
        title: "Watch the match. Understand every moment.",
        intro:
          "A platform that turns plays and match data into explanations that are easy to explore.",
        start: "Start",
        discoverKicker: "What you can discover",
        discoverTitle: "The whole match, in a story you can explore.",
        liveTitle: "Follow the match",
        liveCopy: "Explore events as they happen.",
        playTitle: "Understand the plays",
        playCopy: "See the movement and data behind every moment.",
        recapTitle: "Relive the story",
        recapCopy: "Get a clear recap when the match ends.",
        exampleKicker: "Explanation example",
        exampleTitle: "67′ · One pass changed the match",
        exampleCopy:
          "It beat two defenders and left the striker through on goal.",
        evidence: "The evidence behind the moment",
        modesKicker: "An experience made for you",
        modesTitle: "Choose how you want to understand the game.",
        close: "Choose how you want to experience football.",
        explore: "Start exploring",
      }

  return (
    <main className="landing">
      <header className="landing-header">
        <Brand />
        <div className="landing-actions">
          <div className="language-switch" aria-label="Language selector">
            <button
              className={language === "Español" ? "active" : ""}
              onClick={() => setLanguage("Español")}
            >
              ES
            </button>
            <button
              className={language === "English" ? "active" : ""}
              onClick={() => setLanguage("English")}
            >
              EN
            </button>
          </div>
          <Button onClick={() => navigate("onboarding")}>
            Get started <Icon name="arrow" size={17} />
          </Button>
        </div>
      </header>
      <section className="hero" id="home">
        <div className="hero-copy">
          <span className="eyebrow">
            <span className="live-dot" /> {copy.eyebrow}
          </span>
          <h1>
            {spanish ? (
              <>
                Ve el <strong>partido.</strong>
              </>
            ) : (
              <>
                Watch the <strong>match.</strong>
              </>
            )}
          </h1>
          <p>{copy.intro}</p>
          <Button variant="lime" onClick={() => navigate("onboarding")}>
            {copy.start} <Icon name="arrow" size={19} />
          </Button>
        </div>
        <div className="hero-art">
          <img
            alt="Illustrated football stadium filled with supporters"
            className="hero-main-illustration"
            src="/images/inside-the-game-stadium.png"
          />
          <span className="hero-live-chip">
            <i /> LIVE · 67′
          </span>
          <p className="hero-image-caption">
            {spanish ? "Entiende cada momento." : "Understand every moment."}
          </p>
        </div>
      </section>
      <section className="home-discover">
        <div className="home-section-heading">
          <span className="section-kicker">{copy.discoverKicker}</span>
          <h2>
            {spanish ? (
              <>
                Todo el partido, en una historia que{" "}
                <strong>puedes explorar.</strong>
              </>
            ) : (
              <>
                The whole match, in a story <strong>you can explore.</strong>
              </>
            )}
          </h2>
        </div>
        <div className="discover-showcase">
          <div className="discover-illustration">
            <img
              alt="Illustrated female footballer dribbling a ball"
              src="/images/inside-the-game-player.png"
            />
          </div>
          <div className="discover-points">
            {[
              [copy.liveTitle, copy.liveCopy, "match"],
              [copy.playTitle, copy.playCopy, "spark"],
              [copy.recapTitle, copy.recapCopy, "replay"],
            ].map(([title, description, icon], index) => (
              <button
                className={selectedDiscovery === index ? "active" : ""}
                key={title}
                onClick={() => setSelectedDiscovery(index)}
              >
                <span className="point-number">0{index + 1}</span>
                <span className="point-icon">
                  <Icon name={icon} />
                </span>
                <div>
                  <h3>{title}</h3>
                  <p>{description}</p>
                </div>
                <Icon name="arrow" size={18} />
              </button>
            ))}
          </div>
        </div>
      </section>
      <section className="home-example">
        <div className="example-copy">
          <span className="section-kicker">{copy.exampleKicker}</span>
          <h2>{copy.exampleTitle}</h2>
          <p>{copy.exampleCopy}</p>
          <span className="ai-explanation-label">
            <Icon name="spark" size={17} /> AI Match Assistant
          </span>
        </div>
        <div className={`example-card ${examplePlaying ? "is-active" : ""}`}>
          <div className="sample-pitch">
            <span className="sample-player player-one" />
            <span className="sample-player player-two" />
            <span className="sample-player player-three" />
            <span className="sample-player player-target" />
            <span className="sample-pass" />
            <span className="sample-ball">
              <Icon name="ball" size={16} />
            </span>
            <button
              aria-label={
                examplePlaying ? "Pause play animation" : "Play animation"
              }
              className="sample-play"
              onClick={() => setExamplePlaying(!examplePlaying)}
            >
              <Icon name={examplePlaying ? "pause" : "play"} />
            </button>
          </div>
          <strong>{copy.evidence}</strong>
          <div className="evidence-stats">
            <span>
              <b>31m</b>
              <small>{spanish ? "Progresión" : "Progression"}</small>
            </span>
            <span>
              <b>2</b>
              <small>
                {spanish ? "Defensas superados" : "Defenders beaten"}
              </small>
            </span>
            <span>
              <b>0.42</b>
              <small>{spanish ? "Prob. de gol" : "Goal probability"}</small>
            </span>
          </div>
        </div>
      </section>
      <section className="home-modes">
        <div className="home-section-heading">
          <span className="section-kicker">{copy.modesKicker}</span>
          <h2>
            {spanish ? (
              <>
                Elige cómo quieres
                <br />
                <strong>entender el juego.</strong>
              </>
            ) : (
              <>
                Choose how you want to
                <br />
                <strong>understand the game.</strong>
              </>
            )}
          </h2>
        </div>
        <div className="home-mode-grid">
          {[
            [
              "Casual Fan",
              spanish
                ? "Historias claras, simples y emocionantes."
                : "Clear, simple and exciting stories.",
              "/images/inside-the-game-fans.png",
            ],
            [
              "Football Expert",
              spanish
                ? "Táctica avanzada y estadísticas en profundidad."
                : "Advanced tactics and in-depth statistics.",
              "/images/inside-the-game-duel.png",
            ],
            [
              "Player Focus",
              spanish
                ? "Sigue el impacto de tus jugadores favoritos."
                : "Follow the impact of your favorite players.",
              "/images/inside-the-game-player.png",
            ],
          ].map(([title, description, image], index) => (
            <article
              className={`mode-preview mode-preview-${index + 1}`}
              key={title}
            >
              <div className="mode-preview-art">
                <img alt="" src={image} />
                <span>0{index + 1}</span>
              </div>
              <div className="mode-preview-copy">
                <h3>{title}</h3>
                <p>{description}</p>
                <small>
                  {spanish
                    ? "Disponible en tu experiencia"
                    : "Available in your experience"}
                  <Icon name="arrow" size={15} />
                </small>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="home-closing">
        <div className="closing-copy">
          <span className="closing-kicker">
            <Icon name="spark" size={16} /> Inside the Game
          </span>
          <h2>
            {spanish ? (
              <>
                Elige cómo quieres <strong>vivir el fútbol.</strong>
              </>
            ) : (
              <>
                Choose how you want to <strong>experience football.</strong>
              </>
            )}
          </h2>
          <p>
            {spanish
              ? `Tu experiencia está preparada en modo ${mode}. Puedes cambiarla cuando quieras.`
              : `Your experience is ready in ${mode} mode. You can change it at any time.`}
          </p>
          <div className="closing-tags">
            <span>
              <Icon name="match" size={15} /> Live events
            </span>
            <span>
              <Icon name="spark" size={15} /> AI insights
            </span>
            <span>
              <Icon name="replay" size={15} /> Match recap
            </span>
          </div>
          <Button variant="lime" onClick={() => navigate("onboarding")}>
            {copy.explore} <Icon name="arrow" size={19} />
          </Button>
        </div>
        <div className="closing-art">
          <span className="closing-orbit orbit-one" />
          <span className="closing-orbit orbit-two" />
          <img
            alt="Three illustrated football supporters celebrating"
            src="/images/inside-the-game-fans.png"
          />
        </div>
      </section>
      <footer>
        <Brand />
        <span>AI-powered football storytelling · Synthetic demo data</span>
      </footer>
    </main>
  )
}

function Onboarding({
  favorite,
  favoritePlayer,
  language,
  mode,
  setFavorite,
  setFavoritePlayer,
  setLanguage,
  setMode,
  navigate,
}: {
  favorite: string
  favoritePlayer: string
  language: string
  mode: Mode
  setFavorite: (team: string) => void
  setFavoritePlayer: (player: string) => void
  setLanguage: (language: string) => void
  setMode: (mode: Mode) => void
  navigate: (screen: Screen) => void
}) {
  const validClub = preferenceClubs.some((club) => club.name === favorite)
  const validPlayer = favoritePlayers.includes(favoritePlayer)
  const [draftTeam, setDraftTeam] = useState(validClub ? favorite : "")
  const [draftPlayer, setDraftPlayer] = useState(
    validPlayer ? favoritePlayer : "",
  )
  const [draftLanguage, setDraftLanguage] = useState(language)
  const [draftMode, setDraftMode] = useState<Mode>(
    mode === "Football Expert" ? mode : "Casual Fan",
  )
  const [step, setStep] = useState(0)
  const stepLabels = ["Idioma", "Club", "Jugador", "Visualización"]
  const selectedClub = preferenceClubs.find((club) => club.name === draftTeam)

  function selectClub(club: string) {
    setDraftTeam(club)
    setDraftPlayer("")
  }

  function saveAndExplore() {
    setFavorite(draftTeam)
    setFavoritePlayer(draftPlayer)
    setLanguage(draftLanguage)
    setMode(draftMode)
    navigate("discover")
  }

  return (
    <main className="onboarding compact-onboarding">
      <section className="onboarding-modal compact-modal">
        <div className="compact-modal-top">
          <Brand />
          <button className="skip-setup" onClick={() => navigate("discover")}>
            Skip
          </button>
        </div>
        <div className="onboarding-form">
          <div className="onboarding-heading compact-heading">
            <span className="section-kicker">Configura tu experiencia</span>
            <h1>Hagamos tu experiencia más tuya</h1>
            <p>Cuatro decisiones rápidas. Podrás cambiarlas cuando quieras.</p>
          </div>
          <div
            className="experience-stepper"
            aria-label={`Paso ${step + 1} de 4`}
          >
            {stepLabels.map((label, index) => (
              <button
                aria-label={`Ir al paso ${index + 1}: ${label}`}
                className={`${index === step ? "active" : ""} ${
                  index < step ? "complete" : ""
                }`}
                key={label}
                onClick={() => setStep(index)}
              >
                <span>
                  {index < step ? <Icon name="check" size={13} /> : index + 1}
                </span>
                <small>{label}</small>
              </button>
            ))}
          </div>

          {step === 0 && (
            <div className="onboarding-preference onboarding-step compact-step">
              <div className="step-intro">
                <span>01</span>
                <div>
                  <h2>¿En qué idioma quieres vivir el partido?</h2>
                  <p>Esto adapta la interfaz y las explicaciones.</p>
                </div>
              </div>
              <div className="onboarding-language language-cards">
                {["Español", "English"].map((item) => (
                  <button
                    className={draftLanguage === item ? "selected" : ""}
                    key={item}
                    onClick={() => setDraftLanguage(item)}
                  >
                    <b>{item === "Español" ? "ES" : "EN"}</b>
                    <span>
                      <strong>{item}</strong>
                      <small>
                        {item === "Español"
                          ? "Experiencia en español"
                          : "Experience in English"}
                      </small>
                    </span>
                    {draftLanguage === item && <Icon name="check" size={16} />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="onboarding-preference onboarding-step compact-step">
              <div className="step-intro">
                <span>02</span>
                <div>
                  <h2>Elige tu club</h2>
                  <p>Verás primero sus partidos y jugadores.</p>
                </div>
              </div>
              <div className="club-logo-grid">
                {preferenceClubs.map((club) => (
                  <button
                    className={draftTeam === club.name ? "selected" : ""}
                    key={club.name}
                    onClick={() => selectClub(club.name)}
                  >
                    <img alt={`Escudo de ${club.name}`} src={club.logo} />
                    <strong>{club.name}</strong>
                    {draftTeam === club.name && (
                      <span>
                        <Icon name="check" size={14} />
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="onboarding-preference onboarding-step compact-step">
              <div className="step-intro">
                <span>03</span>
                <div>
                  <h2>
                    {selectedClub
                      ? `Jugadores de ${selectedClub.name}`
                      : "Elige primero un club"}
                  </h2>
                  <p>Selecciona al jugador que quieres seguir.</p>
                </div>
              </div>
              {selectedClub ? (
                <div className="player-card-grid">
                  {selectedClub.players.map((player) => (
                    <button
                      className={draftPlayer === player.name ? "selected" : ""}
                      key={player.name}
                      onClick={() => setDraftPlayer(player.name)}
                    >
                      <img alt={player.name} src={player.image} />
                      <span>
                        <strong>{player.name}</strong>
                        <small>{player.role}</small>
                      </span>
                      {draftPlayer === player.name && (
                        <i>
                          <Icon name="check" size={14} />
                        </i>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <button
                  className="choose-club-prompt"
                  onClick={() => setStep(1)}
                >
                  <Icon name="match" size={24} /> Elegir un club
                </button>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="onboarding-preference onboarding-step compact-step">
              <div className="step-intro">
                <span>04</span>
                <div>
                  <h2>Modo de visualización</h2>
                  <p>Elige cómo quieres ver y entender cada jugada.</p>
                </div>
              </div>
              <div className="visualization-modes">
                {([
                  [
                    "Casual Fan",
                    "Aficionado",
                    "Explicaciones claras y sencillas",
                    "/images/inside-the-game-fans.png",
                  ],
                  [
                    "Football Expert",
                    "Analista",
                    "Más detalle táctico y datos",
                    "/images/inside-the-game-duel.png",
                  ],
                ] as [Mode, string, string, string][]).map(
                  ([value, title, description, image]) => (
                    <button
                      className={draftMode === value ? "selected" : ""}
                      key={value}
                      onClick={() => setDraftMode(value)}
                    >
                      <div>
                        <img alt="" src={image} />
                      </div>
                      <span>
                        <strong>{title}</strong>
                        <small>{description}</small>
                      </span>
                      {draftMode === value && (
                        <i>
                          <Icon name="check" size={14} />
                        </i>
                      )}
                    </button>
                  ),
                )}
              </div>
            </div>
          )}

          <div className="onboarding-actions compact-actions">
            <div>
              {step > 0 && (
                <Button variant="ghost" onClick={() => setStep(step - 1)}>
                  <Icon name="back" size={18} /> Atrás
                </Button>
              )}
              {step < 3 ? (
                <Button onClick={() => setStep(step + 1)}>
                  Continuar <Icon name="arrow" size={18} />
                </Button>
              ) : (
                <Button onClick={saveAndExplore}>
                  Explorar partidos <Icon name="arrow" size={18} />
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function AppNav({
  screen,
  navigate,
}: {
  screen: Screen
  navigate: (screen: Screen) => void
}) {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("itg-sidebar") === "collapsed",
  )

  function toggleSidebar() {
    setCollapsed(!collapsed)
    localStorage.setItem("itg-sidebar", collapsed ? "expanded" : "collapsed")
  }

  return (
    <>
      <aside className={`app-sidebar ${collapsed ? "collapsed" : ""}`}>
        <div className="sidebar-top">
          <Brand />
          <button
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="collapse-sidebar"
            onClick={toggleSidebar}
          >
            <Icon name={collapsed ? "arrow" : "back"} size={18} />
          </button>
        </div>
        <nav>
          <button
            className={screen === "discover" ? "active" : ""}
            onClick={() => navigate("discover")}
          >
            <Icon name="home" /> Discover
          </button>
          <button
            className={screen === "matches" ? "active" : ""}
            onClick={() => navigate("matches")}
          >
            <Icon name="match" /> All matches
          </button>
          <button
            className={screen === "profile" ? "active" : ""}
            onClick={() => navigate("profile")}
          >
            <Icon name="user" /> My experience
          </button>
        </nav>
        <button className="sidebar-profile" onClick={() => navigate("profile")}>
          <span>AL</span>
          <div>
            <strong>Alex Morgan</strong>
            <small>My preferences</small>
          </div>
          <Icon name="arrow" size={15} />
        </button>
      </aside>
      <nav className="mobile-nav">
        <button
          className={screen === "discover" ? "active" : ""}
          onClick={() => navigate("discover")}
        >
          <Icon name="home" />
          <span>Discover</span>
        </button>
        <button
          className={screen === "matches" ? "active" : ""}
          onClick={() => navigate("matches")}
        >
          <Icon name="match" />
          <span>Matches</span>
        </button>
        <button
          className={screen === "profile" ? "active" : ""}
          onClick={() => navigate("profile")}
        >
          <Icon name="user" />
          <span>Profile</span>
        </button>
      </nav>
    </>
  )
}

function MatchScore({
  match,
  compact = false,
}: {
  match: MatchData
  compact?: boolean
}) {
  return (
    <div className={`match-score ${compact ? "compact" : ""}`}>
      <div className="score-team">
        <Badge team={getTeam(match.home)} />
        <strong>{match.home}</strong>
      </div>
      <div className="score-center">
        <span className={`status status-${match.status.toLowerCase()}`}>
          {match.status}
        </span>
        <b>
          {match.homeScore} <em>–</em> {match.awayScore}
        </b>
        <small>{match.minute}</small>
      </div>
      <div className="score-team away">
        <Badge team={getTeam(match.away)} />
        <strong>{match.away}</strong>
      </div>
    </div>
  )
}

function MatchCard({
  match,
  open,
  favorite,
}: {
  match: MatchData
  open: (match: MatchData) => void
  favorite: boolean
}) {
  return (
    <button
      className={`match-card ${match.status === "LIVE" ? "match-live" : ""}`}
      onClick={() => open(match)}
    >
      <div className="match-card-top">
        <span>Champions League · Matchday 12</span>
        <span className={`status status-${match.status.toLowerCase()}`}>
          {match.status}
        </span>
      </div>
      {favorite && (
        <span className="favorite-row">
          <span className="favorite-label">Favorite team</span>
        </span>
      )}
      <div className="match-card-main">
        <div>
          <Badge team={getTeam(match.home)} />
          <strong>{match.home}</strong>
        </div>
        <span className="card-score">
          {match.homeScore} – {match.awayScore}
          <small>{match.minute}</small>
        </span>
        <div>
          <Badge team={getTeam(match.away)} />
          <strong>{match.away}</strong>
        </div>
      </div>
      <span className="explore-label">
        {match.status === "FT" ? "View recap" : "Open Match Center"}{" "}
        <Icon name="arrow" size={16} />
      </span>
    </button>
  )
}

function Discover({
  allMatches = false,
  favorite,
  favoritePlayer,
  language,
  mode,
  setLanguage,
  navigate,
  openMatch,
}: {
  allMatches?: boolean
  favorite: string
  favoritePlayer: string
  language: string
  mode: Mode
  setLanguage: (language: string) => void
  navigate: (screen: Screen) => void
  openMatch: (match: MatchData) => void
}) {
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<MatchFilter>("LIVE")
  const [followOnly, setFollowOnly] = useState(false)
  const playerClub = preferencePlayers.find(
    (player) => player.name === favoritePlayer,
  )?.club
  const ordered = useMemo(
    () =>
      [...matches].sort(
        (a, b) =>
          Number(b.home === favorite || b.away === favorite) -
          Number(a.home === favorite || a.away === favorite),
      ),
    [favorite],
  )
  const visible = ordered.filter(
    (match) =>
      match.status === filter &&
      (!followOnly || match.home === playerClub || match.away === playerClub) &&
      `${match.home} ${match.away}`.toLowerCase().includes(query.toLowerCase()),
  )
  const favoriteMatches = favorite
    ? ordered.filter(
        (match) =>
          (match.home === favorite || match.away === favorite) &&
          `${match.home} ${match.away}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      )
    : []
  const playerMatches = playerClub
    ? ordered.filter(
        (match) => match.home === playerClub || match.away === playerClub,
      )
    : []
  function search(value: string) {
    setQuery(value)
    setLoading(true)
    window.setTimeout(() => setLoading(false), 240)
  }

  const languageSelector = (
    <div className="header-language" aria-label="Language selector">
      {[
        ["Español", "ES"],
        ["English", "EN"],
      ].map(([value, label]) => (
        <button
          className={language === value ? "active" : ""}
          key={value}
          onClick={() => setLanguage(value)}
        >
          {label}
        </button>
      ))}
    </div>
  )

  if (allMatches) {
    return (
      <main className="app-shell light-shell">
        <AppNav screen="matches" navigate={navigate} />
        <section className="discover-content">
          <header className="page-header">
            <div>
              <span className="section-kicker">Match explorer</span>
              <h1>Todos los partidos.</h1>
              <p>Busca, filtra y abre cualquier encuentro de la demo.</p>
            </div>
            {languageSelector}
          </header>
          <label className="search-box">
            <Icon name="search" />
            <input
              value={query}
              onChange={(event) => search(event.target.value)}
              placeholder="Buscar partidos o equipos..."
            />
            <kbd>⌘ K</kbd>
          </label>
          <div className="all-match-controls">
            <div className="match-filters" aria-label="Filter matches">
              {([
                ["LIVE", "Live"],
                ["UPCOMING", "Upcoming"],
                ["FT", "Recaps"],
              ] as [MatchFilter, string][]).map(([value, label]) => (
                <button
                  className={filter === value ? "active" : ""}
                  key={value}
                  onClick={() => setFilter(value)}
                >
                  {value === "LIVE" && <span className="live-dot" />}
                  {label}
                  <small>
                    {matches.filter((match) => match.status === value).length}
                  </small>
                </button>
              ))}
            </div>
            {favoritePlayer && playerClub && (
              <button
                className={`follow-player-filter ${followOnly ? "active" : ""}`}
                onClick={() => setFollowOnly(!followOnly)}
              >
                <Icon name="user" size={17} />
                <span>
                  Solo partidos de <strong>{favoritePlayer}</strong>
                </span>
                <i>{followOnly ? "ON" : "OFF"}</i>
              </button>
            )}
          </div>
          <section className="discover-section all-matches-section">
            <div className="section-heading">
              <div>
                {filter === "LIVE" && <span className="live-dot" />}
                <h2>
                  {followOnly
                    ? `Partidos relacionados con ${favoritePlayer}`
                    : filter === "LIVE"
                      ? "En vivo"
                      : filter === "UPCOMING"
                        ? "Próximos encuentros"
                        : "Últimos resúmenes"}
                </h2>
              </div>
              <span>{visible.length} resultados</span>
            </div>
            {loading ? (
              <div className="loading-cards">
                <span />
                <span />
              </div>
            ) : visible.length ? (
              <div className="match-grid">
                {visible.map((match) => (
                  <MatchCard
                    favorite={
                      match.home === favorite || match.away === favorite
                    }
                    key={match.id}
                    match={match}
                    open={openMatch}
                  />
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Icon name="search" size={30} />
                <h3>No hay partidos con estos filtros</h3>
                <p>
                  Prueba otra categoría o desactiva el seguimiento del jugador.
                </p>
                <Button
                  onClick={() => {
                    setQuery("")
                    setFollowOnly(false)
                    setFilter("LIVE")
                  }}
                >
                  Limpiar filtros
                </Button>
              </div>
            )}
          </section>
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell light-shell">
      <AppNav screen="discover" navigate={navigate} />
      <section className="discover-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">Your matchday</span>
            <h1>Good evening, Alex.</h1>
            <p>
              {favorite ? `${favorite} comes first. ` : "Explore every match. "}
              Insights are set to <strong>{mode}</strong>.
            </p>
          </div>
          {languageSelector}
        </header>
        {favorite && (
          <section className="favorite-club-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon">
                  <Icon name="spark" size={17} />
                </span>
                <div>
                  <small>Tu club favorito</small>
                  <h2>Partidos de {favorite}</h2>
                </div>
              </div>
              <button onClick={() => navigate("matches")}>
                Ver todos los partidos <Icon name="arrow" size={15} />
              </button>
            </div>
            {favoriteMatches.length ? (
              <div className="favorite-match-row">
                {favoriteMatches.map((match) => (
                  <MatchCard
                    favorite
                    key={`favorite-${match.id}`}
                    match={match}
                    open={openMatch}
                  />
                ))}
              </div>
            ) : (
              <div className="favorite-filter-empty">
                <Icon name="match" size={22} />
                <span>
                  No hay partidos de {favorite} disponibles.
                  <small>Explora todos los encuentros de la demo.</small>
                </span>
              </div>
            )}
          </section>
        )}
        {favoritePlayer && playerMatches.length > 0 && (
          <section className="favorite-club-section player-matches-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon player-icon">
                  <Icon name="user" size={17} />
                </span>
                <div>
                  <small>Tu jugador favorito</small>
                  <h2>Partidos de {favoritePlayer}</h2>
                </div>
              </div>
              <button onClick={() => navigate("matches")}>
                Ver todos los partidos <Icon name="arrow" size={15} />
              </button>
            </div>
            <div className="favorite-match-row">
              {playerMatches.map((match) => (
                <MatchCard
                  favorite={match.home === favorite || match.away === favorite}
                  key={`player-${match.id}`}
                  match={match}
                  open={openMatch}
                />
              ))}
            </div>
          </section>
        )}
        {favoritePlayer && (
          <section className="player-insight-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon">
                  <Icon name="user" size={17} />
                </span>
                <div>
                  <small>Seguimiento personalizado</small>
                  <h2>Información de tu jugador favorito</h2>
                </div>
              </div>
              <button onClick={() => navigate("profile")}>
                Cambiar jugador
              </button>
            </div>
            <div className="insight-banner">
              <div className="insight-art">
                <span>47</span>
                <small>touches</small>
              </div>
              <div>
                <span className="section-kicker">
                  Player story · AI analysis
                </span>
                <h2>¿Cómo está influyendo {favoritePlayer} en el partido?</h2>
                <p>
                  Su movimiento está generando espacios y nuevas líneas de pase.
                  Explora las acciones y datos que explican su impacto.
                </p>
                <span className="favorite-player-label">
                  <Icon name="user" size={14} /> Following {favoritePlayer}
                </span>
                <Button onClick={() => navigate("matches")}>
                  Ver partidos de {favoritePlayer}{" "}
                  <Icon name="arrow" size={17} />
                </Button>
              </div>
              <Icon name="spark" size={40} />
            </div>
          </section>
        )}
      </section>
    </main>
  )
}

const playerDots = [
  [12, 50],
  [28, 20],
  [27, 77],
  [43, 35],
  [44, 67],
  [60, 18],
  [58, 50],
  [61, 80],
  [76, 32],
  [79, 67],
  [88, 50],
  [15, 35],
  [17, 66],
  [34, 50],
  [48, 18],
  [49, 82],
  [63, 38],
  [65, 63],
  [80, 18],
  [82, 82],
  [91, 50],
]

function Pitch({
  event,
  playing,
  onSelectPlayer,
}: {
  event: EventData
  playing: boolean
  onSelectPlayer?: (name: string) => void
}) {
  return (
    <div className={`pitch event-${event.type} ${playing ? "is-playing" : ""}`}>
      <div className="pitch-lines">
        <span className="half-line" />
        <span className="center-circle" />
        <span className="box box-left" />
        <span className="box box-right" />
      </div>
      <svg
        className="pass-lines"
        viewBox="0 0 100 60"
        preserveAspectRatio="none"
      >
        <path d="M28 38 Q42 16 60 31 T79 22" />
        <path d="M60 31 Q67 47 79 40" />
      </svg>
      {playerDots.map(([x, y], index) => (
        <button
          aria-label={`Select ${
            index < 11 ? "Manchester City" : "Arsenal"
          } player ${index + 1}`}
          className={`player-dot ${index < 11 ? "home" : "away"} ${
            index === 6 || index === 8 ? "involved" : ""
          }`}
          key={`${x}-${y}`}
          onClick={() =>
            onSelectPlayer?.(
              index === 6
                ? event.player
                : index < 11
                  ? "Manchester City player"
                  : "Arsenal player",
            )
          }
          style={
            {
              "--x": `${x}%`,
              "--y": `${y}%`,
              "--delay": `${(index % 5) * 0.08}s`,
            } as React.CSSProperties
          }
        >
          <span>{index < 11 ? index + 1 : index - 10}</span>
        </button>
      ))}
      <span className="pitch-ball">
        <Icon name="ball" size={15} />
      </span>
      <span className="player-label">{event.player}</span>
    </div>
  )
}

function Timeline({
  selected,
  setSelected,
}: {
  selected: EventData
  setSelected: (event: EventData) => void
}) {
  return (
    <div className="timeline">
      <div className="timeline-line" />
      {events.map((event) => (
        <button
          className={`timeline-event type-${event.type} ${
            selected.id === event.id ? "selected" : ""
          }`}
          key={event.id}
          onClick={() => setSelected(event)}
          style={{ left: `${Math.max(4, event.minute)}%` }}
        >
          <span>
            {event.type === "goal" ? "⚽" : event.type === "press" ? "✦" : "•"}
          </span>
          <small>{event.minute}'</small>
        </button>
      ))}
    </div>
  )
}

function Assistant({
  event,
  mode,
  onRelated,
}: {
  event: EventData
  mode: Mode
  onRelated: () => void
}) {
  const [question, setQuestion] = useState("Why does this moment matter?")
  const answers: Record<Mode, string> = {
    "Casual Fan": `City won the ball where Arsenal were vulnerable. That meant ${event.player} could attack before the defense was ready — a small moment that shifted the game's momentum.`,
    "Football Expert":
      "City's 4–1 press locked the near-side pivot and forced a predictable outlet. The regain created a 4v3 overload with Arsenal's rest defense facing its own goal.",
    "Player Focus": `${event.player}'s body angle is the key. They scan before the trigger, close the passing lane, then accelerate into the space created by the turnover.`,
  }
  const questions = [
    "Why does this moment matter?",
    "Who created the space?",
    "What happens next?",
  ]
  return (
    <aside className="assistant">
      <div className="assistant-title">
        <span>
          <Icon name="spark" /> AI Match Assistant
        </span>
        <span className="ai-mode">{mode}</span>
      </div>
      <div className="assistant-question">{question}</div>
      <div className="assistant-answer">
        <span className="spark-avatar">
          <Icon name="spark" size={17} />
        </span>
        <p>{answers[mode]}</p>
      </div>
      <div className="suggestions">
        <strong>Ask about this moment</strong>
        {questions.map((item) => (
          <button
            className={item === question ? "active" : ""}
            key={item}
            onClick={() => setQuestion(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <Button variant="secondary" onClick={onRelated}>
        <Icon name="play" size={17} /> Explore related event
      </Button>
    </aside>
  )
}

function MatchCenter({
  match,
  mode,
  navigate,
  selectedEvent,
  setSelectedEvent,
}: {
  match: MatchData
  mode: Mode
  navigate: (screen: Screen) => void
  selectedEvent: EventData
  setSelectedEvent: (event: EventData) => void
}) {
  const [tab, setTab] = useState("Overview")
  const [playing, setPlaying] = useState(false)
  const [player, setPlayer] = useState("")
  const selectedIndex = Math.max(
    0,
    events.findIndex((event) => event.id === selectedEvent.id),
  )
  const simulatedMatch =
    match.id === "mci-ars"
      ? {
          ...match,
          homeScore:
            selectedEvent.minute >= 58 ? 2 : selectedEvent.minute >= 24 ? 1 : 0,
          awayScore: selectedEvent.minute >= 51 ? 1 : 0,
          minute: `${selectedEvent.minute}:00`,
        }
      : match
  const simulationProgress = (selectedIndex + 1) / events.length
  const liveStats = [
    [
      "Possession",
      `${Math.round(58 + simulationProgress * 8)}%`,
      `${Math.round(42 - simulationProgress * 8)}%`,
    ],
    [
      "Shots",
      `${Math.max(1, Math.round(simulationProgress * 12))}`,
      `${Math.max(1, Math.round(simulationProgress * 7))}`,
    ],
    [
      "Pass accuracy",
      `${Math.round(86 + simulationProgress * 5)}%`,
      `${Math.round(80 + simulationProgress * 4)}%`,
    ],
    [
      "High regains",
      `${Math.max(1, Math.round(simulationProgress * 8))}`,
      `${Math.max(1, Math.round(simulationProgress * 3))}`,
    ],
  ]
  const tabs = [
    "Overview",
    "Live Events",
    "Stats",
    "Tactical View",
    "AI Insights",
  ]

  useEffect(() => {
    if (!playing) return
    const timer = window.setTimeout(() => {
      const currentIndex = events.findIndex(
        (event) => event.id === selectedEvent.id,
      )
      const nextIndex = currentIndex < 0 ? 0 : currentIndex + 1
      if (nextIndex >= events.length) {
        setPlaying(false)
        return
      }
      setSelectedEvent(events[nextIndex])
    }, 1600)
    return () => window.clearTimeout(timer)
  }, [playing, selectedEvent, setSelectedEvent])

  return (
    <main className="app-shell dark-shell">
      <AppNav screen="match" navigate={navigate} />
      <section className="match-content">
        <header className="dark-header">
          <div>
            <span className="section-kicker">
              Champions League · Matchday 12
            </span>
            <h1>Match Center</h1>
          </div>
          <div className="header-live">
            <span className="live-dot" /> Live data simulation
          </div>
        </header>
        <MatchScore match={simulatedMatch} />
        <nav className="match-tabs">
          {tabs.map((item) => (
            <button
              className={tab === item ? "active" : ""}
              onClick={() => setTab(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </nav>
        <div className="match-layout">
          <div className="pitch-column">
            {tab === "Stats" ? (
              <div className="stats-panel">
                <h2>Match statistics</h2>
                {liveStats.map(([label, home, away]) => (
                  <div className="stat-row" key={label}>
                    <b>{home}</b>
                    <div>
                      <span>{label}</span>
                      <i>
                        <em style={{ width: home }} />
                      </i>
                    </div>
                    <b>{away}</b>
                  </div>
                ))}
              </div>
            ) : tab === "Live Events" ? (
              <div className="event-feed">
                {events.map((event) => (
                  <button
                    key={event.id}
                    onClick={() => {
                      setSelectedEvent(event)
                      setTab("Overview")
                    }}
                  >
                    <span>{event.minute}'</span>
                    <div>
                      <strong>{event.label}</strong>
                      <small>{event.detail}</small>
                    </div>
                    <Icon name="arrow" />
                  </button>
                ))}
              </div>
            ) : (
              <div className="pitch-wrap">
                <div className="pitch-meta">
                  <span>
                    <Icon name="spark" size={16} /> Selected moment
                  </span>
                  <strong>
                    {selectedEvent.minute}' · {selectedEvent.title}
                  </strong>
                </div>
                <Pitch
                  event={selectedEvent}
                  playing={playing}
                  onSelectPlayer={setPlayer}
                />
                {player && (
                  <button
                    className="player-popover"
                    onClick={() => setPlayer("")}
                  >
                    <strong>{player}</strong>
                    <span>Tap to close</span>
                    <Icon name="close" size={15} />
                  </button>
                )}
              </div>
            )}
            <div className="playback">
              <Button
                className="play-main"
                onClick={() => setPlaying(!playing)}
              >
                {playing ? <Icon name="pause" /> : <Icon name="play" />}
              </Button>
              <Timeline
                selected={selectedEvent}
                setSelected={setSelectedEvent}
              />
              <Button
                variant="ghost"
                onClick={() => {
                  setSelectedEvent(events[0])
                  setPlaying(true)
                }}
              >
                <Icon name="replay" /> Replay
              </Button>
            </div>
            <div className="event-chips">
              {events.slice(1).map((event) => (
                <button
                  className={selectedEvent.id === event.id ? "active" : ""}
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                >
                  {event.label}
                </button>
              ))}
            </div>
          </div>
          <Assistant
            event={selectedEvent}
            mode={mode}
            onRelated={() => navigate("moment")}
          />
        </div>
      </section>
    </main>
  )
}

function MomentDetail({
  event,
  mode,
  navigate,
}: {
  event: EventData
  mode: Mode
  navigate: (screen: Screen) => void
}) {
  const [tab, setTab] = useState("Explanation")
  const [playing, setPlaying] = useState(false)
  return (
    <main className="detail-page">
      <header className="detail-header">
        <Button variant="ghost" onClick={() => navigate("match")}>
          <Icon name="back" /> Back to Match Center
        </Button>
        <Brand light />
        <span className="share-label">Synthetic match data</span>
      </header>
      <div className="detail-grid">
        <section className="detail-main">
          <span className="moment-pill">
            <Icon name="spark" size={16} /> Key moment · {event.minute}'
          </span>
          <h1>{event.title}</h1>
          <p>{event.detail}</p>
          <div className="detail-pitch">
            <Pitch event={event} playing={playing} />
          </div>
          <div className="video-controls">
            <Button className="play-main" onClick={() => setPlaying(!playing)}>
              {playing ? <Icon name="pause" /> : <Icon name="play" />}
            </Button>
            <div>
              <span className={playing ? "running" : ""} />
            </div>
            <small>{playing ? "0:07" : "0:00"} / 0:12</small>
            <Button variant="ghost" onClick={() => setPlaying(true)}>
              <Icon name="replay" /> Replay
            </Button>
          </div>
        </section>
        <aside className="detail-insight">
          <nav>
            {["Explanation", "Stats", "Player Involvement"].map((item) => (
              <button
                className={tab === item ? "active" : ""}
                onClick={() => setTab(item)}
                key={item}
              >
                {item}
              </button>
            ))}
          </nav>
          {tab === "Explanation" && (
            <div className="tab-copy">
              <span className="big-spark">
                <Icon name="spark" size={26} />
              </span>
              <h2>Why is this important?</h2>
              <p>
                {mode === "Football Expert"
                  ? "The pressing trap eliminates Arsenal's central exit. City's weak-side winger narrows early, allowing the full-back to jump and create a numerical superiority around the recovery."
                  : "City pressure Arsenal into a difficult pass, win the ball close to goal, and create a chance before the defense can reset."}
              </p>
              <div className="takeaway">
                <strong>Key takeaway</strong>
                <span>
                  The chance is created by collective movement, not just the
                  final pass.
                </span>
              </div>
            </div>
          )}
          {tab === "Stats" && (
            <div className="moment-stats">
              <h2>Sequence by numbers</h2>
              <div>
                <strong>6.2s</strong>
                <span>Regain to shot</span>
              </div>
              <div>
                <strong>4</strong>
                <span>Players involved</span>
              </div>
              <div>
                <strong>0.34</strong>
                <span>Expected goals</span>
              </div>
              <div>
                <strong>28m</strong>
                <span>Territory gained</span>
              </div>
            </div>
          )}
          {tab === "Player Involvement" && (
            <div className="player-list">
              <h2>Players involved</h2>
              {[
                ["Phil Foden", "Press trigger"],
                ["Rodri", "Lane blocked"],
                ["Kevin De Bruyne", "Final pass"],
                ["Erling Haaland", "Shot"],
              ].map(([name, role], index) => (
                <div key={name}>
                  <span>{index + 1}</span>
                  <div>
                    <strong>{name}</strong>
                    <small>{role}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </main>
  )
}

function Recap({
  mode,
  navigate,
  selectMoment,
}: {
  mode: Mode
  navigate: (screen: Screen) => void
  selectMoment: (event: EventData) => void
}) {
  const recapMatch = matches[2]
  const recapMoments: EventData[] = [
    {
      id: "barca-opening",
      minute: 18,
      label: "Goal · Yamal",
      type: "goal",
      player: "Lamine Yamal",
      title: "Yamal unlocks Inter's back line",
      detail:
        "Yamal receives wide, cuts inside the full-back and bends Barcelona's opener beyond the goalkeeper.",
    },
    {
      id: "inter-counter",
      minute: 57,
      label: "Goal · Martínez",
      type: "goal",
      player: "Lautaro Martínez",
      title: "Inter counter with perfect timing",
      detail:
        "Inter break through Barcelona's advanced line and Martínez finishes a three-pass counterattack.",
    },
    {
      id: "barca-winner",
      minute: 84,
      label: "Goal · Pedri",
      type: "pass",
      player: "Pedri",
      title: "Pedri finds the winning pass",
      detail:
        "Pedri waits for the defensive line to step before threading the pass that creates Barcelona's winner.",
    },
  ]
  return (
    <main className="app-shell light-shell">
      <AppNav screen="recap" navigate={navigate} />
      <section className="recap-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">Full time · Match recap</span>
            <h1>One match. Three turning points.</h1>
          </div>
        </header>
        <MatchScore match={recapMatch} />
        <section className="recap-hero">
          <div className="recap-art">
            <span className="celebration-number">3</span>
            <PlayerIllustration compact />
          </div>
          <div>
            <span className="section-kicker">
              <Icon name="spark" size={16} /> AI match summary
            </span>
            <h2>Barcelona's patience made the difference.</h2>
            <p>
              Inter repeatedly threatened in transition, but Barcelona kept
              rebuilding. Their width stretched the block, and one late passing
              lane settled a five-goal classic.
            </p>
            <span className="personal-note">Personalized for {mode}</span>
          </div>
        </section>
        <section className="recap-moments">
          <div className="section-heading">
            <div>
              <h2>Top 3 moments</h2>
            </div>
            <span>Select a moment for the full analysis</span>
          </div>
          <div className="recap-list">
            {recapMoments.map((event, index) => (
              <button key={event.title} onClick={() => selectMoment(event)}>
                <span className="moment-number">{index + 1}</span>
                <span className="moment-time">{event.minute}'</span>
                <div>
                  <strong>{event.title}</strong>
                  <small>{event.detail}</small>
                </div>
                <Icon name="arrow" />
              </button>
            ))}
          </div>
        </section>
      </section>
    </main>
  )
}

function Profile({
  favorite,
  favoritePlayer,
  language,
  mode,
  setFavorite,
  setFavoritePlayer,
  setLanguage,
  setMode,
  navigate,
}: {
  favorite: string
  favoritePlayer: string
  language: string
  mode: Mode
  setFavorite: (team: string) => void
  setFavoritePlayer: (player: string) => void
  setLanguage: (language: string) => void
  setMode: (mode: Mode) => void
  navigate: (screen: Screen) => void
}) {
  const [draftTeam, setDraftTeam] = useState(
    preferenceClubs.some((club) => club.name === favorite) ? favorite : "",
  )
  const [draftPlayer, setDraftPlayer] = useState(
    favoritePlayers.includes(favoritePlayer) ? favoritePlayer : "",
  )
  const [draftLanguage, setDraftLanguage] = useState(language)
  const [draftMode, setDraftMode] = useState<Mode>(mode)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setDraftLanguage(language)
  }, [language])

  function save() {
    setFavorite(draftTeam)
    setFavoritePlayer(draftPlayer)
    setLanguage(draftLanguage)
    setMode(draftMode)
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }
  return (
    <main className="app-shell light-shell">
      <AppNav screen="profile" navigate={navigate} />
      <section className="profile-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">My experience</span>
            <h1>Make every match yours.</h1>
            <p>Update what you follow and how the AI explains the game.</p>
          </div>
        </header>
        <div className="profile-card">
          <div className="profile-intro">
            <span>AL</span>
            <div>
              <h2>Alex Morgan</h2>
              <p>Match explorer since 2025</p>
            </div>
          </div>
          <div className="preference-summary">
            <span>
              <small>Language</small>
              <strong>{draftLanguage}</strong>
            </span>
            <span>
              <small>Favorite player</small>
              <strong>{draftPlayer}</strong>
            </span>
            <span>
              <small>Experience</small>
              <strong>{draftMode}</strong>
            </span>
          </div>
          <div className="preference-block">
            <h3>Language</h3>
            <div className="language-options">
              {["English", "Español"].map((item) => (
                <button
                  className={draftLanguage === item ? "selected" : ""}
                  key={item}
                  onClick={() => setDraftLanguage(item)}
                >
                  <span>{item === "English" ? "EN" : "ES"}</span>
                  <strong>{item}</strong>
                  {draftLanguage === item && <Icon name="check" size={16} />}
                </button>
              ))}
            </div>
          </div>
          <div className="preference-block">
            <h3>Favorite team</h3>
            <div className="team-grid compact-grid">
              {preferenceClubs.map((team) => (
                <button
                  className={`team-select ${
                    draftTeam === team.name ? "selected" : ""
                  }`}
                  key={team.name}
                  onClick={() => {
                    setDraftTeam(team.name)
                    setDraftPlayer("")
                  }}
                >
                  <img
                    alt={`Escudo de ${team.name}`}
                    className="profile-club-logo"
                    src={team.logo}
                  />
                  <strong>{team.name}</strong>
                </button>
              ))}
            </div>
          </div>
          <div className="preference-block">
            <h3>Favorite player</h3>
            <div className="player-options">
              {preferencePlayers
                .filter((item) => !draftTeam || item.club === draftTeam)
                .map((item) => (
                  <button
                    className={draftPlayer === item.name ? "selected" : ""}
                    key={item.name}
                    onClick={() => setDraftPlayer(item.name)}
                  >
                    <img alt="" src={item.image} />
                    <div>
                      <strong>{item.name}</strong>
                      <small>{item.club}</small>
                    </div>
                    {draftPlayer === item.name && (
                      <Icon name="check" size={16} />
                    )}
                  </button>
                ))}
            </div>
          </div>
          <div className="preference-block">
            <h3>Experience mode</h3>
            <div className="profile-modes">
              {([
                "Casual Fan",
                "Football Expert",
                "Player Focus",
              ] as Mode[]).map((item) => (
                <button
                  className={draftMode === item ? "selected" : ""}
                  key={item}
                  onClick={() => setDraftMode(item)}
                >
                  <Icon
                    name={
                      item === "Casual Fan"
                        ? "spark"
                        : item === "Football Expert"
                          ? "chart"
                          : "user"
                    }
                  />
                  <span>
                    <strong>{item}</strong>
                    <small>
                      {item === "Casual Fan"
                        ? "Clear, story-led insights"
                        : item === "Football Expert"
                          ? "Detailed tactical language"
                          : "Individual player analysis"}
                    </small>
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="save-row">
            <Button onClick={save}>
              {saved ? (
                <>
                  <Icon name="check" /> Preferences saved
                </>
              ) : (
                "Save preferences"
              )}
            </Button>
            <Button variant="ghost" onClick={() => navigate("discover")}>
              Return to Discover
            </Button>
          </div>
        </div>
      </section>
    </main>
  )
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("landing")
  const [favorite, setFavoriteState] = useState(
    () => localStorage.getItem("itg-team") ?? "North City",
  )
  const [favoritePlayer, setFavoritePlayerState] = useState(
    () => localStorage.getItem("itg-player") ?? "Milo Arden",
  )
  const [language, setLanguageState] = useState(
    () => localStorage.getItem("itg-language") || "Español",
  )
  const [mode, setModeState] = useState<Mode>(
    () => localStorage.getItem("itg-mode") as Mode || "Casual Fan",
  )
  const [match, setMatch] = useState(matches[0])
  const [selectedEvent, setSelectedEvent] = useState(events[events.length - 1])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" })
  }, [screen])

  useEffect(() => {
    const handleLanguageChange = (event: Event) => {
      setLanguageState((event as CustomEvent<string>).detail)
    }
    window.addEventListener("itg-language-change", handleLanguageChange)
    return () =>
      window.removeEventListener("itg-language-change", handleLanguageChange)
  }, [])

  function setFavorite(value: string) {
    setFavoriteState(value)
    localStorage.setItem("itg-team", value)
  }
  function setMode(value: Mode) {
    setModeState(value)
    localStorage.setItem("itg-mode", value)
  }
  function setFavoritePlayer(value: string) {
    setFavoritePlayerState(value)
    localStorage.setItem("itg-player", value)
  }
  function setLanguage(value: string) {
    setLanguageState(value)
    localStorage.setItem("itg-language", value)
  }
  function navigate(next: Screen) {
    setScreen(next)
  }
  function openMatch(nextMatch: MatchData) {
    setMatch(nextMatch)
    if (nextMatch.status === "FT") navigate("recap")
    else navigate("match")
  }
  function selectMoment(event: EventData) {
    setSelectedEvent(event)
    navigate("moment")
  }

  if (screen === "landing")
    return (
      <Landing
        language={language}
        mode={mode}
        setLanguage={setLanguage}
        navigate={navigate}
      />
    )
  if (screen === "onboarding")
    return (
      <Onboarding
        favorite={favorite}
        favoritePlayer={favoritePlayer}
        language={language}
        mode={mode}
        setFavorite={setFavorite}
        setFavoritePlayer={setFavoritePlayer}
        setLanguage={setLanguage}
        setMode={setMode}
        navigate={navigate}
      />
    )
  if (screen === "discover")
    return (
      <Discover
        favorite={favorite}
        favoritePlayer={favoritePlayer}
        language={language}
        mode={mode}
        setLanguage={setLanguage}
        navigate={navigate}
        openMatch={openMatch}
      />
    )
  if (screen === "matches")
    return (
      <Discover
        allMatches
        favorite={favorite}
        favoritePlayer={favoritePlayer}
        language={language}
        mode={mode}
        setLanguage={setLanguage}
        navigate={navigate}
        openMatch={openMatch}
      />
    )
  if (screen === "match")
    return (
      <MatchCenter
        match={match}
        mode={mode}
        navigate={navigate}
        selectedEvent={selectedEvent}
        setSelectedEvent={setSelectedEvent}
      />
    )
  if (screen === "moment")
    return (
      <MomentDetail event={selectedEvent} mode={mode} navigate={navigate} />
    )
  if (screen === "recap")
    return <Recap mode={mode} navigate={navigate} selectMoment={selectMoment} />
  return (
    <Profile
      favorite={favorite}
      favoritePlayer={favoritePlayer}
      language={language}
      mode={mode}
      setFavorite={setFavorite}
      setFavoritePlayer={setFavoritePlayer}
      setLanguage={setLanguage}
      setMode={setMode}
      navigate={navigate}
    />
  )
}
