from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR, settings
from app.database import db
from app.mobile.routes import router as mobile_router
from app.repository import repository
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    repository.seed_from_desktop_if_empty()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(web_router)
app.include_router(mobile_router)


@app.get("/downloads/hvac-mobile.apk", response_class=FileResponse)
def download_android_client() -> FileResponse:
    apk = Path("/app/downloads/hvac-mobile.apk")
    if not apk.is_file():
        apk = Path(__file__).resolve().parent.parent / "android-client" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if not apk.is_file():
        raise HTTPException(status_code=404, detail="Android kurulum dosyasi bulunamadi.")
    return FileResponse(
        apk,
        media_type="application/vnd.android.package-archive",
        filename="HVAC-Mobile.apk",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "true", "app": settings.app_name}
