"""Rutas de la analítica de Persona 2 para la experiencia del partido."""

from typing import Annotated

from fastapi import APIRouter, Query

from match_intelligence.application.analytics.moment_analysis import (
    MomentAnalysis,
    MomentNotFound,
    analyze_moment,
)
from match_intelligence.application.analytics.pipeline import MatchAnalytics
from match_intelligence.application.analytics.presentation import PresentationAnalytics
from match_intelligence.application.match_session import NotFoundError

from .match_router import ERRORS, Preferences, Session

router = APIRouter(prefix="/api/v1/matches", tags=["Analítica"], responses=ERRORS)

# Con el motor provisional la sesión no trae MatchAnalytics: se usa uno compartido,
# que ya guarda en caché el análisis de cada partido.
_shared_analytics = MatchAnalytics()


@router.get(
    "/{match_id}/moments/{candidate_id}/analysis",
    response_model=MomentAnalysis,
    summary="Análisis de un momento: motivos, hechos, posiciones y «¿qué habría pasado si…?»",
    description=(
        "Explica un momento ya mostrado con la analítica de Persona 2: prioridad y motivos del "
        "motor de atención para el perfil, hechos con unidades y eventos de origen, posiciones "
        "del instante y cuatro lecturas alternativas medidas con el seguimiento (pase o remate "
        "un segundo antes, apoyo hacia el compañero más libre y arquero 3 m más adelante). "
        "Solo usa eventos ocurridos hasta el momento. Las lecturas comparan espacios; no "
        "predicen el resultado."
    ),
)
def get_moment_analysis(
    session: Session,
    candidate_id: str,
    prefs: Preferences,
    anchor_event_id: Annotated[str | None, Query(description="Evento ancla, si el id no lo indica")] = None,
) -> MomentAnalysis:
    analytics = (
        session.analytics.analytics
        if isinstance(session.analytics, PresentationAnalytics)
        else _shared_analytics
    )
    try:
        return analyze_moment(
            session.metadata,
            session.events,
            candidate_id=candidate_id,
            anchor_event_id=anchor_event_id,
            tracks=session.track_set(),
            preferences=prefs,
            analytics=analytics,
        )
    except MomentNotFound as error:
        raise NotFoundError(str(error)) from error
