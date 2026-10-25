"""Agente determinista y documento local para la previa de un partido sintético.

El agente no dibuja ni anima la interfaz. Entrega un contrato estructurado con
alineaciones y fotogramas que el frontend puede representar y reproducir.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.domain.contracts import MatchMetadata, Player, Position


AGENT_INSTRUCTIONS = """
Eres el agente de previa táctica de The Prime Moment.
Trabajas únicamente con los equipos y jugadores sintéticos recibidos.
Tu salida siempre debe ser datos estructurados, nunca HTML ni instrucciones visuales.
Para cada equipo debes proponer formaciones compatibles con la plantilla disponible,
asignar una posición válida de 0 a 100 a cada jugador y explicar brevemente el plan.
    También debes crear al menos tres tácticas reproducibles para cada equipo mediante
    fotogramas ordenados. Cada táctica debe incluir al menos diez contactos de balón y cinco
    atacantes participantes antes del remate. Cada fotograma incluye a los dos equipos,
    poseedor, posición y recorrido del balón, acción y fase. Mientras exista poseedor, su
    posición debe coincidir con la coordenada del balón. El ataque debe organizarse, enlazar
    varios pases y terminar en un gol simulado; el rival debe mantener una respuesta defensiva
    coherente. Las opciones deben incluir ataques posicionales, una transición que recorra el
    campo y una progresión con varios pases hacia adelante. El defensor más cercano presiona
    y sus compañeros ajustan marcas y coberturas por carril, sin formar una línea inmóvil.
    Los jugadores deben conservar su función y su posición entre fotogramas: el
    portero participa solo en el inicio, los defensores sostienen la cobertura y no atacan el
    área rival, los mediocampistas conectan líneas y los atacantes crean y ocupan los espacios
    de finalización. El siguiente receptor debe preparar su apoyo o desmarque antes de recibir.
    El equipo se desplaza como bloque, mantiene defensa de seguridad detrás del balón y ningún
    jugador vuelve de forma instantánea a su posición inicial. El último fotograma representa
    el balón dentro del arco y no tiene poseedor.
