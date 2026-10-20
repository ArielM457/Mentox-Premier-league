const PATHS = {
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
  eye: (<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>),
  eyeOff: (<><path d="M3 3l18 18" /><path d="M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4.2M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.6 9.6 0 0 0 5.4-1.6" /><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" /></>),
  lock: (<><rect x="4" y="10" width="16" height="11" rx="2.5" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>),
  alert: (<><path d="M12 3 2 20h20L12 3Z" /><path d="M12 10v4M12 17h.01" /></>),
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
