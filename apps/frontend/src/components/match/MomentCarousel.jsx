import { useEffect, useRef, useState } from 'react'
import { usePreferences } from '../../app/preferences.js'
import { formatMatchClock, kindLabel } from '../../lib/overlays.js'

const SPEED_PX_PER_S = 40

// Momentos ya ocurridos como carrusel infinito. Si no caben, la fila avanza sola en bucle con una
// copia oculta detrás (sin foco ni lectura) y se detiene al pasar el ratón o al enfocar un momento.
// Si caben, queda quieta. Con movimiento reducido no se anima y se desplaza a mano.
export function MomentCarousel({ moments, currentId, onOpen }) {
  const { t } = usePreferences()
  const viewport = useRef(null)
  const group = useRef(null)
  const [distance, setDistance] = useState(0)

  // Ancho de una vuelta (incluye el espacio hasta la copia); 0 si los momentos caben.
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      const width = group.current?.offsetWidth ?? 0
      setDistance(width > (viewport.current?.clientWidth ?? 0) ? width : 0)
    })
    observer.observe(viewport.current)
    observer.observe(group.current)
    return () => observer.disconnect()
  }, [])

  const chips = moments.map((moment) => (
    <button className={currentId === moment.message_id ? 'active' : ''} key={moment.message_id} onClick={() => onOpen(moment)} type="button">
      {formatMatchClock(moment, t.match.period)} · {kindLabel(t.kinds, moment.kind)}
    </button>
  ))

  return (
    <div className={`event-chips moment-carousel ${distance ? 'is-looping' : ''}`} ref={viewport}>
      <div className="moment-carousel-track" style={{ '--loop-distance': `${distance}px`, '--loop-duration': `${distance / SPEED_PX_PER_S}s` }}>
        <div className="moment-carousel-group" ref={group}>{chips}</div>
        {distance > 0 && <div aria-hidden="true" className="moment-carousel-group" inert>{chips}</div>}
      </div>
    </div>
  )
}
