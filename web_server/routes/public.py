from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from web_server.config import settings
from web_server.server_database import connect_server_database
from web_server.services.download_service import DownloadService
from web_server.services.event_loader import EventLoader
from web_server.services.search_service import SearchService
from web_server.state import get_event_loader, templates

router = APIRouter()


async def _read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="Upload too large")
    return content


def _donation_config(loader: EventLoader, event_slug: str) -> dict[str, str | None]:
    connection = connect_server_database(loader.server_db_path)
    try:
        row = connection.execute(
            "SELECT message, qr_code_path FROM donation_config WHERE event_slug = ?",
            (event_slug,),
        ).fetchone()
    finally:
        connection.close()
    if not row:
        return {"message": None, "qr_url": None}
    qr_path = row["qr_code_path"]
    qr_url = None
    if qr_path:
        qr_url = f"/static/uploads/qr/{Path(str(qr_path)).name}"
    return {"message": row["message"], "qr_url": qr_url}


@router.get("/")
def index(request: Request, loader: EventLoader = Depends(get_event_loader)):
    connection = connect_server_database(loader.server_db_path)
    try:
        rows = connection.execute(
            "SELECT slug, name FROM server_events WHERE is_published = 1 ORDER BY created_at DESC"
        ).fetchall()
    finally:
        connection.close()
    return templates.TemplateResponse(request, "public/index.html", {"events": rows})


@router.get("/events/{event_slug}")
def event_page(request: Request, event_slug: str, loader: EventLoader = Depends(get_event_loader)):
    bundle = loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse(
        request,
        "public/event.html",
        {
            "event": bundle.manifest.event,
            "stats": bundle.manifest.stats,
            "donation": _donation_config(loader, event_slug),
        },
    )


@router.post("/events/{event_slug}/search/bib")
def search_bib(
    request: Request,
    event_slug: str,
    bib_number: str = Form(...),
    loader: EventLoader = Depends(get_event_loader),
):
    bundle = loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    results = SearchService(bundle).search_by_bib(bib_number)
    return templates.TemplateResponse(
        request,
        "public/results.html",
        {
            "event_slug": event_slug,
            "search_type": "bib",
            "query": bib_number,
            "results": results,
            "donation": _donation_config(loader, event_slug),
        },
    )


@router.post("/events/{event_slug}/search/face")
async def search_face(
    request: Request,
    event_slug: str,
    selfie: UploadFile,
    loader: EventLoader = Depends(get_event_loader),
):
    if selfie.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG uploads are allowed")
    content = await _read_upload_limited(selfie, settings.max_selfie_size_mb * 1024 * 1024)
    is_jpeg = content.startswith(b"\xff\xd8\xff")
    is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
    if not ((selfie.content_type == "image/jpeg" and is_jpeg) or (selfie.content_type == "image/png" and is_png)):
        raise HTTPException(status_code=400, detail="Upload content is not a valid JPEG or PNG")
    bundle = loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        results = SearchService(bundle).search_by_face(content)
    except RuntimeError as exc:
        results = {"bib_matches": [], "face_matches": [], "suggested": [], "total_results": 0, "message": str(exc)}
    return templates.TemplateResponse(
        request,
        "public/results.html",
        {
            "event_slug": event_slug,
            "search_type": "face",
            "results": results,
            "donation": _donation_config(loader, event_slug),
        },
    )


@router.get("/events/{event_slug}/photos/{photo_id}/thumbnail")
def thumbnail(event_slug: str, photo_id: int, loader: EventLoader = Depends(get_event_loader)):
    bundle = loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    connection = bundle.get_connection()
    try:
        row = connection.execute("SELECT path FROM thumbnails WHERE photo_id = ?", (photo_id,)).fetchone()
    finally:
        connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = (bundle.bundle_path / str(row["path"])).resolve()
    if bundle.bundle_path.resolve() not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid thumbnail path")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/events/{event_slug}/photos/{photo_id}/download")
def download(event_slug: str, photo_id: int, request: Request, loader: EventLoader = Depends(get_event_loader)):
    bundle = loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    original_path = bundle.get_original_path(photo_id)
    if not original_path or not original_path.exists():
        raise HTTPException(status_code=404, detail="Original not found")
    DownloadService(bundle, loader.server_db_path).track_download(
        photo_id, request.client.host if request.client else None, request.headers.get("user-agent")
    )
    return FileResponse(original_path, media_type="image/jpeg", filename=original_path.name)
