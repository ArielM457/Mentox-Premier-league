"""Refresh narrative requests in the importable Postman collection."""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTION = Path(__file__).with_name("match-intelligence.postman_collection.json")
FIXTURES = ROOT / "apps" / "backend" / "tests" / "fixtures"


def request(name: str, path: str, body: dict, checks: list[str], description: str) -> dict:
    return {
        "name": name,
        "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "url": "{{baseUrl}}" + path,
            "description": description,
            "body": {
                "mode": "raw",
                "raw": json.dumps(body, ensure_ascii=False, indent=2),
                "options": {"raw": {"language": "json"}},
            },
        },
        "event": [
            {
                "listen": "test",
                "script": {"type": "text/javascript", "exec": checks},
            }
        ],
    }


def get(name: str, path: str, checks: list[str], description: str) -> dict:
    return {
        "name": name,
        "request": {"method": "GET", "header": [], "url": "{{baseUrl}}" + path, "description": description},
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": checks}}],
    }


def status(code: int) -> str:
    return f"pm.test('HTTP {code}', () => pm.response.to.have.status({code}));"


def match_experience_items() -> list[dict]:
    """Recorrido de Persona 4 sobre el partido sintético de aceptación.

    El orden importa: los mensajes registran las narraciones que después se
    consultan, revisan y reportan.
    """
    base = "/api/v1/matches/synthetic-acceptance-001"
    goal_draft = "draft-moment-evt-010-es-casual-normal"
    summary = "summary-synthetic-acceptance-001-es-casual-extended"
    body = "const body = pm.response.json();"
    return [
        request(
            "POST Cargar partido sintético",
            "/api/v1/matches",
            {"seed": 2026, "match_id": "synthetic-acceptance-001"},
            [status(201), body, "pm.test('Duración y eventos', () => { pm.expect(body.event_count).to.equal(10); pm.expect(body.duration_ms).to.equal(42000); });"],
            "Carga o reinicia el partido de aceptación de Persona 1.",
        ),
        get(
            "GET Partidos cargados",
            "/api/v1/matches",
            [
                status(200),
                body,
                "pm.test('Incluye los tres estados', () => { const byId = Object.fromEntries(body.map(m => [m.match_id, m.status])); pm.expect(byId['synthetic-acceptance-001']).to.equal('FT'); pm.expect(byId['synthetic-analytics-001']).to.equal('UPCOMING'); pm.expect(byId['synthetic-live-001']).to.equal('LIVE'); });",
            ],
            "Lista los partidos disponibles para la interfaz.",
        ),
        get(
            "GET Detalle del partido",
            base,
            [status(200), body, "pm.test('Equipos', () => pm.expect(body.metadata.home_team.name).to.equal('Aurora FC'));"],
            "Metadatos, duración y fuente de vídeo.",
        ),
        get(
            "GET Previa táctica del próximo partido",
            "/api/v1/matches/synthetic-analytics-001/preview",
            [
                status(200),
                body,
                "pm.test('Formaciones de ambos equipos', () => { pm.expect(body.home.formations.length).to.be.above(1); pm.expect(body.away.formations.length).to.be.above(1); });",
                "pm.test('Tres tácticas para cada equipo', () => { pm.expect(body.simulations.length).to.equal(6); pm.expect(new Set(body.simulations.map(s => s.team_id)).size).to.equal(2); });",
                "pm.test('Jugadas con ambos equipos y pases', () => pm.expect(body.simulations.every(s => s.frames.length === 7 && s.frames.every(f => f.players.length === 14 && f.action && f.ball_owner_id))).to.equal(true));",
                "pm.test('Documento previo local aprobado', () => { pm.expect(body.information.source.storage_kind).to.equal('local_fixture'); pm.expect(body.information.source.approved).to.equal(true); pm.expect(body.information.teams.length).to.equal(2); });",
            ],
            "Contrato estructurado del agente con alineaciones, tácticas y documento previo sintético.",
        ),
        get(
            "GET Eventos hasta 20 s",
            base + "/events?until_video_ms=20000",
            [status(200), body, "pm.test('Sin eventos futuros', () => pm.expect(body.events.every(e => e.video_time_ms <= 20000)).to.equal(true));"],
            "Nunca devuelve eventos posteriores al tiempo del vídeo.",
        ),
        get(
            "GET Seguimiento 11 contra 11",
            "/api/v1/matches/synthetic-live-001/tracking?from_video_ms=3000&to_video_ms=6000",
            [
                status(200),
                body,
                "pm.test('Fuente sintética declarada', () => pm.expect(body.source).to.equal('synthetic_mock'));",
                "pm.test('Veintidós jugadores identificados', () => pm.expect(body.frames.every(f => f.objects.filter(o => o.player_id).length === 22)).to.equal(true));",
            ],
            "Ventana acotada de TrackingFrame v1 para interpolar el movimiento del partido en vivo.",
        ),
        get(
            "GET Análisis de un momento",
            "/api/v1/matches/synthetic-live-001/moments/moment-live-018/analysis?mode=analyst",
            [
                status(200),
                body,
                "pm.test('Momento del motor de Persona 2', () => pm.expect(body.found_in_engine && body.kind === 'yellow_card').to.equal(true));",
                "pm.test('Cuatro lecturas alternativas', () => pm.expect(body.what_if.length).to.equal(4));",
                "pm.test('Posiciones del instante', () => pm.expect(body.frame.objects.length).to.be.above(21));",
            ],
            "Motivos, hechos, posiciones del instante y lecturas «¿qué habría pasado si…?» de un momento.",
        ),
        get(
            "GET Estado tras el gol",
            base + "/state?video_time_ms=34000",
            [status(200), body, "pm.test('Marcador 1-0', () => pm.expect(body.score['team-aurora']).to.equal(1));"],
            "MatchSnapshot v1 en el segundo 34 del vídeo.",
        ),
        get(
            "GET Mensajes en pantalla",
            base + "/overlays?language=es&mode=casual&level=normal",
            [status(200), body, "pm.test('Un solo gol', () => pm.expect(body.overlays.filter(o => o.kind === 'goal').length).to.equal(1));", "pm.test('Tiempo de vídeo', () => pm.expect(body.overlays.every(o => o.video_time_ms >= 0)).to.equal(true));"],
            "OverlayMessage v1 planificados con una sola zona de pantalla.",
        ),
        get(
            "GET Canal en directo sin jugador",
            base + "/stream?mode=player",
            [status(400), body, "pm.test('Explica el error', () => pm.expect(body.detail).to.include('jugador favorito'));"],
            "El canal SSE valida las preferencias antes de abrirse. Con preferencias válidas responde text/event-stream.",
        ),
        get(
            "GET Fuentes del gol",
            base + f"/drafts/{goal_draft}/sources",
            [status(200), body, "pm.test('Eventos de origen', () => pm.expect(body.events.map(e => e.event_id)).to.include('evt-010'));"],
            "Explicación y eventos que sustentan el mensaje.",
        ),
        request(
            "POST Pregunta sobre pases",
            base + "/questions",
            {"question": "¿Cuántos pases lleva Aurora?", "video_time_ms": 40000},
            [status(200), body, "pm.test('Cuenta con evidencia', () => { pm.expect(body.answer.headline).to.include('Aurora FC: 4'); pm.expect(body.answer.source_event_ids.length).to.equal(4); });"],
            "Respuesta calculada con los eventos ocurridos.",
        ),
        get(
            "GET Resumen final",
            base + "/summary?language=es&mode=casual",
            [status(200), body, "pm.test('Pendiente de revisión', () => pm.expect(body.status).to.equal('pending'));"],
            "El resumen se retiene hasta la revisión editorial.",
        ),
        get(
            "GET Publicación sin aprobar",
            base + f"/editorial/{summary}/published",
            [status(409), body, "pm.test('Bloqueado', () => pm.expect(body.detail).to.include('pending'));"],
            "No se publica sin aprobación editorial (RF-38).",
        ),
        request(
            "POST Aprobar resumen",
            base + f"/editorial/{summary}/review",
            {"decision": "approve", "reviewer": "Editor de prueba"},
            [status(200), body, "pm.test('Aprobado', () => pm.expect(body.status).to.equal('approved'));"],
            "Registra la decisión editorial.",
        ),
        get(
            "GET Publicación aprobada",
            base + f"/editorial/{summary}/published",
            [status(200), body, "pm.test('Estado editorial', () => pm.expect(body.editorial_status).to.equal('approved'));"],
            "Después de aprobar, el análisis final se publica.",
        ),
        get(
            "GET Cola editorial",
            base + "/editorial",
            [status(200), body, "pm.test('Incluye el resumen', () => pm.expect(body.map(r => r.draft.draft_id)).to.include('" + summary + "'));"],
            "Análisis finales y su estado.",
        ),
        request(
            "POST Reporte que no corresponde",
            base + "/reports",
            {"draft_id": goal_draft, "reason": "No fue gol"},
            [status(201), body, "pm.test('Se confirma la salida', () => pm.expect(body.outcome).to.equal('confirmed'));"],
            "El mensaje coincide con sus eventos y no se corrige.",
        ),
        get(
            "GET Reportes",
            base + "/reports",
            [status(200), body, "pm.test('Registra el reporte', () => pm.expect(body.length).to.be.above(0));"],
            "Historial de reportes y resultado de su verificación.",
        ),
        request(
            "POST Reproducir hasta 20 s",
            base + "/playback",
            {"action": "play", "video_time_ms": 20000},
            [status(200), body, "pm.test('Eventos aplicados', () => pm.expect(body.events_applied).to.equal(5));"],
            "Control del reproductor con el sincronizador de Persona 1.",
        ),
        get(
            "GET Estado del reproductor",
            base + "/playback",
            [status(200), body, "pm.test('Reproduciendo', () => pm.expect(body.state).to.equal('playing'));"],
            "Posición y estado actuales.",
        ),
        request(
            "POST Simular colas y agentes",
            base + "/simulation?language=es&mode=casual&level=normal",
            {},
            [status(200), body, "pm.test('Seis rutas', () => { pm.expect(body.steps.length).to.equal(6); pm.expect(body.metrics_queue).to.equal(1); pm.expect(body.important_queue).to.equal(4); });"],
            "Envía casos sintéticos por ingreso, métricas, eventos importantes y agentes.",
        ),
        get(
            "GET Recortes destacados",
            base + "/highlights",
            [status(200), body, "pm.test('Recorte pendiente', () => pm.expect(body[0].status).to.equal('pending'));"],
            "Lista los recortes propuestos por la simulación.",
        ),
        request(
            "POST Confirmar recorte destacado",
            base + "/highlights/clip-overlay-moment-evt-010-es-casual-normal/review",
            {"decision": "approved", "reviewer": "Analista de prueba"},
            [status(200), body, "pm.test('Confirmado', () => pm.expect(body.status).to.equal('approved'));"],
            "Registra la confirmación humana antes de publicar el recorte.",
        ),
    ]


