"""Entrada de la analítica de seguimiento desde las observaciones de Persona 1.

Persona 1 entrega cada posición como ``VisualTrackObservation`` (tiempo de
vídeo, ``track_id``, equipo, confianza y posición de 0 a 100 en el campo fijo)
y solo asocia una pista con un jugador mediante ``ResolvedVisualIdentity``
confirmada (DV-US-12). El origen se marca con su ``PredictionOrigin``. Este
adaptador no cambia esas reglas: convierte posiciones a metros, ubica cada
observación en ``(period, clock_ms)`` con el reloj de los eventos y arma un
``TrackSet`` para el dominio.

``VisualTrackObservation`` no distingue todavía el balón ni los porteros. Hasta
acordarlo con Persona 1, el balón se reconoce por ``ball_track_ids`` y los
porteros por ``goalkeeper_player_ids``; una pista sin equipo que no es el balón
queda como ``unassigned`` y no entra en las cifras de jugadores.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from match_intelligence.application.vision_evaluation import PredictionOrigin
from match_intelligence.application.visual_identity import (
    IdentityStatus,
    ResolvedVisualIdentity,
    VisualTrackObservation,
)
from match_intelligence.domain.analytics.tracking import Sample, Track, TrackedKind, TrackSet
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata

DEFAULT_BALL_TRACK_IDS = frozenset({"ball"})


@dataclass(frozen=True, slots=True)
class VideoClock:
    """Relación entre el tiempo de vídeo y el reloj de cada período, tomada de los eventos."""

    period_starts: tuple[tuple[int, int], ...]  # (period, video_time_ms con clock 0)

    @classmethod
    def from_events(cls, events: Iterable[MatchEvent]) -> "VideoClock":
        starts: dict[int, int] = {}
        for event in sorted(events, key=lambda e: (e.period, e.clock_ms)):
            if event.video_time_ms is not None and event.period not in starts:
                starts[event.period] = event.video_time_ms - event.clock_ms
        return cls(tuple(sorted(starts.items())))

    def locate(self, video_time_ms: int) -> tuple[int, int] | None:
        located = None
        for period, start in self.period_starts:
            if video_time_ms >= start:
                located = (period, video_time_ms - start)
        return located


@dataclass(frozen=True, slots=True)
class TrackingInput:
    """Lo que Persona 1 entrega para un partido."""

    observations: tuple[VisualTrackObservation, ...]
    identities: tuple[ResolvedVisualIdentity, ...] = ()
    origin: PredictionOrigin = PredictionOrigin.ACTUAL_MODEL
    ball_track_ids: frozenset[str] = DEFAULT_BALL_TRACK_IDS
    goalkeeper_player_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class TrackingConversion:
    tracks: TrackSet
    skipped_observation_ids: tuple[str, ...]
    conflicting_track_ids: tuple[str, ...]


def confirmed_players(identities: Sequence[ResolvedVisualIdentity]) -> tuple[dict[str, str], set[str]]:
    """``track_id → player_id`` solo con identidad confirmada y sin contradicciones."""
    players: dict[str, str] = {}
    conflicts: set[str] = set()
    for identity in identities:
        if identity.identity_status is not IdentityStatus.CONFIRMED or identity.player_id is None:
            continue
        known = players.get(identity.track_id)
        if known is not None and known != identity.player_id:
            conflicts.add(identity.track_id)
        players.setdefault(identity.track_id, identity.player_id)
    for track_id in conflicts:
        players.pop(track_id, None)
    return players, conflicts


def tracks_from_observations(
    metadata: MatchMetadata, events: Sequence[MatchEvent], tracking: TrackingInput
) -> TrackingConversion:
    clock = VideoClock.from_events(events)
    players, conflicts = confirmed_players(tracking.identities)
    tracks: dict[str, Track] = {}
    seen: set[tuple[str, int]] = set()
    skipped: list[str] = []

    for observation in sorted(tracking.observations, key=lambda o: (o.video_time_ms, o.track_id)):
        located = clock.locate(observation.video_time_ms)
        key = (observation.track_id, observation.video_time_ms)
        if (
            observation.match_id != metadata.match_id
            or observation.position is None
            or located is None
            or key in seen
        ):
            skipped.append(observation.observation_id)
            continue
        seen.add(key)
        track = tracks.get(observation.track_id)
        if track is None:
            player_id = players.get(observation.track_id)
            if observation.track_id in tracking.ball_track_ids:
                kind = TrackedKind.BALL
            elif observation.team_id is None:
                kind = TrackedKind.UNASSIGNED
            elif player_id in tracking.goalkeeper_player_ids:
                kind = TrackedKind.GOALKEEPER
            else:
                kind = TrackedKind.PLAYER
            track = Track(
                track_id=observation.track_id, kind=kind,
                team_id=None if kind is TrackedKind.BALL else observation.team_id,
                player_id=player_id if kind is not TrackedKind.BALL else None,
            )
            tracks[observation.track_id] = track
        period, clock_ms = located
        track.samples.append(Sample(
            period=period, clock_ms=clock_ms, video_time_ms=observation.video_time_ms,
            x=observation.position.x * metadata.pitch_length_m / 100,
            y=observation.position.y * metadata.pitch_width_m / 100,
        ))

    return TrackingConversion(
        tracks=TrackSet(metadata.match_id, tracking.origin.value, tracks),
        skipped_observation_ids=tuple(skipped),
        conflicting_track_ids=tuple(sorted(conflicts)),
    )
