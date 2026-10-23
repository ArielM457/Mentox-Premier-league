"""CrewAI interpretation backed by an explicitly configured Azure deployment."""

from __future__ import annotations

import os
import time
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.narrative.contracts import (
    InsightCandidate,
    MatchSnapshot,
    ViewerPreferences,
)
from match_intelligence.application.narrative.gateway import NarrativePlan


class ObservedFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_indexes: list[int] = Field(default_factory=list)
    reason: str


class AnalysisProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    angle: str
    evidence_limit: str | None = None
    reason: str


class SelectionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_indexes: list[int] = Field(default_factory=list)
    angle: str
    reason: str


class ReviewProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool
    reason: str


class CrewAIGateway:
    def __init__(self, *, timeout_seconds: int = 20) -> None:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        router_deployment = os.getenv("AZURE_OPENAI_ROUTER_DEPLOYMENT", deployment)
        narrative_deployment = os.getenv("AZURE_OPENAI_NARRATIVE_DEPLOYMENT", deployment)
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        if not all((endpoint, deployment, router_deployment, narrative_deployment, api_key)):
            raise ValueError(
                "Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT and AZURE_OPENAI_API_KEY"
            )
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
            raise ValueError("AZURE_OPENAI_ENDPOINT must be an HTTPS resource URL without a deployment path")
        try:
            from crewai import LLM
        except ImportError as exc:
            raise RuntimeError("Install the backend agents extra to use CrewAI") from exc

        def llm_for(name: str):
            return LLM(
                model=f"azure/{name}",
                endpoint=f"{endpoint.rstrip('/')}/openai/deployments/{name}",
                api_key=api_key,
                api_version=api_version,
                temperature=0,
                max_tokens=512,
                timeout=timeout_seconds,
                max_retries=0,
            )

        self._fast_llm = llm_for(router_deployment)
        self._quality_llm = llm_for(narrative_deployment)

    def plan(
        self,
        snapshot: MatchSnapshot,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
        *,
        question: str | None = None,
    ) -> NarrativePlan:
        from crewai import Agent, Crew, Process, Task

        stage_elapsed_ms: dict[str, int] = {}
        last_stage_time = [time.perf_counter()]

        def record_stage(name: str):
            def callback(_output: object) -> None:
                now = time.perf_counter()
                stage_elapsed_ms[name] = int((now - last_stage_time[0]) * 1000)
                last_stage_time[0] = now

            return callback

        evidence = candidate.model_dump_json()
        context = (
            f"Snapshot: {snapshot.model_dump_json()}\n"
            f"Candidate: {evidence}\nPreferences: {preferences.model_dump_json()}\n"
            f"Question: {question or 'live explanation'}"
        )
        observer = Agent(
            role="Match evidence observer",
            goal="Identify exact indexed facts that answer the request",
            backstory="You cite provided events and do not infer new statistics.",
            llm=self._fast_llm,
            allow_delegation=False,
            verbose=False,
        )
        analyst = Agent(
            role="Evidence analyst",
            goal="Choose a cautious interpretation and state any evidence limit",
            backstory="You distinguish observed facts from unproven tactics and causes.",
            llm=self._quality_llm,
            allow_delegation=False,
            verbose=False,
        )
        narrator = Agent(
            role="Narrative selector",
            goal="Choose relevant fact indexes and an angle for this viewer",
            backstory="You adapt focus but never change facts or numbers.",
            llm=self._quality_llm,
            allow_delegation=False,
            verbose=False,
        )
        verifier = Agent(
            role="Narrative verifier",
            goal="Reject unsupported selections and explanations",
            backstory="You reject invented causes, players, events or figures.",
            llm=self._fast_llm,
            allow_delegation=False,
            verbose=False,
        )
        tasks = [
            Task(
                description=f"Observe this evidence. Fact indexes are zero based. {context}",
                expected_output="ObservedFacts with fact_indexes and reason",
                agent=observer,
                output_pydantic=ObservedFacts,
                callback=record_stage("observer"),
            ),
            Task(
                description=f"Interpret only the observed facts. Use angle observed, decisive or player. State missing evidence. {context}",
                expected_output="AnalysisProposal with angle, evidence_limit and reason",
                agent=analyst,
                output_pydantic=AnalysisProposal,
                callback=record_stage("analyst"),
            ),
            Task(
                description=f"Select fact indexes for the viewer and question. If evidence is absent return an empty list. Do not write final prose. {context}",
                expected_output="SelectionProposal with fact_indexes, angle and reason",
                agent=narrator,
                output_pydantic=SelectionProposal,
                callback=record_stage("narrator"),
            ),
            Task(
                description=f"Check selected indexes against the original candidate and reject unsupported interpretation. {context}",
                expected_output="ReviewProposal with approved and reason",
                agent=verifier,
                output_pydantic=ReviewProposal,
                callback=record_stage("verifier"),
            ),
        ]
        output = Crew(
            agents=[observer, analyst, narrator, verifier],
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
            memory=False,
        ).kickoff()
        observed = ObservedFacts.model_validate(output.tasks_output[0].pydantic)
        analysis = AnalysisProposal.model_validate(output.tasks_output[1].pydantic)
        selection = SelectionProposal.model_validate(output.tasks_output[2].pydantic)
        review = ReviewProposal.model_validate(output.tasks_output[3].pydantic)
        if not set(selection.fact_indexes) <= set(observed.fact_indexes):
            review = ReviewProposal(approved=False, reason="Selected facts were not observed")
        return NarrativePlan(
            fact_indexes=selection.fact_indexes,
            angle=selection.angle if selection.angle == analysis.angle else "observed",
            reason=selection.reason,
            evidence_limit=analysis.evidence_limit,
            reviewer_approved=review.approved,
            reviewer_reason=review.reason,
            stage_elapsed_ms=stage_elapsed_ms,
        )
