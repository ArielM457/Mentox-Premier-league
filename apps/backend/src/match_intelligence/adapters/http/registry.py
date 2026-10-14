from collections.abc import Callable

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import SyntheticMatch, generate_acceptance_match
from match_intelligence.application.match_session import MatchSession, NotFoundError
from match_intelligence.application.ports import AnalyticsPort, NarrativePort

DEMO_MATCH_ID = "synthetic-acceptance-001"
ANALYTICS_MATCH_ID = "synthetic-analytics-001"

# Escenarios sintéticos disponibles: el partido corto de aceptación de Persona 1
# y el partido de dos tiempos que usa Persona 2 para validar su analítica.
SCENARIOS: dict[str, Callable[..., SyntheticMatch]] = {
    "acceptance": generate_acceptance_match,
    "analytics": generate_analytics_scenario,
}
DEFAULT_SEEDS = {"acceptance": 2026, "analytics": 7}


class MatchRegistry:
    """Partidos cargados en memoria para la demo.

    Las fábricas permiten cambiar los adaptadores provisionales por los
    módulos reales de Persona 2 y Persona 3 sin tocar las rutas.
    """

    def __init__(
        self,
        analytics: Callable[[], AnalyticsPort],
        narrative: Callable[[str | None], NarrativePort],
    ) -> None:
        self._analytics = analytics
        self._narrative = narrative
        self._sessions: dict[str, MatchSession] = {}

    def load_synthetic(
        self,
        *,
        scenario: str = "acceptance",
        seed: int | None = None,
        match_id: str = DEMO_MATCH_ID,
        inject_error_in: str | None = None,
    ) -> MatchSession:
        generate = SCENARIOS.get(scenario)
        if generate is None:
            raise NotFoundError(f"No existe el escenario {scenario}")
        match = generate(seed=DEFAULT_SEEDS[scenario] if seed is None else seed, match_id=match_id)
        session = MatchSession(
            metadata=match.metadata,
            events=match.events,
            analytics=self._analytics(),
            narrative=self._narrative(inject_error_in),
            correction_narrative=self._narrative(None),
        )
        self._sessions[match_id] = session
        return session

    def get(self, match_id: str) -> MatchSession:
        session = self._sessions.get(match_id)
        if session is None:
            raise NotFoundError(f"No existe el partido {match_id}")
        return session

    def all(self) -> list[MatchSession]:
        return list(self._sessions.values())


def _default_registry() -> MatchRegistry:
    from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics
    from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative

    registry = MatchRegistry(
        analytics=ProvisionalAnalytics,
        narrative=lambda inject: ProvisionalNarrative(inject_error_in=inject),
    )
    registry.load_synthetic()
    registry.load_synthetic(scenario="analytics", match_id=ANALYTICS_MATCH_ID)
    return registry


_registry: MatchRegistry | None = None


def get_registry() -> MatchRegistry:
    """Dependencia de FastAPI; las pruebas la sustituyen con ``dependency_overrides``."""
    global _registry
    if _registry is None:
        _registry = _default_registry()
    return _registry
