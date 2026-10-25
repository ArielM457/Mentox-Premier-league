"""Situaciones del partido (``situation@1``): faltas, tarjetas y detenciones.

``MatchEvent 1.0`` ya trae estos hechos como eventos propios (``foul``,
``yellow_card``, ``red_card``, ``injury_stoppage``). La regla no infiere nada:
convierte cada uno en un momento con su conteo hasta ese instante o, en una
detención, con la duración que indica el evento.
"""

from match_intelligence.domain.contracts import EventType

from .signals import NO_DETECTION, Detection, DetectionContext, signal_from
from .statistics import metric

SITUATION_RULE = "situation@1"
LIMIT_STOPPAGE = (
    "La duración sale del evento (stoppage_ms); no es un diagnóstico médico."
)

# Evento → (tipo de momento, clave del conteo).
_COUNTED = {
    EventType.FOUL: ("foul", "fouls"),
    EventType.YELLOW_CARD: ("yellow_card", "yellow_cards"),
    EventType.RED_CARD: ("red_card", "red_cards"),
}


class SituationDetector:
    """Un momento por falta, tarjeta o detención por lesión."""

    rule = SITUATION_RULE

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        players = [event.player_id] if event.player_id else []

        if event.type is EventType.INJURY_STOPPAGE:
            seconds = event.stoppage_ms / 1_000 if event.stoppage_ms else None
            return Detection(signals=(
                signal_from(
                    context, "injury_stoppage", self.rule,
                    facts=[metric(
                        "stoppage_seconds", seconds, [event.event_id],
                        team_id=event.team_id, player_id=event.player_id,
                    )],
                    source_event_ids=[event.event_id], team_id=event.team_id,
                    player_ids=players, evidence_limits=[LIMIT_STOPPAGE],
                ),
            ))

        counted = _COUNTED.get(event.type)
        if counted is None:
            return NO_DETECTION
        kind, key = counted
        team_events = [
            e.event_id for e in context.history
            if e.type is event.type and e.team_id == event.team_id
        ]
        facts = [metric(key, len(team_events), team_events, team_id=event.team_id)]
        if event.player_id:
            player_events = [
                e.event_id for e in context.history
                if e.type is event.type and e.player_id == event.player_id
            ]
            facts.append(metric(
                key, len(player_events), player_events,
                team_id=event.team_id, player_id=event.player_id,
            ))
        return Detection(signals=(
            signal_from(
                context, kind, self.rule, facts=facts, source_event_ids=[event.event_id],
                team_id=event.team_id, player_ids=players,
            ),
        ))
