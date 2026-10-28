"""Análisis temporal previo a Play mediante SoccerNet TeamSpotting."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from hashlib import sha256
from math import isfinite
from typing import Any

import aiohttp
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from match_intelligence.application.realtime_observations import LiveObservation
from match_intelligence.application.model_http import model_payload, ModelStartingError, wait_for_model


class TeamSpottingUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TeamSpottingSettings:
    endpoint: str | None
    api_key: str | None
    blob_endpoint: str | None
    blob_container: str
    blob_name: str | None
    timeout_seconds: float = 900.0

    @classmethod
    def from_environment(cls) -> "TeamSpottingSettings":
        endpoint = os.getenv("SOCCERNET_ENDPOINT")
        return cls(
            endpoint=endpoint.rstrip("/") if endpoint else None,
            api_key=os.getenv("SOCCERNET_API_KEY"),
            blob_endpoint=os.getenv("AZURE_BLOB_SERVICE_ENDPOINT"),
            blob_container=os.getenv("VISION_VIDEO_CONTAINER", "synthetic-videos"),
            blob_name=os.getenv("VISION_VIDEO_BLOB_NAME"),
            timeout_seconds=float(os.getenv("SOCCERNET_TIMEOUT_SECONDS", "900")),
        )

    @property
    def configured(self) -> bool:
        return all((self.endpoint, self.api_key, self.blob_endpoint, self.blob_name))


class TeamSpottingAnalysis:
    """Descarga el video privado, ejecuta TeamSpotting una vez y publica acciones."""

    def __init__(self, publisher: Any, settings: TeamSpottingSettings) -> None:
        self.publisher = publisher
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None
        self._cached_predictions: tuple[dict[str, Any], ...] | None = None
        self._device: str | None = None
        self._processing_time_ms: float | None = None
        self._media_sha256: str | None = None
        self._match_id: str | None = None
        self._phase = "idle"
        self._published: set[str] = set()
        self._pending_observations: dict[str, LiveObservation] = {}
        self._prepared_video: bytes | None = None
        self._error: str | None = None
        self.runs = 0
        self.failures = 0

    def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.timeout_seconds)
            )
        return self._session

    @property
    def predictions(self) -> tuple[dict[str, Any], ...]:
        return self._cached_predictions or ()

    def bind_video(self, video: bytes) -> None:
        """Usa el mismo snapshot que el reproductor, sin descargar otro MP4."""
        digest = sha256(video).hexdigest()
        if self._media_sha256 is not None and digest != self._media_sha256:
            self._cached_predictions = None
            self._published.clear()
            self._pending_observations.clear()
        self._prepared_video = video

    async def publish_between(self, match_id: str, start_ms: int, end_ms: int) -> int:
        for item in self.observations_between(match_id, start_ms, end_ms):
            if item.observation_id not in self._published:
                self._pending_observations.setdefault(item.observation_id, item)
        items = tuple(item for item in self._pending_observations.values() if item.timestamp_ms <= end_ms)
        count = await self.publisher.publish_many(items)
        self._published.update(item.observation_id for item in items)
        for item in items:
            self._pending_observations.pop(item.observation_id, None)
        return count

    def observations_between(self, match_id: str, start_ms: int, end_ms: int):
        if self._match_id != match_id or self._phase != "ready":
            return ()
        return tuple(item for item in self._observations(match_id, self.predictions, self._media_sha256)
                     if start_ms <= item.timestamp_ms <= end_ms)

    async def readiness(self) -> dict[str, Any]:
        if not self.settings.configured:
            if self.settings.endpoint:
                raise TeamSpottingUnavailableError(
                    "TeamSpotting incompleto: configure API key, Blob endpoint y VISION_VIDEO_BLOB_NAME"
                )
            return {"status": "disabled", "configured": False}
        try:
            async with self._http().get(
                f"{self.settings.endpoint}/health/ready",
                timeout=aiohttp.ClientTimeout(total=min(90, self.settings.timeout_seconds)),
            ) as response:
                payload = await model_payload(response)
                if response.status in {429, 502, 503, 504}:
                    raise ModelStartingError(f"TeamSpotting está iniciando (HTTP {response.status})")
                if response.status >= 400:
                    raise TeamSpottingUnavailableError(
                        f"SoccerNet no está listo (HTTP {response.status}): {payload}"
                    )
                return {**payload, "configured": True}
        except (aiohttp.ClientError, TimeoutError) as error:
            raise ModelStartingError(
                "SoccerNet todavía está iniciando o no es accesible"
            ) from error

    async def prepare(self, match_id: str) -> dict[str, Any]:
        self._phase, self._error = "checking", None
        try:
            ready = await wait_for_model(self.readiness)
            if ready.get("status") == "disabled":
                self._phase = "disabled"
                return ready
            if ready.get("status") != "ready":
                raise TeamSpottingUnavailableError(f"TeamSpotting no está listo: {ready}")
            reused = self._cached_predictions is not None
            if self._cached_predictions is None:
                self._phase = "downloading_video"
                video = self._prepared_video if self._prepared_video is not None else await self._download_video()
                self._media_sha256 = sha256(video).hexdigest()
                self._phase = "processing"
                result = await self._predict(video)
                predictions = result.get("predictions")
                if not isinstance(predictions, list):
                    raise TeamSpottingUnavailableError("TeamSpotting no devolvió una lista de predicciones")
                ids = set()
                for item in predictions:
                    if not isinstance(item, dict) or not isinstance(item.get("prediction_id"), str):
                        raise TeamSpottingUnavailableError("Predicción TeamSpotting sin identificador")
                    timestamp = item.get("video_time_ms")
                    confidence = item.get("confidence")
                    if (item["prediction_id"] in ids or not isinstance(timestamp, int) or isinstance(timestamp, bool)
                            or timestamp < 0 or not isinstance(item.get("label"), str)
                            or not isinstance(confidence, (float, int)) or not isfinite(confidence) or not 0 <= confidence <= 1):
                        raise TeamSpottingUnavailableError("Predicción TeamSpotting inválida o duplicada")
                    ids.add(item["prediction_id"])
                self._cached_predictions = tuple(predictions)
                self._device = result.get("device")
                self._processing_time_ms = result.get("processing_time_ms")
                self.runs += 1
            self._phase = "ready"
            self._match_id = match_id
            return {
                "status": "ready",
                "configured": True,
                "model": "SoccerNet T-DEED TeamSpotting",
                "device": self._device,
                "predictions": len(self._cached_predictions),
                "observations_published": len(self._published),
                "processing_time_ms": self._processing_time_ms,
                "cached": reused,
                "media_sha256": self._media_sha256,
            }
        except asyncio.CancelledError:
            self._phase = "interrupted"
            raise
        except Exception as error:
            self.failures += 1
            self._phase, self._error = "failed", str(error)
            raise

    async def _download_video(self) -> bytes:
        credential = DefaultAzureCredential()
        service = BlobServiceClient(
            account_url=self.settings.blob_endpoint,
            credential=credential,
        )
        try:
            blob = service.get_blob_client(
                container=self.settings.blob_container,
                blob=self.settings.blob_name,
            )
            return await (await blob.download_blob()).readall()
        finally:
            await service.close()
            await credential.close()

    async def _predict(self, video: bytes) -> dict[str, Any]:
        form = aiohttp.FormData()
        form.add_field("video", video, filename="match.mp4", content_type="video/mp4")
        async with self._http().post(
            f"{self.settings.endpoint}/v1/predict",
            data=form,
            headers={"X-API-Key": self.settings.api_key},
        ) as response:
            payload = await model_payload(response)
            if response.status >= 400:
                raise TeamSpottingUnavailableError(
                    f"SoccerNet respondió HTTP {response.status}: {payload}"
                )
            return payload

    @staticmethod
    def _event_semantics(label: object) -> tuple[str | None, str, str]:
        """Normaliza clases de T-DEED sin atribuir actor, equipo ni resultado inventados."""
        normalized = str(label or "").strip().lower()
        mapping = {
            "pass": ("pass", "unknown"),
            "high pass": ("pass", "unknown"),
            "cross": ("pass", "unknown"),
            "shot": ("shot", "unknown"),
            "goal": ("shot", "goal"),
            "player successful tackle": ("tackle", "success"),
            "free kick": ("restart", "unknown"),
            "throw in": ("restart", "unknown"),
            "out": ("restart", "unknown"),
        }
        event_type, outcome = mapping.get(normalized, (None, "unknown"))
        status = "mapped_candidate" if event_type else "unmapped_observation"
        return event_type, outcome, status

    @staticmethod
    def _observations(
        match_id: str,
        predictions: tuple[dict[str, Any], ...],
        media_sha256: str | None = None,
    ) -> tuple[LiveObservation, ...]:
        received_at = datetime.now(UTC)
        output = []
        for item in predictions:
            event_type, outcome, evidence_status = TeamSpottingAnalysis._event_semantics(
                item.get("label")
            )
            output.append(LiveObservation(
                observation_id=f"ts-{sha256(match_id.encode()).hexdigest()[:12]}-{(media_sha256 or 'unknown')[:12]}-{item['prediction_id']}",
                source="soccernet",
                kind="temporal_action",
                timestamp_ms=int(item["video_time_ms"]),
                payload={
                    **item,
                    "match_id": match_id,
                    "media_sha256": media_sha256,
                    "timestamp_ms": int(item["video_time_ms"]),
                    "video_time_ms": int(item["video_time_ms"]),
                    "event_type": event_type,
                    "outcome": outcome,
                    "evidence_status": evidence_status,
                    "player_id": None,
                    "receiver_player_id": None,
                    "team_id": None,
                    "limitations": [
                        "TeamSpotting localiza la acción, pero no identifica por sí solo al actor."
                    ],
                    "capture_mode": "precomputed_video",
                },
                received_at=received_at,
            ))
        return tuple(output)

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.settings.configured,
            "runs": self.runs,
            "failures": self.failures,
            "cached_predictions": len(self._cached_predictions or ()),
            "device": self._device,
            "status": self._phase,
            "error": self._error,
            "media_sha256": self._media_sha256,
        }

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