def community_items() -> list[dict]:
    """Revisión comunitaria del resumen creado en «Experiencia del partido» (ejecutar después)."""
    base = "/api/v1/matches/synthetic-acceptance-001/community"
    summary = "summary-synthetic-acceptance-001-es-casual-extended"
    body = "const body = pm.response.json();"
    person = {"client_id": "postman-cliente-01", "author": "Postman"}
    return [
        get(
            "GET Votos por resumen",
            base,
            [status(200), body, "pm.test('Lista los resúmenes', () => pm.expect(body.map(r => r.draft_id)).to.include('" + summary + "'));"],
            "Conteo de votos de la comunidad para cada resumen de la cola editorial.",
        ),
        request(
            "POST Votar aprobar",
            base + f"/{summary}/votes",
            {**person, "vote": "approve"},
            [status(200), body, "pm.test('Cuenta el voto', () => pm.expect(body.approve).to.be.at.least(1));"],
            "Un voto por persona; volver a votar lo cambia.",
        ),
        request(
            "POST Sugerencia",
            base + f"/{summary}/messages",
            {**person, "kind": "suggestion", "text": "Agregaría el minuto exacto del gol."},
            [status(201), body, "pm.test('Guardada como sugerencia', () => pm.expect(body.kind).to.equal('suggestion'));"],
            "Las sugerencias pasan por el filtro de contenido.",
        ),
        request(
            "POST Comentario ofensivo",
            base + f"/{summary}/messages",
            {**person, "kind": "chat", "text": "qué resumen de mierda"},
            [status(422), body, "pm.test('Filtrado', () => pm.expect(body.rejection).to.equal('profanity'));"],
            "El filtro rechaza groserías, enlaces y spam antes de publicar.",
        ),
        get(
            "GET Sala del resumen",
            base + f"/{summary}?client_id=postman-cliente-01",
            [status(200), body, "pm.test('Recuerda mi voto', () => pm.expect(body.my_vote).to.equal('approve'));", "pm.test('Incluye la sugerencia', () => pm.expect(body.suggestions.length).to.be.above(0));"],
            "Votos, sugerencias y chat de un resumen.",
        ),
        get(
            "GET Canal de un resumen inexistente",
            base + "/no-existe/stream",
            [status(404), body, "pm.test('Explica el error', () => pm.expect(body.detail).to.include('no-existe'));"],
            "Con un resumen existente responde text/event-stream con vote y message en tiempo real.",
        ),
    ]


