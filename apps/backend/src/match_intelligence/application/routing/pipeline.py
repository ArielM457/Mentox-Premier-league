"""Clasificación y entrega de eventos en tres rutas con garantías distintas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .contracts import RoutingEvaluationRequest, RoutingOutcome
from .service import AgentRoutingService


class RoutingTransport(Protocol):
    async def publish_ingress(self, payload: dict[str, Any], *, partition_key: str) -> None: ...

    async def publish_metrics(self, payload: dict[str, Any], *, partition_key: str) -> None: ...

    async def publish_important(self, payload: dict[str, Any], *, message_id: str) -> None: ...

    def status(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class MemoryRoutingTransport:
    """Transporte reproducible para desarrollo; refleja las tres rutas de Azure."""

    ingress: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    important: list[dict[str, Any]] = field(default_factory=list)

    async def publish_ingress(self, payload: dict[str, Any], *, partition_key: str) -> None:
        self.ingress.append({"partition_key": partition_key, "payload": payload})

    async def publish_metrics(self, payload: dict[str, Any], *, partition_key: str) -> None:
        self.metrics.append({"partition_key": partition_key, "payload": payload})

    async def publish_important(self, payload: dict[str, Any], *, message_id: str) -> None:
        self.important.append({"message_id": message_id, "payload": payload})

    def status(self) -> dict[str, Any]:
        return {
            "transport": "memory",
            "ingress_published": len(self.ingress),
            "metrics_published": len(self.metrics),
            "important_published": len(self.important),
            "telemetry_failures": 0,
        }


class RoutedEventPipeline:
    """Publica primero el ingreso y entrega el resultado según su criticidad.

    La ruta de métricas es tolerante a fallos: queda registrada en el estado y se
    puede reconstruir desde ingreso. La ruta importante propaga el error porque
    perderla impediría reintentar una jugada narrativa.
    """

    def __init__(
        self,
        transport: RoutingTransport,
        service: AgentRoutingService | None = None,
    ) -> None:
        self.transport = transport
        self.service = service or AgentRoutingService()
        self.telemetry_failures: list[str] = []

    async def evaluate(self, request: RoutingEvaluationRequest) -> RoutingOutcome:
        request_payload = request.model_dump(mode="json")
        await self.transport.publish_ingress(request_payload, partition_key=request.match_id)
        outcome = self.service.evaluate(request)
        payload = outcome.model_dump(mode="json")

        if outcome.decision.route == "metrics_only":
            try:
                await self.transport.publish_metrics(payload, partition_key=request.match_id)
            except Exception as error:  # telemetría reconstruible desde ingreso
                self.telemetry_failures.append(f"{type(error).__name__}: {error}")
        elif outcome.decision.route != "rejected":
            await self.transport.publish_important(
                payload,
                message_id=outcome.decision.decision_id,
            )
        return outcome

    def status(self) -> dict[str, Any]:
        result = self.transport.status()
        result["telemetry_failures"] = len(self.telemetry_failures)
        result["last_telemetry_failure"] = (
            self.telemetry_failures[-1] if self.telemetry_failures else None
        )
        return result
