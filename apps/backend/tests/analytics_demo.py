"""Datos del tablero de demostración de Persona 2.

Todo sale del motor real: estado, estadísticas, indicadores, momentos y
decisiones de atención se calculan con ``MatchAnalytics`` sobre el escenario
sintético. Lo único simulado son las observaciones de seguimiento
(``tracking_mock``), con el mismo formato que entregará Persona 1 y marcadas
como ``simulated_fixture``.
"""

from collections.abc import Sequence
from typing import Any

from analytics_scenarios import generate_analytics_scenario
from tracking_mock import generate_mock_tracking
from match_intelligence.application.analytics.pipeline import MatchAnalytics, MatchAnalyzer, build_snapshot
from match_intelligence.application.analytics.tracking_input import tracks_from_observations
from match_intelligence.domain.analytics.attention import BASE_PRIORITY
from match_intelligence.domain.analytics.catalog import METRIC_CATALOG
from match_intelligence.domain.analytics.models import ATTENTION_VERSION, ENGINE_VERSION, MetricValue
from match_intelligence.domain.analytics.tracking import (
    BALL_WINDOW_MS,
    PLAYER_MAX_SPEED_MS,
    SPEED_WINDOW_MS,
    TrackedKind,
    TrackSet,
    cumulative_distance,
    tracking_alerts,
    tracking_metrics,
    window_speeds,
)

PROFILES: tuple[tuple[str, str, dict[str, str] | None], ...] = (
    ("neutral", "Neutro (flujo publicado)", None),
    ("casual", "Aficionado casual", {"mode": "casual"}),
    ("analyst", "Analista", {"mode": "analyst"}),
    ("rio_fan", "Afición de Río", {"mode": "casual", "favorite_team_id": "team-rio"}),
    ("player_sol", "Modo jugador: L. Sol", {"mode": "player", "favorite_player_id": "aurora-8"}),
)
STAT_KEYS = (
    "goals", "shots", "shots_on_target", "passes_completed", "passes_attempted", "pass_accuracy",
    "possession_share", "recoveries", "pressures", "progressive_passes", "tackles_won",
)


def _value(metrics: Sequence[MetricValue], key: str, team_id: str | None = None) -> float | None:
    for item in metrics:
        if item.key == key and item.team_id == team_id and item.player_id is None:
            return item.value
    return None


def _fact(item: MetricValue) -> list[Any]:
    window = None
    if item.window_ms is not None and item.window_end_clock_ms is not None:
        window = [item.period, item.window_start_clock_ms, item.window_end_clock_ms]
    return [
        item.key, item.team_id, item.player_id, item.value, item.unit, item.origin.value,
        item.formula_version, window, item.source_event_ids,
        [[c.key, c.value, c.unit, c.weight, c.contribution] for c in item.components],
    ]


def _tracking(track_set: TrackSet, team_ids: Sequence[str], events) -> dict[str, Any]:
    tracks = track_set.tracks
    order = sorted(tracks)
    index = {track_id: i for i, track_id in enumerate(order)}
    meta = [
        [track_id, tracks[track_id].kind.value,
         team_ids.index(tracks[track_id].team_id) if tracks[track_id].team_id in team_ids else None,
         tracks[track_id].player_id]
        for track_id in order
    ]
    seconds = [i for i in track_set.instants() if i.clock_ms % 1000 == 0]
    compact_frames = [
        [i.period, i.clock_ms, [[index[track.track_id], round(x, 1), round(y, 1)] for track, x, y in i.positions]]
        for i in seconds
    ]

    series: dict[str, list[list[float]]] = {}
    for track_id, track in tracks.items():
        if track.kind not in {TrackedKind.PLAYER, TrackedKind.GOALKEEPER}:
            continue
        totals = {(p, c): d for p, c, d in cumulative_distance(track)}
        speeds = window_speeds(track.samples, window_ms=SPEED_WINDOW_MS, max_speed=PLAYER_MAX_SPEED_MS)
        speed_at = {(end.period, end.clock_ms): speed for _, end, speed in speeds}
        last_distance = 0.0
        rows = []
        for f in seconds:
            last_distance = totals.get((f.period, f.clock_ms), last_distance)
            rows.append([round(last_distance), round(speed_at.get((f.period, f.clock_ms), 0.0) * 3.6, 1)])
        series[track.player_id or track_id] = rows

    ball = next((t for t in tracks.values() if t.kind is TrackedKind.BALL), None)
    ball_series = []
    if ball is not None:
        speeds = window_speeds(ball.samples, window_ms=BALL_WINDOW_MS, max_speed=40.0)
        speed_at = {(end.period, end.clock_ms): speed for _, end, speed in speeds}
        ball_series = [round(speed_at.get((f.period, f.clock_ms), 0.0) * 3.6) for f in seconds]

    final = tracking_metrics(track_set, team_ids, events)
    return {
        "source": track_set.origin,
        "hz_original": 5,
        "tracks": meta,
        "frames": compact_frames,
        "series": series,
        "ball_speed": ball_series,
        "final": [_fact(m) for m in final],
        "alerts": [
            [a.alert_id, a.kind, a.period, a.clock_ms, a.player_id, a.team_id, a.facts[0].value, a.facts[0].unit]
            for a in tracking_alerts(track_set)
        ],
    }


