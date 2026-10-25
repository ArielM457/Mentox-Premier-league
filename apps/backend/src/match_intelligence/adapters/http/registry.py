import os
from collections.abc import Callable

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import SyntheticMatch, generate_acceptance_match
from match_intelligence.application.match_session import MatchSession, NotFoundError
from match_intelligence.application.persistence import MatchPersistence, NullMatchPersistence
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
        return self.load_match(match, inject_error_in=inject_error_in)

    def load_match(self, match: SyntheticMatch, *, inject_error_in: str | None = None) -> MatchSession:
        """Carga un partido ya generado, por ejemplo leído de Supabase."""
        session = MatchSession(
            metadata=match.metadata,
            events=match.events,
            analytics=self._analytics(),
            narrative=self._narrative(inject_error_in),
            correction_narrative=self._narrative(None),
            persistence=self._persistence,
        )
        self._persistence.save_match(match.metadata, match.events)
        self._sessions[match.metadata.match_id] = session
        return session

    def get(self, match_id: str) -> MatchSession:
        session = self._sessions.get(match_id)
        if session is None:
            raise NotFoundError(f"No existe el partido {match_id}")
        return session

    def all(self) -> list[MatchSession]:
        return list(self._sessions.values())


# ANALYTICS_ENGINE elige la analítica: la provisional de Persona 4 o la real de
# Persona 2. MATCH_SOURCE elige de dónde salen los partidos al iniciar: los
# generadores sintéticos o la base de Supabase (SUPABASE_DB_URL).
ANALYTICS_ENGINES = ("provisional", "persona2")
MATCH_SOURCES = ("synthetic", "supabase")


def _setting(name: str, default: str, allowed: tuple[str, ...]) -> str:
    value = os.getenv(name, default).strip().lower() or default
    if value not in allowed:
        raise RuntimeError(f"{name} debe ser uno de {', '.join(allowed)}; se recibió {value}")
    return value


def _analytics_factory(engine: str, tracks: dict) -> Callable[[], AnalyticsPort]:
    if engine == "provisional":
        from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics

        return ProvisionalAnalytics

    from match_intelligence.application.analytics.pipeline import MatchAnalytics
    from match_intelligence.application.analytics.presentation import PresentationAnalytics

    return lambda: PresentationAnalytics(
        MatchAnalytics(tracking_provider=lambda metadata: tracks.get(metadata.match_id))
    )


def _stored_matches(load_tracking: bool) -> tuple[list[SyntheticMatch], dict]:
    from match_intelligence.adapters.storage.supabase_store import (
        DATABASE_URL_VARIABLE,
        SupabaseMatchStore,
    )
    from match_intelligence.application.analytics.tracking_input import tracks_from_observations

    store = SupabaseMatchStore.from_env()
    if store is None:
        raise RuntimeError(f"MATCH_SOURCE=supabase requiere la variable {DATABASE_URL_VARIABLE}")
    matches = store.load_matches()
    tracks = {}
    if load_tracking:
        for match in matches:
            tracking = store.load_tracking(match.metadata.match_id)
            if tracking is not None:
                conversion = tracks_from_observations(match.metadata, match.events, tracking)
                tracks[match.metadata.match_id] = conversion.tracks
    return matches, tracks


def _default_registry() -> MatchRegistry:
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

    engine = _setting("ANALYTICS_ENGINE", "provisional", ANALYTICS_ENGINES)
    source = _setting("MATCH_SOURCE", "synthetic", MATCH_SOURCES)
    matches, tracks = _stored_matches(engine == "persona2") if source == "supabase" else ([], {})

    registry = MatchRegistry(
        analytics=_analytics_factory(engine, tracks),
        narrative=narrative,
        persistence=SupabaseMatchRepository.from_environment(),
    )
    for match in matches:
        registry.load_match(match)
    if not matches:
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
