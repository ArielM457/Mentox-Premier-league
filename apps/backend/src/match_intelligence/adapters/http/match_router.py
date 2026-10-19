"""Rutas del partido para la experiencia de Persona 4.

Las rutas solo traducen HTTP; la lógica vive en ``MatchSession``.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from match_intelligence.application.match_session import (
    EditorialRecord,
    ErrorReport,
    MatchSession,
    ReviewDecision,
)
from match_intelligence.domain.presentation import (
    DetailLevel,
    Language,
    MatchSnapshot,
    NarrativeDraft,
    ViewerMode,
    ViewerPreferences,
)

from match_intelligence.application.auth import User

from .auth_router import require_analyst
from .match_schemas import (
    AnalystFeedResponse,
    AnalystMomentResponse,
    AnswerResponse,
    EditorialRecordResponse,
    ErrorResponse,
    EventsResponse,
    LoadMatchRequest,
    MatchDetailResponse,
    MatchListItem,
    OverlaysResponse,
    PlaybackRequest,
    PlaybackResponse,
    QuestionRequest,
    ReportRequest,
    ReportResponse,
    ReviewRequest,
    SourcesResponse,
    VideoSource,
)
from .registry import MatchRegistry, get_registry

STREAM_TICK_S = 0.2
STREAM_LOOKAHEAD_MS = 1_000

ERRORS = {
    400: {"model": ErrorResponse, "description": "Datos o preferencias inválidos"},
    404: {"model": ErrorResponse, "description": "Partido o narración inexistente"},
}

router = APIRouter(prefix="/api/v1/matches", tags=["Partido y experiencia"], responses=ERRORS)

Registry = Annotated[MatchRegistry, Depends(get_registry)]


def _session(match_id: str, registry: Registry) -> MatchSession:
    return registry.get(match_id)


Session = Annotated[MatchSession, Depends(_session)]
Analyst = Annotated[User, Depends(require_analyst)]

ANALYST_ERRORS = {
    401: {"model": ErrorResponse, "description": "Sin sesión"},
    403: {"model": ErrorResponse, "description": "La sesión no es de un analista"},
}


def preferences(
    language: Language = Language.ES,
    mode: ViewerMode = ViewerMode.CASUAL,
    level: DetailLevel = DetailLevel.NORMAL,
    favorite_team_id: str | None = None,
    favorite_player_id: str | None = None,
) -> ViewerPreferences:
    return ViewerPreferences(
        language=language,
        mode=mode,
        level=level,
        favorite_team_id=favorite_team_id or None,
        favorite_player_id=favorite_player_id or None,
    )


Preferences = Annotated[ViewerPreferences, Depends(preferences)]


def _detail(session: MatchSession) -> MatchDetailResponse:
    return MatchDetailResponse(
        metadata=session.metadata,
        duration_ms=session.duration_ms,
        event_count=len(session.events),
        video=VideoSource(),
    )


def _editorial(record: EditorialRecord) -> EditorialRecordResponse:
    return EditorialRecordResponse(
        draft=record.draft,
        status=record.status,
        reviewer=record.reviewer,
        note=record.note,
        decided_at=record.decided_at,
    )


def _report(report: ErrorReport) -> ReportResponse:
    return ReportResponse(
        report_id=report.report_id,
        draft_id=report.draft_id,
        message_id=report.message_id,
        reason=report.reason,
        outcome=report.outcome.value,
        issues=report.issues,
        corrected_draft=report.corrected_draft,
        created_at=report.created_at,
    )


@router.get("", response_model=list[MatchListItem], summary="Listar partidos cargados")
def list_matches(registry: Registry) -> list[MatchListItem]:
    return [
        MatchListItem(
            match_id=s.match_id,
            home_team=s.metadata.home_team.name,
            away_team=s.metadata.away_team.name,
            duration_ms=s.duration_ms,
            event_count=len(s.events),
            created_at=s.created_at,
        )
        for s in registry.all()
    ]


@router.post(
    "",
    response_model=MatchDetailResponse,
    status_code=201,
    summary="Cargar un partido sintético",
    description="Genera el partido con el escenario elegido (Persona 1 o Persona 2). Si el identificador ya existe, lo reemplaza y reinicia revisiones y reportes.",
)
def load_match(body: LoadMatchRequest, registry: Registry) -> MatchDetailResponse:
    session = registry.load_synthetic(
        scenario=body.scenario,
        seed=body.seed,
        match_id=body.match_id,
        inject_error_in=body.inject_error_in,
    )
    return _detail(session)


@router.get("/{match_id}", response_model=MatchDetailResponse, summary="Metadatos del partido")
def get_match(session: Session) -> MatchDetailResponse:
    return _detail(session)


@router.get(
    "/{match_id}/events",
    response_model=EventsResponse,
    summary="Eventos ocurridos hasta un tiempo de vídeo",
    description="Nunca devuelve eventos futuros, para no adelantar lo que todavía no pasó en el vídeo.",
)
def get_events(session: Session, until_video_ms: Annotated[int, Query(ge=0)]) -> EventsResponse:
    return EventsResponse(until_video_ms=until_video_ms, events=session.events_until(until_video_ms))


@router.get("/{match_id}/state", response_model=MatchSnapshot, summary="Estado del partido (MatchSnapshot v1)")
def get_state(session: Session, video_time_ms: Annotated[int, Query(ge=0)]) -> MatchSnapshot:
    return session.snapshot(video_time_ms)


@router.get(
    "/{match_id}/overlays",
    response_model=OverlaysResponse,
    summary="Mensajes para pantalla (OverlayMessage v1)",
    description=(
        "Planifica los mensajes hasta `until_video_ms` con las preferencias dadas. "
        "Se usa para reconstruir la pantalla al adelantar o retroceder."
    ),
)
def get_overlays(
    session: Session,
    prefs: Preferences,
    until_video_ms: Annotated[int | None, Query(ge=0)] = None,
) -> OverlaysResponse:
    limit = session.duration_ms if until_video_ms is None else until_video_ms
    batch = session.overlays(prefs, until_video_ms=limit)
    return OverlaysResponse(
        until_video_ms=limit, preferences=prefs, pipeline_ms=round(batch.pipeline_ms, 3), overlays=batch.overlays
    )


@router.get(
    "/{match_id}/stream",
    summary="Canal en directo (Server-Sent Events)",
    description=(
        "Emite `ready`, `match_event`, `overlay` y `end` siguiendo el reloj del vídeo desde `from_video_ms`. "
        "Cada `overlay` incluye `emitted_at_ms` y `pipeline_ms` para medir el retraso. "
        "Al pausar o adelantar, el cliente cierra el canal y abre otro desde la nueva posición."
    ),
    response_class=StreamingResponse,
)
async def stream(
    request: Request,
    session: Session,
    prefs: Preferences,
    from_video_ms: Annotated[int, Query(ge=0)] = 0,
    speed: Annotated[float, Query(gt=0, le=8)] = 1.0,
) -> StreamingResponse:
    session.overlays(prefs, until_video_ms=from_video_ms)  # valida antes de abrir el canal
    return StreamingResponse(
        _stream_events(request, session, prefs, from_video_ms, speed),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def _stream_events(
    request: Request,
    session: MatchSession,
    prefs: ViewerPreferences,
    from_video_ms: int,
    speed: float,
) -> AsyncIterator[str]:
    duration = session.duration_ms
    sent_overlays = {o.message_id for o in session.overlays(prefs, until_video_ms=from_video_ms).overlays}
    sent_events = len(session.events_until(from_video_ms))
    started = time.perf_counter()
    yield _sse("ready", {"from_video_ms": from_video_ms, "duration_ms": duration, "speed": speed})

    while True:
        if await request.is_disconnected():
            return
        position = from_video_ms + int((time.perf_counter() - started) * 1000 * speed)
        horizon = min(duration, position + STREAM_LOOKAHEAD_MS)

        events = session.events_until(horizon)
        for event in events[sent_events:]:
            yield _sse("match_event", event.model_dump(mode="json"))
        sent_events = len(events)

        batch = session.overlays(prefs, until_video_ms=horizon)
        for overlay in batch.overlays:
            if overlay.message_id in sent_overlays:
                continue
            sent_overlays.add(overlay.message_id)
            yield _sse(
                "overlay",
                {
                    "overlay": overlay.model_dump(mode="json"),
                    "emitted_at_ms": int(time.time() * 1000),
                    "server_video_ms": position,
                    "pipeline_ms": round(batch.pipeline_ms, 3),
                },
            )

        if position >= duration:
            yield _sse("end", {"video_time_ms": duration})
            return
        await asyncio.sleep(STREAM_TICK_S)


@router.get(
    "/{match_id}/drafts/{draft_id}/sources",
    response_model=SourcesResponse,
    summary="Explicación y eventos de origen de un mensaje",
)
def get_sources(session: Session, draft_id: str) -> SourcesResponse:
    draft, events = session.sources(draft_id)
    return SourcesResponse(draft=draft, events=events)


@router.post("/{match_id}/questions", response_model=AnswerResponse, summary="Preguntar sobre el partido")
def ask(session: Session, body: QuestionRequest) -> AnswerResponse:
    answer = session.ask(body.question, body.video_time_ms, body.preferences)
    return AnswerResponse(answer=answer, snapshot=session.snapshot(body.video_time_ms))


@router.get(
    "/{match_id}/summary",
    response_model=EditorialRecordResponse,
    summary="Resumen final personalizado",
    description="Crea o recupera el resumen para estas preferencias. Queda pendiente de revisión editorial.",
)
def get_summary(session: Session, prefs: Preferences) -> EditorialRecordResponse:
    return _editorial(session.summary(prefs))


@router.get("/{match_id}/editorial", response_model=list[EditorialRecordResponse], summary="Cola de revisión editorial")
def editorial_queue(session: Session) -> list[EditorialRecordResponse]:
    return [_editorial(r) for r in session.editorial_queue()]


@router.post(
    "/{match_id}/editorial/{draft_id}/review",
    response_model=EditorialRecordResponse,
    summary="Aprobar o rechazar un análisis final",
    description="Solo un analista con sesión iniciada puede aprobar o rechazar (RF-38).",
    responses={409: {"model": ErrorResponse, "description": "Ya fue revisado"}, **ANALYST_ERRORS},
)
def review(session: Session, draft_id: str, body: ReviewRequest, _: Analyst) -> EditorialRecordResponse:
    record = session.review(draft_id, ReviewDecision(body.decision), body.reviewer, body.note)
    return _editorial(record)


@router.get(
    "/{match_id}/editorial/{draft_id}/published",
    response_model=NarrativeDraft,
    summary="Análisis final publicado",
    description="Responde 409 mientras el análisis no tenga aprobación editorial (RF-38).",
    responses={409: {"model": ErrorResponse, "description": "Sin aprobación"}},
)
def published(session: Session, draft_id: str) -> NarrativeDraft:
    return session.published(draft_id)


@router.post("/{match_id}/reports", response_model=ReportResponse, status_code=201, summary="Reportar un posible error")
def report_error(session: Session, body: ReportRequest) -> ReportResponse:
    return _report(session.report(body.draft_id, body.reason, body.message_id))


@router.get("/{match_id}/reports", response_model=list[ReportResponse], summary="Reportes y resultado de su verificación")
def list_reports(session: Session) -> list[ReportResponse]:
    return [_report(r) for r in session.reports()]


@router.get("/{match_id}/playback", response_model=PlaybackResponse, summary="Estado del reproductor")
def get_playback(session: Session) -> PlaybackResponse:
    return _playback(session)


@router.post("/{match_id}/playback", response_model=PlaybackResponse, summary="Reproducir, pausar, adelantar o reiniciar")
async def control_playback(session: Session, body: PlaybackRequest) -> PlaybackResponse:
    await session.control(body.action, body.video_time_ms)
    return _playback(session)


def _playback(session: MatchSession) -> PlaybackResponse:
    replay = session.replay
    return PlaybackResponse(
        match_id=session.match_id,
        state=replay.state.value,
        video_time_ms=replay.video_time_ms,
        events_applied=replay.position,
        duration_ms=session.duration_ms,
    )


@router.get(
    "/{match_id}/analyst/feed",
    response_model=AnalystFeedResponse,
    summary="Consola del analista: todo lo generado hasta un tiempo",
    description=(
        "Eventos, estado, cada momento candidato con sus hechos y límites, la narración casual y "
        "analista de cada uno y el comentario en vivo completo. Requiere sesión de analista."
    ),
    responses=ANALYST_ERRORS,
)
def analyst_feed(
    session: Session,
    prefs: Preferences,
    _: Analyst,
    until_video_ms: Annotated[int | None, Query(ge=0)] = None,
) -> AnalystFeedResponse:
    feed = session.analyst_feed(prefs, until_video_ms=until_video_ms)
    return AnalystFeedResponse(
        until_video_ms=feed.until_video_ms,
        pipeline_ms=round(feed.pipeline_ms, 3),
        snapshot=feed.snapshot,
        events=feed.events,
        moments=[
            AnalystMomentResponse(
                candidate=m.candidate, video_time_ms=m.video_time_ms, drafts=m.drafts, shown_in=m.shown_in
            )
            for m in feed.moments
        ],
        commentary=feed.commentary,
    )
