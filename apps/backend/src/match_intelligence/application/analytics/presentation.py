"""Analítica real de Persona 2 detrás del ``AnalyticsPort`` de la API (Persona 4).

La API valida sus respuestas con los contratos de ``domain/presentation.py``,
que son un subconjunto de ``MatchSnapshot v1`` e ``InsightCandidate v1`` de
Persona 2. Este adaptador calcula con ``MatchAnalytics`` y entrega solo los
campos que la API conoce. Los campos adicionales (razones, señales,
componentes, evidencia de seguimiento) siguen disponibles en ``MatchAnalytics``
y en el canal ``match-insights``.
"""

from collections.abc import Sequence

from match_intelligence.domain import presentation
from match_intelligence.domain.analytics import models
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata

from .pipeline import MatchAnalytics

_METRIC_FIELDS = frozenset(presentation.MetricValue.model_fields)
_SNAPSHOT_FIELDS = frozenset(presentation.MatchSnapshot.model_fields) - {"metrics"}
_CANDIDATE_FIELDS = frozenset(presentation.InsightCandidate.model_fields) - {"facts"}


def to_presentation_metric(metric: models.MetricValue) -> presentation.MetricValue:
    return presentation.MetricValue.model_validate(metric.model_dump(include=_METRIC_FIELDS))


def to_presentation_snapshot(snapshot: models.MatchSnapshot) -> presentation.MatchSnapshot:
    data = snapshot.model_dump(include=_SNAPSHOT_FIELDS)
    data["metrics"] = [to_presentation_metric(m) for m in snapshot.metrics]
    return presentation.MatchSnapshot.model_validate(data)


def to_presentation_candidate(candidate: models.InsightCandidate) -> presentation.InsightCandidate:
    data = candidate.model_dump(include=_CANDIDATE_FIELDS)
    data["facts"] = [to_presentation_metric(f) for f in candidate.facts]
    return presentation.InsightCandidate.model_validate(data)


class PresentationAnalytics:
    """``AnalyticsPort`` de Persona 4 calculado con el motor de Persona 2."""

    def __init__(self, analytics: MatchAnalytics | None = None) -> None:
        self._analytics = analytics or MatchAnalytics()

    @property
    def analytics(self) -> MatchAnalytics:
        return self._analytics

    def snapshot(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        *,
        video_time_ms: int,
    ) -> presentation.MatchSnapshot:
        full = self._analytics.snapshot(metadata, events, video_time_ms=video_time_ms)
        return to_presentation_snapshot(full)

    def candidates(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        preferences: presentation.ViewerPreferences,
    ) -> list[presentation.InsightCandidate]:
        return [
            to_presentation_candidate(c)
            for c in self._analytics.candidates(metadata, events, preferences)
        ]
