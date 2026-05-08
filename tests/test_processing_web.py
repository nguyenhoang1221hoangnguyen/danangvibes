from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from processing_web import folders, jobs
from processing_web.config import ProcessingSettings
import processing_web.routes as routes
from processing_web.jobs import ProcessingJobManager
from processing_web.main import app


def _create_photo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-jpeg")


def _configure(tmp_path: Path, monkeypatch, runner):
    settings = ProcessingSettings(
        host="127.0.0.1",
        port=8010,
        output_root=tmp_path / "dist",
        config_path=tmp_path / "config.yaml",
    )
    manager = ProcessingJobManager(runner=runner)
    monkeypatch.setattr(routes, "settings", settings)
    monkeypatch.setattr(routes, "job_manager", manager)
    monkeypatch.setattr(jobs, "check_ai_dependencies", lambda: jobs.AiDependencyStatus(True, True, True))
    monkeypatch.setattr(jobs, "validate_ai_runtime", lambda: None)
    monkeypatch.setattr(routes, "check_ai_dependencies", lambda: jobs.AiDependencyStatus(True, True, True))
    return settings, manager


def test_processing_dashboard_renders(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Processing App 1" in response.text
    assert "Start full OCR + face processing" in response.text


def test_processing_rejects_invalid_source(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(tmp_path / "missing"),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
        },
    )

    assert response.status_code == 400
    assert "Source folder" in response.text


def test_processing_rejects_empty_source(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "photos"
    source.mkdir()
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(source),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
        },
    )

    assert response.status_code == 400
    assert ".jpg" in response.text


def test_processing_rejects_existing_output_without_force(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    (tmp_path / "dist" / "test-event").mkdir(parents=True)
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(source),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
        },
    )

    assert response.status_code == 400
    assert "Bundle đã tồn tại" in response.text


def test_processing_starts_full_ocr_face_job(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def runner(**kwargs) -> None:
        calls.append(kwargs)
        (kwargs["output"] / kwargs["event_slug"]).mkdir(parents=True)

    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    settings, manager = _configure(tmp_path, monkeypatch, runner)
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(source),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
            "event_location": "Da Nang",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    for _ in range(50):
        job = manager.current_job()
        if job and job.status == "succeeded":
            break
        time.sleep(0.01)
    assert calls
    assert calls[0]["skip_ocr"] is False
    assert calls[0]["skip_faces"] is False
    assert calls[0]["isolate_ai_stages"] is True
    assert calls[0]["output"] == settings.output_root
    assert manager.current_job() is not None
    assert manager.current_job().status == "succeeded"


def test_processing_rejects_second_running_job(tmp_path: Path, monkeypatch) -> None:
    def runner(**kwargs) -> None:
        time.sleep(0.2)

    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    _configure(tmp_path, monkeypatch, runner)
    client = TestClient(app)
    data = {
        "source_path": str(source),
        "event_slug": "test-event",
        "event_name": "Test Event",
        "event_date": "2026-05-07",
    }

    assert client.post("/process", data=data, follow_redirects=False).status_code == 303
    response = client.post("/process", data={**data, "event_slug": "other-event"})

    assert response.status_code == 400
    assert "job khác" in response.text


def test_processing_failed_job_status(tmp_path: Path, monkeypatch) -> None:
    def runner(**kwargs) -> None:
        raise RuntimeError("boom")

    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    _, manager = _configure(tmp_path, monkeypatch, runner)
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(source),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    for _ in range(50):
        job = manager.current_job()
        if job and job.status == "failed":
            break
        time.sleep(0.01)
    status = client.get("/jobs/current/status")
    assert status.status_code == 200
    assert status.json()["error"] == "boom"


def test_folder_browser_renders_roots(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(folders, "allowed_roots", lambda: [folders.FolderRoot("Test Root", root.resolve())])
    client = TestClient(app)

    response = client.get("/folders")

    assert response.status_code == 200
    assert "Test Root" in response.text
    assert "Chọn thư mục này" in response.text


def test_folder_browser_lists_child_directories(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    child = root / "photos"
    child.mkdir(parents=True)
    _create_photo(root / "runner.jpg")
    monkeypatch.setattr(folders, "allowed_roots", lambda: [folders.FolderRoot("Test Root", root.resolve())])
    client = TestClient(app)

    response = client.get("/folders", params={"path": str(root)})

    assert response.status_code == 200
    assert "photos" in response.text
    assert "Số ảnh JPG/JPEG" in response.text
    assert "<strong>1</strong>" in response.text


def test_folder_browser_rejects_outside_path(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(folders, "allowed_roots", lambda: [folders.FolderRoot("Test Root", root.resolve())])
    client = TestClient(app)

    response = client.get("/folders", params={"path": str(outside)})

    assert response.status_code == 400


def test_dashboard_prefills_selected_source_path(tmp_path: Path, monkeypatch) -> None:
    selected = tmp_path / "photos"
    selected.mkdir()
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    client = TestClient(app)

    response = client.get("/", params={"source_path": str(selected)})

    assert response.status_code == 200
    assert f'value="{selected}"' in response.text


def test_ai_dependencies_require_paddle_backend(monkeypatch) -> None:
    def fake_find_spec(name: str):
        return None if name == "paddle" else object()

    monkeypatch.setattr(jobs.importlib.util, "find_spec", fake_find_spec)

    status = jobs.check_ai_dependencies()

    assert not status.ready
    assert status.missing == ["paddlepaddle"]


def test_processing_allows_retry_for_ocr_only_bundle(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    bundle = tmp_path / "dist" / "test-event"
    bundle.mkdir(parents=True)
    (bundle / "manifest.json").write_text(
        '{"bundle_version":"1.0","event":{"slug":"test-event","name":"Test Event","date":"2026-05-07","location":null,"created_at":"2026-05-07T00:00:00Z"},"processing":{"app_version":"0.1.0","ocr_model":"PaddleOCR","ocr_model_version":"v1","face_model":"disabled","face_model_version":"disabled","processed_at":"2026-05-07T00:00:00Z","processing_machine":"test","processing_duration_seconds":1},"stats":{"total_photos":1,"photos_with_bib_candidates":0,"photos_with_faces":0,"total_faces_detected":0,"total_bib_candidates":0,"total_thumbnails":1},"files":{"database":"event.db","faiss_index":"faiss.index","thumbnails_dir":"thumbnails","originals_mode":"mapping","originals_mapping":"originals_mapping.json"},"checksums":{}}',
        encoding="utf-8",
    )
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(source),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_processing_rejects_broken_ai_runtime(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    _configure(tmp_path, monkeypatch, lambda **kwargs: None)
    monkeypatch.setattr(jobs, "validate_ai_runtime", lambda: (_ for _ in ()).throw(RuntimeError("Install tf-keras")))
    client = TestClient(app)

    response = client.post(
        "/process",
        data={
            "source_path": str(source),
            "event_slug": "test-event",
            "event_name": "Test Event",
            "event_date": "2026-05-07",
        },
    )

    assert response.status_code == 400
    assert "Install tf-keras" in response.text


def test_processing_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "processing-web"}
