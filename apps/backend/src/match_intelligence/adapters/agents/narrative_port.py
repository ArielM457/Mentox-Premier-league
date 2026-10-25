"""Adaptador entre los contratos de Persona 4 y el servicio real de Persona 3."""

from __future__ import annotations

from collections.abc import Sequence

from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative
from match_intelligence.application.narrative.contracts import (
    EvidenceFact as AgentFact,
    InsightCandidate as AgentCandidate,
    MatchSnapshot as AgentSnapshot,
    NarrativeDraft as AgentDraft,
    NarrativeRequest,
    QuestionRequest,
    ViewerPreferences as AgentPreferences,
)
from match_intelligence.application.narrative.gateway import FixtureGateway, NarrativeGateway
from match_intelligence.application.narrative.service import NarrativeService
from match_intelligence.application.ports import VerificationResult
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import (
    EditorialStatus,
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    VerificationStatus,
    ViewerPreferences,
)


def _preferences(value: ViewerPreferences) -> AgentPreferences:
    return AgentPreferences(
        language=value.language.value,
        mode=value.mode.value,
        level=value.level.value,
        favorite_team_id=value.favorite_team_id,
        favorite_player_id=value.favorite_player_id,
    )


def _facts(values) -> list[AgentFact]:
    return [
        AgentFact(
            key=item.key,
            value=item.value,
            unit=item.unit,
            team_id=item.team_id,
            player_id=item.player_id,
            window_ms=item.window_ms,
            formula_version=item.formula_version,
            source_event_ids=item.source_event_ids,
        )
        for item in values
        if item.available and item.value is not None and item.source_event_ids
    ]


def _snapshot(value: MatchSnapshot) -> AgentSnapshot:
    return AgentSnapshot(
        match_id=value.match_id,
        period=value.period,
        clock_ms=value.clock_ms,
        score=value.score,
        metrics=_facts(value.metrics),
        recent_event_ids=value.recent_event_ids,
    )


def _candidate(value: InsightCandidate) -> AgentCandidate:
    facts = _facts(value.facts)
    if not facts:
        raise ValueError("El candidato no contiene hechos disponibles con fuentes")
    return AgentCandidate(
        candidate_id=value.candidate_id,
        match_id=value.match_id,
        period=value.period,
        clock_ms=value.clock_ms,
        kind=value.kind,
        priority=value.priority,
        selection_reason=f"Momento {value.kind} seleccionado por la analítica",
        facts=facts,
        source_event_ids=value.source_event_ids,
        evidence_limits=value.evidence_limits,
    )


def _draft(value: AgentDraft) -> NarrativeDraft:
    editorial = EditorialStatus(value.editorial_status) if value.editorial_status else None
    status = (
        VerificationStatus.APPROVED
        if value.verification_status == "approved"
        else VerificationStatus.REJECTED
    )
    return NarrativeDraft(
        draft_id=value.draft_id,
        candidate_id=value.candidate_id,
        match_id=value.match_id,
        language=value.language,
        mode=value.mode,
        level=value.level,
        content_kind=value.content_kind,
        headline=value.headline,
        explanation=value.explanation,
        applied_preferences=[f"{key}:{item}" for key, item in value.applied_preferences.items()],
        source_event_ids=value.source_event_ids,
        verification_status=status,
        editorial_status=editorial,
    )


