from fastapi import FastAPI

from .adapters.http.router import router
from .adapters.http.integration_router import (
    integration_lifespan,
    router as integration_router,
)

app = FastAPI(
    title="Match Intelligence API",
    description="Contrato inicial para eventos sintéticos de fútbol",
    version="0.1.0",
    lifespan=integration_lifespan,
)
app.include_router(router)
app.include_router(integration_router)
