from __future__ import annotations

from fastapi import FastAPI

from server.api.routes import router as api_router
from server.api.ws import router as ws_router

app = FastAPI(title="HouseInsight Agent", version="0.1.0")
app.include_router(api_router, prefix="")
app.include_router(ws_router, prefix="")


@app.get("/")
async def root() -> dict:
    return {"service": "houseinsight-agent", "docs": "/docs"}