La información editorial solo puede proceder de un documento sintético aprobado.
No inventes jugadores para las alineaciones, no modifiques el partido real y no uses
datos de partidos reales de la Premier League. Ninguna jugada es una predicción.
""".strip()


class PositionedPlayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    team_id: str
    name: str
    shirt_number: int | None = None
    position: Position


class FormationOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formation_id: str
    name: str
    summary: str
    players: list[PositionedPlayer]


class TeamPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    team_name: str
    role: str
    color: str
    formations: list[FormationOption]


class SimulationFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at_ms: int = Field(ge=0)
    phase: str
    action: str
    ball: Position
    ball_owner_id: str | None = None
    involved_player_ids: list[str] = Field(default_factory=list)
    players: list[PositionedPlayer]


class TacticalSimulation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_id: str
    team_id: str
    title: str
    summary: str
    result: str
    duration_ms: int = Field(gt=0)
    frames: list[SimulationFrame]


class PrematchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    storage_kind: str
    approved: bool
    synthetic: bool
    updated_at: str


class MatchFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class RecentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opponent: str
    score: str
    result: str
    note: str


class PlayerAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player: str
    status: str
    reason: str


class KeyPlayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player: str
    role: str
    reason: str


class TeamPrematchInformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    overview: str
    form_summary: str
    recent_results: list[RecentResult]
    availability: list[PlayerAvailability]
    key_players: list[KeyPlayer]
    tactical_keys: list[str]
    probable_lineup: list[str]


class PrematchInformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    match_id: str
    source: PrematchSource
    headline: str
    overview: str
    match_facts: list[MatchFact]
    teams: list[TeamPrematchInformation]


class PrematchPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = "1"
    match_id: str
    status: str = "UPCOMING"
    generated_by: str = "prematch-tactics-agent"
    disclosure: str
    home: TeamPreview
    away: TeamPreview
    simulations: list[TacticalSimulation]
    information: PrematchInformation


FORMATION_TEMPLATES = (
    (
        "balanced",
        "4-3-3",
        "Salida equilibrada, tres apoyos en el medio y amplitud con los extremos.",
        (
            (8, 50),
            (26, 15), (28, 38), (28, 62), (26, 85),
            (49, 25), (44, 50), (49, 75),
            (73, 18), (77, 50), (73, 82),
        ),
    ),
    (
        "wide",
        "4-2-3-1",
        "Doble apoyo por dentro, extremos abiertos y una referencia alta.",
        (
            (8, 50),
            (27, 14), (29, 38), (29, 62), (27, 86),
            (48, 40), (48, 60),
            (64, 20), (62, 50), (64, 80),
            (78, 50),
        ),
    ),
    (
        "attack",
        "3-4-3",
        "Tres defensores sostienen la cobertura y cinco jugadores ocupan zonas de ataque.",
        (
            (8, 50),
            (29, 24), (31, 50), (29, 76),
            (51, 14), (49, 40), (49, 60), (51, 86),
            (74, 20), (78, 50), (74, 80),
        ),
    ),
)

TACTICS = {
    "wide_overload": {
        "title": "Superioridad por banda",
        "summary": "Forma un triángulo, crea un 2 contra 1 por fuera y termina con un pase atrás.",
        "phases": (
            "Control inicial", "Salida corta", "Devolución", "Cambio de lado", "Apoyo interior",
            "Triangulación", "Apertura", "Pared", "Desdoblamiento", "Pase atrás",
            "Descarga", "Remate", "Gol simulado",
        ),
        "actions": (
            "El portero controla y espera que el equipo se abra.",
            "El defensor recibe cerca del área para iniciar la salida.",
            "La pelota vuelve al portero y atrae la primera presión.",
            "El defensor del lado contrario recibe con espacio.",
            "El mediocampista baja y ofrece una línea de pase interior.",
            "El interior completa el triángulo mientras los defensores guardan la cobertura.",
            "El extremo recibe abierto y fija al lateral rival.",
            "El interior devuelve de primera para acelerar la jugada.",
            "El extremo recibe otra vez y ataca el espacio por fuera.",
            "El pase atrás encuentra al mediocampista que llega de frente.",
            "El delantero descarga y deja la pelota preparada.",
            "El atacante remata después de doce contactos coordinados.",
            "La jugada termina en un gol simulado.",
        ),
        "ball": (
            (10, 50), (21, 34), (14, 50), (29, 68), (40, 58), (49, 38), (60, 18),
            (65, 35), (76, 17), (80, 39), (85, 48), (91, 49), (98, 50),
        ),
        "owners": (0, 1, 0, 4, 7, 5, 8, 5, 8, 6, 9, 9, None),
        "lane": "wide",
    },
    "outside_box_shot": {
        "title": "Remate desde fuera del área",
        "summary": "Mueve al rival, libera la frontal y prepara al delantero para un remate lejano.",
        "phases": (
            "Control inicial", "Salida con central", "Pase vertical", "Apoyo interior",
            "Cambio de orientación", "Recepción entre líneas", "Descarga", "Segunda llegada",
            "Fijación", "Pase a la frontal", "Preparación", "Remate lejano", "Gol simulado",
        ),
        "actions": (
            "El portero inicia mientras el equipo ocupa todo el ancho.",
            "El central recibe y atrae al primer rival.",
            "El mediocampista supera la primera línea con un pase vertical.",
            "El interior ofrece un apoyo diagonal y mantiene la pelota hacia adelante.",
            "El cambio de orientación obliga al bloque rival a desplazarse.",
            "El extremo recibe entre líneas y fija al lateral.",
            "El delantero descarga de cara sin entrar todavía al área.",
            "El segundo mediocampista llega para continuar la circulación.",
            "Un atacante fija a los centrales y abre espacio frente al área.",
            "El pase encuentra al delantero libre en la frontal.",
            "El delantero acomoda la pelota fuera del área para preparar el disparo.",
            "El delantero remata desde fuera del área antes de que llegue el cierre.",
            "El remate lejano termina en un gol simulado.",
        ),
        "ball": (
            (10, 50), (21, 40), (34, 46), (45, 60), (54, 50), (62, 28), (68, 45),
            (73, 58), (77, 48), (80, 40), (82, 50), (83, 50), (99, 50),
        ),
        "owners": (0, 2, 5, 7, 6, 8, 9, 5, 10, 7, 9, 9, None),
        "lane": "central",
    },
    "high_press": {
        "title": "Presión alta y ataque rápido",
        "summary": "Recupera en bloque compacto, asegura la posesión y ataca antes del repliegue rival.",
        "phases": (
            "Recuperación", "Pase seguro", "Apoyo lateral", "Devolución", "Cambio corto",
            "Apoyo interior", "Pase vertical", "Descarga", "Nueva llegada", "Pase al área",
            "Control", "Remate", "Gol simulado",
        ),
        "actions": (
            "El mediocampista recupera y pone el balón bajo control.",
            "El primer apoyo asegura la posesión después de la presión.",
            "El segundo interior recibe mientras los delanteros cierran las salidas.",
            "Un defensor sostiene la línea alta y recicla sin abandonar la cobertura.",
            "El equipo cambia el ángulo con un pase corto.",
            "El interior ofrece apoyo antes de acelerar.",
            "El pase vertical rompe la primera línea defensiva.",
            "El delantero descarga para que continúe la llegada.",
            "El mediocampista recibe de nuevo cerca del área.",
            "La pelota entra al área con un pase preciso.",
            "El delantero controla y protege el balón.",
            "El atacante remata antes del cierre defensivo.",
            "La presión termina en un gol simulado.",
        ),
        "ball": (
            (55, 47), (59, 35), (62, 62), (50, 68), (65, 43), (70, 34), (74, 55),
            (80, 58), (84, 45), (87, 37), (90, 48), (93, 50), (98, 50),
        ),
        "owners": (7, 5, 6, 3, 5, 5, 6, 9, 7, 8, 9, 9, None),
        "lane": "press",
    },
    "full_field_counter": {
        "title": "Contraataque de campo completo",
        "summary": "Recupera en campo propio, abre una salida y acelera con apoyos hasta el área rival.",
        "phases": (
            "Recuperación", "Salida segura", "Primer pase vertical", "Apoyo de cara",
            "Aceleración", "Cambio de ritmo", "Carrera exterior", "Apoyo frontal",
            "Pase al espacio", "Llegada opuesta", "Pase atrás", "Remate", "Gol simulado",
        ),
        "actions": (
            "El mediocampista recupera en campo propio y levanta la cabeza.",
            "El defensor ofrece una salida segura antes de que llegue la presión.",
            "El primer pase vertical supera a los delanteros rivales.",
            "El interior recibe de cara y activa a los jugadores que corren por delante.",
            "El extremo acelera por fuera mientras el bloque acompaña la transición.",
            "El mediocampista cambia el ritmo con otro pase hacia adelante.",
            "El jugador exterior ataca el espacio y obliga al rival a retroceder.",
            "El delantero descarga de primera para sostener el contraataque.",
            "Un pase al espacio encuentra la carrera del segundo atacante.",
            "El extremo opuesto llega al área mientras los mediocampistas guardan el rebote.",
            "El pase atrás evita al último defensor y deja la pelota de frente.",
            "El atacante remata antes de que el bloque rival consiga reorganizarse.",
            "El contraataque termina en un gol simulado.",
        ),
        "ball": (
            (24, 62), (31, 55), (40, 60), (49, 52), (59, 35), (68, 46), (76, 24),
            (82, 43), (87, 66), (91, 54), (94, 45), (96, 50), (99, 50),
        ),
        "owners": (5, 2, 5, 7, 8, 6, 8, 9, 10, 9, 9, 9, None),
        "lane": "counter",
    },
    "vertical_progression": {
        "title": "Progresión vertical y pase al espacio",
        "summary": "Escalona apoyos por todo el campo y avanza con pases que rompen líneas.",
        "phases": (
            "Inicio abierto", "Pase a central", "Pase entre líneas", "Apoyo interior",
            "Giro hacia adelante", "Ruptura de línea", "Descarga", "Nuevo pase vertical",
            "Desmarque", "Pase al espacio", "Control orientado", "Definición", "Gol simulado",
        ),
        "actions": (
            "El portero inicia con el equipo repartido por todo el campo.",
            "El central recibe abierto y atrae al primer rival.",
            "El mediocampista aparece detrás de la primera presión.",
            "El interior ofrece un apoyo diagonal sin cerrar el carril central.",
            "La pelota vuelve a avanzar y supera la línea del medio.",
            "El extremo recibe entre líneas con un compañero corriendo por delante.",
            "El delantero descarga y mantiene la jugada orientada hacia el arco.",
            "Otro pase vertical aprovecha el espacio entre central y lateral.",
            "El atacante se desmarca antes de recibir cerca del área.",
            "El pase al espacio rompe la última línea defensiva.",
            "El delantero controla hacia el arco mientras llegan dos apoyos.",
            "La jugada termina con un remate después de una progresión continua.",
            "La progresión vertical termina en un gol simulado.",
        ),
        "ball": (
            (10, 50), (20, 38), (32, 44), (43, 58), (53, 48), (63, 28), (70, 47),
            (78, 60), (84, 38), (89, 52), (93, 48), (96, 50), (99, 50),
        ),
        "owners": (0, 2, 5, 7, 6, 8, 9, 6, 9, 9, 9, 9, None),
        "lane": "vertical",
    },
}

LOCAL_PREMATCH_DIR = Path(__file__).resolve().parents[3] / "data" / "prematch"


class PrematchTacticsAgent:
    """Genera la propuesta con reglas repetibles y sin alterar el estado real."""

    instructions = AGENT_INSTRUCTIONS

    def generate(self, metadata: MatchMetadata) -> PrematchPreview:
        home_players = [p for p in metadata.players if p.team_id == metadata.home_team.team_id]
        away_players = [p for p in metadata.players if p.team_id == metadata.away_team.team_id]
        home = self._team(metadata.home_team.team_id, metadata.home_team.name, "local", "#8257f5", home_players, False)
        away = self._team(metadata.away_team.team_id, metadata.away_team.name, "visitante", "#d8ff65", away_players, True)
        return PrematchPreview(
            match_id=metadata.match_id,
            disclosure="Datos sintéticos de demostración.",
            home=home,
            away=away,
            simulations=[
                *self._simulations(home, away, attacking_right=True),
                *self._simulations(away, home, attacking_right=False),
            ],
            information=self._load_information(metadata),
        )

    def _team(
        self,
        team_id: str,
        team_name: str,
        role: str,
        color: str,
        players: list[Player],
        mirror: bool,
    ) -> TeamPreview:
        formations = []
        for key, name, summary, template in FORMATION_TEMPLATES:
            selected = template[: len(players)]
            positioned = [
                PositionedPlayer(
                    player_id=player.player_id,
                    team_id=player.team_id,
                    name=player.name,
                    shirt_number=player.shirt_number,
                    position=Position(
                        x=round(95 - x * 0.45, 2) if mirror else round(5 + x * 0.45, 2),
                        y=y,
                    ),
                )
                for player, (x, y) in zip(players, selected, strict=False)
            ]
            formations.append(
                FormationOption(
                    formation_id=f"{team_id}-{key}",
                    name=name,
                    summary=summary,
                    players=positioned,
                )
            )
        return TeamPreview(
            team_id=team_id,
            team_name=team_name,
            role=role,
            color=color,
            formations=formations,
        )

    def _simulations(
        self, attacking: TeamPreview, defending: TeamPreview, *, attacking_right: bool
    ) -> list[TacticalSimulation]:
        return [
            self._simulation(attacking, defending, key, spec, attacking_right=attacking_right)
            for key, spec in TACTICS.items()
        ]

    def _simulation(
        self,
        attacking: TeamPreview,
        defending: TeamPreview,
        tactic_key: str,
        spec: dict,
        *,
        attacking_right: bool,
    ) -> TacticalSimulation:
        attack_base = attacking.formations[0].players
        defend_base = defending.formations[0].players
        total = len(spec["phases"])

        def orient(x: float) -> float:
            return x if attacking_right else 100 - x

        def attack_targets(lane: str, ball_x: float, ball_y: float) -> tuple[tuple[float, float], ...]:
            """Mantiene una estructura por funciones alrededor de la jugada."""
            progress = max(0, min(1, (ball_x - 10) / 89))
            lateral_shift = max(-7, min(7, (ball_y - 50) * 0.16))
            shapes = {
                "wide": (
                    (12 + 4 * progress, 50 + lateral_shift * 0.25),
                    (31 + 7 * progress, 15), (33 + 7 * progress, 38),
                    (33 + 7 * progress, 62), (31 + 7 * progress, 85),
                    (48 + 18 * progress, 28), (47 + 20 * progress, 50),
                    (48 + 18 * progress, 72), (61 + 22 * progress, 16),
                    (65 + 23 * progress, 50), (61 + 22 * progress, 84),
                ),
                "central": (
                    (12 + 4 * progress, 50 + lateral_shift * 0.25),
                    (32 + 7 * progress, 18), (34 + 7 * progress, 39),
                    (34 + 7 * progress, 61), (32 + 7 * progress, 82),
                    (46 + 22 * progress, 38), (48 + 24 * progress, 50),
                    (46 + 22 * progress, 62), (61 + 23 * progress, 32),
                    (64 + 25 * progress, 50), (61 + 23 * progress, 68),
                ),
                "press": (
                    (17 + 3 * progress, 50 + lateral_shift * 0.25),
                    (43 + 7 * progress, 16), (45 + 7 * progress, 38),
                    (45 + 7 * progress, 62), (43 + 7 * progress, 84),
                    (58 + 18 * progress, 32), (59 + 18 * progress, 50),
                    (58 + 18 * progress, 68), (71 + 16 * progress, 24),
                    (74 + 16 * progress, 50), (71 + 16 * progress, 76),
                ),
                "counter": (
                    (12 + 4 * progress, 50 + lateral_shift * 0.2),
                    (28 + 7 * progress, 15), (30 + 8 * progress, 38),
                    (30 + 8 * progress, 62), (28 + 7 * progress, 85),
                    (40 + 24 * progress, 34), (42 + 25 * progress, 52),
                    (40 + 24 * progress, 70), (61 + 28 * progress, 18),
                    (64 + 29 * progress, 50), (61 + 28 * progress, 82),
                ),
                "vertical": (
                    (12 + 4 * progress, 50 + lateral_shift * 0.2),
                    (29 + 8 * progress, 17), (31 + 9 * progress, 39),
                    (31 + 9 * progress, 61), (29 + 8 * progress, 83),
                    (43 + 23 * progress, 36), (45 + 24 * progress, 50),
                    (43 + 23 * progress, 64), (62 + 27 * progress, 24),
                    (65 + 28 * progress, 50), (62 + 27 * progress, 76),
                ),
            }[lane]
            return tuple(
                (orient(x), max(8, min(92, y + lateral_shift))) for x, y in shapes
            )

        def defend_targets(
            ball_x: float,
            ball_y: float,
            attackers: list[PositionedPlayer],
            defenders: list[PositionedPlayer],
        ) -> tuple[tuple[float, float], ...]:
            """Replica presión cercana, marcas por carril y repliegue del seguimiento."""
            progress = max(0, min(1, (ball_x - 10) / 89))
            shifted = max(-10, min(10, (ball_y - 50) * 0.28))
            xs = (
                94 + progress,
                78 + 10 * progress, 78 + 10 * progress,
                78 + 10 * progress, 78 + 10 * progress,
                63 + 14 * progress, 63 + 14 * progress, 63 + 14 * progress,
                48 + 16 * progress, 48 + 16 * progress, 48 + 16 * progress,
            )
            ys = (
                50 + shifted * 0.2,
                15 + shifted, 38 + shifted, 62 + shifted, 85 + shifted,
                25 + shifted, 50 + shifted, 75 + shifted,
                20 + shifted, 50 + shifted, 80 + shifted,
            )
            bases = [(x, max(8, min(92, y))) for x, y in zip(xs, ys, strict=False)]
            relative_defenders = [
                (player.position.x if attacking_right else 100 - player.position.x, player.position.y)
                for player in defenders
            ]
            presser_index = min(
                range(1, len(relative_defenders)),
                key=lambda index: (
                    (relative_defenders[index][0] - ball_x) ** 2
                    + (relative_defenders[index][1] - ball_y) ** 2
                ),
            )
            relative_attackers = [
                (
                    player.position.x if attacking_right else 100 - player.position.x,
                    player.position.y,
                )
                for player in attackers[1:]
            ]
            targets: list[tuple[float, float]] = []
            for index, (base_x, base_y) in enumerate(bases):
                if index == 0:
                    target_x, target_y = base_x, base_y
                elif index == presser_index:
                    target_x = max(14, min(96, ball_x + 2.5))
                    target_y = max(8, min(92, ball_y))
                else:
                    marked_x, marked_y = min(
                        relative_attackers,
                        key=lambda point: (
                            abs(point[1] - base_y) + 0.25 * abs(point[0] - base_x)
                        ),
                    )
                    goal_side_x = max(ball_x + 3, marked_x + 2.5)
                    target_x = base_x * 0.55 + min(96, goal_side_x) * 0.45
                    target_y = base_y * 0.45 + marked_y * 0.55
                targets.append((orient(target_x), max(8, min(92, target_y))))
            return tuple(targets)

        initial_ball_x, initial_ball_y = spec["ball"][0]
        attacker_state = self._advance_players(
            list(attack_base),
            attack_targets(spec["lane"], initial_ball_x, initial_ball_y),
            max_step=100,
        )
        defender_state = self._advance_players(
            list(defend_base),
            defend_targets(initial_ball_x, initial_ball_y, attacker_state, list(defend_base)),
            max_step=100,
        )
        frames: list[SimulationFrame] = []
        for index, (phase, action, ball_point, owner_index) in enumerate(
            zip(spec["phases"], spec["actions"], spec["ball"], spec["owners"], strict=True)
        ):
            ball = Position(x=orient(ball_point[0]), y=ball_point[1])
            targets = attack_targets(spec["lane"], ball_point[0], ball.y)
            attackers = self._advance_players(attacker_state, targets, max_step=8)
            defensive_targets = defend_targets(
                ball_point[0], ball.y, attackers, defender_state
            )
            defenders = self._advance_players(defender_state, defensive_targets, max_step=7)

            # El receptor se mueve antes de que salga el pase. Se parte de su
            # posición anterior para que el desmarque sea continuo y no una
            # persecución tardía del balón.
            if index + 1 < total:
                next_owner_index = spec["owners"][index + 1]
                if next_owner_index is not None and next_owner_index != owner_index:
                    safe_next_index = min(next_owner_index, len(attackers) - 1)
                    next_ball_point = spec["ball"][index + 1]
                    next_ball = Position(x=orient(next_ball_point[0]), y=next_ball_point[1])
                    next_player = attackers[safe_next_index]
                    prepared_position = self._step_position(
                        attacker_state[safe_next_index].position, next_ball, max_step=12
                    )
                    attackers[safe_next_index] = next_player.model_copy(
                        update={"position": prepared_position}
                    )
            owner_id = None
            if owner_index is not None:
                safe_owner_index = min(owner_index, len(attackers) - 1)
                owner = attackers[safe_owner_index]
                attackers[safe_owner_index] = owner.model_copy(update={"position": ball})
                owner_id = owner.player_id
            attacking_involved = {
                attackers[min(owner, len(attackers) - 1)].player_id
                for owner in (
                    spec["owners"][index - 1] if index > 0 else None,
                    owner_index,
                    spec["owners"][index + 1] if index + 1 < total else None,
                )
                if owner is not None
            }
            closest_defenders = sorted(
                defenders,
                key=lambda player: (
                    (player.position.x - ball.x) ** 2 + (player.position.y - ball.y) ** 2
                ),
            )[:2]
            involved_player_ids = [
                *sorted(attacking_involved),
                *(player.player_id for player in closest_defenders),
            ]
            attacker_state = attackers
            defender_state = defenders
            frames.append(
                SimulationFrame(
                    at_ms=index * 900,
                    phase=phase,
                    action=action,
                    ball=ball,
                    ball_owner_id=owner_id,
                    involved_player_ids=involved_player_ids,
                    players=[*attackers, *defenders],
                )
            )
        return TacticalSimulation(
            simulation_id=f"{attacking.team_id}-{tactic_key}",
            team_id=attacking.team_id,
            title=spec["title"],
            summary=spec["summary"],
            result=f"Gol simulado de {attacking.team_name} después de {len(frames) - 2} acciones de preparación.",
            duration_ms=(total - 1) * 900,
            frames=frames,
        )

    @staticmethod
    def _advance_players(
        players: list[PositionedPlayer], targets: tuple[tuple[float, float], ...], max_step: float
    ) -> list[PositionedPlayer]:
        """Avanza desde el fotograma anterior sin devolver jugadores a la base."""
        positioned = []
        for index, player in enumerate(players):
            target_x, target_y = targets[index % len(targets)]
            delta_x = max(-max_step, min(max_step, target_x - player.position.x))
            delta_y = max(-max_step, min(max_step, target_y - player.position.y))
            positioned.append(
                player.model_copy(
                    update={
                        "position": Position(
                            x=round(player.position.x + delta_x, 2),
                            y=round(player.position.y + delta_y, 2),
                        )
                    }
                )
            )
        return positioned

    @staticmethod
    def _step_position(origin: Position, target: Position, max_step: float) -> Position:
        return Position(
            x=round(origin.x + max(-max_step, min(max_step, target.x - origin.x)), 2),
            y=round(origin.y + max(-max_step, min(max_step, target.y - origin.y)), 2),
        )

    @staticmethod
    def _load_information(metadata: MatchMetadata) -> PrematchInformation:
        path = LOCAL_PREMATCH_DIR / f"{metadata.match_id}.json"
        if path.exists():
            return PrematchInformation.model_validate(json.loads(path.read_text(encoding="utf-8")))
        return PrematchInformation(
            contract_version="1",
            match_id=metadata.match_id,
            source=PrematchSource(
                document_id=f"prematch-{metadata.match_id}-generated",
                storage_kind="local_generated",
                approved=True,
                synthetic=True,
                updated_at="2026-10-23",
            ),
            headline="Todo listo para el próximo partido",
            overview="Información previa generada únicamente con los metadatos sintéticos disponibles.",
            match_facts=[],
            teams=[
                TeamPrematchInformation(
                    team_id=team.team_id,
                    overview=f"{team.name} prepara el partido con la plantilla sintética disponible.",
                    form_summary="No hay resultados previos cargados en el documento local.",
                    recent_results=[],
                    availability=[],
                    key_players=[],
                    tactical_keys=[],
                    probable_lineup=[player.name for player in metadata.players if player.team_id == team.team_id],
                )
                for team in (metadata.home_team, metadata.away_team)
            ],
        )
