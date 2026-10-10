"""Expected Goals (xG) con regresión logística de distancia y ángulo.

``p(gol) = 1 / (1 + exp(-(b0 + b1·distancia_m + b2·ángulo_rad)))``

Es la forma más simple de xG basada en geometría. Modelos más ricos usan parte
del cuerpo, tipo de asistencia y posición del portero, que ``MatchEvent 1.0``
no trae. El adaptador solo se activa con coeficientes con procedencia y
pruebas de plausibilidad superadas; sin ellos la métrica no se publica.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import exp, log, radians
from pathlib import Path
from typing import Any

from match_intelligence.application.analytics.value_models import (
    ModelProvenance,
    ValueModelName,
    ValueModelStatus,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.contracts import EventType, MatchEvent

from .expected_threat import provenance_issues

FORMAT_VERSION = "1"
PENALTY_SPOT = (11.0, radians(36.5))
LONG_RANGE = (30.0, radians(13.5))


@dataclass(frozen=True, slots=True)
class LogisticCoefficients:
    intercept: float
    distance_m: float
    angle_rad: float

    def probability(self, distance_m: float, angle_rad: float) -> float:
        z = self.intercept + self.distance_m * distance_m + self.angle_rad * angle_rad
        if z >= 0:
            return 1 / (1 + exp(-z))
        ez = exp(z)
        return ez / (1 + ez)

    def plausibility_issues(self) -> list[str]:
        issues = []
        if self.distance_m >= 0:
            issues.append("La probabilidad debe bajar al alejarse de la portería")
        if self.angle_rad <= 0:
            issues.append("La probabilidad debe subir con un ángulo de tiro mayor")
        penalty = self.probability(*PENALTY_SPOT)
        long_range = self.probability(*LONG_RANGE)
        if not 0.2 <= penalty <= 0.9:
            issues.append(f"Un tiro desde 11 m centrado da {penalty:.2f}, fuera de 0,2-0,9")
        if not long_range < 0.1:
            issues.append(f"Un tiro desde 30 m da {long_range:.2f}; se espera menos de 0,1")
        return issues


class LogisticExpectedGoalsModel:
    name = ValueModelName.XG

    def __init__(
        self,
        coefficients: LogisticCoefficients | None,
        provenance: ModelProvenance | None,
        *,
        reasons: Iterable[str] = (),
    ) -> None:
        self._coefficients = coefficients
        self._provenance = provenance
        problems = list(reasons)
        if coefficients is None:
            problems.append("No hay coeficientes xG")
        else:
            problems.extend(coefficients.plausibility_issues())
        if provenance is None:
            problems.append("Falta la procedencia del modelo")
        else:
            problems.extend(provenance_issues(provenance))
        self._reasons = tuple(problems)

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "LogisticExpectedGoalsModel":
        if document.get("model") != "xg" or document.get("format_version") != FORMAT_VERSION:
            return cls(None, None, reasons=["El documento no es un modelo xG con formato 1"])
        try:
            coefficients = LogisticCoefficients(**document["coefficients"])
            provenance = ModelProvenance(**document["provenance"])
        except (KeyError, TypeError, ValueError) as error:
            return cls(None, None, reasons=[f"Documento xG inválido: {error}"])
        return cls(coefficients, provenance)

    @classmethod
    def from_file(cls, path: Path) -> "LogisticExpectedGoalsModel":
        return cls.from_document(json.loads(path.read_text(encoding="utf-8")))

    def status(self) -> ValueModelStatus:
        return ValueModelStatus(
            name=self.name, enabled=not self._reasons, reasons=self._reasons,
            provenance=self._provenance,
        )

    def value(self, frame: PitchFrame, event: MatchEvent) -> float | None:
        if self._coefficients is None or self._reasons or event.type is not EventType.SHOT:
            return None
        point = frame.event_start(event)
        if point is None:
            return None
        return self._coefficients.probability(
            frame.goal_distance_m(point), radians(frame.goal_angle_deg(point))
        )


@dataclass(frozen=True, slots=True)
class ShotSample:
    distance_m: float
    angle_rad: float
    goal: bool


def fit_logistic_xg(
    samples: Sequence[ShotSample], *, iterations: int = 50, tolerance: float = 1e-9
) -> LogisticCoefficients:
    """Máxima verosimilitud por Newton-Raphson (3 parámetros, sin dependencias)."""
    beta = [0.0, 0.0, 0.0]
    for _ in range(iterations):
        gradient = [0.0, 0.0, 0.0]
        hessian = [[0.0] * 3 for _ in range(3)]
        for sample in samples:
            features = (1.0, sample.distance_m, sample.angle_rad)
            p = LogisticCoefficients(*beta).probability(sample.distance_m, sample.angle_rad)
            error = float(sample.goal) - p
            weight = p * (1 - p)
            for i in range(3):
                gradient[i] += error * features[i]
                for j in range(3):
                    hessian[i][j] += weight * features[i] * features[j]
        step = _solve3(hessian, gradient)
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < tolerance:
            break
    return LogisticCoefficients(*beta)


def _solve3(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Resuelve un sistema 3×3 por eliminación de Gauss con pivoteo parcial."""
    rows = [matrix[i][:] + [vector[i]] for i in range(3)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda r: abs(rows[r][column]))
        rows[column], rows[pivot] = rows[pivot], rows[column]
        if abs(rows[column][column]) < 1e-12:
            raise ValueError("Los tiros no permiten estimar los coeficientes")
        for r in range(column + 1, 3):
            factor = rows[r][column] / rows[column][column]
            for c in range(column, 4):
                rows[r][c] -= factor * rows[column][c]
    solution = [0.0, 0.0, 0.0]
    for r in range(2, -1, -1):
        solution[r] = (rows[r][3] - sum(rows[r][c] * solution[c] for c in range(r + 1, 3))) / rows[r][r]
    return solution


def calibration_report(
    coefficients: LogisticCoefficients, samples: Sequence[ShotSample], *, bins: int = 5
) -> dict[str, float]:
    """Brier, log-loss y error máximo entre probabilidad media y tasa observada por tramo."""
    if not samples:
        raise ValueError("Se necesitan tiros para calibrar")
    predictions = [coefficients.probability(s.distance_m, s.angle_rad) for s in samples]
    brier = sum((p - s.goal) ** 2 for p, s in zip(predictions, samples)) / len(samples)
    clipped = [min(1 - 1e-12, max(1e-12, p)) for p in predictions]
    log_loss = -sum(
        log(p) if s.goal else log(1 - p) for p, s in zip(clipped, samples)
    ) / len(samples)
    ordered = sorted(zip(predictions, samples), key=lambda item: item[0])
    size = max(1, len(ordered) // bins)
    worst = 0.0
    for start in range(0, len(ordered), size):
        chunk = ordered[start:start + size]
        expected = sum(p for p, _ in chunk) / len(chunk)
        observed = sum(s.goal for _, s in chunk) / len(chunk)
        worst = max(worst, abs(expected - observed))
    return {"brier": brier, "log_loss": log_loss, "max_bin_gap": worst, "shots": float(len(samples))}


def coefficients_document(
    coefficients: LogisticCoefficients, provenance: ModelProvenance
) -> dict[str, Any]:
    return {
        "model": "xg",
        "format_version": FORMAT_VERSION,
        "provenance": {
            "source": provenance.source,
            "license": provenance.license,
            "training_data": provenance.training_data,
            "version": provenance.version,
            "validation": dict(provenance.validation),
        },
        "coefficients": {
            "intercept": coefficients.intercept,
            "distance_m": coefficients.distance_m,
            "angle_rad": coefficients.angle_rad,
        },
    }
