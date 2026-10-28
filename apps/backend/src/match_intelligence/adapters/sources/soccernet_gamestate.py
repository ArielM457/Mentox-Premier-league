"""Adaptador de filas exportadas por SoccerNet GameState/TrackLab.

El `.pklz` de TrackLab se convierte primero a JSONL dentro del contenedor del
modelo. Este módulo recibe esas filas simples, conserva equipo/dorsal como
observaciones y produce `TrackingFrame v1` solo cuando hay pista y posición de
campo válidas. La identidad solo se completa cuando varias lecturas coherentes
de equipo y dorsal coinciden con una entrada única de la plantilla verificada.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Any

from match_intelligence.application.realtime_observations import VisionObservationEnvelope
from match_intelligence.domain.analytics.tracking import (
    TrackedKind,
    TrackedObject,
    TrackingFrame,
    TrackingSource,
)
from match_intelligence.domain.contracts import MatchMetadata

_KINDS = {
    "player": TrackedKind.PLAYER,
    "goalkeeper": TrackedKind.GOALKEEPER,
    "referee": TrackedKind.REFEREE,
    "ball": TrackedKind.BALL,
}


@dataclass(frozen=True, slots=True)
class GameStateConversion:
    observations: list[VisionObservationEnvelope]
    frames: list[TrackingFrame]
    ignored_rows: int
    rows_without_pitch_position: int


@dataclass(frozen=True, slots=True)
class GameStateIdentityResolution:
    """Asociaciones de plantilla sustentadas por varias lecturas del dorsal."""

    player_by_track: dict[str, str]
    evidence_by_track: dict[str, dict[str, object]]
    ambiguous_tracks: int


def resolve_gamestate_identities(
    rows: Iterable[Mapping[str, object]],
    *,
    metadata: MatchMetadata,
    team_by_side: Mapping[str, str],
    minimum_votes: int = 3,
    minimum_vote_share: float = 0.70,
    minimum_jersey_confidence: float = 0.50,
) -> GameStateIdentityResolution:
    """Resuelve ``track_id`` solo con equipo, dorsal y plantilla verificada.

    La confianza de una detección aislada nunca confirma una identidad. Se exige
    una mayoría de lecturas del mismo dorsal y que ese dorsal sea único en el
    equipo indicado por los metadatos del partido.
    """
    if minimum_votes < 1:
        raise ValueError("minimum_votes debe ser al menos 1")
    if not 0.5 <= minimum_vote_share <= 1:
        raise ValueError("minimum_vote_share debe estar entre 0.5 y 1")
    if not 0 <= minimum_jersey_confidence <= 1:
        raise ValueError("minimum_jersey_confidence debe estar entre 0 y 1")

    roster: dict[tuple[str, int], list[str]] = defaultdict(list)
    for player in metadata.players:
        if player.shirt_number is not None:
            roster[(player.team_id, player.shirt_number)].append(player.player_id)

    votes: dict[str, Counter[tuple[str, int]]] = defaultdict(Counter)
    confidence_totals: dict[tuple[str, str, int], float] = defaultdict(float)
    seen_frames: set[tuple[str, int]] = set()
    for row in rows:
        track_id = gamestate_track_id(row.get("track_id"))
        try:
            frame_index = int(row["frame_index"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        side = str(row.get("team")) if row.get("team") is not None else None
        team_id = team_by_side.get(side) if side else None
        jersey = _optional_int(row.get("jersey_number"))
        confidence = _confidence(row.get("jersey_confidence"))
        if (
            track_id is None
            or team_id is None
            or jersey is None
            or confidence is None
            or confidence < minimum_jersey_confidence
            or frame_index < 0
            or (track_id, frame_index) in seen_frames
        ):
            continue
        seen_frames.add((track_id, frame_index))
        votes[track_id][(team_id, jersey)] += 1
        confidence_totals[(track_id, team_id, jersey)] += confidence

    resolved: dict[str, str] = {}
    evidence: dict[str, dict[str, object]] = {}
    ambiguous = 0
    for track_id, track_votes in votes.items():
        (team_id, jersey), count = track_votes.most_common(1)[0]
        total = sum(track_votes.values())
        share = count / total
        candidates = roster.get((team_id, jersey), [])
        accepted = (
            count >= minimum_votes
            and share >= minimum_vote_share
            and len(candidates) == 1
        )
        evidence[track_id] = {
            "team_id": team_id,
            "jersey_number": jersey,
            "votes": count,
            "total_valid_votes": total,
            "vote_share": round(share, 4),
            "mean_jersey_confidence": round(
                confidence_totals[(track_id, team_id, jersey)] / count, 4
            ),
            "roster_candidates": candidates,
            "status": "confirmed" if accepted else "ambiguous",
        }
        if accepted:
            resolved[track_id] = candidates[0]
        else:
            ambiguous += 1
    # Dos pistas simultáneas no pueden ser el mismo jugador de la plantilla.
    frames_by_track: dict[str, set[int]] = defaultdict(set)
    for track_id, frame_index in seen_frames:
        frames_by_track[track_id].add(frame_index)
    conflicting: set[str] = set()
    tracks_by_player: dict[str, list[str]] = defaultdict(list)
    for track_id, player_id in resolved.items():
        tracks_by_player[player_id].append(track_id)
    for tracks in tracks_by_player.values():
        for index, left in enumerate(tracks):
            for right in tracks[index + 1:]:
                if frames_by_track[left] & frames_by_track[right]:
                    conflicting.update((left, right))
    for track_id in conflicting:
        del resolved[track_id]
        evidence[track_id].update(status="ambiguous", reason="Identidad repetida en pistas simultáneas")
        ambiguous += 1
    return GameStateIdentityResolution(resolved, evidence, ambiguous)


def convert_gamestate_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    match_id: str,
    fps: float,
    period: int,
    pitch_length_m: float,
    pitch_width_m: float,
    team_by_side: Mapping[str, str] | None = None,
    clock_at_first_frame_ms: int = 0,
    video_at_first_frame_ms: int = 0,
    produced_at: datetime | None = None,
    player_by_track: Mapping[str, str] | None = None,
    identity_evidence_by_track: Mapping[str, Mapping[str, object]] | None = None,
) -> GameStateConversion:
    if not isfinite(fps) or fps <= 0:
        raise ValueError("fps debe ser mayor que cero")
    if not all(isfinite(value) and value > 0 for value in (pitch_length_m, pitch_width_m)):
        raise ValueError("las dimensiones del campo deben ser positivas")
    team_by_side = team_by_side or {}
    produced_at = produced_at or datetime.now(UTC)
    player_by_track = player_by_track or {}
    identity_evidence_by_track = identity_evidence_by_track or {}
    observations: list[VisionObservationEnvelope] = []
    grouped: dict[int, list[TrackedObject]] = defaultdict(list)
    ignored = 0
    missing_pitch = 0
    seen_tracks: set[tuple[int, str]] = set()

    for ordinal, row in enumerate(rows):
        try:
            frame_index = int(row["frame_index"])  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError, OverflowError):
            ignored += 1
            continue
        if frame_index < 0:
            ignored += 1
            continue
        offset_ms = int(round(frame_index / fps * 1_000))
        role = str(row.get("role") or "other").lower()
        side = str(row.get("team")) if row.get("team") is not None else None
        track_value = row.get("track_id")
        track_id = gamestate_track_id(track_value)
        player_id = player_by_track.get(track_id) if track_id else None
        confidence = _confidence(row.get("bbox_confidence"))
        position = _pitch_position(row.get("bbox_pitch"), pitch_length_m, pitch_width_m)
        if position is None:
            missing_pitch += 1

        detection_id = str(row.get("detection_id") or ordinal)
        payload: dict[str, Any] = {
            "match_id": match_id,
            "frame_index": frame_index,
            "period": period,
            "clock_ms": clock_at_first_frame_ms + offset_ms,
            "video_time_ms": video_at_first_frame_ms + offset_ms,
            "track_id": track_id,
            "role": role,
            "team_side": side,
            "team_id": team_by_side.get(side) if side else None,
            "jersey_number": _optional_int(row.get("jersey_number")),
            "bbox_ltwh": row.get("bbox_ltwh"),
            "pitch_position_m": (
                {"x": position[0], "y": position[1]} if position is not None else None
            ),
            "bbox_confidence": confidence,
            "role_confidence": _confidence(row.get("role_confidence")),
            "jersey_confidence": _confidence(row.get("jersey_confidence")),
            "player_id": player_id,
            "identity_status": "confirmed" if player_id else "unconfirmed",
            "identity_evidence": identity_evidence_by_track.get(track_id) if track_id else None,
        }
        observations.append(VisionObservationEnvelope(
            observation_id=f"gs-{match_id}-{detection_id}",
            source="soccernet-gamestate",
            kind="game_state_detection",
            timestamp_ms=video_at_first_frame_ms + offset_ms,
            payload=payload,
            produced_at=produced_at,
        ))

        kind = _KINDS.get(role)
        if kind is None or track_id is None or position is None:
            continue
        if (frame_index, track_id) in seen_tracks:
            continue
        seen_tracks.add((frame_index, track_id))
        team_id = team_by_side.get(side) if side and kind in {
            TrackedKind.PLAYER, TrackedKind.GOALKEEPER
        } else None
        grouped[frame_index].append(TrackedObject(
            track_id=track_id,
            kind=kind,
            team_id=team_id,
            player_id=player_id,
            x_m=round(position[0], 3),
            y_m=round(position[1], 3),
            confidence=confidence,
        ))

    frames = []
    for frame_index in sorted(grouped):
        offset_ms = int(round(frame_index / fps * 1_000))
        frames.append(TrackingFrame(
            match_id=match_id,
            period=period,
            clock_ms=clock_at_first_frame_ms + offset_ms,
            video_time_ms=video_at_first_frame_ms + offset_ms,
            source=TrackingSource.VIDEO_MODEL,
            objects=grouped[frame_index],
        ))
    return GameStateConversion(observations, frames, ignored, missing_pitch)


def gamestate_track_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not isfinite(value):
        return None
    text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text if text.startswith("trk-gs-") else f"trk-gs-{text}"


def _confidence(value: object) -> float | None:
    if not isinstance(value, (int, float)) or not isfinite(float(value)):
        return None
    result = float(value)
    return result if 0 <= result <= 1 else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return number if 0 <= number <= 99 else None


def _pitch_position(value: object, length: float, width: float) -> tuple[float, float] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        centered_x = float(value["x_bottom_middle"])  # type: ignore[arg-type]
        centered_y = float(value["y_bottom_middle"])  # type: ignore[arg-type]
    except (KeyError, TypeError, ValueError):
        return None
    if not isfinite(centered_x) or not isfinite(centered_y):
        return None
    x = centered_x + length / 2
    y = centered_y + width / 2
    if not (0 <= x <= length and 0 <= y <= width):
        return None
    return x, y
