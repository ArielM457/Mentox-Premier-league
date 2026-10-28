import asyncio

import httpx

from match_intelligence.main import app


def test_simulation_routes_six_cases_and_proposes_human_review(editor_headers: dict) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/matches/synthetic-acceptance-001/simulation",
                params={"language": "es", "mode": "analyst", "level": "advanced"},
            )

            assert response.status_code == 200
            body = response.json()
            assert body["ingress_events"] == 6
            assert body["metrics_queue"] == 1
            assert body["important_queue"] == 4
            assert body["discarded"] == 1
            assert {item["route"] for item in body["steps"]} == {
                "metrics_only", "moment_candidate", "danger_immediate",
                "dead_ball_context", "recap", "rejected",
            }
            assert all(not item["agent_called"] for item in body["steps"] if item["route"] in {"metrics_only", "rejected"})
            assert body["summary_draft_id"]

            clips = (await client.get("/api/v1/matches/synthetic-acceptance-001/highlights")).json()
            if clips:
                reviewed = await client.post(
                    f"/api/v1/matches/synthetic-acceptance-001/highlights/{clips[0]['clip_id']}/review",
                    json={"decision": "approved"},
                    headers=editor_headers,
                )
                assert reviewed.status_code == 200
                assert reviewed.json()["status"] == "approved"

    asyncio.run(scenario())


def test_analyst_simulation_accepts_global_favorite_from_another_match() -> None:
    """Una preferencia global ausente en este partido no debe bloquear al analista."""
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/matches/synthetic-acceptance-001/simulation",
                params={
                    "language": "es",
                    "mode": "analyst",
                    "level": "advanced",
                    "favorite_team_id": "team-rio",
                    "favorite_player_id": "rio-7",
                },
            )

        assert response.status_code == 200
        assert response.json()["ingress_events"] == 6

    asyncio.run(scenario())
