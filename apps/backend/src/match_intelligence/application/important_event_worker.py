"""Procesamiento idempotente de decisiones importantes desacoplado del proveedor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.routing import RoutingOutcome


class AgentExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispatch_id: str
    match_id: str
    target_agent: str
    status: str = Field(pattern="^(processed|duplicate)$")
    source_event_ids: list[str]


class ImportantEventHandler(Protocol):
    async def handle(self, outcome: RoutingOutcome) -> AgentExecutionResult: ...


@dataclass(slots=True)
class InMemoryIdempotencyStore:
    keys: set[str] = field(default_factory=set)

    def contains(self, key: str) -> bool:
        return key in self.keys

    def add(self, key: str) -> None:
        self.keys.add(key)


class DispatchRecordingHandler:
    """Confirma el despacho; los ejecutores de cada tarea se conectan detrás de este puerto."""

    async def handle(self, outcome: RoutingOutcome) -> AgentExecutionResult:
        if outcome.dispatch is None or outcome.agent_request is None:
            raise ValueError("El evento importante no contiene despacho ni solicitud de agente")
        if outcome.dispatch.request_id != outcome.agent_request.request_id:
            raise ValueError("El despacho no corresponde a la solicitud incluida")
        return AgentExecutionResult(
            dispatch_id=outcome.dispatch.dispatch_id,
            match_id=outcome.dispatch.match_id,
            target_agent=outcome.dispatch.target_agent,
            status="processed",
            source_event_ids=outcome.decision.source_event_ids,
        )


class ImportantEventProcessor:
    def __init__(
        self,
        handler: ImportantEventHandler,
        store: InMemoryIdempotencyStore | None = None,
    ) -> None:
        self.handler = handler
        self.store = store or InMemoryIdempotencyStore()

    async def process(self, outcome: RoutingOutcome) -> AgentExecutionResult:
        if outcome.dispatch is None:
            raise ValueError("RoutingOutcome sin AgentDispatch")
        key = outcome.dispatch.idempotency_key
        if self.store.contains(key):
            return AgentExecutionResult(
                dispatch_id=outcome.dispatch.dispatch_id,
                match_id=outcome.dispatch.match_id,
                target_agent=outcome.dispatch.target_agent,
                status="duplicate",
                source_event_ids=outcome.decision.source_event_ids,
            )
        result = await self.handler.handle(outcome)
        self.store.add(key)
        return result
