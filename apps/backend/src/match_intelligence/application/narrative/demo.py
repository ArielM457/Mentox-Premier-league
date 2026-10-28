"""Run the synthetic narrative fixture without the HTTP module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import InsightCandidate, MatchSnapshot, NarrativeRequest, SummaryRequest, ViewerPreferences
from .gateway import FixtureGateway
from .service import NarrativeService


def main() -> None:
    parser = argparse.ArgumentParser(description="Narrative demo from a synthetic fixture")
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--provider", choices=("fixture", "azure"), default="fixture")
    parser.add_argument("--language", choices=("es", "en"), default="es")
    parser.add_argument(
        "--mode",
        choices=("casual", "analyst", "professional_analyst", "player"),
        default="casual",
    )
    parser.add_argument("--level", choices=("simple", "normal", "advanced"), default="normal")
    parser.add_argument("--favorite-team-id")
    parser.add_argument("--favorite-player-id")
    args = parser.parse_args()
    data = json.loads(args.fixture.read_text(encoding="utf-8"))
    snapshot = MatchSnapshot.model_validate(data["snapshot"])
    candidates = [InsightCandidate.model_validate(item) for item in data["candidates"]]
    preferences = ViewerPreferences(
        language=args.language,
        mode=args.mode,
        level=args.level,
        favorite_team_id=args.favorite_team_id,
        favorite_player_id=args.favorite_player_id,
    )
    if args.provider == "azure":
        from match_intelligence.adapters.agents.crewai_gateway import CrewAIGateway

        gateway = CrewAIGateway()
    else:
        gateway = FixtureGateway()
    service = NarrativeService(gateway)
    results = [
        service.create_live(NarrativeRequest(snapshot=snapshot, candidate=item, preferences=preferences))
        for item in candidates
    ]
    results.append(
        service.summarize(
            SummaryRequest(
                snapshot=snapshot,
                candidates=candidates,
                preferences=preferences,
                match_finished=True,
            )
        )
    )
    print(json.dumps([result.model_dump(mode="json") for result in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
