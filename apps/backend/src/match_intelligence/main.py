from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .adapters.http.match_router import router as match_router
from .adapters.http.router import router
from .application.match_session import SessionError

app = FastAPI(
    title="Match Intelligence API",
    description=(
        "Eventos sintéticos de fútbol, estado del partido, mensajes para pantalla, "
        "preguntas, resúmenes y revisión editorial."
    ),
    version="0.2.0",
)
app.include_router(router)
app.include_router(match_router)


@app.exception_handler(SessionError)
async def session_error_handler(_: Request, error: SessionError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})
