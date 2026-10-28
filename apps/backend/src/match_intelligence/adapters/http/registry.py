import os
from collections.abc import Callable

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.live_scenario import generate_live_scenario
from match_intelligence.adapters.sources.synthetic import SyntheticMatch, generate_acceptance_match
from match_intelligence.application.match_session import MatchSession, NotFoundError
from match_intelligence.application.persistence import MatchPersistence, NullMatchPersistence
from match_intelligence.application.ports import AnalyticsPort, NarrativePort

DEMO_MATCH_ID = "synthetic-acceptance-001"
ANALYTICS_MATCH_ID = "synthetic-analytics-001"
LIVE_MATCH_ID = "synthetic-live-001"

# Escenarios sintéticos disponibles: el partido corto de aceptación de Persona 1,
# su sesión separada marcada en vivo y el partido de dos tiempos de Persona 2.
SCENARIOS: dict[str, Callable[..., SyntheticMatch]] = {
    "acceptance": generate_acceptance_match,
    "analytics": generate_analytics_scenario,
    "live": generate_live_scenario,
}
DEFAULT_SEEDS = {"acceptance": 2026, "analytics": 7, "live": 19}


class MatchRegistry:
    """Partidos cargados en memoria para la demo.

    Las fábricas permiten cambiar los adaptadores provisionales por los
    módulos reales de Persona 2 y Persona 3 sin tocar las rutas.
    """

    def __init__(
        self,
        analytics: Callable[[], AnalyticsPort],
        narrative: Callable[[str | None], NarrativePort],
        persistence: MatchPersistence | None = None,
    ) -> None:
        self._analytics = analytics
        self._narrative = narrative
        self._persistence = persistence or NullMatchPersistence()
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
            persistence=self._persistence,
        )
        self._persistence.save_match(match.metadata, match.events)
        self._sessions[match_id] = session
        return session

    def get(self, match_id: str) -> MatchSession:
        session = self._sessions.get(match_id)
        if session is None:
            raise NotFoundError(f"No existe el partido {match_id}")
        return session

    def load_replay(self, replay) -> MatchSession:
        """Carga solo los eventos y jugadores del vídeo verificado, sin el guion local."""
        session = MatchSession(
            metadata=replay.metadata, events=replay.events,
            analytics=self._analytics(), narrative=self._narrative(None),
            correction_narrative=self._narrative(None), persistence=self._persistence,
            video_duration_ms=replay.duration_ms, data_source="messi_simulator",
        )
        session.set_tracking_frames(replay.tracking)
        self._persistence.save_match(replay.metadata, replay.events)
        self._sessions[session.match_id] = session
        return session

    def all(self) -> list[MatchSession]:
        return list(self._sessions.values())


def _default_registry() -> MatchRegistry:
    from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics
    from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative
    from match_intelligence.adapters.storage.supabase_match import SupabaseMatchRepository

    provider = os.getenv("NARRATIVE_PROVIDER", "provisional").lower()
    if provider == "azure":
        from match_intelligence.adapters.agents.narrative_port import Persona3NarrativeAdapter

        narrative = lambda inject: Persona3NarrativeAdapter.azure(inject)
    elif provider == "fixture":
        from match_intelligence.adapters.agents.narrative_port import Persona3NarrativeAdapter

        narrative = lambda inject: Persona3NarrativeAdapter.fixture(inject)
    else:
        narrative = lambda inject: ProvisionalNarrative(inject_error_in=inject)

    registry = MatchRegistry(
        analytics=ProvisionalAnalytics,
        narrative=narrative,
        persistence=SupabaseMatchRepository.from_environment(),
    )
    registry.load_synthetic()
    registry.load_synthetic(scenario="analytics", match_id=ANALYTICS_MATCH_ID)
    registry.load_synthetic(scenario="live", match_id=LIVE_MATCH_ID)
    return registry


_registry: MatchRegistry | None = None


def get_registry() -> MatchRegistry:
    """Dependencia de FastAPI; las pruebas la sustituyen con ``dependency_overrides``."""
    global _registry
    if _registry is None:
        _registry = _default_registry()
    return _registry