def main() -> None:
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    events_group = next(group for group in collection["item"] if group["name"] == "Eventos")
    events_group["item"] = [
        item for item in events_group["item"]
        if item["name"] != "POST Lote de eventos"
    ]
    valid_event = json.loads(events_group["item"][0]["request"]["body"]["raw"])
    invalid_event = {key: value for key, value in valid_event.items() if key != "clock_ms"}
    events_group["item"].append(
        request(
            "POST Lote de eventos",
            "/api/v1/events/validate-batch",
            [valid_event, invalid_event],
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Acepta y rechaza por separado', () => { pm.expect(body.accepted_count).to.equal(1); pm.expect(body.rejected_count).to.equal(1); });",
                "pm.test('Conserva la causa del rechazo', () => pm.expect(body.rejected[0].issues.some(issue => issue.location.includes('clock_ms'))).to.equal(true));",
            ],
            "Valida un lote sintético y devuelve cada rechazo con su causa.",
        )
    )
    sample = json.loads((FIXTURES / "narrative_match.json").read_text(encoding="utf-8"))
    routing_sample = json.loads(
        (FIXTURES / "agent-routing-scenarios.json").read_text(encoding="utf-8")
    )
    draft = json.loads((FIXTURES / "draft_valid.json").read_text(encoding="utf-8"))
    wrong_draft = copy.deepcopy(draft)
    wrong_draft["claims"][0]["value"] = 99
    snapshot = sample["snapshot"]
    pressure, goal = sample["candidates"]
    es_casual = {"language": "es", "mode": "casual", "level": "normal"}
    en_analyst = {"language": "en", "mode": "analyst", "level": "advanced"}
    player_absent = {
        "language": "es", "mode": "player", "level": "normal", "favorite_player_id": "player-9"
    }

    items = [
        request(
            "POST En directo ES casual",
            "/api/v1/narratives/live?provider=fixture",
            {"snapshot": snapshot, "candidate": pressure, "preferences": es_casual},
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Borrador verificado en español', () => { pm.expect(body.draft.verification_status).to.equal('approved'); pm.expect(body.draft.language).to.equal('es'); pm.expect(body.draft.content_kind).to.equal('live'); });",
                "pm.test('Eventos de origen trazables', () => pm.expect(body.draft.source_event_ids).to.deep.equal(['evt-101', 'evt-102']));",
                "pm.test('Sin causa táctica inventada', () => pm.expect(body.draft.explanation).to.include('No hay datos suficientes'));",
            ],
            "Narración sintética local. provider=fixture no usa Azure ni un modelo.",
        ),
        request(
            "POST En directo EN analista",
            "/api/v1/narratives/live?provider=fixture",
            {"snapshot": snapshot, "candidate": goal, "preferences": en_analyst},
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Modo e idioma aplicados', () => { pm.expect(body.draft.language).to.equal('en'); pm.expect(body.draft.mode).to.equal('analyst'); pm.expect(body.draft.level).to.equal('advanced'); });",
                "pm.test('Gol sustentado por evento', () => { pm.expect(body.draft.claims[0].key).to.equal('goals'); pm.expect(body.draft.source_event_ids).to.include('evt-105'); });",
            ],
            "Compara el modo analista en inglés con la misma fuente sintética.",
        ),
        request(
            "POST Jugador sin novedades",
            "/api/v1/narratives/live?provider=fixture",
            {"snapshot": snapshot, "candidate": pressure, "preferences": player_absent},
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Comunica ausencia de novedades', () => { pm.expect(body.draft.headline).to.include('Sin novedades'); pm.expect(body.draft.claims).to.be.empty; });",
            ],
            "El jugador elegido no participa en este momento.",
        ),
        request(
            "POST Pregunta con evidencia",
            "/api/v1/narratives/questions?provider=fixture",
            {
                "snapshot": snapshot,
                "candidates": [pressure, goal],
                "preferences": es_casual,
                "question": "¿Cuántas recuperaciones tiene player-7?",
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Responde con el dato solicitado', () => { pm.expect(body.draft.content_kind).to.equal('answer'); pm.expect(body.draft.claims[0].key).to.equal('recoveries'); pm.expect(body.draft.claims[0].value).to.equal(1); });",
                "pm.test('Cita el evento', () => pm.expect(body.draft.source_event_ids).to.deep.equal(['evt-103']));",
            ],
            "Pregunta sobre una métrica que existe en los eventos sintéticos.",
        ),
        request(
            "POST Pregunta sin evidencia",
            "/api/v1/narratives/questions?provider=fixture",
            {
                "snapshot": snapshot,
                "candidates": [pressure, goal],
                "preferences": es_casual,
                "question": "¿Cuál fue la velocidad del balón?",
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Reconoce el límite', () => { pm.expect(body.draft.explanation).to.include('No se puede determinar'); pm.expect(body.draft.claims).to.be.empty; });",
            ],
            "No se inventa una velocidad que los eventos no permiten calcular.",
        ),
        request(
            "POST Resumen pendiente",
            "/api/v1/narratives/summaries?provider=fixture",
            {
                "snapshot": snapshot,
                "candidates": [pressure, goal],
                "preferences": es_casual,
                "match_finished": True,
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Resumen final retenido', () => { pm.expect(body.draft.content_kind).to.equal('final'); pm.expect(body.draft.editorial_status).to.equal('pending'); });",
                "pm.test('Marcador y gol consistentes', () => { pm.expect(body.draft.headline).to.include('team-a 1 - team-b 0'); pm.expect(body.draft.source_event_ids).to.include('evt-105'); });",
            ],
            "El borrador final requiere revisión editorial antes de publicarse.",
        ),
        request(
            "POST Resumen antes del final",
            "/api/v1/narratives/summaries?provider=fixture",
            {
                "snapshot": snapshot,
                "candidates": [pressure, goal],
                "preferences": es_casual,
                "match_finished": False,
            },
            [
                "pm.test('HTTP 422', () => pm.response.to.have.status(422));",
                "pm.test('Exige partido finalizado', () => pm.expect(pm.response.json().detail.some(error => error.loc.includes('match_finished'))).to.equal(true));",
            ],
            "No permite pedir el análisis final sin indicar que terminó el partido.",
        ),
        request(
            "POST Reporte falso",
            "/api/v1/narratives/reports/resolve",
            {
                "report_id": "report-false",
                "draft": draft,
                "reason": "La cifra parece incorrecta",
                "snapshot": snapshot,
                "candidate": goal,
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Mantiene la conclusión correcta', () => { pm.expect(body.status).to.equal('no_error'); pm.expect(body.correction).to.equal(null); });",
            ],
            "La cifra original coincide con el evento y no necesita corrección.",
        ),
        request(
            "POST Reporte válido",
            "/api/v1/narratives/reports/resolve",
            {
                "report_id": "report-valid",
                "draft": wrong_draft,
                "reason": "La cifra del gol no coincide",
                "snapshot": snapshot,
                "candidate": goal,
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Confirma el error', () => pm.expect(body.status).to.equal('confirmed_error'));",
                "pm.test('Corrige con trazabilidad', () => { pm.expect(body.correction.original_draft_id).to.equal('draft-moment-goal-es-casual-normal-live'); pm.expect(body.correction.claims[0].value).to.equal(1); pm.expect(body.correction.source_event_ids).to.include('evt-105'); });",
            ],
            "La cifra alterada se contrasta y genera un borrador corregido.",
        ),
    ]
    routing_scenarios = {item["scenario_id"]: item for item in routing_sample["scenarios"]}
    routine = routing_scenarios["metrics-only-pass"]
    danger = routing_scenarios["immediate-danger-shot"]
    routing_items = [
        request(
            "POST Filtro solo métricas",
            "/api/v1/agent-routing/evaluate",
            {
                "match_id": routing_sample["match_id"],
                "events": routine["input_events"],
                "preferences": es_casual,
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('No llama agentes', () => { pm.expect(body.decision.route).to.equal('metrics_only'); pm.expect(body.agent_request).to.equal(null); pm.expect(body.dispatch).to.equal(null); });",
                "pm.test('Actualiza métricas', () => pm.expect(body.metric_updates[0].key).to.equal('passes'));",
            ],
            "Un pase normal actualiza métricas sin crear trabajo para agentes.",
        ),
        request(
            "POST Filtro de peligro",
            "/api/v1/agent-routing/evaluate",
            {
                "match_id": routing_sample["match_id"],
                "events": danger["input_events"],
                "preferences": es_casual,
            },
            [
                "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
                "const body = pm.response.json();",
                "pm.test('Activa peligro inmediato', () => pm.expect(body.decision.route).to.equal('danger_immediate'));",
                "pm.test('Despacha al agente correcto', () => pm.expect(body.dispatch.target_agent).to.equal('danger_simulation'));",
                "pm.test('Conserva trazabilidad', () => { pm.expect(body.agent_request.source_event_ids).to.include('evt-020'); pm.expect(body.agent_request.source_event_ids).to.include('evt-012'); });",
            ],
            "Un tiro desde una zona peligrosa crea una solicitud reducida y trazable.",
        ),
    ]
    collection["item"] = [
        group
        for group in collection["item"]
        if group["name"] not in {"Narrativa", "Enrutamiento de agentes", "Experiencia del partido", "Comunidad"}
    ]
    collection["item"].append(
        {"name": "Enrutamiento de agentes", "item": routing_items}
    )
    collection["item"].append({"name": "Narrativa", "item": items})
    collection["item"].append({"name": "Experiencia del partido", "item": match_experience_items()})
    collection["item"].append({"name": "Comunidad", "item": community_items()})
    collection["info"]["description"] = (
        "Pruebas de todas las rutas HTTP actuales. Usa datos sintéticos y baseUrl local. "
        "El filtro y el orquestador usan proveedores reproducibles. Las rutas de narrativa "
        "usan provider=fixture y no llaman a Azure. La experiencia del partido recorre "
        "estado, mensajes, preguntas, revisión editorial y reportes sobre el partido sintético."
    )
    COLLECTION.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
