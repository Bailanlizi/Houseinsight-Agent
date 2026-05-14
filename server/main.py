from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import router as api_router
from server.api.ws import router as ws_router

_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]

app = FastAPI(title="HouseInsight Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="")
app.include_router(ws_router, prefix="")


@app.get("/")
async def root() -> dict:
    return {"service": "houseinsight-agent", "docs": "/docs"}
