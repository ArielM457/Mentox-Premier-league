"""Lectura diagnóstica de respuestas de los servicios de inferencia."""

import json
import asyncio
from time import monotonic
from typing import Any

import aiohttp


class ModelStartingError(RuntimeError):
    """El proxy o la réplica todavía están iniciando; se puede reintentar."""


async def wait_for_model(operation, *, timeout_seconds: float = 600, interval_seconds: float = 5):
    deadline = monotonic() + timeout_seconds
    while True:
        try:
            return await operation()
        except ModelStartingError:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise
            await asyncio.sleep(min(interval_seconds, remaining))


async def model_payload(response: aiohttp.ClientResponse) -> dict[str, Any]:
    text = await response.text()
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        # Un proxy de Azure puede devolver HTML o texto durante un arranque frío.
        payload = {"detail": text[:500] or "Respuesta vacía del servicio de inferencia"}
    return payload if isinstance(payload, dict) else {"detail": payload}
