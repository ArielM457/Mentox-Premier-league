"""Seguimiento sintético entregado a la cancha del partido en vivo."""

from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.registry import LIVE_MATCH_ID, _default_registry, get_registry
from match_intelligence.main import app


@pytest.fixture
def client() -> TestClient:
    registry = _default_registry()
    app.dependency_overrides[get_registry] = lambda: registry
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_live_match_registers_eleven_players_per_team(client: TestClient) -> None:
    response = client.get(f"/api/v1/matches/{LIVE_MATCH_ID}")

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    counts = defaultdict(int)
    for player in metadata["players"]:
        counts[player["team_id"]] += 1

    assert counts[metadata["home_team"]["team_id"]] == 11
    assert counts[metadata["away_team"]["team_id"]] == 11


def test_live_match_contains_meaningful_situations_and_named_receivers(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/events",
        params={"until_video_ms": 180_000},
    )

    assert response.status_code == 200
    events = response.json()["events"]
    kinds = {event["type"] for event in events}
    assert {
        "pass", "shot", "recovery", "foul", "yellow_card",
        "injury_stoppage", "restart", "pressure", "tackle",
    }.issubset(kinds)
    passes = [event for event in events if event["type"] in {"pass", "restart"}]
    assert all(event["receiver_player_id"] for event in passes)
    assert any(event["situation"] == "long_switch" for event in passes)
    assert any(event["situation"] == "through_ball" for event in passes)
    for event in passes:
        progress = event["end"]["x"] - event["start"]["x"]
        if event["team_id"] == "team-rio":
            progress *= -1
        assert progress >= -8 or event["situation"] in {
            "cutback", "safe_outlet", "support_under_pressure",
        }


def test_injury_stoppage_holds_ball_and_injured_player(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/tracking",
        params={"from_video_ms": 97_000, "to_video_ms": 108_000},
    )

    assert response.status_code == 200
    frames = response.json()["frames"]
    ball_positions = []
    injured_positions = []
    for frame in frames:
        if not 97_000 <= frame["video_time_ms"] <= 108_000:
            continue
        for item in frame["objects"]:
            if item["kind"] == "ball":
                ball_positions.append((item["x_m"], item["y_m"]))
            if item["player_id"] == "rio-10":
                injured_positions.append((item["x_m"], item["y_m"]))

    assert len(set(ball_positions)) == 1
    start = injured_positions[0]
    displacement = max(
        ((x - start[0]) ** 2 + (y - start[1]) ** 2) ** 0.5
        for x, y in injured_positions
    )
    assert displacement < 0.75


def test_tracking_window_contains_all_players_ball_and_synthetic_source(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/tracking",
        params={"from_video_ms": 3_000, "to_video_ms": 8_000},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "synthetic_mock"
    assert len(payload["frames"]) >= 25
    for frame in payload["frames"]:
        people = [item for item in frame["objects"] if item["kind"] in {"player", "goalkeeper"}]
        balls = [item for item in frame["objects"] if item["kind"] == "ball"]
        assert len(people) == 22
        assert len({item["player_id"] for item in people}) == 22
        assert len(balls) <= 1


def test_every_active_player_moves_without_impossible_jumps(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/tracking",
        params={"from_video_ms": 3_000, "to_video_ms": 28_000},
    )
    frames = response.json()["frames"]
    paths: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for frame in frames:
        for item in frame["objects"]:
            if item["player_id"]:
                paths[item["player_id"]].append(
                    (frame["video_time_ms"], item["x_m"], item["y_m"])
                )

    assert len(paths) == 22
    for samples in paths.values():
        travelled = 0.0
        for previous, current in zip(samples, samples[1:], strict=False):
            elapsed = (current[0] - previous[0]) / 1_000
            if elapsed <= 0:
                continue
            step = ((current[1] - previous[1]) ** 2 + (current[2] - previous[2]) ** 2) ** 0.5
            assert step / elapsed <= 8.6
            travelled += step
        assert travelled > 0.5


@pytest.mark.parametrize(
    ("start", "end"),
    [(20_000, 10_000), (0, 30_001)],
)
def test_tracking_rejects_invalid_windows(client: TestClient, start: int, end: int) -> None:
    response = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/tracking",
        params={"from_video_ms": start, "to_video_ms": end},
    )

    assert response.status_code == 400
