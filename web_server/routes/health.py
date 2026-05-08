from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from web_server.services.event_loader import EventLoader
from web_server.state import get_event_loader

router = APIRouter()
STARTED_AT = time.time()


@router.get("/health")
def health(loader: EventLoader = Depends(get_event_loader)) -> dict[str, object]:
    total_photos = sum(bundle.manifest.stats.total_photos for bundle in loader.bundles.values())
    try:
        import psutil

        memory_usage_mb = int(psutil.Process().memory_info().rss / 1024 / 1024)
    except ImportError:
        memory_usage_mb = 0
    return {
        "status": "healthy",
        "uptime_seconds": int(time.time() - STARTED_AT),
        "memory_usage_mb": memory_usage_mb,
        "active_events": len(loader.bundles),
        "total_photos": total_photos,
    }
