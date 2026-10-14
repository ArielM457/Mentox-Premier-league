// Ilustración vectorial del diseño de Persona 5.
export function PlayerIllustration({ compact = false }) {
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
