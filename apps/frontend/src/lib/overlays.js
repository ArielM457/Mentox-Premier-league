// Lógica pura de pantalla: qué mensaje se ve en cada instante del vídeo.

// Aplica un mensaje recibido. Si reemplaza a otro, el anterior termina cuando empieza el nuevo.
export function mergeOverlay(map, overlay) {
  const next = new Map(map)
  next.set(overlay.message_id, overlay)
  const replaced = overlay.replaces_message_id && next.get(overlay.replaces_message_id)
  if (replaced) {
    next.set(replaced.message_id, {
      ...replaced,
      display_until_ms: Math.min(replaced.display_until_ms, overlay.video_time_ms),
    })
  }
  return next
}

export function overlayMap(list) {
  return list.reduce(mergeOverlay, new Map())
}

// Solo un mensaje ocupa la zona principal (RNF-05) y nunca uno futuro (RF-37).
export function visibleOverlay(map, t) {
  let best = null
  for (const m of map.values()) {
    if (m.suppressed || m.video_time_ms > t || t >= m.display_until_ms) continue
    if (!best || m.video_time_ms > best.video_time_ms) best = m
  }
  return best
}

// Historial de lo ya ocurrido, del más reciente al más antiguo.
export function pastOverlays(map, t) {
  return [...map.values()]
    .filter((m) => m.video_time_ms <= t)
    .sort((a, b) => b.video_time_ms - a.video_time_ms)
}

export function formatClock(ms) {
  const total = Math.max(0, Math.floor(ms / 1000))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

// Identificador estable de un momento en la URL: el candidato si existe; si no, el mensaje.
export const momentIdOf = (overlay) => overlay.candidate_id ?? overlay.message_id

// Reloj del partido con su período ("2T · 1:05"); el tiempo de vídeo queda para la reproducción.
export function formatMatchClock(item, periodLabel) {
  return `${periodLabel(item.period)} · ${formatClock(item.clock_ms)}`
}
