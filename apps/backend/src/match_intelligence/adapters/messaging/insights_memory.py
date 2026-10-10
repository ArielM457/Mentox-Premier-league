from match_intelligence.application.analytics.stream import (
    AnalyticsEnvelope,
    AnalyticsMessageType,
)


class InMemoryInsightPublisher:
    """Publicador local de salidas analíticas, sin servicios externos."""

    def __init__(self) -> None:
        self._envelopes: list[AnalyticsEnvelope] = []

    @property
    def envelopes(self) -> tuple[AnalyticsEnvelope, ...]:
        return tuple(self._envelopes)

    def of_type(self, message_type: AnalyticsMessageType) -> list[AnalyticsEnvelope]:
        return [item for item in self._envelopes if item.message_type is message_type]

    async def publish(self, envelope: AnalyticsEnvelope) -> None:
        self._envelopes.append(envelope)

    def clear(self) -> None:
        self._envelopes.clear()
