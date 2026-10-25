"""Partidos ficticios y resultados de la analítica en Supabase (PostgreSQL).

Supabase es un PostgreSQL administrado. El backend se conecta con la cadena del
*Session pooler* (IPv4, puerto 5432), que llega en ``SUPABASE_DB_URL`` y nunca
se escribe en registros ni archivos. Las tablas están en el esquema
``match_analytics`` (``infra/supabase/migrations``) y guardan exactamente los
contratos del proyecto:

* ``MatchMetadata`` y ``MatchEvent`` 1.0 de Persona 1;
* ``VisualTrackObservation`` y ``ResolvedVisualIdentity`` de Persona 1, con su
  ``PredictionOrigin``;
* los archivos del análisis de Persona 2, iguales a los que se guardan en Blob.

``psycopg`` se importa solo al conectar, para que el resto del backend funcione
sin el extra ``db``.
"""

import asyncio
import json
import os
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from match_intelligence.adapters.sources.synthetic import SyntheticMatch
from match_intelligence.application.analytics.tracking_input import TrackingInput
from match_intelligence.application.vision_evaluation import PredictionOrigin
from match_intelligence.application.visual_identity import (
    IdentityEvidenceKind,
    IdentityStatus,
    ResolvedVisualIdentity,
    VisualTrackObservation,
)
from match_intelligence.domain.contracts import (
    MatchEvent,
    MatchMetadata,
    PeriodDirection,
    Player,
    Position,
    Team,
)

DATABASE_URL_VARIABLE = "SUPABASE_DB_URL"
SCHEMA = "match_analytics"
LOCATION_PREFIX = "supabase://match_analytics.analytics_run_files"
REPLAY_SCENARIO = "replay"

Connect = Callable[[], Any]


class SupabaseStoreError(RuntimeError):
    """Datos guardados que no cumplen los contratos del proyecto."""


def connect_from_url(url: str) -> Connect:
    """Conexión de psycopg sin sentencias preparadas, compatible con el pooler de Supabase."""

    def connect() -> Any:
        import psycopg

        return psycopg.connect(
            url, prepare_threshold=None, connect_timeout=15, application_name="match-intelligence"
        )

    return connect


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """Datos de catálogo de un partido ficticio, aparte de su contrato."""

    title: str
    scenario: str
    seed: int | None = None
    kickoff_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StoredMatchSummary:
    match_id: str
    title: str
    scenario: str
    event_count: int
    observation_count: int
    run_count: int


# ----- filas <-> contratos ----------------------------------------------------


def match_row(metadata: MatchMetadata, catalog: CatalogEntry) -> dict[str, Any]:
    return {
        "match_id": metadata.match_id,
        "schema_version": metadata.schema_version,
        "title": catalog.title,
        "scenario": catalog.scenario,
        "seed": catalog.seed,
        "home_team_id": metadata.home_team.team_id,
        "home_team_name": metadata.home_team.name,
        "away_team_id": metadata.away_team.team_id,
        "away_team_name": metadata.away_team.name,
        "pitch_length_m": metadata.pitch_length_m,
        "pitch_width_m": metadata.pitch_width_m,
        "attacking_directions": json.dumps(
            [d.model_dump(mode="json") for d in metadata.attacking_directions]
        ),
        "kickoff_at": catalog.kickoff_at,
    }


def player_row(
    match_id: str, order: int, player: Player, goalkeepers: frozenset[str]
) -> tuple[Any, ...]:
    return (
        match_id, player.player_id, order, player.team_id, player.name, player.shirt_number,
        player.player_id in goalkeepers,
    )


def event_row(event: MatchEvent, sequence: int) -> tuple[Any, ...]:
    start, end = event.start, event.end
    return (
        event.match_id, event.event_id, sequence, event.schema_version, event.period,
        event.clock_ms, event.video_time_ms, event.type.value, event.team_id, event.player_id,
        start.x if start else None, start.y if start else None,
        end.x if end else None, end.y if end else None,
        event.outcome.value, event.source.value, event.confidence, list(event.related_event_ids),
        event.receiver_player_id, event.situation, event.stoppage_ms,
    )


