"""Combinaciones de almacenes para el procesador continuo.

Permiten leer metadatos y guardar el registro del análisis en Supabase y en
Blob Storage a la vez, sin que el procesador sepa cuántos destinos hay.
"""

from match_intelligence.application.analytics.stream import (
    AnalyticsArtifactWriter,
    MatchMetadataProvider,
)
from match_intelligence.domain.contracts import MatchMetadata


class FirstAvailableMetadataProvider:
    """Devuelve los metadatos del primer proveedor que conoce el partido."""

    def __init__(self, *providers: MatchMetadataProvider) -> None:
        if not providers:
            raise ValueError("Se necesita al menos un proveedor de metadatos")
        self._providers = providers

    async def get(self, match_id: str) -> MatchMetadata | None:
        for provider in self._providers:
            metadata = await provider.get(match_id)
            if metadata is not None:
                return metadata
        return None


class FanOutAnalyticsWriter:
    """Escribe cada archivo en todos los destinos y devuelve la ubicación del primero."""

    def __init__(self, *writers: AnalyticsArtifactWriter) -> None:
        if not writers:
            raise ValueError("Se necesita al menos un destino")
        self._writers = writers

    async def write(
        self, *, match_id: str, run_id: str, name: str, content: bytes, content_type: str
    ) -> str:
        written = [
            await writer.write(
                match_id=match_id, run_id=run_id, name=name, content=content, content_type=content_type
            )
            for writer in self._writers
        ]
        return written[0]
