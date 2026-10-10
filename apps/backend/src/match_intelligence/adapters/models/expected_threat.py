"""Expected Threat (xT) con una cuadrícula de valores por zona.

Implementa el método de Karun Singh (2019): el valor de una zona es la
probabilidad de marcar desde ella, ya sea tirando o moviendo el balón a otra
zona. La biblioteca socceraction (licencia MIT) usa el mismo método; aquí se
reimplementa sin pandas para que el adaptador sea opcional y comprobable.

El valor de una acción es ``xT(final) − xT(inicio)`` en coordenadas
normalizadas por dirección de ataque. Sin una cuadrícula entrenada con datos
con licencia y validada, el modelo queda desactivado.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from match_intelligence.application.analytics.value_models import (
    ModelProvenance,
    ValueModelName,
    ValueModelStatus,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.analytics.statistics import is_completed_pass
from match_intelligence.domain.contracts import MatchEvent

FORMAT_VERSION = "1"


@dataclass(frozen=True, slots=True)
class ExpectedThreatGrid:
    """``values[fila_y][columna_x]``; la última columna está junto a la portería rival."""

    values: tuple[tuple[float, ...], ...]

    @property
    def length_cells(self) -> int:
        return len(self.values[0]) if self.values else 0

    @property
    def width_cells(self) -> int:
        return len(self.values)

    def at(self, x: float, y: float) -> float:
        column = min(self.length_cells - 1, max(0, int(x / 100 * self.length_cells)))
        row = min(self.width_cells - 1, max(0, int(y / 100 * self.width_cells)))
        return self.values[row][column]

    def plausibility_issues(self) -> list[str]:
        """Comprobaciones mínimas antes de llamar xT a un valor."""
        issues = []
        if self.width_cells < 3 or self.length_cells < 4:
            return ["La cuadrícula debe tener al menos 4 columnas y 3 filas"]
        if any(len(row) != self.length_cells for row in self.values):
            return ["Todas las filas deben tener el mismo número de columnas"]
        flat = [value for row in self.values for value in row]
        if any(not 0 <= value <= 1 for value in flat):
            issues.append("Los valores deben estar entre 0 y 1")
        first = sum(row[0] for row in self.values) / self.width_cells
        last = sum(row[-1] for row in self.values) / self.width_cells
        if last <= first:
            issues.append("La amenaza media junto a la portería rival no supera a la de la propia")
        best = max(flat)
        best_column = next(c for row in self.values for c, v in enumerate(row) if v == best)
        if best_column < self.length_cells - 2:
            issues.append("El valor máximo no está en las dos columnas más cercanas a la portería")
        return issues


class ExpectedThreatModel:
    name = ValueModelName.XT

    def __init__(
        self,
        grid: ExpectedThreatGrid | None,
        provenance: ModelProvenance | None,
        *,
        reasons: Iterable[str] = (),
    ) -> None:
        self._grid = grid
        self._provenance = provenance
        problems = list(reasons)
        if grid is None:
            problems.append("No hay cuadrícula xT")
        else:
            problems.extend(grid.plausibility_issues())
        if provenance is None:
            problems.append("Falta la procedencia del modelo")
        else:
            problems.extend(provenance_issues(provenance))
        self._reasons = tuple(problems)

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "ExpectedThreatModel":
        if document.get("model") != "xt" or document.get("format_version") != FORMAT_VERSION:
            return cls(None, None, reasons=["El documento no es un modelo xT con formato 1"])
        try:
            grid = ExpectedThreatGrid(tuple(tuple(float(v) for v in row) for row in document["grid"]))
            provenance = ModelProvenance(**document["provenance"])
        except (KeyError, TypeError, ValueError) as error:
            return cls(None, None, reasons=[f"Documento xT inválido: {error}"])
        return cls(grid, provenance)

    @classmethod
    def from_file(cls, path: Path) -> "ExpectedThreatModel":
        return cls.from_document(json.loads(path.read_text(encoding="utf-8")))

    def status(self) -> ValueModelStatus:
        return ValueModelStatus(
            name=self.name, enabled=not self._reasons, reasons=self._reasons,
            provenance=self._provenance,
        )

    def value(self, frame: PitchFrame, event: MatchEvent) -> float | None:
        if self._grid is None or self._reasons or not is_completed_pass(event):
            return None
        start = frame.event_start(event)
        end = frame.event_end(event)
        if start is None or end is None:
            return None
        return self._grid.at(*end) - self._grid.at(*start)


def provenance_issues(provenance: ModelProvenance) -> list[str]:
    issues = []
    for field_name in ("source", "license", "training_data", "version"):
        if not getattr(provenance, field_name).strip():
            issues.append(f"La procedencia no indica {field_name}")
    if "synthetic" in provenance.training_data.lower() and not provenance.validation.get("reference"):
        issues.append(
            "Entrenado solo con datos sintéticos y sin comparación con una referencia externa"
        )
    return issues


@dataclass(frozen=True, slots=True)
class TrainingAction:
    """Acción en coordenadas normalizadas: ``x = 100`` es la portería rival."""

    start_x: float
    start_y: float
    end_x: float | None
    end_y: float | None
    kind: str  # "move" o "shot"
    success: bool  # movimiento completado o tiro convertido


def train_expected_threat(
    actions: Iterable[TrainingAction],
    *,
    length_cells: int = 12,
    width_cells: int = 8,
    max_iterations: int = 200,
    tolerance: float = 1e-6,
) -> ExpectedThreatGrid:
    """Iteración de valor de Singh (2019) sobre una cuadrícula ``length × width``."""

    def cell(x: float, y: float) -> tuple[int, int]:
        column = min(length_cells - 1, max(0, int(x / 100 * length_cells)))
        row = min(width_cells - 1, max(0, int(y / 100 * width_cells)))
        return row, column

    size = (width_cells, length_cells)
    totals = [[0] * size[1] for _ in range(size[0])]
    shots = [[0] * size[1] for _ in range(size[0])]
    goals = [[0] * size[1] for _ in range(size[0])]
    moves = [[0] * size[1] for _ in range(size[0])]
    transitions: dict[tuple[int, int], dict[tuple[int, int], int]] = {}

    for action in actions:
        row, column = cell(action.start_x, action.start_y)
        totals[row][column] += 1
        if action.kind == "shot":
            shots[row][column] += 1
            goals[row][column] += int(action.success)
        elif action.kind == "move":
            moves[row][column] += 1
            if action.success and action.end_x is not None and action.end_y is not None:
                target = cell(action.end_x, action.end_y)
                bucket = transitions.setdefault((row, column), {})
                bucket[target] = bucket.get(target, 0) + 1

    values = [[0.0] * size[1] for _ in range(size[0])]
    for _ in range(max_iterations):
        updated = [[0.0] * size[1] for _ in range(size[0])]
        change = 0.0
        for row in range(size[0]):
            for column in range(size[1]):
                total = totals[row][column]
                if total == 0:
                    continue
                shot_probability = shots[row][column] / total
                move_probability = moves[row][column] / total
                scoring = goals[row][column] / shots[row][column] if shots[row][column] else 0.0
                expected_move = 0.0
                if moves[row][column]:
                    for (target_row, target_column), count in transitions.get((row, column), {}).items():
                        expected_move += count / moves[row][column] * values[target_row][target_column]
                value = shot_probability * scoring + move_probability * expected_move
                updated[row][column] = value
                change = max(change, abs(value - values[row][column]))
        values = updated
        if change < tolerance:
            break
    return ExpectedThreatGrid(tuple(tuple(row) for row in values))


def grid_document(grid: ExpectedThreatGrid, provenance: ModelProvenance) -> dict[str, Any]:
    return {
        "model": "xt",
        "format_version": FORMAT_VERSION,
        "provenance": {
            "source": provenance.source,
            "license": provenance.license,
            "training_data": provenance.training_data,
            "version": provenance.version,
            "validation": dict(provenance.validation),
        },
        "grid": [list(row) for row in grid.values],
    }