EVENT_COLUMNS = (
    "match_id, event_id, sequence, schema_version, period, clock_ms, video_time_ms, type, "
    "team_id, player_id, start_x, start_y, end_x, end_y, outcome, source, confidence, "
    "related_event_ids, receiver_player_id, situation, stoppage_ms"
)


def _position(x: float | None, y: float | None) -> Position | None:
    return None if x is None or y is None else Position(x=x, y=y)


def event_from_row(row: dict[str, Any]) -> MatchEvent:
    return MatchEvent.model_validate({
        "schema_version": row["schema_version"],
        "event_id": row["event_id"],
        "match_id": row["match_id"],
        "period": row["period"],
        "clock_ms": row["clock_ms"],
        "video_time_ms": row["video_time_ms"],
        "type": row["type"],
        "team_id": row["team_id"],
        "player_id": row["player_id"],
        "start": _position(row["start_x"], row["start_y"]),
        "end": _position(row["end_x"], row["end_y"]),
        "outcome": row["outcome"],
        "source": row["source"],
        "confidence": row["confidence"],
        "related_event_ids": list(row["related_event_ids"] or []),
        "receiver_player_id": row.get("receiver_player_id"),
        "situation": row.get("situation"),
        "stoppage_ms": row.get("stoppage_ms") or 0,
    })


def metadata_from_rows(match: dict[str, Any], players: Iterable[dict[str, Any]]) -> MatchMetadata:
    directions = match["attacking_directions"]
    if isinstance(directions, str):
        directions = json.loads(directions)
    return MatchMetadata(
        schema_version=match["schema_version"],
        match_id=match["match_id"],
        home_team=Team(team_id=match["home_team_id"], name=match["home_team_name"]),
        away_team=Team(team_id=match["away_team_id"], name=match["away_team_name"]),
        pitch_length_m=match["pitch_length_m"],
        pitch_width_m=match["pitch_width_m"],
        players=[
            Player(
                player_id=p["player_id"], team_id=p["team_id"], name=p["name"],
                shirt_number=p["shirt_number"],
            )
            for p in players
        ],
        attacking_directions=[PeriodDirection.model_validate(d) for d in directions],
    )


def observation_row(observation: VisualTrackObservation, origin: PredictionOrigin) -> tuple[Any, ...]:
    position = observation.position
    return (
        observation.match_id, observation.observation_id, observation.video_time_ms,
        observation.track_id, observation.team_id,
        position.x if position else None, position.y if position else None,
        observation.detector_confidence, origin.value,
    )


OBSERVATION_COLUMNS = (
    "match_id, observation_id, video_time_ms, track_id, team_id, x, y, detector_confidence, origin"
)


def observation_from_row(row: dict[str, Any]) -> VisualTrackObservation:
    return VisualTrackObservation(
        observation_id=row["observation_id"],
        match_id=row["match_id"],
        video_time_ms=row["video_time_ms"],
        track_id=row["track_id"],
        detector_confidence=row["detector_confidence"],
        team_id=row["team_id"],
        position=_position(row["x"], row["y"]),
    )


def identity_row(identity: ResolvedVisualIdentity) -> tuple[Any, ...]:
    kind = identity.identity_evidence_kind
    return (
        identity.match_id, identity.observation_id, identity.video_time_ms, identity.track_id,
        identity.player_id, identity.identity_status.value, identity.detector_confidence,
        kind.value if kind else None, identity.identity_evidence_reference,
    )


IDENTITY_COLUMNS = (
    "match_id, observation_id, video_time_ms, track_id, player_id, identity_status, "
    "detector_confidence, identity_evidence_kind, identity_evidence_reference"
)


