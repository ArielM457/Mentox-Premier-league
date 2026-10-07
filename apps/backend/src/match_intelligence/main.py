from fastapi import FastAPI

from .adapters.http.router import router

app = FastAPI(
    title="Match Intelligence API",
    description="Contrato inicial para eventos sintéticos de fútbol",
    version="0.1.0",
)
app.include_router(router)
