from __future__ import annotations

from datetime import date
from pathlib import Path

from urllib.parse import quote as url_quote

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from processing_web import folders
from processing_web.config import settings
from processing_web.jobs import ProcessingJobRequest, check_ai_dependencies, job_manager

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["url_quote"] = lambda s: url_quote(str(s), safe="")


def _dashboard_context(request: Request, error: str | None = None, source_path: str = "") -> dict[str, object]:
    return {
        "request": request,
        "settings": settings,
        "job": job_manager.current_job(),
        "ai_dependencies": check_ai_dependencies(),
        "today": date.today().isoformat(),
        "error": error,
        "source_path": source_path,
    }


@router.get("/")
def dashboard(request: Request, source_path: str = ""):
    return templates.TemplateResponse(request, "processing_dashboard.html", _dashboard_context(request, source_path=source_path))


@router.post("/process")
def start_processing(
    request: Request,
    source_path: str = Form(...),
    event_slug: str = Form(...),
    event_name: str = Form(...),
    event_date: str = Form(...),
    event_location: str = Form(""),
    force: bool = Form(False),
    skip_ocr: bool = Form(False),
    ocr_method: str = Form("hybrid"),
):
    job_request = ProcessingJobRequest(
        source_path=Path(source_path).expanduser().resolve(),
        event_slug=event_slug.strip(),
        event_name=event_name.strip(),
        event_date=event_date.strip(),
        event_location=event_location.strip() or None,
        output_root=settings.output_root,
        force=force,
        config_path=settings.config_path,
        skip_ocr=skip_ocr,
        ocr_method=ocr_method,
    )
    try:
        job_manager.start_job(job_request)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "processing_dashboard.html",
            _dashboard_context(request, str(exc)),
            status_code=400,
        )
    return RedirectResponse("/jobs/current", status_code=303)


@router.get("/folders")
def folder_browser(request: Request, path: str | None = Query(default=None)):
    try:
        current_path = folders.resolve_allowed_folder(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "processing_folders.html",
        {
            "roots": folders.allowed_roots(),
            "current_path": current_path,
            "parent_path": folders.parent_within_roots(current_path),
            "children": folders.list_child_directories(current_path),
            "jpeg_count": folders.count_direct_jpegs(current_path),
        },
    )


@router.get("/jobs/current")
def current_job_page(request: Request):
    job = job_manager.current_job()
    if not job:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "processing_job.html", {"job": job})


@router.get("/jobs/current/status")
def current_job_status() -> dict[str, object]:
    job = job_manager.current_job()
    if not job:
        raise HTTPException(status_code=404, detail="No processing job")
    return {
        "id": job.id,
        "status": job.status,
        "message": job.message,
        "source_path": str(job.request.source_path),
        "output_bundle_path": str(job.output_bundle_path) if job.output_bundle_path else str(job.request.output_root / job.request.event_slug),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error": job.error,
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "processing-web"}
