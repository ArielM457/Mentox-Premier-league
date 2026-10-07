import { useEffect, useState } from 'react'
import './App.css'

const exampleEvent = {
  schema_version: '1.0',
  event_id: 'evt-104',
  match_id: 'demo-001',
  period: 1,
  clock_ms: 802000,
  video_time_ms: 805500,
  type: 'pass',
  team_id: 'team-a',
  player_id: 'player-7',
  start: { x: 43, y: 51 },
  end: { x: 62, y: 46 },
  outcome: 'success',
  source: 'synthetic',
  confidence: null,
  related_event_ids: [],
}

function App() {
  const [status, setStatus] = useState('Comprobando conexión')
  const [eventText, setEventText] = useState(JSON.stringify(exampleEvent, null, 2))
  const [result, setResult] = useState('')

  useEffect(() => {
    fetch('/api/v1/health')
      .then((response) => {
        if (!response.ok) throw new Error('La API no respondió correctamente')
        return response.json()
      })
      .then((data) => setStatus(data.status === 'ok' ? 'API conectada' : 'Estado desconocido'))
      .catch(() => setStatus('API sin conexión'))
  }, [])

  async function validateEvent(event) {
    event.preventDefault()
    setResult('Validando evento')

    try {
      const parsed = JSON.parse(eventText)
      const response = await fetch('/api/v1/events/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      })
      const data = await response.json()
      setResult(response.ok
        ? 'Evento válido: ' + data.event.event_id
        : 'Evento inválido: ' + JSON.stringify(data.detail))
    } catch (error) {
      setResult('No se pudo validar: ' + error.message)
    }
  }

  return (
    <main className="page">
      <header>
        <p className="eyebrow">Hackathon · Inteligencia de partidos</p>
        <h1>Base del proyecto</h1>
        <p>El monorepo ya conecta React con FastAPI. Aquí puedes comprobar el formato de un evento sintético. La narración, el vídeo y los agentes se incorporarán en las siguientes fases.</p>
      </header>

      <section className="panel" aria-labelledby="api-title">
        <h2 id="api-title">Backend</h2>
        <p className="status" role="status">{status}</p>
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">Abrir Swagger UI</a>
      </section>

      <section className="panel" aria-labelledby="event-title">
        <h2 id="event-title">Validar un evento</h2>
        <p>Edita el JSON y comprueba si cumple el contrato inicial.</p>
        <form onSubmit={validateEvent}>
          <label htmlFor="event-json">Evento en JSON</label>
          <textarea id="event-json" value={eventText} onChange={(event) => setEventText(event.target.value)} spellCheck="false" />
          <button type="submit">Validar evento</button>
        </form>
        {result && <p className="result" role="status">{result}</p>}
      </section>
    </main>
  )
}

export default App
