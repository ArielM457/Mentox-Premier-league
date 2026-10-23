"""Geometría del campo a partir de ``MatchMetadata``.

Las coordenadas de ``MatchEvent 1.0`` son fijas (0 a 100) y no cambian al
cambiar de lado. Para comparar ataques se normaliza ``x`` según la dirección
de ataque del equipo en cada período: ``x' = 100`` es siempre la portería
rival. Si falta la dirección, las funciones devuelven ``None`` en lugar de
suponer un sentido.
"""

from dataclasses import dataclass
from math import atan2, degrees, hypot

from match_intelligence.domain.contracts import (
    AttackDirection,
    MatchEvent,
    MatchMetadata,
    Position,
)

FINAL_THIRD_X = 200 / 3
DEFENSIVE_THIRD_X = 100 / 3
HALFWAY_X = 50.0
GOAL_WIDTH_M = 7.32


@dataclass(frozen=True, slots=True)
class PitchFrame:
    match_id: str
    length_m: float
    width_m: float
    team_ids: tuple[str, str]
    directions: dict[tuple[int, str], AttackDirection]
    player_teams: dict[str, str]

    @classmethod
    def from_metadata(cls, metadata: MatchMetadata) -> "PitchFrame":
        return cls(
            match_id=metadata.match_id,
            length_m=metadata.pitch_length_m,
            width_m=metadata.pitch_width_m,
            team_ids=(metadata.home_team.team_id, metadata.away_team.team_id),
            directions={
                (item.period, item.team_id): item.direction
                for item in metadata.attacking_directions
            },
            player_teams={player.player_id: player.team_id for player in metadata.players},
        )

    def opponent_of(self, team_id: str) -> str | None:
        home, away = self.team_ids
        if team_id == home:
            return away
        if team_id == away:
            return home
        return None

    def has_direction(self, team_id: str, period: int) -> bool:
        return (period, team_id) in self.directions

    def attack_x(self, team_id: str, period: int, x: float) -> float | None:
        """Convierte ``x`` fija en distancia hacia la portería rival (0 a 100)."""
        direction = self.directions.get((period, team_id))
        if direction is None:
            return None
        return x if direction is AttackDirection.LEFT_TO_RIGHT else 100.0 - x

    def attack_point(
        self, team_id: str, period: int, position: Position | None
    ) -> tuple[float, float] | None:
        if position is None:
            return None
        x = self.attack_x(team_id, period, position.x)
        if x is None:
            return None
        return (x, position.y)

    def event_start(self, event: MatchEvent) -> tuple[float, float] | None:
        return self.attack_point(event.team_id, event.period, event.start)

    def event_end(self, event: MatchEvent) -> tuple[float, float] | None:
        return self.attack_point(event.team_id, event.period, event.end)

    def distance_m(self, start: Position, end: Position) -> float:
        dx = (end.x - start.x) * self.length_m / 100
        dy = (end.y - start.y) * self.width_m / 100
        return hypot(dx, dy)

    def forward_gain_m(self, event: MatchEvent) -> float | None:
        """Avance hacia la portería rival en metros; negativo si retrocede."""
        start = self.event_start(event)
        end = self.event_end(event)
        if start is None or end is None:
            return None
        return (end[0] - start[0]) * self.length_m / 100

    def goal_distance_m(self, point: tuple[float, float]) -> float:
        """Distancia al centro de la portería rival desde un punto normalizado."""
        dx = (100.0 - point[0]) * self.length_m / 100
        dy = (point[1] - 50.0) * self.width_m / 100
        return hypot(dx, dy)

    def goal_angle_deg(self, point: tuple[float, float]) -> float:
        """Ángulo visible entre los dos postes desde un punto normalizado."""
        dx = (100.0 - point[0]) * self.length_m / 100
        dy = (point[1] - 50.0) * self.width_m / 100
        half = GOAL_WIDTH_M / 2
        angle = atan2(dy + half, dx) - atan2(dy - half, dx)
        return abs(degrees(angle))


def in_final_third(x: float) -> bool:
    return x >= FINAL_THIRD_X


def in_opponent_half(x: float) -> bool:
    return x >= HALFWAY_X
