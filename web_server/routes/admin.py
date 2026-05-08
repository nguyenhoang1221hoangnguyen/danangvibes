from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse

from shared.bundle import validate_bundle
from web_server.config import settings
from web_server.services.admin_service import AdminService
from web_server.services.event_loader import EventLoader
from web_server.services.importer import import_bundle
from web_server.state import get_event_loader, templates
from web_server.utils import verify_admin_token

MAX_QR_BYTES = 2 * 1024 * 1024

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_admin_token)])


def _list_importable_bundles() -> list[str]:
    inbox = settings.bundle_inbox_path
    if not inbox.exists():
        return []
    bundles = []
    for child in inbox.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            try:
                validate_bundle(child, verify_checksums=False)
            except (FileNotFoundError, ValueError):
                continue
            bundles.append(child.name)
    return sorted(bundles)


def _resolve_inbox_bundle(bundle_name: str) -> Path:
    if not bundle_name or "/" in bundle_name or "\\" in bundle_name or bundle_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid bundle name")
    if bundle_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid bundle name")
    inbox = settings.bundle_inbox_path.resolve()
    bundle_path = (inbox / bundle_name).resolve()
    if inbox not in bundle_path.parents or not bundle_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid bundle path")
    return bundle_path


@router.get("/")
def dashboard(request: Request, loader: EventLoader = Depends(get_event_loader)):
    events = AdminService(loader).list_events()
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"events": events, "inbox_path": settings.bundle_inbox_path, "importable_bundles": _list_importable_bundles()},
    )


@router.post("/import")
def import_from_inbox(
    bundle_name: str = Form(...),
    publish: bool = Form(False),
    loader: EventLoader = Depends(get_event_loader),
):
    bundle_path = _resolve_inbox_bundle(bundle_name)
    try:
        import_bundle(bundle_path, loader.storage_path, loader.server_db_path)
        if publish:
            AdminService(loader).set_published(bundle_name, True)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/admin/", status_code=303)


@router.post("/events/{event_slug}/publish")
def publish(event_slug: str, loader: EventLoader = Depends(get_event_loader)):
    AdminService(loader).set_published(event_slug, True)
    return RedirectResponse("/admin/", status_code=303)


@router.post("/events/{event_slug}/unpublish")
def unpublish(event_slug: str, loader: EventLoader = Depends(get_event_loader)):
    AdminService(loader).set_published(event_slug, False)
    return RedirectResponse("/admin/", status_code=303)


@router.get("/events/{event_slug}/ocr-review")
def ocr_review(
    request: Request,
    event_slug: str,
    confidence_threshold: float = 0.7,
    loader: EventLoader = Depends(get_event_loader),
):
    candidates = AdminService(loader).low_confidence_ocr(event_slug, confidence_threshold)
    return templates.TemplateResponse(
        request,
        "admin/ocr-review.html",
        {"event_slug": event_slug, "candidates": candidates, "threshold": confidence_threshold},
    )


@router.post("/events/{event_slug}/ocr-correct")
def correct_ocr(
    event_slug: str,
    ocr_candidate_id: int = Form(...),
    corrected_text: str = Form(...),
    loader: EventLoader = Depends(get_event_loader),
):
    AdminService(loader).correct_ocr(event_slug, ocr_candidate_id, corrected_text)
    return RedirectResponse(f"/admin/events/{event_slug}/ocr-review", status_code=303)


@router.post("/events/{event_slug}/donation-message")
def donation_message(event_slug: str, message: str = Form(...), loader: EventLoader = Depends(get_event_loader)):
    AdminService(loader).save_donation_message(event_slug, message)
    return RedirectResponse("/admin/", status_code=303)


@router.post("/events/{event_slug}/qr")
async def qr_upload(event_slug: str, qr_image: UploadFile, loader: EventLoader = Depends(get_event_loader)):
    content = await qr_image.read(MAX_QR_BYTES + 1)
    try:
        AdminService(loader).save_qr_file(event_slug, qr_image.filename or "qr.png", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/admin/", status_code=303)


@router.post("/events/{event_slug}/reload")
def reload_event(event_slug: str, loader: EventLoader = Depends(get_event_loader)):
    try:
        loader.reload_event(event_slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse("/admin/", status_code=303)
