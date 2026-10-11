from fastapi import FastAPI

from .adapters.http.router import router
from .adapters.http.narrative_router import router as narrative_router
from .adapters.http.routing_router import router as routing_router

app = FastAPI(
    title="Match Intelligence API",
    description="Filtro de eventos, enrutamiento de agentes y narraciones basadas en evidencia",
    version="0.2.0",
)
app.include_router(router)
app.include_router(narrative_router)
app.include_router(routing_router)
