"""Ejemplos de contrato de Persona 2 para trabajar en paralelo.

Genera los archivos de ``docs/persona-2-estado-y-analitica/ejemplos``. Una
prueba vuelve a generarlos y compara el resultado con los archivos guardados:
si alguien cambia una regla sin regenerar los ejemplos, la prueba falla.
"""

import json
from typing import Any

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import SyntheticMatch, generate_acceptance_match
from match_intelligence.domain.analytics.models import AttentionOutcome

from match_intelligence.application.analytics.engine import replay
from match_intelligence.application.analytics.pipeline import MatchAnalytics, MatchAnalyzer, build_snapshot

PROFILES: dict[str, dict[str, str] | None] = {
    "neutral": None,
    "casual": {"mode": "casual"},
    "analyst": {"mode": "analyst"},
    "casual_rio": {"mode": "casual", "favorite_team_id": "team-rio"},
    "player_aurora_8": {"mode": "player", "favorite_player_id": "aurora-8"},
}


def _match_output(match: SyntheticMatch) -> dict[str, Any]:
    analytics = MatchAnalytics()
    analyzer = MatchAnalyzer(match.metadata)
    analyzer.extend(match.events)
    engine = replay(match.metadata, match.events)
    timeline = []
    for index in range(1, len(match.events) + 1):
        snapshot = build_snapshot(match.metadata, match.events[:index])
        timeline.append({
            "event_id": match.events[index - 1].event_id,
            "period": snapshot.period,
            "clock_ms": snapshot.clock_ms,
            "score": snapshot.score,
            "possession_team_id": snapshot.possession_team_id,
        })

    neutral = analytics.attention_report(match.metadata, match.events)
    profiles = {}
    for name, preferences in PROFILES.items():
        report = analytics.attention_report(match.metadata, match.events, preferences)
        profiles[name] = {
            "profile": report.profile,
            "emitted": [
                {"candidate_id": c.candidate_id, "kind": c.kind, "priority": c.priority}
                for c in report.candidates
            ],
            "discarded": [
                {
                    "candidate_id": d.candidate_id,
                    "kind": d.kind,
                    "priority": d.priority,
                    "threshold": d.threshold,
                    "reasons": [f"{r.code}:{r.points}" for r in d.reasons],
                }
                for d in report.discarded
            ],
        }
    return {
        "match_id": match.metadata.match_id,
        "event_count": len(match.events),
        "final_snapshot": engine.snapshot().model_dump(mode="json"),
        "state_timeline": timeline,
        "sequences": [
            {
                "sequence_id": s.sequence_id,
                "team_id": s.team_id,
                "period": s.period,
                "start_clock_ms": s.start_clock_ms,
                "end_clock_ms": s.end_clock_ms,
                "started_by": s.started_by,
                "outcome": s.outcome.value,
                "event_ids": list(s.event_ids),
                "context_event_ids": list(s.context_event_ids),
                "player_ids": list(s.player_ids),
            }
            for s in analyzer.sequences
        ],
        "detection_notes": [
            {"rule": n.rule, "anchor_event_id": n.anchor_event_id, "reason": n.reason}
            for n in analyzer.notes
        ],
        "candidates_neutral": [c.model_dump(mode="json") for c in neutral.candidates],
        "profiles": profiles,
    }


def build_examples() -> dict[str, Any]:
    acceptance = generate_acceptance_match()
    scenario = generate_analytics_scenario()
    analytics = MatchAnalytics()
    snapshot = build_snapshot(acceptance.metadata, acceptance.events)
    goal = next(
        c for c in analytics.candidates(acceptance.metadata, acceptance.events) if c.kind == "goal"
    )
    discarded = next(
        d for d in analytics.attention_report(scenario.metadata, scenario.events, {"mode": "casual"}).decisions
        if d.outcome is AttentionOutcome.DISCARDED
    )
    return {
        "match-snapshot-v1.valido.json": snapshot.model_dump(mode="json"),
        "match-snapshot-v1.sin-opcionales.json": {
            "contract_version": "1",
            "match_id": acceptance.metadata.match_id,
            "period": 1,
            "clock_ms": 0,
            "score": {"team-aurora": 0, "team-rio": 0},
        },
        "match-snapshot-v1.invalido.json": {
            "contract_version": "1",
            "match_id": acceptance.metadata.match_id,
            "period": 1,
            "clock_ms": 802000,
            "metrics": [{"key": "pass_accuracy", "team_id": "team-rio", "value": None,
                         "available": True, "unit": "percent"}],
        },
        "insight-candidate-v1.valido.json": goal.model_dump(mode="json"),
        "insight-candidate-v1.sin-opcionales.json": {
            "contract_version": "1",
            "candidate_id": "moment-evt-010",
            "match_id": acceptance.metadata.match_id,
            "period": 1,
            "clock_ms": 32000,
            "kind": "goal",
            "priority": 90,
            "source_event_ids": ["evt-010"],
        },
        "insight-candidate-v1.invalido.json": {
            "contract_version": "1",
            "candidate_id": "moment-evt-010",
            "match_id": acceptance.metadata.match_id,
            "period": 1,
            "clock_ms": 32000,
            "kind": "goal",
            "priority": 120,
            "source_event_ids": [],
        },
        "attention-decision-v1.descartado.json": discarded.model_dump(mode="json"),
        "partido-aceptacion.analitica.json": _match_output(acceptance),
        "escenario-analitica.analitica.json": _match_output(scenario),
    }


def render(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