def identity_from_row(row: dict[str, Any]) -> ResolvedVisualIdentity:
    kind = row["identity_evidence_kind"]
    return ResolvedVisualIdentity(
        observation_id=row["observation_id"],
        match_id=row["match_id"],
        video_time_ms=row["video_time_ms"],
        track_id=row["track_id"],
        player_id=row["player_id"],
        identity_status=IdentityStatus(row["identity_status"]),
        detector_confidence=row["detector_confidence"],
        identity_evidence_kind=IdentityEvidenceKind(kind) if kind else None,
        identity_evidence_reference=row["identity_evidence_reference"],
    )


def with_match_id(match: SyntheticMatch, match_id: str) -> SyntheticMatch:
    """Copia del partido con otro ``match_id``, para repetirlo como un partido nuevo."""
    return SyntheticMatch(
        metadata=match.metadata.model_copy(update={"match_id": match_id}),
        events=tuple(e.model_copy(update={"match_id": match_id}) for e in match.events),
    )


def file_content(name: str, content: bytes) -> Any:
    """El contenido de un archivo del análisis como JSON; un .jsonl pasa a arreglo."""
    text = content.decode("utf-8")
    if name.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


# ----- almacén ---------------------------------------------------------------


class SupabaseMatchStore:
    """Lectura y escritura síncronas; cada operación usa su propia conexión."""

    def __init__(self, connect: Connect) -> None:
        self._connect = connect

    @classmethod
    def from_url(cls, url: str) -> "SupabaseMatchStore":
        return cls(connect_from_url(url))

    @classmethod
    def from_env(cls, variable: str = DATABASE_URL_VARIABLE) -> "SupabaseMatchStore | None":
        url = os.getenv(variable, "").strip()
        return cls.from_url(url) if url else None

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        connection = self._connect()
        try:
            with connection.transaction():
                yield connection
        finally:
            connection.close()

    def _rows(self, connection: Any, query: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        from psycopg.rows import dict_row

        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            return list(cursor.fetchall())

    # ----- esquema -------------------------------------------------------------
    def apply_sql(self, script: str) -> None:
        with self._transaction() as connection:
            connection.execute(script)

    # ----- escritura -----------------------------------------------------------
    def replace_match(
        self,
        match: SyntheticMatch,
        catalog: CatalogEntry,
        *,
        goalkeeper_player_ids: frozenset[str] = frozenset(),
    ) -> None:
        """Borra el partido (y todo lo que depende de él) y lo vuelve a escribir."""
        metadata = match.metadata
        wrong = [e.event_id for e in match.events if e.match_id != metadata.match_id]
        if wrong:
            raise SupabaseStoreError("Eventos de otro partido: " + ", ".join(wrong))
        row = match_row(metadata, catalog)
        with self._transaction() as connection:
            connection.execute(f"delete from {SCHEMA}.matches where match_id = %s", (metadata.match_id,))
            columns = ", ".join(row)
            placeholders = ", ".join(
                "%s::jsonb" if name == "attacking_directions" else "%s" for name in row
            )
            connection.execute(
                f"insert into {SCHEMA}.matches ({columns}) values ({placeholders})", tuple(row.values())
            )
            with connection.cursor() as cursor:
                cursor.executemany(
                    f"insert into {SCHEMA}.match_players "
                    "(match_id, player_id, roster_order, team_id, name, shirt_number, is_goalkeeper) "
                    "values (%s, %s, %s, %s, %s, %s, %s)",
                    [
                        player_row(metadata.match_id, order, p, goalkeeper_player_ids)
                        for order, p in enumerate(metadata.players)
                    ],
                )
                with cursor.copy(f"copy {SCHEMA}.match_events ({EVENT_COLUMNS}) from stdin") as copy:
                    for sequence, event in enumerate(match.events):
                        copy.write_row(event_row(event, sequence))

    def replace_tracking(self, match_id: str, tracking: TrackingInput) -> int:
        """Reemplaza las observaciones y las identidades resueltas de un partido."""
        foreign = [o.observation_id for o in tracking.observations if o.match_id != match_id]
        foreign += [i.observation_id for i in tracking.identities if i.match_id != match_id]
        if foreign:
            raise SupabaseStoreError("Observaciones de otro partido: " + ", ".join(foreign[:5]))
        with self._transaction() as connection:
            for table in ("tracking_observations", "visual_identities"):
                connection.execute(f"delete from {SCHEMA}.{table} where match_id = %s", (match_id,))
            with connection.cursor() as cursor:
                with cursor.copy(
                    f"copy {SCHEMA}.tracking_observations ({OBSERVATION_COLUMNS}) from stdin"
                ) as copy:
                    for observation in tracking.observations:
                        copy.write_row(observation_row(observation, tracking.origin))
                with cursor.copy(
                    f"copy {SCHEMA}.visual_identities ({IDENTITY_COLUMNS}) from stdin"
                ) as copy:
                    for identity in tracking.identities:
                        copy.write_row(identity_row(identity))
        return len(tracking.observations)

    def save_run_file(
        self,
        *,
        match_id: str,
        run_id: str,
        name: str,
        content: bytes,
        content_type: str,
        produced_by: str,
    ) -> str:
        parsed = file_content(name, content)
        with self._transaction() as connection:
            connection.execute(
                f"insert into {SCHEMA}.analytics_runs (run_id, match_id, produced_by) "
                "values (%s, %s, %s) on conflict (run_id) do nothing",
                (run_id, match_id, produced_by),
            )
            owner = self._rows(
                connection, f"select match_id from {SCHEMA}.analytics_runs where run_id = %s", (run_id,)
            )
            if owner[0]["match_id"] != match_id:
                raise SupabaseStoreError(f"El análisis {run_id} pertenece a otro partido")
            connection.execute(
                f"insert into {SCHEMA}.analytics_run_files "
                "(run_id, name, content_type, sha256, size_bytes, content) "
                "values (%s, %s, %s, %s, %s, %s::jsonb) "
                "on conflict (run_id, name) do update set content_type = excluded.content_type, "
                "sha256 = excluded.sha256, size_bytes = excluded.size_bytes, content = excluded.content",
                (run_id, name, content_type, sha256(content).hexdigest(), len(content), json.dumps(parsed)),
            )
            if name == "run.json":
                connection.execute(
                    f"update {SCHEMA}.analytics_runs set engine_version = %s, attention_version = %s, "
                    "profile = %s, event_count = %s, candidate_count = %s, manifest = %s::jsonb "
                    "where run_id = %s",
                    (
                        parsed.get("engine_version"), parsed.get("attention_version"),
                        parsed.get("profile"), parsed.get("events"), parsed.get("candidates"),
                        json.dumps(parsed), run_id,
                    ),
                )
        return f"{LOCATION_PREFIX}/{run_id}/{name}"

    def delete_runs(self, match_id: str, *, produced_by: str) -> int:
        with self._transaction() as connection:
            cursor = connection.execute(
                f"delete from {SCHEMA}.analytics_runs where match_id = %s and produced_by = %s",
                (match_id, produced_by),
            )
            return cursor.rowcount

    # ----- lectura -------------------------------------------------------------
    def summaries(self) -> list[StoredMatchSummary]:
        with self._transaction() as connection:
            rows = self._rows(connection, f"""
                select m.match_id, m.title, m.scenario,
                       (select count(*) from {SCHEMA}.match_events e where e.match_id = m.match_id) as events,
                       (select count(*) from {SCHEMA}.tracking_observations o
                         where o.match_id = m.match_id) as observations,
                       (select count(*) from {SCHEMA}.analytics_runs r where r.match_id = m.match_id) as runs
                from {SCHEMA}.matches m
                order by m.kickoff_at nulls last, m.match_id
            """)
        return [
            StoredMatchSummary(
                r["match_id"], r["title"], r["scenario"], r["events"], r["observations"], r["runs"]
            )
            for r in rows
        ]

    def load_metadata(self, match_id: str) -> MatchMetadata | None:
        with self._transaction() as connection:
            return self._metadata(connection, match_id)

    def _metadata(self, connection: Any, match_id: str) -> MatchMetadata | None:
        matches = self._rows(connection, f"select * from {SCHEMA}.matches where match_id = %s", (match_id,))
        if not matches:
            return None
        players = self._rows(
            connection,
            f"select * from {SCHEMA}.match_players where match_id = %s order by roster_order",
            (match_id,),
        )
        return metadata_from_rows(matches[0], players)

    def load_match(self, match_id: str) -> SyntheticMatch | None:
        with self._transaction() as connection:
            metadata = self._metadata(connection, match_id)
            if metadata is None:
                return None
            rows = self._rows(
                connection,
                f"select * from {SCHEMA}.match_events where match_id = %s order by sequence",
                (match_id,),
            )
        return SyntheticMatch(metadata=metadata, events=tuple(event_from_row(r) for r in rows))

    def load_matches(self, *, exclude_scenarios: Sequence[str] = (REPLAY_SCENARIO,)) -> list[SyntheticMatch]:
        """Partidos guardados; por defecto sin las repeticiones del flujo en directo."""
        ids = [s.match_id for s in self.summaries() if s.scenario not in exclude_scenarios]
        matches = [self.load_match(match_id) for match_id in ids]
        return [m for m in matches if m is not None]

    def load_tracking(self, match_id: str) -> TrackingInput | None:
        """Lo que Persona 1 entregó para el partido, o ``None`` si no hay observaciones."""
        with self._transaction() as connection:
            observations = self._rows(
                connection,
                f"select * from {SCHEMA}.tracking_observations where match_id = %s "
                "order by video_time_ms, track_id",
                (match_id,),
            )
            if not observations:
                return None
            identities = self._rows(
                connection,
                f"select * from {SCHEMA}.visual_identities where match_id = %s order by video_time_ms",
                (match_id,),
            )
            goalkeepers = self._rows(
                connection,
                f"select player_id from {SCHEMA}.match_players where match_id = %s and is_goalkeeper",
                (match_id,),
            )
        origins = {row["origin"] for row in observations}
        if len(origins) != 1:
            raise SupabaseStoreError(f"El partido {match_id} mezcla orígenes de seguimiento: {sorted(origins)}")
        return TrackingInput(
            observations=tuple(observation_from_row(r) for r in observations),
            identities=tuple(identity_from_row(r) for r in identities),
            origin=PredictionOrigin(origins.pop()),
            goalkeeper_player_ids=frozenset(r["player_id"] for r in goalkeepers),
        )


# ----- adaptadores asíncronos para el procesador continuo --------------------


class SupabaseMatchMetadataProvider:
    """``MatchMetadataProvider`` del procesador continuo."""

    def __init__(self, store: SupabaseMatchStore) -> None:
        self._store = store

    async def get(self, match_id: str) -> MatchMetadata | None:
        return await asyncio.to_thread(self._store.load_metadata, match_id)

    async def close(self) -> None:
        return None


class SupabaseAnalyticsWriter:
    """``AnalyticsArtifactWriter``: guarda cada archivo del análisis en Supabase."""

    def __init__(self, store: SupabaseMatchStore, *, produced_by: str) -> None:
        self._store = store
        self._produced_by = produced_by

    async def write(
        self, *, match_id: str, run_id: str, name: str, content: bytes, content_type: str
    ) -> str:
        return await asyncio.to_thread(
            self._store.save_run_file,
            match_id=match_id, run_id=run_id, name=name, content=content,
            content_type=content_type, produced_by=self._produced_by,
        )

    async def close(self) -> None:
        return None
