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


def main() -> None:
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    sample = json.loads((FIXTURES / "narrative_match.json").read_text(encoding="utf-8"))
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
    collection["item"] = [
        group for group in collection["item"] if group["name"] != "Narrativa"
    ]
    collection["item"].append({"name": "Narrativa", "item": items})
    collection["info"]["description"] = (
        "Pruebas de todas las rutas HTTP actuales. Usa datos sintéticos y baseUrl local. "
        "Las rutas de narrativa usan provider=fixture y no llaman a Azure."
    )
    COLLECTION.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
