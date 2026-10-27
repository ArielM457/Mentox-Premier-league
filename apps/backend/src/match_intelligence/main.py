from contextlib import asynccontextmanager

from .env_file import load_env_file

# Antes de importar las rutas: algunas leen variables de entorno al importarse.
load_env_file()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .adapters.http.analytics_router import router as analytics_router
from .adapters.http.community_router import router as community_router
from .adapters.http.match_router import router as match_router
from .adapters.http.narrative_router import router as narrative_router
from .adapters.http.router import router
from .adapters.http.integration_router import integration_lifespan, router as integration_router
from .adapters.http.routing_router import close_routing_transport, router as routing_router
from .application.match_session import SessionError

@asynccontextmanager
async def application_lifespan(application: FastAPI):
    async with integration_lifespan(application):
        try:
            yield
        finally:
            await close_routing_transport()


app = FastAPI(
    title="Match Intelligence API",
    description=(
        "Filtro de eventos, enrutamiento de agentes, narraciones basadas en evidencia "
        "y experiencia del partido: estado, mensajes para pantalla, preguntas, "
        "resúmenes y revisión editorial."
    ),
    version="0.2.0",
    lifespan=application_lifespan,
)
app.include_router(router)
app.include_router(narrative_router)
app.include_router(routing_router)
app.include_router(match_router)
app.include_router(community_router)
app.include_router(analytics_router)
app.include_router(integration_router)


@app.exception_handler(SessionError)
async def session_error_handler(_: Request, error: SessionError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})
