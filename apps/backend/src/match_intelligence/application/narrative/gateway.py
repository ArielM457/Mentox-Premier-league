"""The model can select and interpret evidence, never calculate match facts."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from .contracts import InsightCandidate, MatchSnapshot, ViewerPreferences


class NarrativePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_indexes: list[int] = Field(default_factory=list)
    angle: str = "observed"
    reason: str = ""
    evidence_limit: str | None = None
    reviewer_approved: bool = True
    reviewer_reason: str = ""
    stage_elapsed_ms: dict[str, int] = Field(default_factory=dict)


class NarrativeGateway(Protocol):
    def plan(
        self,
        snapshot: MatchSnapshot,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
        *,
        question: str | None = None,
    ) -> NarrativePlan: ...


class FixtureGateway:
    """Repeatable local model substitute for contracts and offline demos."""

    def plan(
        self,
        snapshot: MatchSnapshot,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
        *,
        question: str | None = None,
    ) -> NarrativePlan:
        if question:
            terms = question.casefold()
            matches = [
                index
                for index, fact in enumerate(candidate.facts)
                if fact.key.casefold().replace("_", " ") in terms
                or (fact.team_id and fact.team_id.casefold() in terms)
                or (fact.player_id and fact.player_id.casefold() in terms)
            ]
            return NarrativePlan(
                fact_indexes=matches[:2],
                angle="observed",
                reason="Matched question to available evidence" if matches else "No matching evidence",
            )
        indexes = list(range(len(candidate.facts)))
        if preferences.favorite_player_id:
            indexes.sort(
                key=lambda index: candidate.facts[index].player_id != preferences.favorite_player_id
            )
        elif preferences.favorite_team_id:
            indexes.sort(
                key=lambda index: candidate.facts[index].team_id != preferences.favorite_team_id
            )
        if preferences.mode == "professional_analyst":
            limit = 3
        else:
            limit = 1 if preferences.mode == "casual" or preferences.level == "simple" else 2
        return NarrativePlan(
            fact_indexes=indexes[:limit],
            angle="decisive" if candidate.kind in {"goal", "shot"} else "observed",
            reason="Selected documented facts in preference order",
            evidence_limit=candidate.evidence_limits[0] if candidate.evidence_limits else None,
        )
