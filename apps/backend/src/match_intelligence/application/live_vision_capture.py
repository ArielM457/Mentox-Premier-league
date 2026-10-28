"""Inferencia de fotogramas en vivo controlada por el reproductor."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import os
from math import isfinite
from typing import Any, Protocol

import aiohttp

from match_intelligence.application.realtime_observations import LiveObservation
from match_intelligence.application.model_http import model_payload, ModelStartingError


class ObservationPublisher(Protocol):
    async def publish_many(self, observations: tuple[LiveObservation, ...]) -> int: ...


class FramePredictor(Protocol):
    async def readiness(self) -> dict[str, Any]: ...

    async def predict(self, image: bytes, content_type: str) -> dict[str, Any]: ...


class CaptureUnavailableError(RuntimeError):
    pass


class CaptureNotPlayingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LiveVisionSettings:
    endpoint: str | None
    api_key: str | None
    interval_ms: int = 1_000
    max_image_bytes: int = 8 * 1024 * 1024
    timeout_seconds: float = 45.0

    @classmethod
    def from_environment(cls) -> "LiveVisionSettings":
        endpoint = os.getenv("ROBOFLOW_SUITE_ENDPOINT")
        return cls(
            endpoint=endpoint.rstrip("/") if endpoint else None,
            api_key=os.getenv("ROBOFLOW_SUITE_API_KEY") or os.getenv("MENTOX_MODEL_API_KEY"),
            interval_ms=int(os.getenv("VISION_CAPTURE_INTERVAL_MS", "1000")),
            max_image_bytes=int(os.getenv("VISION_CAPTURE_MAX_BYTES", str(8 * 1024 * 1024))),
            timeout_seconds=float(os.getenv("VISION_MODEL_TIMEOUT_SECONDS", "45")),
        )


class RoboflowSuitePredictor:
    def __init__(self, settings: LiveVisionSettings) -> None:
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None

    def _session_for_request(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.settings.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def readiness(self) -> dict[str, Any]:
        if not self.settings.endpoint or not self.settings.api_key:
            raise CaptureUnavailableError(
                "Configure ROBOFLOW_SUITE_ENDPOINT y ROBOFLOW_SUITE_API_KEY en el backend"
            )
        try:
            async with self._session_for_request().get(
                f"{self.settings.endpoint}/health/ready"
            ) as response:
                payload = await model_payload(response)
                if response.status in {429, 502, 503, 504}:
                    raise ModelStartingError(f"Roboflow está iniciando (HTTP {response.status})")
                if response.status >= 400:
                    raise CaptureUnavailableError(
                        f"El modelo no está listo (HTTP {response.status}): {payload}"
                    )
                if not {"player", "ball", "pitch"}.issubset(payload.get("models", [])):
                    raise CaptureUnavailableError("El endpoint Roboflow no tiene listos player, ball y pitch")
                return payload
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise ModelStartingError(
                "El modelo todavía está iniciando o no es accesible"
            ) from error

    async def predict(self, image: bytes, content_type: str) -> dict[str, Any]:
        try:
            return await self._predict(image, content_type)
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise CaptureUnavailableError("Roboflow no respondió a la captura; compruebe su réplica y conectividad") from error

    async def _predict(self, image: bytes, content_type: str) -> dict[str, Any]:
        if not self.settings.endpoint or not self.settings.api_key:
            raise CaptureUnavailableError(
                "Configure ROBOFLOW_SUITE_ENDPOINT y ROBOFLOW_SUITE_API_KEY en el backend"
            )
        form = aiohttp.FormData()
        form.add_field("image", image, filename="frame.jpg", content_type=content_type)
        async with self._session_for_request().post(
            f"{self.settings.endpoint}/v1/predict",
            params={"models": "all"},
            data=form,
            headers={"X-API-Key": self.settings.api_key},
        ) as response:
            payload = await model_payload(response)
            if response.status >= 400:
                raise CaptureUnavailableError(
                    f"El modelo respondió HTTP {response.status}: {payload}"
                )
            outputs = payload.get("results")
            if not isinstance(outputs, list) or any(not isinstance(item, dict) for item in outputs):
                raise CaptureUnavailableError("Roboflow no devolvió resultados válidos")
            returned_models = {item.get("model") for item in outputs}
            if returned_models != {"player", "ball", "pitch"} or len(outputs) != 3:
                raise CaptureUnavailableError("La inferencia Roboflow no devolvió los tres modelos solicitados")
            for item in outputs:
                if not isinstance(item.get("detections"), list):
                    raise CaptureUnavailableError("Roboflow no devolvió la lista de detecciones")
                for detection in item["detections"]:
                    if not isinstance(detection, dict):
                        raise CaptureUnavailableError("Detección Roboflow inválida")
                    box, confidence = detection.get("bounding_box"), detection.get("confidence")
                    valid_box = (isinstance(box, list) and len(box) == 4 and all(
                        isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and 0 <= value <= 1 for value in box))
                    if (not valid_box or box[0] > box[2] or box[1] > box[3]
                            or not isinstance(confidence, (int, float)) or not isfinite(confidence) or not 0 <= confidence <= 1
                            or not isinstance(detection.get("label"), str)):
                        raise CaptureUnavailableError("Detección Roboflow sin caja normalizada, clase o confianza válida")
            return payload

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()


class LiveVisionCapture:
    """Acepta un fotograma solo cuando el partido indicado está reproduciéndose."""

    def __init__(
        self,
        predictor: FramePredictor,
        publisher: ObservationPublisher,
        settings: LiveVisionSettings,
    ) -> None:
        self.predictor = predictor
        self.publisher = publisher
        self.settings = settings
        self._playing: set[str] = set()
        self._last_timestamp: dict[str, int] = {}
        self._generation: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self.frames_received = 0
        self.frames_processed = 0
        self.frames_skipped = 0
        self.observations_published = 0
        self.failures = 0
        self._model_ready = False

    async def ensure_ready(self) -> dict[str, Any]:
        readiness = getattr(self.predictor, "readiness", None)
        if readiness is None:
            self._model_ready = True
            return {"status": "ready"}
        self._model_ready = False
        result = await readiness()
        if result.get("status") != "ready":
            raise CaptureUnavailableError(f"El modelo no está listo: {result}")
        self._model_ready = True
        return result

    def play(self, match_id: str) -> None:
        self._playing.add(match_id)

    def pause(self, match_id: str) -> None:
        self._playing.discard(match_id)
        self.seek(match_id)

    def seek(self, match_id: str) -> None:
        # Permite volver a capturar tras retroceder o volver al inicio del vídeo.
        self._last_timestamp.pop(match_id, None)
        self._generation[match_id] = self._generation.get(match_id, 0) + 1

    def restart(self, match_id: str) -> None:
        self.pause(match_id)

    def status(self, match_id: str | None = None) -> dict[str, object]:
        return {
            "configured": bool(self.settings.endpoint and self.settings.api_key),
            "model_ready": self._model_ready,
            "playing": bool(match_id and match_id in self._playing),
            "interval_ms": self.settings.interval_ms,
            "frames_received": self.frames_received,
            "frames_processed": self.frames_processed,
            "frames_skipped": self.frames_skipped,
            "observations_published": self.observations_published,
            "failures": self.failures,
        }

    def ensure_accepting(self, match_id: str, content_type: str) -> None:
        """Rechaza la captura antes de leer el fotograma: en pausa o con un tipo no admitido."""
        if match_id not in self._playing:
            raise CaptureNotPlayingError("La captura está pausada para este partido")
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError("Use JPEG, PNG o WebP")

    async def capture(
        self,
        *,
        match_id: str,
        video_time_ms: int,
        image: bytes,
        content_type: str,
    ) -> dict[str, object]:
        self.frames_received += 1
        self.ensure_accepting(match_id, content_type)
        if not image or len(image) > self.settings.max_image_bytes:
            raise ValueError("El fotograma está vacío o supera el límite permitido")

        lock = self._locks.setdefault(match_id, asyncio.Lock())
        if lock.locked():
            self.frames_skipped += 1
            return {"accepted": False, "reason": "inference_in_progress"}
        previous = self._last_timestamp.get(match_id)
        if previous is not None and video_time_ms - previous < self.settings.interval_ms:
            self.frames_skipped += 1
            return {"accepted": False, "reason": "capture_interval"}

        async with lock:
            # Se vuelve a comprobar después de esperar el lock para que Pause sea inmediato.
            if match_id not in self._playing:
                raise CaptureNotPlayingError("La captura fue pausada")
            try:
                generation = self._generation.get(match_id, 0)
                prediction = await self.predictor.predict(image, content_type)
                if match_id not in self._playing or generation != self._generation.get(match_id, 0):
                    self.frames_skipped += 1
                    return {"accepted": False, "reason": "paused_during_inference"}
                observations = self._observations(match_id, video_time_ms, image, prediction)
                published = await self.publisher.publish_many(observations)
            except Exception:
                self.failures += 1
                raise
            self._last_timestamp[match_id] = video_time_ms
            self.frames_processed += 1
            self.observations_published += published
            return {
                "accepted": True,
                "video_time_ms": video_time_ms,
                "models": len(prediction.get("results", [])),
                "observations": published,
                "inference_ms": prediction.get("inference_ms"),
                "device": prediction.get("device"),
            }

    @staticmethod
    def _observations(
        match_id: str,
        video_time_ms: int,
        image: bytes,
        prediction: dict[str, Any],
    ) -> tuple[LiveObservation, ...]:
        frame_hash = sha256(image).hexdigest()[:16]
        now = datetime.now(UTC)
        output: list[LiveObservation] = []
        for result in prediction.get("results", []):
            model = str(result.get("model", "unknown"))
            for index, detection in enumerate(result.get("detections", [])):
                output.append(
                    LiveObservation(
                        observation_id=(
                            f"{match_id}-{video_time_ms}-{frame_hash}-{model}-{index}"
                        ),
                        source=f"roboflow-{model}",
                        kind="spatial_detection",
                        timestamp_ms=video_time_ms,
                        payload={
                            **detection,
                            "match_id": match_id,
                            "timestamp_ms": video_time_ms,
                            "prediction_id": (
                                f"{match_id}-{video_time_ms}-{frame_hash}-{model}-{index}"
                            ),
                            "model_role": model,
                            "inference_ms": prediction.get("inference_ms"),
                            "device": prediction.get("device"),
                            "capture_mode": "frontend_video_frame",
                        },
                        received_at=now,
                    )
                )
        return tuple(output)

    async def close(self) -> None:
        close = getattr(self.predictor, "close", None)
        if close is not None:
            await close()
