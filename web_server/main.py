from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web_server.config import settings
from web_server.paths import STATIC_DIR
from web_server.routes import admin, health, public
from web_server.services.event_loader import EventLoader
from web_server.state import set_event_loader


@asynccontextmanager
async def lifespan(app: FastAPI):
    loader = EventLoader(settings.storage_path, settings.server_db_path)
    loader.load_published_events()
    set_event_loader(loader)
    yield


app = FastAPI(title="DaNang Vibes", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(health.router)
app.include_router(public.router)
app.include_router(admin.router)
