from fastapi import FastAPI

from .adapters.http.router import router
from .adapters.http.narrative_router import router as narrative_router

app = FastAPI(
    title="Match Intelligence API",
    description="Validación de eventos sintéticos y narraciones basadas en evidencia",
    version="0.1.0",
)
app.include_router(router)
app.include_router(narrative_router)
