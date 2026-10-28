"""Análisis asíncrono del vídeo mediante SoccerNet GameState."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from hashlib import sha256
from math import isfinite
from typing import Any

import aiohttp
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from match_intelligence.application.realtime_observations import LiveObservation
from match_intelligence.adapters.sources.soccernet_gamestate import (
    convert_gamestate_rows,
    gamestate_track_id,
    resolve_gamestate_identities,
)
from match_intelligence.domain.analytics.tracking import TrackingFrame, track_set_from_frames, tracking_metrics
from match_intelligence.domain.contracts import MatchMetadata
from match_intelligence.application.model_http import model_payload


class GameStateUnavailableError(RuntimeError):
    pass


class GameStateFailedError(GameStateUnavailableError):
    """El servidor terminó el análisis; un próximo intento puede crear otro."""


@dataclass(frozen=True, slots=True)
class GameStateSettings:
    endpoint: str | None
    api_key: str | None
    blob_endpoint: str | None
    blob_container: str
    blob_name: str | None
    timeout_seconds: float = 3_600.0
    polling_seconds: float = 5.0
    sample_interval_ms: int = 1_000
    team_by_side: tuple[tuple[str, str], ...] = ()
    roster_verified: bool = False

    def __post_init__(self) -> None:
        if not isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("SOCCERNET_GAMESTATE_TIMEOUT_SECONDS debe ser positivo")
        if not isfinite(self.polling_seconds) or self.polling_seconds <= 0:
            raise ValueError("SOCCERNET_GAMESTATE_POLL_SECONDS debe ser positivo")
        if self.sample_interval_ms < 1:
            raise ValueError("SOCCERNET_GAMESTATE_SAMPLE_INTERVAL_MS debe ser positivo")

    @classmethod
    def from_environment(cls) -> "GameStateSettings":
        endpoint = os.getenv("SOCCERNET_GAMESTATE_ENDPOINT")
        mapping = json.loads(os.getenv("SOCCERNET_GAMESTATE_TEAM_BY_SIDE") or "{}")
        if not isinstance(mapping, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in mapping.items()
        ):
            raise ValueError("SOCCERNET_GAMESTATE_TEAM_BY_SIDE debe ser un objeto JSON lado:team_id")
        return cls(
            endpoint=endpoint.rstrip("/") if endpoint else None,
            api_key=os.getenv("SOCCERNET_GAMESTATE_API_KEY"),
            blob_endpoint=os.getenv("AZURE_BLOB_SERVICE_ENDPOINT"),
            blob_container=os.getenv("VISION_VIDEO_CONTAINER", "synthetic-videos"),
            blob_name=os.getenv("VISION_VIDEO_BLOB_NAME"),
            timeout_seconds=float(os.getenv("SOCCERNET_GAMESTATE_TIMEOUT_SECONDS", "3600")),
            polling_seconds=float(os.getenv("SOCCERNET_GAMESTATE_POLL_SECONDS", "5")),
            sample_interval_ms=int(os.getenv("SOCCERNET_GAMESTATE_SAMPLE_INTERVAL_MS", "1000")),
            team_by_side=tuple(mapping.items()),
            roster_verified=os.getenv("SOCCERNET_GAMESTATE_ROSTER_VERIFIED", "false").lower()
            in {"1", "true", "yes"},
        )

    @property
    def configured(self) -> bool:
        return all((self.endpoint, self.api_key, self.blob_endpoint, self.blob_name))


class GameStateAnalysis:
    """Ejecuta GameState una vez por vídeo y publica seguimiento sincronizado."""

    def __init__(self, publisher: Any, settings: GameStateSettings) -> None:
        self.publisher = publisher
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None
        self._cached_rows: tuple[dict[str, Any], ...] | None = None
        self._video: dict[str, Any] = {}
        self._device: str | None = None
        self._analysis_id: str | None = None
        self._tracking_frames: tuple[TrackingFrame, ...] = ()
        self._metrics: tuple[dict[str, Any], ...] = ()
        self._identity_evidence: dict[str, dict[str, object]] = {}
        self._resolved_identities = 0
        self._ambiguous_identities = 0
        self._metadata: MatchMetadata | None = None
        self._match_id: str | None = None
        self._media_sha256: str | None = None
        self._phase = "idle"
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
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.settings.api_key or ""}

    async def readiness(self) -> dict[str, Any]:
        if not self.settings.configured:
            if self.settings.endpoint:
                raise GameStateUnavailableError(
                    "GameState incompleto: configure API key, Blob endpoint y VISION_VIDEO_BLOB_NAME"
                )
            return {"status": "disabled", "configured": False}
        try:
            async with self._http().get(
                f"{self.settings.endpoint}/health/ready",
                timeout=aiohttp.ClientTimeout(total=min(90, self.settings.timeout_seconds)),
            ) as response:
                payload = await model_payload(response)
                if response.status >= 400:
                    raise GameStateUnavailableError(
                        f"GameState no está listo (HTTP {response.status}): {payload}"
                    )
                self._device = payload.get("device")
                return {**payload, "configured": True}
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise GameStateUnavailableError(
                "GameState todavía está iniciando o no es accesible"
            ) from error

    async def prepare(
        self, match_id: str, metadata: MatchMetadata | None = None
    ) -> dict[str, Any]:
        self._phase, self._error = "checking", None
        try:
            ready = await self.readiness()
            if ready.get("status") == "disabled":
                self._phase = "disabled"
                return ready
            if ready.get("status") != "ready":
                raise GameStateUnavailableError(f"GameState no está listo: {ready}")
            if metadata is not None and metadata.match_id != match_id:
                raise ValueError("La plantilla pertenece a otro partido")
            if metadata is not None and (metadata.pitch_length_m, metadata.pitch_width_m) != (105, 68):
                raise ValueError("La calibración GameState actual requiere un campo de 105 x 68 m")
            self._match_id = match_id
            reused = self._cached_rows is not None
            if self._cached_rows is None:
                if self._analysis_id is None:
                    self._phase = "downloading_video"
                    video = await self._download_video()
                    self._media_sha256 = sha256(video).hexdigest()
                    self._phase = "uploading_video"
                    created = await self._create(video)
                    self._analysis_id = str(created["analysis_id"])
                    self._video = dict(created.get("video") or {})
                self._phase = "processing"
                try:
                    await self._wait(self._analysis_id)
                except GameStateFailedError:
                    self._analysis_id = None
                    raise
                self._phase = "downloading_result"
                self._cached_rows = await self._result(self._analysis_id)
                self.runs += 1
            self._phase = "converting"
            self._tracking_frames, self._metrics = (), ()
            self._metadata = metadata
            self._identity_evidence = {}
            self._resolved_identities = self._ambiguous_identities = 0
            player_by_track: dict[str, str] = {}
            if metadata is not None:
                team_by_side = self._team_by_side(metadata)
                if self.settings.roster_verified:
                    identities = resolve_gamestate_identities(
                        self._cached_rows,
                        metadata=metadata,
                        team_by_side=team_by_side,
                    )
                    player_by_track = identities.player_by_track
                    self._identity_evidence = identities.evidence_by_track
                    self._resolved_identities = len(player_by_track)
                    self._ambiguous_identities = identities.ambiguous_tracks
                conversion = convert_gamestate_rows(
                    self._cached_rows,
                    match_id=match_id,
                    fps=float(self._video.get("fps") or 25),
                    period=1,
                    pitch_length_m=metadata.pitch_length_m,
                    pitch_width_m=metadata.pitch_width_m,
                    team_by_side=team_by_side,
                    player_by_track=player_by_track,
                    identity_evidence_by_track=self._identity_evidence,
                )
                self._tracking_frames = tuple(conversion.frames)
                self._metrics = tuple(
                    metric.model_dump(mode="json")
                    for metric in tracking_metrics(
                        track_set_from_frames(self._tracking_frames),
                        (metadata.home_team.team_id, metadata.away_team.team_id),
                    )
                )
            observations = self._observations(
                match_id,
                self._cached_rows,
                self._video,
                player_by_track=player_by_track,
                identity_evidence_by_track=self._identity_evidence,
            )
            self._phase = "publishing"
            published = await self.publisher.publish_many(observations)
            self._phase = "ready"
            return {
                "status": "ready",
                "configured": True,
                "model": "SoccerNet GameState Reconstruction",
                "device": self._device,
                "analysis_id": self._analysis_id,
                "detections": len(self._cached_rows),
                "observations_published": published,
                "cached": reused,
                "tracking_frames": len(self._tracking_frames),
                "metrics": len(self._metrics),
                "resolved_identities": self._resolved_identities,
                "ambiguous_identities": self._ambiguous_identities,
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
        service = BlobServiceClient(account_url=self.settings.blob_endpoint, credential=credential)
        try:
            blob = service.get_blob_client(
                container=self.settings.blob_container, blob=self.settings.blob_name
            )
            return await (await blob.download_blob()).readall()
        finally:
            await service.close()
            await credential.close()

    async def _create(self, video: bytes) -> dict[str, Any]:
        form = aiohttp.FormData()
        form.add_field("video", video, filename="match.mp4", content_type="video/mp4")
        async with self._http().post(
            f"{self.settings.endpoint}/v1/analyses", data=form, headers=self._headers
        ) as response:
            payload = await model_payload(response)
            if response.status >= 400:
                raise GameStateUnavailableError(
                    f"GameState rechazó el vídeo (HTTP {response.status}): {payload}"
                )
            return payload

    async def _wait(self, analysis_id: str) -> None:
        deadline = asyncio.get_running_loop().time() + self.settings.timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            async with self._http().get(
                f"{self.settings.endpoint}/v1/analyses/{analysis_id}", headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=min(30, deadline - asyncio.get_running_loop().time())),
            ) as response:
                payload = await model_payload(response)
                if response.status == 404:
                    raise GameStateFailedError("El análisis GameState desapareció; se puede reintentar")
                if response.status >= 400:
                    raise GameStateUnavailableError(f"No se pudo consultar GameState: {payload}")
            if payload.get("status") == "succeeded":
                return
            if payload.get("status") == "failed":
                raise GameStateFailedError(
                    f"GameState falló: {payload.get('error', 'sin detalle')}"
                )
            await asyncio.sleep(self.settings.polling_seconds)
        raise GameStateUnavailableError("GameState superó el tiempo máximo de procesamiento")

    async def _result(self, analysis_id: str) -> tuple[dict[str, Any], ...]:
        async with self._http().get(
            f"{self.settings.endpoint}/v1/analyses/{analysis_id}/result",
            headers=self._headers,
        ) as response:
            content = await response.text()
            if response.status >= 400:
                raise GameStateUnavailableError(f"No se pudo descargar GameState: {content}")
        return tuple(json.loads(line) for line in content.splitlines() if line.strip())

    def _observations(
        self,
        match_id: str,
        rows: tuple[dict[str, Any], ...],
        video: dict[str, Any],
        *,
        player_by_track: dict[str, str] | None = None,
        identity_evidence_by_track: dict[str, dict[str, object]] | None = None,
    ) -> tuple[LiveObservation, ...]:
        player_by_track = player_by_track or {}
        identity_evidence_by_track = identity_evidence_by_track or {}
        fps = float(video.get("fps") or 25)
        width = float(video.get("width") or 1)
        height = float(video.get("height") or 1)
        if not all(isfinite(value) and value > 0 for value in (fps, width, height)):
            raise ValueError("FPS y dimensiones de GameState deben ser finitos y positivos")
        buckets: dict[tuple[int, str], tuple[int, dict[str, Any]]] = {}
        interval = max(1, self.settings.sample_interval_ms)
        for ordinal, row in enumerate(rows):
            try:
                timestamp = round(int(row["frame_index"]) / fps * 1000)
            except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
                continue
            if timestamp < 0:
                continue
            track = gamestate_track_id(row.get("track_id"))
            key_track = track or f"det-{row.get('detection_id', ordinal)}"
            bucket = round(timestamp / interval) * interval
            key = (bucket, key_track)
            current = buckets.get(key)
            if current is None or abs(timestamp - bucket) < abs(current[0] - bucket):
                buckets[key] = (timestamp, row)

        received_at = datetime.now(UTC)
        output = []
        for (_, track), (timestamp, row) in sorted(buckets.items()):
            box = self._normalized_box(row.get("bbox_ltwh"), width, height)
            role = str(row.get("role") or "other").lower()
            confidence = row.get("bbox_confidence")
            canonical_track = gamestate_track_id(row.get("track_id"))
            player_id = player_by_track.get(canonical_track)
            output.append(LiveObservation(
                observation_id=f"gs-{match_id}-{timestamp}-{track}",
                source="soccernet-gamestate",
                kind="game_state_detection",
                timestamp_ms=timestamp,
                payload={
                    **row,
                    "match_id": match_id,
                    "timestamp_ms": timestamp,
                    "video_time_ms": timestamp,
                    "label": role,
                    "confidence": confidence,
                    "bounding_box": box,
                    "track_id": canonical_track,
                    "player_id": player_id,
                    "identity_status": "confirmed" if player_id else "unconfirmed",
                    "identity_evidence": identity_evidence_by_track.get(canonical_track),
                    "capture_mode": "precomputed_video",
                },
                received_at=received_at,
            ))
        return tuple(output)

    def _team_by_side(self, metadata: MatchMetadata) -> dict[str, str]:
        """El lado/cluster del modelo no establece por sí solo local y visitante."""
        mapping = dict(self.settings.team_by_side)
        teams = {metadata.home_team.team_id, metadata.away_team.team_id}
        if any(team not in teams for team in mapping.values()):
            raise ValueError("El mapeo GameState contiene equipos ajenos a este partido")
        return mapping

    @property
    def tracking_frames(self) -> tuple[TrackingFrame, ...]:
        return self._tracking_frames

    @property
    def match_id(self) -> str | None:
        return self._match_id

    @property
    def metrics(self) -> tuple[dict[str, Any], ...]:
        return self._metrics

    def metrics_until(self, video_time_ms: int | None) -> tuple[dict[str, Any], ...]:
        """Calcula un prefijo causal para que la UI nunca vea datos del futuro."""
        if video_time_ms is None:
            return self._metrics
        if video_time_ms < 0:
            raise ValueError("video_time_ms no puede ser negativo")
        if self._metadata is None:
            return ()
        frames = tuple(
            frame for frame in self._tracking_frames
            if frame.video_time_ms is not None and frame.video_time_ms <= video_time_ms
        )
        return tuple(
            metric.model_dump(mode="json")
            for metric in tracking_metrics(
                track_set_from_frames(frames),
                (self._metadata.home_team.team_id, self._metadata.away_team.team_id),
            )
        )

    @staticmethod
    def _normalized_box(value: Any, width: float, height: float) -> list[float] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 4 or width <= 0 or height <= 0:
            return None
        try:
            left, top, box_width, box_height = (float(item) for item in value)
        except (TypeError, ValueError):
            return None
        if not all(isfinite(item) for item in (left, top, box_width, box_height)):
            return None
        if box_width <= 0 or box_height <= 0:
            return None
        return [
            max(0.0, min(1.0, left / width)),
            max(0.0, min(1.0, top / height)),
            max(0.0, min(1.0, (left + box_width) / width)),
            max(0.0, min(1.0, (top + box_height) / height)),
        ]

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.settings.configured,
            "runs": self.runs,
            "failures": self.failures,
            "cached_detections": len(self._cached_rows or ()),
            "analysis_id": self._analysis_id,
            "device": self._device,
            "tracking_frames": len(self._tracking_frames),
            "metrics": len(self._metrics),
            "resolved_identities": self._resolved_identities,
            "ambiguous_identities": self._ambiguous_identities,
            "match_id": self._match_id,
            "media_sha256": self._media_sha256,
            "status": self._phase,
            "error": self._error,
            "video": self._video,
            "roster_verified": self.settings.roster_verified,
            "team_mapping_configured": bool(self.settings.team_by_side),
        }

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
