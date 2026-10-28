const PATHS = {
  sun: (<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>),
  moon: <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />,
  arrow: (<><path d="M5 12h14" /><path d="m14 7 5 5-5 5" /></>),
  back: <path d="m15 18-6-6 6-6" />,
  home: (<><path d="m3 11 9-8 9 8" /><path d="M5 10v10h14V10M9 20v-6h6v6" /></>),
  match: (<><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M12 4v16M3 12h18" /><circle cx="12" cy="12" r="2.5" /></>),
  spark: (<><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" /><path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" /></>),
  user: (<><circle cx="12" cy="8" r="4" /><path d="M4 21c.7-4.4 3.4-6.5 8-6.5s7.3 2.1 8 6.5" /></>),
  search: (<><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>),
  play: <path d="m9 7 9 5-9 5V7Z" />,
  pause: <path d="M9 7v10M15 7v10" />,
  replay: (<><path d="M20 7v5h-5" /><path d="M19 12a7 7 0 1 0-2 5" /></>),
  chart: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  check: <path d="m5 12 4 4L19 6" />,
  ball: (<><circle cx="12" cy="12" r="9" /><path d="m9 9 3-2 3 2-1 4h-4L9 9ZM6 5l3 4M15 9l3-4M10 13l-3 5M14 13l3 5" /></>),
  shield: (<><path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6l-8-3Z" /><path d="m9 12 2 2 4-4" /></>),
  flag: (<><path d="M5 21V4" /><path d="M5 4h11l-2 4 2 4H5" /></>),
  broadcast: (<><circle cx="12" cy="12" r="2.2" /><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7" /><path d="M5.5 5.5a9.2 9.2 0 0 0 0 13M18.5 5.5a9.2 9.2 0 0 1 0 13" /></>),
  fullscreen: <path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5" />,
  fullscreenExit: <path d="M3 8h5V3M21 8h-5V3M3 16h5v5M21 16h-5v5" />,
  eye: (<><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="3" /></>),
  thumbUp: (<><path d="M7 10v10H3V10h4Z" /><path d="M7 18c3 2 8 2 10 1l2-7c.3-1.2-.5-2-1.5-2H14l1-4c.3-1.5-.8-3-2-3l-1 3-5 5v7Z" /></>),
  thumbDown: (<><path d="M7 14V4H3v10h4Z" /><path d="M7 6c3-2 8-2 10-1l2 7c.3 1.2-.5 2-1.5 2H14l1 4c.3 1.5-.8 3-2 3l-1-3-5-5V6Z" /></>),
  trash: (<><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14" /><path d="M10 11v6M14 11v6" /></>),
}

export function Icon({ name, size = 20 }) {
  return (
    <svg aria-hidden="true" className="icon" fill="none" height={size} viewBox="0 0 24 24" width={size}>
      <g stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
        {PATHS[name]}
      </g>
    </svg>
  )
}
