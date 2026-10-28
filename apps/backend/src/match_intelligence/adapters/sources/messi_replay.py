"""MESSI replay/3 + events/6 → contratos propios, sin atribuirlos a visión."""

from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from typing import Any

from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.analytics.tracking import TrackingFrame


@dataclass(frozen=True)
class MessiReplay:
    metadata: MatchMetadata
    events: tuple[MatchEvent, ...]
    tracking: tuple[TrackingFrame, ...]
    evidence: dict[str, dict[str, Any]]
    duration_ms: int
    media_sha256: str
    ignored: dict[str, int]


def rows(data: bytes) -> list[dict[str, Any]]:
    result = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in result):
        raise ValueError("MESSI requiere registros JSON por línea")
    return result


def number(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Número MESSI inválido")
    parsed = float(value)
    if not isfinite(parsed):
        raise ValueError("Número MESSI no finito")
    return parsed


def convert_messi_replay(match_id: str, manifest: dict, artifacts: dict[str, bytes]) -> MessiReplay:
    if manifest.get("schema_version") != "the-prime-moment.messi-match.v1" or manifest.get("source") != "synthetic":
        raise ValueError("Manifiesto MESSI no compatible")
    names = ("match.mp4", "events.jsonl", "tracking.jsonl", "metadata.jsonl")
    entries = manifest.get("artifacts", [])
    expected = {item["name"]: item for item in entries}
    if len(expected) != len(entries):
        raise ValueError("Artefactos duplicados en el manifiesto")
    for name in names:
        data, item = artifacts[name], expected[name]
        if len(data) != item["bytes"] or sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Integridad MESSI incorrecta: {name}")

    records = rows(artifacts["metadata.jsonl"])
    by_type = {item["record_type"]: item for item in records}
    if by_type["replay"]["schema"] != "uos-footballmarl.replay/3":
        raise ValueError("Replay MESSI no compatible")
    if by_type["schemas"]["events"] != "uos-footballmarl.events/6":
        raise ValueError("Eventos MESSI no compatibles")
    if by_type["schemas"]["tracking"] != "uos-footballmarl.tracking/2":
        raise ValueError("Tracking MESSI no compatible")
    if by_type["coordinates"]["origin"] != "pitch_center":
        raise ValueError("Origen de coordenadas MESSI desconocido")
    timebase, roster = by_type["timebase"], by_type["roster"]
    fps = number(timebase["control_fps"])
    duration = round(number(timebase["video_duration_s"]) * 1000)
    if fps <= 0 or duration <= 0 or abs(duration - number(manifest["video_duration_seconds"]) * 1000) > 1:
        raise ValueError("Base de tiempo MESSI inválida")
    if number(timebase.get("render_sample_fps", fps)) != fps:
        raise ValueError("Esta versión requiere control_fps igual a render_sample_fps")
    pitch = by_type["coordinates"]["pitch"]
    length, width = number(pitch["length"]), number(pitch["width"])
    teams = [f"{match_id}-home", f"{match_id}-away"]
    player_teams = dict(zip(roster["starter_player_ids"], roster["team_id"], strict=True))
    if len(player_teams) != 22 or Counter(player_teams.values()) != {0: 11, 1: 11}:
        raise ValueError("Se requiere una plantilla MESSI de 11 contra 11")

    def player_id(raw: object, team: int | None = None) -> str | None:
        if raw is None or raw == -1:
            return None
        if raw not in player_teams or (team is not None and player_teams[raw] != team):
            raise ValueError(f"Jugador MESSI ajeno a la plantilla/equipo: {raw}")
        return f"{match_id}-messi-player-{raw}"

    metadata = MatchMetadata.model_validate({
        "schema_version": "1.0", "match_id": match_id,
        "home_team": {"team_id": teams[0], "name": "MESSI Local"},
        "away_team": {"team_id": teams[1], "name": "MESSI Visitante"},
        "pitch_length_m": length, "pitch_width_m": width,
        # MESSI dibuja los slots 0..10. No inventar un dorsal 1..11.
        "players": [{"player_id": player_id(raw), "team_id": teams[team],
                     "name": f"Jugador {slot % 11}", "shirt_number": None}
                    for slot, (raw, team) in enumerate(player_teams.items())],
    })
    raw_events = rows(artifacts["events.jsonl"])
    raw_ids = [row["event_id"] for row in raw_events]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in raw_ids):
        raise ValueError("Identificador MESSI inválido")
    if len(raw_ids) != len(set(raw_ids)):
        raise ValueError("Eventos MESSI con identificadores duplicados")
    periods = sorted((number(row["video_time_s"]), int(row["index"]) + 1)
                     for row in raw_events if row["type"] == "period_start")
    if not periods or periods[0] != (0, 1):
        raise ValueError("Falta el inicio del partido MESSI")
    starts = [item[0] for item in periods]

    def timing(seconds: float) -> tuple[int, int, int]:
        if seconds < 0 or seconds * 1000 > duration + 1:
            raise ValueError("Tiempo fuera del vídeo MESSI")
        start, period = periods[max(0, bisect_right(starts, seconds) - 1)]
        return period, round((seconds - start) * 1000), round(seconds * 1000)

    def position(value: object) -> dict | None:
        if value is None:
            return None
        x, y = number(value[0]), number(value[1])
        # El simulador permite salir del campo: el contrato de evento no.
        if not (-length / 2 <= x <= length / 2 and -width / 2 <= y <= width / 2):
            return None
        return {"x": (x + length / 2) / length * 100, "y": (y + width / 2) / width * 100}

    touches = {row["touch_id"]: row for row in raw_events if row["type"] == "touch"}
    output, evidence, ignored = [], {}, Counter()
    identity_prefix = f"messi-{sha256(match_id.encode()).hexdigest()[:12]}-{expected['match.mp4']['sha256'][:12]}"
    for row in raw_events:
        raw_type, label = row["type"], row.get("label")
        kind = {"pass_outcome": "pass", "shot_outcome": "shot", "possession": "possession_change", "restart": "restart"}.get(raw_type)
        if raw_type == "touch":
            kind = {"TACKLE": "tackle", "INTERCEPT": "recovery"}.get(label)
        if kind is None:
            ignored[raw_type] += 1
            continue
        team = row.get("team")
        if team not in (0, 1):
            ignored[f"{raw_type}:unknown_team"] += 1
            continue
        launch = number(row["video_time_s"])
        seconds = launch
        touch = touches.get(row.get("source_touch_id"), row)
        outcome = "unknown"
        if raw_type.endswith("_outcome"):
            # Estos registros están estampados al lanzamiento, pero describen
            # el FUTURO. Publicar una sola acción, cuando ya se conoce su final.
            if row.get("outcome_frame") is not None:
                seconds = max(launch, (number(row["outcome_frame"]) - 1) / fps)
            elif row.get("outcome") != "unresolved":
                raise ValueError("Resultado MESSI sin tiempo de finalización")
            outcome = {"completed": "success", "intercepted": "failure", "out": "failure", "out_of_play": "failure",
                       "goal": "goal", "saved": "saved", "blocked": "blocked",
                       "off_target": "off_target"}.get(row.get("outcome"), "unknown")
        elif kind in {"possession_change", "recovery"}:
            outcome = "success"
        period, clock, video = timing(seconds)
        event_id = f"{identity_prefix}-{row['event_id']}"
        actor = row.get("player_id", row.get("player", row.get("taker")))
        receiver = row.get("receiver") if kind == "pass" and outcome == "success" else None
        end_touch = next((item for item in touches.values()
                          if receiver is not None and item.get("player_id", item.get("player")) == receiver
                          and item.get("f") == row.get("outcome_frame")), None)
        event = MatchEvent.model_validate({
            "schema_version": "1.0", "event_id": event_id, "match_id": match_id,
            "period": period, "clock_ms": clock, "video_time_ms": video,
            "type": kind, "team_id": teams[team], "player_id": player_id(actor, team),
            "receiver_player_id": player_id(receiver, team),
            "start": position(touch.get("ball_pos")),
            "end": position(end_touch.get("ball_pos")) if end_touch else None, "outcome": outcome,
            "source": "synthetic", "situation": "messi_simulator",
        })
        output.append(event)
        distance = number(row["distance_m"]) if row.get("distance_m") is not None else None
        speed = number(row["launch_speed"]) if row.get("launch_speed") is not None else None
        if (distance is not None and distance < 0) or (speed is not None and speed < 0):
            raise ValueError("Magnitud MESSI negativa")
        evidence[event_id] = {"simulator_event_id": row["event_id"], "simulator_type": raw_type,
                              "launch_video_ms": round(launch * 1000),
                              "distance_m": distance, "launch_speed_m_s": speed,
                              "raw_outcome": row.get("outcome"), "identity_source": "messi_simulator"}

    frames, directions = [], {}
    previous_video = -1
    for row in rows(artifacts["tracking.jsonl"]):
        period, clock, video = timing(number(row["video_time_s"]))
        if video <= previous_video:
            raise ValueError("Tracking MESSI duplicado o desordenado")
        previous_video = video
        players = row["players"]
        for team in (0, 1):
            indexes = [i for i, value in enumerate(players["team_id"]) if value == team]
            if "attack_dir" in players and indexes:
                signs = {number(players["attack_dir"][i]) for i in indexes}
                if len(signs) != 1 or not signs.issubset({-1, 1}):
                    raise ValueError("Dirección de ataque MESSI ambigua")
                directions.setdefault((period, team), "left_to_right" if next(iter(signs)) == 1 else "right_to_left")
        count = len(players["player_id"])
        if any(len(players[key]) != count for key in ("pos", "team_id", "gk", "on_pitch")):
            raise ValueError("Tracking MESSI con arrays inconsistentes")
        objects = []
        for index, raw in enumerate(players["player_id"]):
            if not players["on_pitch"][index]:
                continue
            team = players["team_id"][index]
            owner = player_id(raw, team)
            objects.append({"track_id": owner, "kind": "goalkeeper" if players["gk"][index] else "player",
                            "player_id": owner, "team_id": teams[team],
                            "x_m": number(players["pos"][index][0]) + length / 2,
                            "y_m": number(players["pos"][index][1]) + width / 2})
        objects.append({"track_id": f"{match_id}-messi-ball", "kind": "ball",
                        "x_m": number(row["ball"]["pos"][0]) + length / 2,
                        "y_m": number(row["ball"]["pos"][1]) + width / 2})
        frames.append(TrackingFrame.model_validate({"match_id": match_id, "period": period,
                      "clock_ms": clock, "video_time_ms": video, "source": "synthetic_simulator", "objects": objects}))
    if not frames:
        raise ValueError("El replay MESSI no contiene seguimiento")
    metadata = MatchMetadata.model_validate({**metadata.model_dump(), "attacking_directions": [
        {"period": period, "team_id": teams[team], "direction": direction}
        for (period, team), direction in sorted(directions.items())]})
    return MessiReplay(metadata, tuple(sorted(output, key=lambda event: (event.video_time_ms, evidence[event.event_id]["simulator_event_id"]))),
                       tuple(frames), evidence, duration, expected["match.mp4"]["sha256"], dict(ignored))
