from __future__ import annotations

from fastapi import HTTPException
from fastapi.templating import Jinja2Templates

from web_server.paths import TEMPLATES_DIR
from web_server.services.event_loader import EventLoader

_event_loader: EventLoader | None = None
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def set_event_loader(loader: EventLoader) -> None:
    global _event_loader
    _event_loader = loader


def get_event_loader() -> EventLoader:
    if _event_loader is None:
        raise HTTPException(status_code=503, detail="Event loader not initialized")
    return _event_loader
