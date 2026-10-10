"""Puerto para modelos de valor de acciones: xT, xG y VAEP.

El dominio no importa ninguna biblioteca de modelos. Un adaptador solo se usa
si su estado es ``enabled``; en otro caso la métrica se publica como no
disponible con el motivo y nunca se presenta un valor improvisado con el
nombre de xT, xG o VAEP.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from match_intelligence.domain.analytics.models import MetricOrigin, MetricValue
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.contracts import MatchEvent


class ValueModelName(StrEnum):
    XT = "xt"
    XG = "xg"
    VAEP = "vaep"


METRIC_KEYS: dict[ValueModelName, str] = {
    ValueModelName.XT: "xt_added",
    ValueModelName.XG: "xg",
    ValueModelName.VAEP: "vaep",
}
METRIC_UNITS: dict[ValueModelName, str] = {
    ValueModelName.XT: "xt",
    ValueModelName.XG: "xg",
    ValueModelName.VAEP: "vaep",
}


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    """Origen del modelo: sin esto no se puede revisar licencia ni calibración."""

    source: str
    license: str
    training_data: str
    version: str
    validation: dict[str, float | str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ValueModelStatus:
    name: ValueModelName
    enabled: bool
    reasons: tuple[str, ...] = ()
    provenance: ModelProvenance | None = None

    @property
    def formula_version(self) -> str:
        if self.provenance is None:
            return f"{self.name.value}@disabled"
        return f"{self.name.value}@{self.provenance.version}"


@dataclass(frozen=True, slots=True)
class EventValue:
    event_id: str
    team_id: str
    player_id: str | None
    value: float


class ActionValueModel(Protocol):
    name: ValueModelName

    def status(self) -> ValueModelStatus: ...

    def value(self, frame: PitchFrame, event: MatchEvent) -> float | None:
        """Valor del evento o ``None`` si no aplica o le faltan datos."""


class ValueModelRegistry:
    """Modelos disponibles para un análisis. Vacío por defecto."""

    def __init__(self, models: Iterable[ActionValueModel] = ()) -> None:
        self._models: dict[ValueModelName, ActionValueModel] = {}
        for model in models:
            self._models[model.name] = model

    def status(self, name: ValueModelName) -> ValueModelStatus:
        model = self._models.get(name)
        if model is None:
            return ValueModelStatus(
                name=name, enabled=False,
                reasons=("No hay un modelo configurado y validado para este análisis",),
            )
        return model.status()

    def statuses(self) -> list[ValueModelStatus]:
        return [self.status(name) for name in ValueModelName]

    def event_value(
        self, name: ValueModelName, frame: PitchFrame, event: MatchEvent
    ) -> EventValue | None:
        model = self._models.get(name)
        if model is None or not model.status().enabled:
            return None
        value = model.value(frame, event)
        if value is None:
            return None
        return EventValue(event.event_id, event.team_id, event.player_id, value)

    def event_metric(
        self, name: ValueModelName, frame: PitchFrame, event: MatchEvent
    ) -> MetricValue | None:
        item = self.event_value(name, frame, event)
        if item is None:
            return None
        return MetricValue(
            key=METRIC_KEYS[name], team_id=item.team_id, player_id=item.player_id,
            value=round(item.value, 4), unit=METRIC_UNITS[name],
            formula_version=self.status(name).formula_version,
            source_event_ids=[item.event_id], origin=MetricOrigin.VALUE_MODEL,
        )

    def team_metrics(
        self, frame: PitchFrame, events: Sequence[MatchEvent]
    ) -> list[MetricValue]:
        """Totales por equipo, o una cifra no disponible por modelo desactivado."""
        results: list[MetricValue] = []
        for name in ValueModelName:
            status = self.status(name)
            key, unit = METRIC_KEYS[name], METRIC_UNITS[name]
            if not status.enabled:
                results.append(
                    MetricValue(
                        key=key, value=None, available=False, unit=unit,
                        formula_version=status.formula_version, origin=MetricOrigin.VALUE_MODEL,
                        unavailable_reason="; ".join(status.reasons) or "Modelo desactivado",
                    )
                )
                continue
            values = [item for e in events if (item := self.event_value(name, frame, e)) is not None]
            for team_id in frame.team_ids:
                own = [item for item in values if item.team_id == team_id]
                results.append(
                    MetricValue(
                        key=key, team_id=team_id, value=round(sum(i.value for i in own), 4),
                        unit=unit, formula_version=status.formula_version,
                        source_event_ids=[i.event_id for i in own], origin=MetricOrigin.VALUE_MODEL,
                    )
                )
        return results
