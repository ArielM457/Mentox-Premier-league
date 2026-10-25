const video = document.querySelector('#match-video')
const connection = document.querySelector('#connection')
const errorBox = document.querySelector('#error')
const eventsBox = document.querySelector('#events')
const currentTime = document.querySelector('#current-time')
const videoTime = document.querySelector('#video-time')
const playbackState = document.querySelector('#playback-state')
const cursor = document.querySelector('#cursor')
const reconstructedCount = document.querySelector('#reconstructed-count')
const reconstructedEvents = document.querySelector('#reconstructed-events')
const visibleCount = document.querySelector('#visible-count')
const pipelineStatus = document.querySelector('#pipeline-status')
const pipelineSummary = document.querySelector('#pipeline-summary')
const liveStatus = document.querySelector('#live-status')
const liveResults = document.querySelector('#live-results')

let requestQueue = Promise.resolve()
let lastAdvancedMs = -1
const liveItems = []

function enqueue(operation) {
  requestQueue = requestQueue.then(operation).catch((error) => {
    errorBox.textContent = error.message
    connection.textContent = 'Error de sincronización'
    connection.classList.add('bad')
  })
  return requestQueue
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method ?? 'POST',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? `Error HTTP ${response.status}`)
  return payload
}

function eventCard(event) {
  const article = document.createElement('article')
  article.className = 'event'
  article.innerHTML = `
    <div><span class="event-type">${event.type}</span><span>${event.outcome}</span></div>
    <strong>${event.event_id}</strong>
    <dl>
      <div><dt>clock_ms</dt><dd>${event.clock_ms}</dd></div>
      <div><dt>video_time_ms</dt><dd>${event.video_time_ms}</dd></div>
      <div><dt>source</dt><dd>${event.source}</dd></div>
      <div><dt>player_id</dt><dd>${event.player_id ?? 'no disponible'}</dd></div>
      <div><dt>track_id</dt><dd>${event.track_id ?? 'no disponible'}</dd></div>
      <div><dt>origen</dt><dd>${event.prediction_origin}</dd></div>
    </dl>`
  return article
}

function metric(label, value) {
  const article = document.createElement('article')
  article.className = 'metric'
  article.innerHTML = `<span>${label}</span><strong>${value}</strong>`
  return article
}

function modelCard(kind, item) {
  const article = document.createElement('article')
  article.className = `event ${kind === 'CANDIDATO' ? 'candidate' : ''}`
  const identifier = item.prediction_id ?? item.action?.prediction_id ?? 'sin identificador'
  const timestamp = item.timestamp_ms ?? item.action?.timestamp_ms
  const label = item.label ?? item.action?.label
  const confidence = item.confidence ?? item.action?.confidence
  const track = item.track_id ?? item.player?.track_id
  article.innerHTML = `
    <div><span class="event-type">${kind}</span><span>${label}</span></div>
    <strong>${identifier}</strong>
    <dl>
      <div><dt>video_time_ms</dt><dd>${timestamp}</dd></div>
      <div><dt>confidence</dt><dd>${Number(confidence).toFixed(4)}</dd></div>
      <div><dt>track_id</dt><dd>${track ?? 'no disponible'}</dd></div>
      <div><dt>player_id</dt><dd>${item.player_id ?? 'no disponible'}</dd></div>
    </dl>`
  return article
}

async function loadPipelineStatus() {
  const status = await api('/api/v1/integration/status', { method: 'GET' })
  pipelineStatus.textContent = status.status === 'ready' ? 'Pipeline listo' : status.status
  pipelineSummary.replaceChildren(
    metric('Video', status.video_available ? 'disponible' : 'ausente'),
    metric('Roboflow', 'fuente preparada'),
    metric('SoccerNet', 'fuente preparada'),
    metric('Fusión', `${status.fusion.candidates} candidato`),
    metric('MatchEvent visual', status.fusion.match_events_published),
    metric('Transporte visual', status.runtime.vision_observations.transport),
    metric('Blob Azure', status.runtime.blob_storage_configured ? 'configurado' : 'local'),
  )
}