def build_demo_data() -> dict[str, Any]:
    match = generate_analytics_scenario()
    metadata, events = match.metadata, list(match.events)
    team_ids = (metadata.home_team.team_id, metadata.away_team.team_id)
    track_set = tracks_from_observations(metadata, events, generate_mock_tracking(metadata, events)).tracks
    analytics = MatchAnalytics()

    timeline = []
    for count in range(1, len(events) + 1):
        snapshot = build_snapshot(metadata, events[:count])
        stats = [[_value(snapshot.metrics, key, team) for key in STAT_KEYS] for team in team_ids]
        timeline.append([
            snapshot.score[team_ids[0]], snapshot.score[team_ids[1]],
            team_ids.index(snapshot.possession_team_id) if snapshot.possession_team_id else None,
            _value(snapshot.metrics, "control_index", team_ids[0]),
            _value(snapshot.metrics, "momentum_index", team_ids[0]),
            _value(snapshot.metrics, "chaos_index"),
            stats,
        ])

    analyzer = MatchAnalyzer(metadata)
    analyzer.extend(events)
    moments = {
        m.candidate_id: {
            "kind": m.kind, "period": m.period, "clock": m.clock_ms, "anchor": m.anchor_event_id,
            "team": team_ids.index(m.team_id) if m.team_id in team_ids else None,
            "players": list(m.player_ids), "facts": [_fact(f) for f in m.facts],
            "sources": list(m.source_event_ids), "limits": list(m.evidence_limits),
            "signals": m.signal_kinds,
        }
        for m in analyzer.moments()
    }
    profiles = []
    for key, label, preferences in PROFILES:
        report = analytics.attention_report(metadata, events, preferences)
        profiles.append({
            "key": key, "label": label, "profile": report.profile,
            "decisions": [
                [d.candidate_id, "e" if d.outcome.value == "emitted" else "d", d.priority, d.threshold,
                 [[r.code, r.points, r.detail] for r in d.reasons]]
                for d in report.decisions
            ],
        })

    period_ends = {}
    for track in track_set.tracks.values():
        for sample in track.samples:
            period_ends[sample.period] = max(period_ends.get(sample.period, 0), sample.clock_ms)
    used_keys = {fact[0] for moment in moments.values() for fact in moment["facts"]} | set(STAT_KEYS) | {
        "control_index", "momentum_index", "chaos_index", "distance_covered_m", "top_speed_kmh",
        "sprints", "high_intensity_distance_m", "ball_speed_kmh", "shot_speed_kmh", "team_width_m",
        "team_depth_m", "team_compactness_m", "pressure_proximity_share", "nearest_defender_m",
    }
    return {
        "versions": {"engine": ENGINE_VERSION, "attention": ATTENTION_VERSION},
        "match": {
            "id": metadata.match_id,
            "teams": [
                {"id": metadata.home_team.team_id, "name": metadata.home_team.name, "short": "AUR"},
                {"id": metadata.away_team.team_id, "name": metadata.away_team.name, "short": "RÍO"},
            ],
            "length": metadata.pitch_length_m,
            "width": metadata.pitch_width_m,
            "players": {p.player_id: [p.name, p.shirt_number, team_ids.index(p.team_id)] for p in metadata.players},
            "directions": {f"{d.period}:{team_ids.index(d.team_id)}": d.direction.value for d in metadata.attacking_directions},
            "periods": [[period, end] for period, end in sorted(period_ends.items())],
        },
        "events": [
            [e.event_id, e.period, e.clock_ms, e.type.value, team_ids.index(e.team_id), e.player_id,
             e.outcome.value,
             e.start.x if e.start else None, e.start.y if e.start else None,
             e.end.x if e.end else None, e.end.y if e.end else None]
            for e in events
        ],
        "stat_keys": list(STAT_KEYS),
        "timeline": timeline,
        "moments": moments,
        "base_priority": BASE_PRIORITY,
        "profiles": profiles,
        "tracking": _tracking(track_set, team_ids, events),
        "catalog": {
            key: [METRIC_CATALOG[key].unit, METRIC_CATALOG[key].origin.value, METRIC_CATALOG[key].formula]
            for key in sorted(used_keys) if key in METRIC_CATALOG
        },
    }
