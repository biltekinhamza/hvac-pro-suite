from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR, settings
from app.database import db
from app.repository import repository
from app.web.routes import router as web_router
from app.whatsapp.webhook import router as whatsapp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    repository.seed_from_desktop_if_empty()
    repository.seed_round_prices_if_empty()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(web_router)
app.include_router(whatsapp_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "true", "app": settings.app_name}
