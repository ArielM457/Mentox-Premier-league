"""Evidence-first narration, Q&A, final drafts and report resolution."""

from __future__ import annotations

import time

from .contracts import (
    Claim,
    DecisionRecord,
    ErrorReport,
    EvidenceFact,
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    NarrativeOutcome,
    NarrativeRequest,
    QuestionRequest,
    ReportResolution,
    SummaryRequest,
    ViewerPreferences,
)
from .gateway import NarrativeGateway


LABELS = {
    "es": {
        "recoveries": ("recuperación", "recuperaciones"),
        "shots": ("tiro", "tiros"),
        "goals": ("gol", "goles"),
        "goal": ("gol", "goles"),
        "passes": ("pase", "pases"),
        "passes_in_build_up": ("pase en la jugada", "pases en la jugada"),
        "seconds_since_recovery": ("segundo desde la recuperación", "segundos desde la recuperación"),
        "forward_progress": ("metro de progresión", "metros de progresión"),
        "pressure": ("acción de presión", "acciones de presión"),
    },
    "en": {
        "recoveries": ("recovery", "recoveries"),
        "shots": ("shot", "shots"),
        "goals": ("goal", "goals"),
        "goal": ("goal", "goals"),
        "passes": ("pass", "passes"),
        "passes_in_build_up": ("pass in the move", "passes in the move"),
        "seconds_since_recovery": ("second since the recovery", "seconds since the recovery"),
        "forward_progress": ("metre of progression", "metres of progression"),
        "pressure": ("pressure", "pressures"),
    },
}

QUESTION_TERMS = {
    "recoveries": ("recovery", "recoveries", "recuperación", "recuperaciones"),
    "shots": ("shot", "shots", "tiro", "tiros", "disparo", "disparos"),
    "goals": ("goal", "goals", "gol", "goles"),
    "passes": ("pass", "passes", "pase", "pases"),
    "pressure": ("pressure", "presión", "presiones"),
}


def _question_facts(question: str, facts: list[EvidenceFact]) -> list[EvidenceFact]:
    text = question.casefold()
    requested = {
        key for key, terms in QUESTION_TERMS.items() if any(term in text for term in terms)
    }
    mentioned_players = {fact.player_id for fact in facts if fact.player_id and fact.player_id.casefold() in text}
    mentioned_teams = {fact.team_id for fact in facts if fact.team_id and fact.team_id.casefold() in text}
    if not requested and not mentioned_players:
        return []
    return [
        fact for fact in facts
        if (not requested or fact.key in requested)
        and (not mentioned_players or fact.player_id in mentioned_players)
        and (not mentioned_teams or fact.team_id in mentioned_teams)
    ]


def _claim(fact: EvidenceFact) -> Claim:
    return Claim.model_validate(fact.model_dump())


def _grounded(claim: Claim, facts: list[EvidenceFact]) -> bool:
    return any(claim.model_dump() == _claim(fact).model_dump() for fact in facts)


def _fact_text(fact: EvidenceFact, language: str) -> str:
    labels = LABELS[language].get(fact.key)
    label = labels[0 if fact.value == 1 else 1] if labels else fact.key.replace("_", " ")
    subject = fact.player_id or fact.team_id or ("El partido" if language == "es" else "The match")
    unit = "" if fact.unit in (None, "count") else f" {fact.unit}"
    value = int(fact.value) if isinstance(fact.value, float) and fact.value.is_integer() else fact.value
    if language == "es":
        return f"{subject}: {value}{unit} {label}".strip()
    return f"{subject}: {value}{unit} {label}".strip()


def _render(
    candidate: InsightCandidate,
    facts: list[EvidenceFact],
    preferences: ViewerPreferences,
) -> tuple[str, str]:
    language = preferences.language
    clock = f"{candidate.clock_ms // 60000}'"
    if not facts:
        if preferences.mode == "player":
            player = preferences.favorite_player_id
            return (
                (f"Sin novedades de {player}" if language == "es" else f"No update on {player}"),
                (
                    "Los eventos disponibles no registran una nueva acción suya."
                    if language == "es"
                    else "Available events do not record a new action by this player."
                ),
            )
        return (
            "Datos insuficientes" if language == "es" else "Insufficient evidence",
            "No se puede determinar con los datos disponibles."
            if language == "es"
            else "The available data cannot determine this.",
        )
    focus = facts[0].player_id or facts[0].team_id
    if candidate.kind == "question":
        headline = "Respuesta" if language == "es" else "Answer"
    elif candidate.kind == "goal" and any(fact.key in {"goal", "goals"} and fact.value for fact in facts):
        headline = f"Gol de {focus} - {clock}" if language == "es" else f"Goal for {focus} - {clock}"
    elif candidate.kind == "shot" and any(fact.key == "shots" for fact in facts):
        headline = f"Tiro de {focus} - {clock}" if language == "es" else f"Shot by {focus} - {clock}"
    else:
        headline = (
            f"Momento de {focus} - {clock}" if language == "es" else f"Moment for {focus} - {clock}"
        )
    explanation = ". ".join(_fact_text(fact, language) for fact in facts) + "."
    if preferences.level == "advanced":
        windows = [fact.window_ms for fact in facts if fact.window_ms is not None]
        if windows:
            seconds = min(windows) // 1000
            explanation += (
                f" Ventana de {seconds} segundos."
                if language == "es"
                else f" Window of {seconds} seconds."
            )
    if candidate.evidence_limits and preferences.level != "simple":
        explanation += (
            " No hay datos suficientes para afirmar una causa táctica."
            if language == "es"
            else " There is not enough evidence to assert a tactical cause."
        )
    return headline, explanation