function connectLiveChannel() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/integration/live/ws`)
  socket.addEventListener('open', () => { liveStatus.textContent = 'Worker conectado' })
  socket.addEventListener('close', () => {
    liveStatus.textContent = 'Desconectado; reintentando…'
    window.setTimeout(connectLiveChannel, 2000)
  })
  socket.addEventListener('message', (message) => {
    const data = JSON.parse(message.data)
    if (data.type !== 'observation') return
    const observation = data.observation
    liveItems.unshift(observation)
    liveItems.splice(24)
    liveStatus.textContent = `${liveItems.length} recientes`
    liveResults.replaceChildren(...liveItems.map(item => modelCard(
      item.kind === 'spatial_detection' ? 'DETECCIÓN EN VIVO' : 'ACCIÓN EN VIVO',
      item.payload,
    )))
  })
}

function render(snapshot) {
  connection.textContent = 'Backend conectado'
  connection.classList.remove('bad')
  errorBox.textContent = ''
  currentTime.textContent = `${video.currentTime.toFixed(3)} s`
  videoTime.textContent = snapshot.video_time_ms
  playbackState.textContent = snapshot.playback_state
  cursor.textContent = `${snapshot.event_cursor} / ${snapshot.total_events}`
  reconstructedCount.textContent = snapshot.reconstructed_state.event_count
  reconstructedEvents.textContent = snapshot.reconstructed_state.event_ids.join(', ') || 'Sin eventos anteriores'
  visibleCount.textContent = `${snapshot.visible_events.length} eventos`
  eventsBox.replaceChildren(...snapshot.visible_events.map(eventCard))
  if (snapshot.visible_events.length === 0) {
    const empty = document.createElement('p')
    empty.className = 'empty'
    empty.textContent = 'Todavía no se cruzaron eventos visibles en este tramo.'
    eventsBox.append(empty)
  }
}

function positionMs() {
  return Math.min(30_000, Math.max(0, Math.round(video.currentTime * 1_000)))
}

video.addEventListener('loadedmetadata', () => {
  currentTime.textContent = `${video.currentTime.toFixed(3)} s`
})

video.addEventListener('play', () => enqueue(async () => {
  await api('/api/v1/integration/live/playback/play', {
    body: { video_time_ms: positionMs() },
  })
  render(await api('/api/integration/video-sync/play'))
}))
video.addEventListener('pause', () => enqueue(async () => {
  await api('/api/v1/integration/live/playback/pause', {
    body: { video_time_ms: positionMs() },
  })
  render(await api('/api/integration/video-sync/pause'))
}))
video.addEventListener('timeupdate', () => {
  currentTime.textContent = `${video.currentTime.toFixed(3)} s`
  const target = positionMs()
  if (video.paused || target === lastAdvancedMs) return
  lastAdvancedMs = target
  enqueue(async () => {
    await api('/api/v1/integration/live/playback/advance', {
      body: { video_time_ms: target },
    })
    render(await api('/api/integration/video-sync/advance', {
      body: { video_time_ms: target },
    }))
  })
})
video.addEventListener('seeked', () => {
  const target = positionMs()
  lastAdvancedMs = target
  liveItems.splice(0)
  liveResults.replaceChildren()
  enqueue(async () => {
    await api('/api/v1/integration/live/playback/seek', {
      body: { video_time_ms: target },
    })
    render(await api('/api/integration/video-sync/seek', {
      body: { video_time_ms: target },
    }))
  })
})

document.querySelector('#back').addEventListener('click', () => {
  video.currentTime = Math.max(0, video.currentTime - 5)
})
document.querySelector('#forward').addEventListener('click', () => {
  video.currentTime = Math.min(video.duration || 30, video.currentTime + 5)
})
document.querySelector('#restart').addEventListener('click', () => {
  video.pause()
  video.currentTime = 0
  lastAdvancedMs = 0
  liveItems.splice(0)
  liveResults.replaceChildren()
  enqueue(async () => {
    await api('/api/v1/integration/live/playback/restart')
    render(await api('/api/integration/video-sync/restart'))
  })
})
document.querySelector('#export').addEventListener('click', () => enqueue(async () => {
  const payload = await api('/api/integration/video-sync/log', { method: 'GET' })
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'dv-us-18-session-log.json'
  link.click()
  URL.revokeObjectURL(link.href)
}))

enqueue(async () => {
  await api('/api/v1/integration/live/playback/restart')
  await loadPipelineStatus()
  render(await api('/api/integration/video-sync/session'))
})
connectLiveChannel()
