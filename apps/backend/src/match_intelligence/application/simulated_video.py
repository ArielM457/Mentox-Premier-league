"""Datos MESSI del mismo MP4 y publicación causal durante la reproducción."""

import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import PurePosixPath
import time

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from match_intelligence.adapters.sources.messi_replay import convert_messi_replay
from match_intelligence.application.realtime_observations import LiveObservation
from match_intelligence.application.routing.contracts import RoutingEvaluationRequest
from match_intelligence.domain.analytics.tracking import track_set_from_frames, tracking_metrics

# Un avance pedido por HTTP no puede ir más rápido que el reproductor (8×), con margen de red.
MAX_PLAYBACK_SPEED = 8
ADVANCE_SLACK_MS = 2_000


class SimulatedVideo:
    def __init__(self):
        self.replay = None
        self.match_id = None
        self.phase = "idle"
        self.error = None
        self.video_etag = None
        self.video_bytes: bytes | None = None
        self._key = None
        self._session = None
        self._playing = False
        self._position = 0
        # Punto de partida del límite de avance: solo lo fijan Play, Seek y Restart.
        self._anchor = (0, time.monotonic())
        self._generation = 0
        self._delivered = set()
        self._routed = set()
        self._pending = {}
        self._observation_error = None
        self._lock = asyncio.Lock()

    @property
    def configured(self):
        requested = os.getenv("VISION_SIMULATOR_ENABLED", "auto").lower()
        return requested not in {"false", "0", "no"} and bool(
            os.getenv("AZURE_BLOB_SERVICE_ENDPOINT") and os.getenv("VISION_VIDEO_BLOB_NAME")
        )

    async def _download(self):
        endpoint = os.environ["AZURE_BLOB_SERVICE_ENDPOINT"]
        name = os.environ["VISION_VIDEO_BLOB_NAME"]
        if PurePosixPath(name).name != "match.mp4":
            raise ValueError("La integración MESSI requiere el match.mp4 original y sus archivos compañeros")
        prefix = str(PurePosixPath(name).parent)
        container = os.getenv("VISION_VIDEO_CONTAINER", "synthetic-videos")
        async with DefaultAzureCredential() as credential:
            async with BlobServiceClient(endpoint, credential=credential) as service:
                async def read(filename):
                    path = filename if prefix == "." else f"{prefix}/{filename}"
                    blob = service.get_blob_client(container, path)
                    properties = await blob.get_blob_properties()
                    limit = 256 * 1024 * 1024 if filename == "match.mp4" else 32 * 1024 * 1024
                    if properties.size > limit:
                        raise ValueError(f"Artefacto MESSI demasiado grande: {filename}")
                    content = await (await blob.download_blob()).readall()
                    if len(content) > limit:
                        raise ValueError(f"Artefacto MESSI demasiado grande: {filename}")
                    return content, properties.etag
                manifest, _ = await read("manifest.json")
                pairs = await asyncio.gather(*(read(filename) for filename in (
                    "match.mp4", "events.jsonl", "tracking.jsonl", "metadata.jsonl")))
        self.video_etag = pairs[0][1]
        return json.loads(manifest), dict(zip(
            ("match.mp4", "events.jsonl", "tracking.jsonl", "metadata.jsonl"),
            (pair[0] for pair in pairs), strict=True))

    async def prepare(self, match_id, registry):
        if not self.configured:
            self.phase = "disabled"
            return self.status()
        if match_id != os.getenv("VISION_STARTUP_MATCH_ID", "synthetic-live-001"):
            return {"configured": False, "status": "disabled"}
        key = (match_id, os.getenv("AZURE_BLOB_SERVICE_ENDPOINT"),
               os.getenv("VISION_VIDEO_CONTAINER", "synthetic-videos"), os.getenv("VISION_VIDEO_BLOB_NAME"))
        async with self._lock:
            if self.replay is not None and self._key == key:
                if registry.get(match_id) is not self._session:
                    self._session = registry.load_replay(self.replay)
                return self.status()
            self.phase, self.error = "loading", None
            try:
                manifest, artifacts = await asyncio.wait_for(self._download(), timeout=120)
                replay = convert_messi_replay(match_id, manifest, artifacts)
                self._session = registry.load_replay(replay)
                self.replay, self.match_id, self._key = replay, match_id, key
                self.video_bytes = artifacts["match.mp4"]
                self._delivered.clear()
                self._routed.clear()
                self._pending.clear()
                self._position, self._playing = 0, False
                self._anchor = (0, time.monotonic())
                self.phase = "ready"
                return self.status()
            except Exception as error:
                self.replay, self.match_id = None, None
                self.video_bytes = None
                self.phase, self.error = "failed", f"No se pudo cargar el replay MESSI: {error}"
                raise ValueError(self.error) from error

    def status(self):
        return {"configured": self.configured, "status": self.phase, "error": self.error,
                "source": "messi_simulator", "match_id": self.match_id,
                "events": len(self.replay.events) if self.replay else 0,
                "tracking_frames": len(self.replay.tracking) if self.replay else 0,
                "ignored_records": self.replay.ignored if self.replay else {},
                "media_sha256": self.replay.media_sha256 if self.replay else None,
                "events_routed": len(self._routed),
                "events_pending_delivery": len(self._pending),
                "observation_error": self._observation_error,
                "limitations": ["Las identidades y métricas del simulador no son detecciones de IA."]}

    def observations(self, match_id, start_ms, end_ms, predictions=()):
        if self.replay is None or self.match_id != match_id:
            return []
        result = []
        for event in self.replay.events:
            if not start_ms <= event.video_time_ms <= end_ms:
                continue
            evidence = self.replay.evidence[event.event_id]
            candidates = []
            # Coincidencia temporal y de clase NO verifica quién actuó ni que
            # el modelo haya acertado. Se conservan candidatos ambiguos sin elegir.
            for item in predictions:
                label = str(item.get("label", "")).lower()
                types = {"pass": "pass", "high pass": "pass", "cross": "pass",
                         "shot": "shot", "goal": "shot", "player successful tackle": "tackle"}
                delta = int(item.get("video_time_ms", -100000)) - evidence["launch_video_ms"]
                if (types.get(label) == event.type.value and abs(delta) <= 1000
                        and int(item["video_time_ms"]) <= event.video_time_ms):
                    candidates.append({"prediction_id": item.get("prediction_id"), "delta_ms": delta,
                                       "confidence": item.get("confidence"), "status": "temporal_candidate_only"})
            result.append(LiveObservation(
                observation_id=event.event_id, source="messi-simulator", kind="simulated_match_event",
                timestamp_ms=event.video_time_ms, received_at=datetime.now(UTC),
                payload={**event.model_dump(mode="json"), **evidence,
                         "event_type": event.type.value, "evidence_status": "simulator_reference",
                         "model_candidates": candidates, "media_sha256": self.replay.media_sha256,
                         "provenance": {"event": "messi_simulator", "identity": "messi_simulator",
                                        "model_candidates": "teamspotting_unverified"}},
            ))
        return result

    def analytics(self, match_id, until_ms):
        if self.replay is None or self.match_id != match_id:
            return {"source": "messi_simulator", "status": "not_available", "metrics": []}
        frames = [frame for frame in self.replay.tracking if until_ms is not None and frame.video_time_ms <= until_ms]
        events = [event for event in self.replay.events if until_ms is not None and event.video_time_ms <= until_ms]
        metrics = tracking_metrics(track_set_from_frames(frames), [self.replay.metadata.home_team.team_id,
                                           self.replay.metadata.away_team.team_id], events)
        values = [item.model_dump(mode="json") for item in metrics]
        for event in events:
            evidence = self.replay.evidence[event.event_id]
            for key, raw_value, unit, scale in (
                ("pass_distance_m", evidence["distance_m"] if event.type.value == "pass" else None, "m", 1),
                ("shot_launch_speed_kmh", evidence["launch_speed_m_s"] if event.type.value == "shot" else None, "km/h", 3.6),
            ):
                if raw_value is not None:
                    values.append({"key": key, "value": round(float(raw_value) * scale, 2), "unit": unit,
                                   "available": True, "source": "messi_simulator", "player_id": event.player_id,
                                   "team_id": event.team_id, "source_event_ids": [event.event_id]})
        return {"source": "messi_simulator", "status": "ready", "tracking_frames": len(frames),
                "metrics": values,
                "limitations": ["Posiciones del simulador, no estimadas por IA.",
                                "No se interpola seguimiento escaso para fabricar velocidades."]}

    async def control(self, action, match_id, position, publisher, pipeline, predictions=(), generation=None, temporal=None):
        if self.replay is None or self.match_id != match_id:
            return
        async with self._lock:
            if not 0 <= position <= self.replay.duration_ms:
                raise ValueError("Tiempo fuera del vídeo preparado")
            if action == "advance" and generation is not None and generation != self._generation:
                return self._generation
            if action != "advance":
                self._generation += 1
            if action == "pause":
                self._playing = False
            if action in {"seek", "restart", "play"}:
                self._position, self._anchor = position, (position, time.monotonic())
                if action == "play":
                    self._playing = True
                elif action == "restart":
                    self._playing = False
                return self._generation
            if (self._playing or action == "pause") and position >= self._position:
                current_generation = self._generation
                visible = self.observations(match_id, self._position, position, predictions)
                for observation in visible:
                    if observation.observation_id not in self._delivered:
                        self._pending.setdefault(observation.observation_id, observation)
                observation_error = None
                if temporal is not None:
                    try:
                        await temporal.publish_between(match_id, self._position, position)
                    except Exception as error:
                        observation_error = error
                pending = sorted((item for item in self._pending.values() if item.timestamp_ms <= position),
                                 key=lambda item: item.timestamp_ms)
                for observation in pending:
                    if (not self._playing and action != "pause") or self._generation != current_generation:
                        break
                    if observation.observation_id in self._delivered:
                        continue
                    payload = observation.payload
                    # El contrato del filtro solo admite estos tipos. Las
                    # reanudaciones permanecen en la UI sin forzar otro tipo.
                    if observation.observation_id not in self._routed and payload["type"] in {"pass", "shot", "tackle", "recovery", "possession_change", "pressure"}:
                        allowed = {key: payload[key] for key in (
                            "schema_version", "event_id", "match_id", "period", "clock_ms", "video_time_ms",
                            "type", "team_id", "player_id", "start", "end", "outcome", "source", "confidence",
                            "related_event_ids", "receiver_player_id", "situation", "stoppage_ms")}
                        request = RoutingEvaluationRequest.model_validate({"match_id": match_id, "events": [allowed]})
                        await pipeline.evaluate(request)
                        self._routed.add(observation.observation_id)
                    try:
                        await publisher.publish(observation)
                    except Exception as error:
                        # Un canal visual averiado no debe impedir entregar
                        # los tiros siguientes a la cola durable.
                        observation_error = error
                    else:
                        self._delivered.add(observation.observation_id)
                        self._pending.pop(observation.observation_id, None)
                if self._generation == current_generation:
                    self._position = position
                self._observation_error = str(observation_error) if observation_error else None
                if observation_error is not None:
                    raise RuntimeError(f"Observaciones pendientes de entrega: {observation_error}") from observation_error
            if action == "pause":
                self._playing = False
            return self._generation

    def advance_problem(self, match_id, position, generation):
        """Motivo para rechazar un avance pedido por HTTP, o None si se puede aplicar.

        El simulador es compartido: sin la generación vigente, cualquiera podría
        adelantarlo y publicar eventos que todavía no ocurrieron en el vídeo. Un
        avance con una generación vieja no es un problema: ``control`` lo ignora.
        """
        if self.replay is None or self.match_id != match_id:
            return None
        if generation is None:
            return "El avance necesita playback_generation de la reproducción vigente"
        if generation != self._generation or not self._playing:
            return None
        # Se mide desde el último Play o salto: si cada avance moviera el punto de partida,
        # muchos avances seguidos sumarían el margen una y otra vez.
        anchor_position, anchor_at = self._anchor
        elapsed_ms = (time.monotonic() - anchor_at) * 1000
        if position > anchor_position + elapsed_ms * MAX_PLAYBACK_SPEED + ADVANCE_SLACK_MS:
            return "El avance supera el tiempo transcurrido de la reproducción"
        return None

    def halt(self, match_id):
        """Pausa inmediata, también cuando una cola está esperando red."""
        if self.match_id == match_id:
            self._playing = False
            self._generation += 1