class Persona3NarrativeAdapter:
    """Implementa ``NarrativePort`` sin cambiar las rutas consumidas por React."""

    def __init__(self, gateway: NarrativeGateway, inject_error_in: str | None = None) -> None:
        self.service = NarrativeService(gateway)
        self.fallback = ProvisionalNarrative(inject_error_in=inject_error_in)
        self._inject_error_in = inject_error_in
        self._model_available = True

    @staticmethod
    def _humanize(draft: NarrativeDraft, metadata: MatchMetadata) -> NarrativeDraft:
        replacements = {
            metadata.home_team.team_id: metadata.home_team.name,
            metadata.away_team.team_id: metadata.away_team.name,
            **{player.player_id: player.name for player in metadata.players},
        }
        headline = draft.headline
        explanation = draft.explanation
        for identifier, name in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            headline = headline.replace(identifier, name)
            explanation = explanation.replace(identifier, name)
        return draft.model_copy(update={"headline": headline, "explanation": explanation})

    @classmethod
    def fixture(cls, inject_error_in: str | None = None) -> "Persona3NarrativeAdapter":
        return cls(FixtureGateway(), inject_error_in)

    @classmethod
    def azure(cls, inject_error_in: str | None = None) -> "Persona3NarrativeAdapter":
        from match_intelligence.adapters.agents.crewai_gateway import CrewAIGateway

        return cls(CrewAIGateway(), inject_error_in)

    def live(
        self,
        metadata: MatchMetadata,
        snapshot: MatchSnapshot,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        if self._inject_error_in == candidate.kind:
            return self.fallback.live(metadata, snapshot, candidate, preferences)
        if not self._model_available:
            return self._fallback_live(metadata, snapshot, candidate, preferences)
        outcome = self.service.create_live(NarrativeRequest(
            snapshot=_snapshot(snapshot),
            candidate=_candidate(candidate),
            preferences=_preferences(preferences),
        ))
        if outcome.draft is not None and outcome.draft.source_event_ids:
            draft = self._humanize(_draft(outcome.draft), metadata)
            presentation = self.fallback.live(metadata, snapshot, candidate, preferences)
            return draft.model_copy(update={
                "headline": presentation.headline,
                "explanation": presentation.explanation,
                "source_event_ids": list(candidate.source_event_ids),
            })
        if outcome.decision.action == "unavailable":
            self._model_available = False
        return self._fallback_live(metadata, snapshot, candidate, preferences)

    def _fallback_live(
        self,
        metadata: MatchMetadata,
        snapshot: MatchSnapshot,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        draft = self.fallback.live(metadata, snapshot, candidate, preferences)
        return draft.model_copy(update={
            "applied_preferences": [*draft.applied_preferences, "provider:fallback-local"],
            "verification_status": VerificationStatus.APPROVED,
        })

    def player_quiet(self, *args, **kwargs) -> NarrativeDraft:
        return self.fallback.player_quiet(*args, **kwargs)

    def answer(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        snapshot: MatchSnapshot,
        question: str,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        if not self._model_available:
            return self.fallback.answer(metadata, events, snapshot, question, preferences)
        agent_snapshot = _snapshot(snapshot)
        facts = agent_snapshot.metrics
        sources = list(dict.fromkeys(source for fact in facts for source in fact.source_event_ids))
        candidates = []
        if facts and sources:
            candidates.append(AgentCandidate(
                candidate_id=f"question-context-{snapshot.match_id}-{snapshot.clock_ms}",
                match_id=snapshot.match_id,
                period=snapshot.period,
                clock_ms=snapshot.clock_ms,
                kind="question",
                priority=0,
                selection_reason="Métricas ocurridas hasta el tiempo consultado",
                facts=facts,
                source_event_ids=sources,
            ))
        normalized_question = question
        folded = question.casefold()
        for player in metadata.players:
            if player.name.casefold() in folded or player.name.split()[-1].casefold() in folded:
                normalized_question += f" {player.player_id}"
        for team in (metadata.home_team, metadata.away_team):
            if team.name.casefold() in folded or team.name.split()[0].casefold() in folded:
                normalized_question += f" {team.team_id}"
        outcome = self.service.answer(QuestionRequest(
            snapshot=agent_snapshot,
            candidates=candidates,
            preferences=_preferences(preferences),
            question=normalized_question,
        ))
        if outcome.draft is not None and outcome.draft.source_event_ids:
            return self._humanize(_draft(outcome.draft), metadata)
        if outcome.decision.action == "unavailable":
            self._model_available = False
        return self.fallback.answer(metadata, events, snapshot, question, preferences)

    def summary(
        self,
        metadata: MatchMetadata,
        snapshot: MatchSnapshot,
        candidates: Sequence[InsightCandidate],
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        # El resumen provisional conserva hoy el enfoque por jugador y la
        # revisión editorial que consume la API de Persona 4.
        return self.fallback.summary(metadata, snapshot, candidates, preferences)

    def verify(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        draft: NarrativeDraft,
    ) -> VerificationResult:
        return self.fallback.verify(metadata, events, draft)
