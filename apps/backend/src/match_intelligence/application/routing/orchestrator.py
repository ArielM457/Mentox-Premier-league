"""Dispatch refined requests without coupling the application to one model provider."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from .contracts import AgentDispatch, AgentRequest, AgentTask


class DispatchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_agent: AgentTask
    reason: str


class DispatchGateway(Protocol):
    def route(self, request: AgentRequest) -> DispatchProposal: ...


class FixtureDispatchGateway:
    """Repeatable substitute for the future small routing model."""

    def route(self, request: AgentRequest) -> DispatchProposal:
        return DispatchProposal(
            target_agent=request.task,
            reason="Deterministic route selected from the refined request",
        )


class AgentOrchestrator:
    def __init__(self, gateway: DispatchGateway) -> None:
        self.gateway = gateway

    def dispatch(self, request: AgentRequest) -> AgentDispatch:
        proposal = self.gateway.route(request)
        if proposal.target_agent != request.task:
            raise ValueError("orchestrator cannot change the task without a supported route")
        return AgentDispatch(
            dispatch_id=f"dispatch-{request.request_id}",
            request_id=request.request_id,
            match_id=request.match_id,
            target_agent=proposal.target_agent,
            priority=request.priority,
            ttl_ms=request.ttl_ms,
            correlation_id=request.request_id,
            idempotency_key=f"{request.match_id}:{request.request_id}:{proposal.target_agent}",
            reason=proposal.reason,
        )