class NarrativeService:
    def __init__(self, gateway: NarrativeGateway) -> None:
        self.gateway = gateway

    def create_live(self, request: NarrativeRequest) -> NarrativeOutcome:
        start = time.perf_counter()
        snapshot, candidate, preferences = request.snapshot, request.candidate, request.preferences
        try:
            plan = self.gateway.plan(snapshot, candidate, preferences)
        except Exception as exc:
            return self._failure(candidate, "unavailable", f"Agent unavailable: {type(exc).__name__}", start)
        model_elapsed_ms = int((time.perf_counter() - start) * 1000)
        if not plan.reviewer_approved:
            return self._failure(
                candidate, "rejected", plan.reviewer_reason or "Agent verifier rejected proposal", start
            )
        if any(index < 0 or index >= len(candidate.facts) for index in plan.fact_indexes):
            return self._failure(candidate, "rejected", "Agent selected unknown fact", start)
        if plan.angle not in {"observed", "decisive", "player"}:
            return self._failure(candidate, "rejected", "Unsupported interpretation", start)
        indexes = list(dict.fromkeys(plan.fact_indexes))
        preferred_indexes = [
            index
            for index, fact in enumerate(candidate.facts)
            if (
                preferences.favorite_player_id
                and fact.player_id == preferences.favorite_player_id
            )
            or (
                preferences.favorite_team_id
                and fact.team_id == preferences.favorite_team_id
            )
        ]
        if indexes and preferred_indexes and preferred_indexes[0] not in indexes:
            indexes.insert(0, preferred_indexes[0])
        if preferences.mode == "player":
            indexes = [
                index
                for index in indexes
                if candidate.facts[index].player_id == preferences.favorite_player_id
            ]
        if not indexes and preferences.mode != "player":
            return self._failure(candidate, "discarded", "No supported fact selected", start)
        focus = preferences.favorite_player_id or preferences.favorite_team_id
        if focus:
            indexes.sort(
                key=lambda index: (
                    candidate.facts[index].player_id != focus
                    and candidate.facts[index].team_id != focus
                )
            )
        if candidate.kind == "goal" and preferences.mode != "player":
            goal_indexes = [
                index for index, fact in enumerate(candidate.facts)
                if fact.key == "goals" and isinstance(fact.value, (int, float)) and fact.value > 0
            ]
            if goal_indexes:
                goal_index = goal_indexes[0]
                indexes = [goal_index, *[index for index in indexes if index != goal_index]]
        limit = 1 if preferences.mode == "casual" or preferences.level == "simple" else 2
        facts = [candidate.facts[index] for index in indexes[:limit]]
        draft = self._draft(candidate, preferences, facts)
        reason = "; ".join(
            part for part in (candidate.selection_reason, plan.reason) if part
        ) or "Selected supported facts"
        return NarrativeOutcome(
            draft=draft,
            decision=DecisionRecord(
                candidate_id=candidate.candidate_id,
                match_id=candidate.match_id,
                action="selected",
                reason=reason,
                source_event_ids=draft.source_event_ids,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
                stage_elapsed_ms={
                    **plan.stage_elapsed_ms,
                    "model_total": model_elapsed_ms,
                    "verification_render": int((time.perf_counter() - start) * 1000) - model_elapsed_ms,
                },
            ),
        )

    def answer(self, request: QuestionRequest) -> NarrativeOutcome:
        start = time.perf_counter()
        facts = [fact for item in request.candidates for fact in item.facts]
        facts.extend(request.snapshot.metrics)
        facts = _question_facts(request.question, facts)
        sources = list(dict.fromkeys(source for fact in facts for source in fact.source_event_ids))
        if not facts:
            return self._insufficient_answer(request, start)
        candidate = InsightCandidate(
            candidate_id=f"question-{request.snapshot.match_id}-{request.snapshot.clock_ms}",
            match_id=request.snapshot.match_id,
            period=request.snapshot.period,
            clock_ms=request.snapshot.clock_ms,
            kind="question",
            priority=0,
            facts=facts,
            source_event_ids=sources,
        )
        try:
            plan = self.gateway.plan(
                request.snapshot, candidate, request.preferences, question=request.question
            )
        except Exception as exc:
            return self._failure(candidate, "unavailable", f"Agent unavailable: {type(exc).__name__}", start)
        model_elapsed_ms = int((time.perf_counter() - start) * 1000)
        if not plan.reviewer_approved or any(
            index < 0 or index >= len(facts) for index in plan.fact_indexes
        ):
            return self._failure(candidate, "rejected", "Question plan failed verification", start)
        if not plan.fact_indexes:
            return self._insufficient_answer(request, start)
        selected = [facts[index] for index in list(dict.fromkeys(plan.fact_indexes))[:2]]
        draft = self._draft(candidate, request.preferences, selected, content_kind="answer")
        return NarrativeOutcome(
            draft=draft,
            decision=DecisionRecord(
                candidate_id=candidate.candidate_id,
                match_id=candidate.match_id,
                action="selected",
                reason=plan.reason or "Question answered from evidence",
                source_event_ids=draft.source_event_ids,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
                stage_elapsed_ms={
                    **plan.stage_elapsed_ms,
                    "model_total": model_elapsed_ms,
                    "verification_render": int((time.perf_counter() - start) * 1000) - model_elapsed_ms,
                },
            ),
        )

    def summarize(self, request: SummaryRequest) -> NarrativeOutcome:
        start = time.perf_counter()
        if any(item.match_id != request.snapshot.match_id for item in request.candidates):
            raise ValueError("All candidates must belong to summary match")
        goal_metrics = [metric for metric in request.snapshot.metrics if metric.key == "goals"]
        if any(
            metric.team_id not in request.snapshot.score
            or metric.value != request.snapshot.score[metric.team_id]
            for metric in goal_metrics
        ):
            return self._failure(
                request.candidates[0], "rejected", "Goal metric conflicts with final score", start
            )
        def summary_rank(item: InsightCandidate) -> tuple[int, int, int]:
            favorite = any(
                (request.preferences.favorite_player_id and fact.player_id == request.preferences.favorite_player_id)
                or (request.preferences.favorite_team_id and fact.team_id == request.preferences.favorite_team_id)
                for fact in item.facts
            )
            decisive = item.kind == "goal"
            return (-int(decisive), -int(favorite), -item.priority)

        selected = sorted(request.candidates, key=summary_rank)[:3]
        accepted = [
            result.draft
            for item in selected
            if (result := self.create_live(
                NarrativeRequest(snapshot=request.snapshot, candidate=item, preferences=request.preferences)
            )).draft is not None
        ]
        if not accepted:
            candidate = selected[0]
            return self._failure(candidate, "unavailable", "No verified moments for summary", start)
        language = request.preferences.language
        score = " - ".join(f"{team} {goals}" for team, goals in request.snapshot.score.items())
        headline = (
            f"Resumen final - {score}" if language == "es" else f"Final summary - {score}"
        )
        explanation = " ".join(
            f"{draft.headline}: {draft.explanation}" for draft in accepted
        )
        sources = list(
            dict.fromkeys(source for draft in accepted for source in draft.source_event_ids)
        )
        draft = NarrativeDraft(
            draft_id=f"summary-{request.snapshot.match_id}-{language}-{request.preferences.mode}",
            match_id=request.snapshot.match_id,
            period=request.snapshot.period,
            clock_ms=request.snapshot.clock_ms,
            language=language,
            mode=request.preferences.mode,
            level=request.preferences.level,
            content_kind="final",
            headline=headline,
            explanation=explanation,
            claims=[claim for item in accepted for claim in item.claims],
            source_event_ids=sources,
            applied_preferences=self._applied(request.preferences, [
                fact for item in selected for fact in item.facts
            ]),
            verification_status="approved",
            editorial_status="pending",
        )
        return NarrativeOutcome(
            draft=draft,
            decision=DecisionRecord(
                match_id=draft.match_id,
                action="selected",
                reason="Verified moments assembled; editorial review pending",
                source_event_ids=sources,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            ),
        )

    def resolve_report(self, report: ErrorReport) -> ReportResolution:
        draft, candidate = report.draft, report.candidate
        if (
            candidate is None
            or candidate.match_id != draft.match_id
            or report.snapshot.match_id != draft.match_id
            or (draft.candidate_id is not None and candidate.candidate_id != draft.candidate_id)
        ):
            return ReportResolution(
                report_id=report.report_id,
                status="insufficient_evidence",
                reason="Original candidate evidence is unavailable",
                original_draft_id=draft.draft_id,
            )
        invalid = [claim for claim in draft.claims if not _grounded(claim, candidate.facts)]
        source_union = {source for claim in draft.claims for source in claim.source_event_ids}
        source_matches = set(draft.source_event_ids) == source_union
        text_matches = False
        if not invalid:
            preferences = ViewerPreferences(
                language=draft.language,
                mode=draft.mode,
                level=draft.level,
                favorite_team_id=draft.applied_preferences.get("favorite_team_id"),
                favorite_player_id=draft.applied_preferences.get("favorite_player_id"),
            )
            expected = _render(candidate, [
                fact for claim in draft.claims for fact in candidate.facts
                if _claim(fact).model_dump() == claim.model_dump()
            ], preferences)
            text_matches = (draft.headline, draft.explanation) == expected
        if not invalid and source_matches and text_matches:
            return ReportResolution(
                report_id=report.report_id,
                status="no_error",
                reason="All reported claims match the candidate evidence",
                original_draft_id=draft.draft_id,
                source_event_ids=draft.source_event_ids,
            )
        preferences = ViewerPreferences(
            language=draft.language,
            mode=draft.mode,
            level=draft.level,
            favorite_team_id=draft.applied_preferences.get("favorite_team_id"),
            favorite_player_id=draft.applied_preferences.get("favorite_player_id"),
        )
        correction_facts = candidate.facts[:1]
        if candidate.kind == "goal":
            correction_facts = [
                fact for fact in candidate.facts if fact.key == "goals"
            ][:1] or correction_facts
        correction = self._draft(
            candidate, preferences, correction_facts, content_kind=draft.content_kind
        )
        correction = correction.model_copy(
            update={
                "draft_id": f"{draft.draft_id}-correction-{report.report_id}",
                "original_draft_id": draft.draft_id,
                "editorial_status": "pending",
            }
        )
        return ReportResolution(
            report_id=report.report_id,
            status="confirmed_error",
            reason="Original claims or source references differ from evidence",
            original_draft_id=draft.draft_id,
            correction=correction,
            source_event_ids=correction.source_event_ids,
        )

    def _draft(
        self,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
        facts: list[EvidenceFact],
        *,
        content_kind: str = "live",
    ) -> NarrativeDraft:
        headline, explanation = _render(candidate, facts, preferences)
        sources = list(dict.fromkeys(source for fact in facts for source in fact.source_event_ids))
        return NarrativeDraft(
            draft_id=(
                f"draft-{candidate.candidate_id}-{preferences.language}-{preferences.mode}-"
                f"{preferences.level}-{content_kind}"
            ),
            candidate_id=candidate.candidate_id,
            match_id=candidate.match_id,
            period=candidate.period,
            clock_ms=candidate.clock_ms,
            language=preferences.language,
            mode=preferences.mode,
            level=preferences.level,
            content_kind=content_kind,
            headline=headline,
            explanation=explanation,
            claims=[_claim(fact) for fact in facts],
            source_event_ids=sources,
            applied_preferences=self._applied(preferences, facts),
            verification_status="approved",
        )

    @staticmethod
    def _applied(preferences: ViewerPreferences, facts: list[EvidenceFact]) -> dict[str, str]:
        applied: dict[str, str] = {}
        if preferences.favorite_team_id and any(
            fact.team_id == preferences.favorite_team_id for fact in facts
        ):
            applied["favorite_team_id"] = preferences.favorite_team_id
        if preferences.favorite_player_id and any(
            fact.player_id == preferences.favorite_player_id for fact in facts
        ):
            applied["favorite_player_id"] = preferences.favorite_player_id
        return applied

    @staticmethod
    def _failure(
        candidate: InsightCandidate, action: str, reason: str, start: float
    ) -> NarrativeOutcome:
        return NarrativeOutcome(
            draft=None,
            decision=DecisionRecord(
                candidate_id=candidate.candidate_id,
                match_id=candidate.match_id,
                action=action,
                reason=reason,
                source_event_ids=candidate.source_event_ids,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            ),
        )

    def _insufficient_answer(self, request: QuestionRequest, start: float) -> NarrativeOutcome:
        preferences = request.preferences
        draft = NarrativeDraft(
            draft_id=f"answer-{request.snapshot.match_id}-{request.snapshot.clock_ms}-{preferences.language}",
            match_id=request.snapshot.match_id,
            period=request.snapshot.period,
            clock_ms=request.snapshot.clock_ms,
            language=preferences.language,
            mode=preferences.mode,
            level=preferences.level,
            content_kind="answer",
            headline="Datos insuficientes" if preferences.language == "es" else "Insufficient evidence",
            explanation=(
                "No se puede determinar con los datos disponibles."
                if preferences.language == "es"
                else "The available data cannot determine this."
            ),
            verification_status="approved",
        )
        return NarrativeOutcome(
            draft=draft,
            decision=DecisionRecord(
                match_id=request.snapshot.match_id,
                action="discarded",
                reason="Question has no supporting fact",
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            ),
        )
