"""HTTP API for accounts, listings, search, and follow-up questions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db import init_db
from backend.app.routes.accounts import router as accounts_router
from backend.app.routes.facilities import router as facilities_router
from backend.app.routes.search import router as search_router
from backend.app.seed import seed_if_empty

app = FastAPI(
    title="Assisted Living Pathfinder",
    version="0.1.0",
    summary="Enter, update, search, and ask questions about assisted living communities.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(accounts_router, prefix="/api")
app.include_router(facilities_router, prefix="/api")
app.include_router(search_router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_if_empty()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
