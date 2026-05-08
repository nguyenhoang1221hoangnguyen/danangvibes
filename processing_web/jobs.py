from __future__ import annotations

import importlib.util
import threading

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Literal

from processing_cli.commands.process import run as process_run
from processing_cli.commands.process import _validate_event_slug
from shared.bundle import load_manifest

JobStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass(frozen=True)
class ProcessingJobRequest:
    source_path: Path
    event_slug: str
    event_name: str
    event_date: str
    event_location: str | None
    output_root: Path
    force: bool
    config_path: Path
    skip_ocr: bool = False
    ocr_method: str = "hybrid"  # "hybrid", "paddle", or "skip"


@dataclass
class ProcessingJob:
    id: str
    request: ProcessingJobRequest
    status: JobStatus
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_bundle_path: Path | None = None
    error: str | None = None


@dataclass(frozen=True)
class AiDependencyStatus:
    paddleocr: bool
    deepface: bool
    faiss: bool
    paddlepaddle: bool = True

    @property
    def ready(self) -> bool:
        return self.paddleocr and self.paddlepaddle and self.deepface and self.faiss

    @property
    def missing(self) -> list[str]:
        missing = []
        if not self.paddleocr:
            missing.append("paddleocr")
        if not self.paddlepaddle:
            missing.append("paddlepaddle")
        if not self.deepface:
            missing.append("deepface")
        if not self.faiss:
            missing.append("faiss-cpu")
        return missing


def check_ai_dependencies() -> AiDependencyStatus:
    return AiDependencyStatus(
        paddleocr=importlib.util.find_spec("paddleocr") is not None,
        deepface=importlib.util.find_spec("insightface") is not None or importlib.util.find_spec("deepface") is not None,
        faiss=importlib.util.find_spec("faiss") is not None,
        paddlepaddle=importlib.util.find_spec("paddle") is not None,
    )


def validate_ai_runtime() -> None:
    return None


def _can_resume_face_stage(bundle_path: Path) -> bool:
    try:
        manifest = load_manifest(bundle_path)
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        return False
    return manifest.processing.ocr_model == "PaddleOCR" and manifest.processing.face_model == "disabled"


class ProcessingJobManager:
    def __init__(self, runner: Callable[..., None] = process_run) -> None:
        self._runner = runner
        self._lock = threading.Lock()
        self._current_job: ProcessingJob | None = None

    def current_job(self) -> ProcessingJob | None:
        with self._lock:
            return self._current_job

    def start_job(self, request: ProcessingJobRequest) -> ProcessingJob:
        self._validate_request(request)
        with self._lock:
            if self._current_job and self._current_job.status in {"queued", "running"}:
                raise ValueError("Đang xử lý job khác. Vui lòng chờ job hiện tại hoàn tất.")
            job = ProcessingJob(
                id=datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8],
                request=request,
                status="queued",
                message="Đã xếp hàng xử lý.",
            )
            self._current_job = job
        threading.Thread(target=self._run_job, args=(job,), daemon=True).start()
        return job

    def _validate_request(self, request: ProcessingJobRequest) -> None:
        _validate_event_slug(request.event_slug)
        if not request.source_path.exists() or not request.source_path.is_dir():
            raise ValueError("Source folder không tồn tại hoặc không phải thư mục.")
        if not any(path.suffix.lower() in {".jpg", ".jpeg"} for path in request.source_path.rglob("*")):
            raise ValueError("Source folder chưa có ảnh .jpg hoặc .jpeg.")
        output_bundle = request.output_root / request.event_slug
        if output_bundle.exists() and not request.force and not _can_resume_face_stage(output_bundle):
            raise ValueError("Bundle đã tồn tại. Tick Force rebuild nếu muốn ghi đè.")
        deps = check_ai_dependencies()
        if not deps.ready:
            raise ValueError("Thiếu AI dependencies: " + ", ".join(deps.missing))
        try:
            validate_ai_runtime()
        except Exception as exc:
            raise ValueError(f"AI runtime chưa sẵn sàng: {exc}") from exc

    def _run_job(self, job: ProcessingJob) -> None:
        ocr_method_label = {
            "hybrid": "Hybrid YOLO+Tesseract (nhanh)",
            "paddle": "PaddleOCR (chậm nhưng chính xác)",
            "skip": "không OCR"
        }.get(job.request.ocr_method, job.request.ocr_method)

        if job.request.skip_ocr:
            message = "Đang chạy face detection only."
        else:
            message = f"Đang chạy OCR ({ocr_method_label}) + face detection."

        self._update_job(job, status="running", message=message, started_at=datetime.now(UTC))
        try:
            self._runner(
                source=job.request.source_path,
                event_slug=job.request.event_slug,
                event_name=job.request.event_name,
                event_date=job.request.event_date,
                event_location=job.request.event_location,
                output=job.request.output_root,
                skip_ocr=job.request.skip_ocr,
                skip_faces=False,
                force=job.request.force,
                config_path=job.request.config_path,
                isolate_ai_stages=False,
                ocr_method=job.request.ocr_method,
            )
        except Exception as exc:
            self._update_job(
                job,
                status="failed",
                message="Processing failed.",
                finished_at=datetime.now(UTC),
                error=str(exc),
            )
            return
        self._update_job(
            job,
            status="succeeded",
            message="Processing complete.",
            finished_at=datetime.now(UTC),
            output_bundle_path=job.request.output_root / job.request.event_slug,
        )

    def _update_job(self, job: ProcessingJob, **changes: object) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(job, key, value)


job_manager = ProcessingJobManager()
