from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import processing_cli.services.ocr as ocr_service
from processing_cli.commands import process as process_command
from processing_cli.commands import rebuild_embeddings
from processing_cli.commands.process import run as process_bundle
from processing_cli.commands.process import _validate_event_slug
from shared.bundle import validate_bundle
from web_server.main import app
import web_server.routes.admin as admin_routes
from web_server.server_database import connect_server_database
from web_server.services.event_loader import EventBundle, EventLoader
from web_server.services.importer import import_bundle, set_published
from web_server.services.search_service import SearchService
from web_server.state import set_event_loader


def _create_photo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 240), "white").save(path, "JPEG")


class FakeFaissBuilder:
    def __init__(self) -> None:
        self.count = 0

    def add_embedding(self, embedding: list[float]) -> int:
        vector_id = self.count
        self.count += 1
        return vector_id

    def save(self, output_path: Path) -> None:
        output_path.write_bytes(b"fake-faiss-index\n")


class FakeFaceService:
    def __init__(self, model_name: str = "VGG-Face", model_version: str = "v1") -> None:
        self.model_name = model_name
        self.model_version = model_version

    def detect_and_embed(self, image_path: Path) -> list[dict[str, object]]:
        return [
            {
                "bbox": "[0, 0, 20, 20]",
                "confidence": 0.8,
                "faiss_vector_id": None,
                "embedding_model": self.model_name,
                "embedding_model_version": self.model_version,
                "embedding": [1.0, 0.0],
            }
        ]


def test_process_validate_import_publish_and_search(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner-1234.jpg")

    output = tmp_path / "dist"
    process_bundle(
        source=source,
        event_slug="test-event",
        event_name="Test Event",
        event_date="2026-05-07",
        event_location="Da Nang",
        output=output,
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )

    bundle_path = output / "test-event"
    manifest = validate_bundle(bundle_path)
    assert manifest.stats.total_photos == 1
    assert manifest.processing.ocr_model == "disabled"
    assert manifest.processing.face_model == "disabled"

    storage = tmp_path / "storage"
    server_db = storage / "server.db"
    version = import_bundle(bundle_path, storage, server_db)
    set_published(server_db, "test-event", True)

    imported_db = storage / "test-event" / "active" / "event.db"
    connection = sqlite3.connect(imported_db)
    try:
        connection.execute(
            "INSERT INTO ocr_candidates (photo_id, text, confidence, bbox, is_bib) VALUES (1, '1234', 0.95, '[]', 1)"
        )
        connection.commit()
    finally:
        connection.close()

    assert version == "v1"
    loader = EventLoader(storage, server_db)
    loader.load_published_events()
    bundle = loader.get_event("test-event")
    assert bundle is not None

    results = SearchService(bundle).search_by_bib("1234")
    assert results["total_results"] == 1
    assert (storage / "test-event" / "active").is_symlink()

    server = connect_server_database(server_db)
    try:
        event = server.execute("SELECT is_published FROM server_events WHERE slug = 'test-event'").fetchone()
        assert event["is_published"] == 1
    finally:
        server.close()


def test_public_http_flow_shows_results_and_face_fallback(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner-1234.jpg")
    output = tmp_path / "dist"
    process_bundle(
        source=source,
        event_slug="http-event",
        event_name="HTTP Event",
        event_date="2026-05-07",
        event_location="Da Nang",
        output=output,
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )
    storage = tmp_path / "storage"
    server_db = storage / "server.db"
    import_bundle(output / "http-event", storage, server_db)
    set_published(server_db, "http-event", True)

    imported_db = storage / "http-event" / "active" / "event.db"
    connection = sqlite3.connect(imported_db)
    try:
        connection.execute(
            "INSERT INTO ocr_candidates (photo_id, text, confidence, bbox, is_bib) VALUES (1, '1234', 0.95, '[]', 1)"
        )
        connection.commit()
    finally:
        connection.close()

    loader = EventLoader(storage, server_db)
    loader.load_published_events()
    set_event_loader(loader)
    client = TestClient(app)

    event_response = client.get("/events/http-event")
    assert event_response.status_code == 200
    assert "HTTP Event" in event_response.text

    search_response = client.post("/events/http-event/search/bib", data={"bib_number": "1234"})
    assert search_response.status_code == 200
    assert "Photo #1" in search_response.text

    face_response = client.post(
        "/events/http-event/search/face",
        files={"selfie": ("selfie.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
    )
    assert face_response.status_code == 200
    assert "chưa có face index" in face_response.text

    download_response = client.get("/events/http-event/photos/1/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "image/jpeg"


def test_process_uses_deepface_config_and_rebuild_updates_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(process_command, "FaceService", FakeFaceService)
    monkeypatch.setattr(process_command, "FaissBuilder", FakeFaissBuilder)
    monkeypatch.setattr(rebuild_embeddings, "FaceService", FakeFaceService)
    monkeypatch.setattr(rebuild_embeddings, "FaissBuilder", FakeFaissBuilder)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ocr:
  confidence_threshold: 0.6
face:
  model: DeepFace
  model_name: ArcFace
  model_version: v1
processing:
  thumbnail_size: [800, 600]
  thumbnail_quality: 85
""".strip(),
        encoding="utf-8",
    )
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    output = tmp_path / "dist"

    process_bundle(
        source=source,
        event_slug="face-event",
        event_name="Face Event",
        event_date="2026-05-07",
        event_location=None,
        output=output,
        skip_ocr=True,
        skip_faces=False,
        force=True,
        config_path=config_path,
    )

    bundle_path = output / "face-event"
    manifest = validate_bundle(bundle_path)
    assert manifest.processing.face_model == "DeepFace"
    assert manifest.processing.face_model_version == "ArcFace/v1"
    assert manifest.stats.total_faces_detected == 1

    connection = sqlite3.connect(bundle_path / "event.db")
    try:
        row = connection.execute("SELECT embedding_model, embedding_model_version FROM faces").fetchone()
        assert row == ("ArcFace", "v1")
    finally:
        connection.close()

    rebuild_embeddings.run(bundle_path, model_version="v2", model_name="Facenet", config_path=config_path)
    rebuilt = validate_bundle(bundle_path)
    assert rebuilt.processing.face_model == "DeepFace"
    assert rebuilt.processing.face_model_version == "Facenet/v2"
    assert rebuilt.stats.total_faces_detected == 1


def test_isolated_full_processing_runs_ocr_then_face_subprocesses(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        calls.append(command)

    monkeypatch.setattr(process_command.subprocess, "run", fake_run)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ocr:
  confidence_threshold: 0.6
face:
  model_name: ArcFace
  model_version: v7
processing:
  thumbnail_size: [800, 600]
  thumbnail_quality: 85
""".strip(),
        encoding="utf-8",
    )

    process_bundle(
        source=tmp_path / "photos",
        event_slug="isolated-event",
        event_name="Isolated Event",
        event_date="2026-05-07",
        event_location="Da Nang",
        output=tmp_path / "dist",
        skip_ocr=False,
        skip_faces=False,
        force=True,
        config_path=config_path,
        isolate_ai_stages=True,
    )

    assert len(calls) == 2
    assert calls[0][1:4] == ["-m", "processing_cli", "process"]
    assert "--skip-faces" in calls[0]
    assert "--force" in calls[0]
    assert calls[1][1:4] == ["-m", "processing_cli", "rebuild-embeddings"]
    assert calls[1][calls[1].index("--model-version") + 1] == "v7"
    assert calls[1][calls[1].index("--model-name") + 1] == "ArcFace"


def test_isolated_full_processing_resumes_existing_ocr_only_bundle(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        calls.append(command)

    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    output = tmp_path / "dist"
    bundle = output / "resume-event"
    bundle.mkdir(parents=True)
    (bundle / "manifest.json").write_text(
        '{"bundle_version":"1.0","event":{"slug":"resume-event","name":"Resume Event","date":"2026-05-07","location":null,"created_at":"2026-05-07T00:00:00Z"},"processing":{"app_version":"0.1.0","ocr_model":"PaddleOCR","ocr_model_version":"v1","face_model":"disabled","face_model_version":"disabled","processed_at":"2026-05-07T00:00:00Z","processing_machine":"test","processing_duration_seconds":1},"stats":{"total_photos":1,"photos_with_bib_candidates":0,"photos_with_faces":0,"total_faces_detected":0,"total_bib_candidates":0,"total_thumbnails":1},"files":{"database":"event.db","faiss_index":"faiss.index","thumbnails_dir":"thumbnails","originals_mode":"mapping","originals_mapping":"originals_mapping.json"},"checksums":{}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(process_command.subprocess, "run", fake_run)

    process_bundle(
        source=source,
        event_slug="resume-event",
        event_name="Resume Event",
        event_date="2026-05-07",
        event_location=None,
        output=output,
        skip_ocr=False,
        skip_faces=False,
        force=False,
        isolate_ai_stages=True,
    )

    assert len(calls) == 1
    assert calls[0][1:4] == ["-m", "processing_cli", "rebuild-embeddings"]


def test_face_search_rejects_mixed_models(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    output = tmp_path / "dist"
    process_bundle(
        source=source,
        event_slug="mixed-event",
        event_name="Mixed Event",
        event_date="2026-05-07",
        event_location=None,
        output=output,
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )
    bundle_path = output / "mixed-event"
    (bundle_path / "faiss.index").write_bytes(b"fake-faiss-index\n")
    connection = sqlite3.connect(bundle_path / "event.db")
    try:
        connection.execute(
            "INSERT INTO faces (photo_id, bbox, confidence, faiss_vector_id, embedding_model, embedding_model_version) VALUES (1, '[]', 0.9, 0, 'ArcFace', 'v1')"
        )
        connection.execute(
            "INSERT INTO faces (photo_id, bbox, confidence, faiss_vector_id, embedding_model, embedding_model_version) VALUES (1, '[]', 0.9, 1, 'Facenet', 'v2')"
        )
        connection.commit()
    finally:
        connection.close()

    class FakeBundle(EventBundle):
        def load_faiss_index(self):
            return object()

    result = SearchService(FakeBundle("mixed-event", bundle_path)).search_by_face(b"fake")
    assert "trộn nhiều model" in str(result["message"])


def test_best_face_prefers_confidence_then_area(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    output = tmp_path / "dist"
    process_bundle(
        source=source,
        event_slug="best-face-event",
        event_name="Best Face Event",
        event_date="2026-05-07",
        event_location=None,
        output=output,
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )
    service = SearchService(EventBundle("best-face-event", output / "best-face-event"))
    face = service._best_face(
        [
            {"bbox": "[0, 0, 100, 100]", "confidence": 0.5, "faiss_vector_id": None, "embedding_model": "ArcFace", "embedding_model_version": "v1", "embedding": [0.0, 1.0]},
            {"bbox": "[0, 0, 10, 10]", "confidence": 0.9, "faiss_vector_id": None, "embedding_model": "ArcFace", "embedding_model_version": "v1", "embedding": [1.0, 0.0]},
        ]
    )
    assert face is not None
    assert face["embedding"] == [1.0, 0.0]


def test_admin_dashboard_shows_download_stats(tmp_path: Path, monkeypatch) -> None:
    import web_server.config as config_module
    import web_server.utils as utils_module

    test_settings = replace(config_module.settings, admin_token="dev-secret")
    monkeypatch.setattr(config_module, "settings", test_settings)
    monkeypatch.setattr(utils_module, "settings", test_settings)
    monkeypatch.setattr(admin_routes, "settings", test_settings)
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    output = tmp_path / "dist"
    process_bundle(
        source=source,
        event_slug="stats-event",
        event_name="Stats Event",
        event_date="2026-05-07",
        event_location=None,
        output=output,
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )
    storage = tmp_path / "storage"
    server_db = storage / "server.db"
    import_bundle(output / "stats-event", storage, server_db)
    set_published(server_db, "stats-event", True)
    loader = EventLoader(storage, server_db)
    loader.load_published_events()
    set_event_loader(loader)
    client = TestClient(app)

    assert client.get("/events/stats-event/photos/1/download").status_code == 200
    dashboard = client.get("/admin/", auth=("admin", "dev-secret"))
    assert dashboard.status_code == 200
    assert "1 downloads" in dashboard.text


def test_admin_imports_bundle_from_inbox_and_can_publish(tmp_path: Path, monkeypatch) -> None:
    import web_server.config as config_module
    import web_server.utils as utils_module

    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    inbox = tmp_path / "inbox"
    output = inbox
    process_bundle(
        source=source,
        event_slug="inbox-event",
        event_name="Inbox Event",
        event_date="2026-05-07",
        event_location=None,
        output=output,
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )
    storage = tmp_path / "storage"
    server_db = storage / "server.db"
    test_settings = replace(
        config_module.settings,
        admin_token="dev-secret",
        storage_path=storage,
        server_db_path=server_db,
        bundle_inbox_path=inbox,
    )
    monkeypatch.setattr(config_module, "settings", test_settings)
    monkeypatch.setattr(utils_module, "settings", test_settings)
    monkeypatch.setattr(admin_routes, "settings", test_settings)
    loader = EventLoader(storage, server_db)
    set_event_loader(loader)
    client = TestClient(app)

    dashboard = client.get("/admin/", auth=("admin", "dev-secret"))
    assert dashboard.status_code == 200
    assert "inbox-event" in dashboard.text

    traversal = client.post("/admin/import", data={"bundle_name": "../inbox-event"}, auth=("admin", "dev-secret"))
    assert traversal.status_code == 400

    response = client.post(
        "/admin/import",
        data={"bundle_name": "inbox-event"},
        auth=("admin", "dev-secret"),
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert client.get("/events/inbox-event").status_code == 404

    publish_response = client.post(
        "/admin/events/inbox-event/publish",
        auth=("admin", "dev-secret"),
        follow_redirects=False,
    )
    assert publish_response.status_code == 303
    event_page = client.get("/events/inbox-event")
    assert event_page.status_code == 200
    assert "Inbox Event" in event_page.text


def test_event_slug_rejects_path_traversal() -> None:
    for value in ["../outside", "nested/event", "Event", ".hidden", ""]:
        try:
            _validate_event_slug(value)
        except ValueError:
            continue
        raise AssertionError(f"invalid event slug accepted: {value}")


def test_ocr_rejects_unsupported_paddleocr_major(monkeypatch) -> None:
    monkeypatch.setattr(ocr_service, "version", lambda package_name: "3.5.0")

    try:
        ocr_service.load_paddleocr_class()
    except RuntimeError as exc:
        assert "PaddleOCR 3.5.0 is not supported yet" in str(exc)
        assert "rm -rf venv-ai" in str(exc)
        return
    raise AssertionError("unsupported PaddleOCR major version accepted")


def test_ocr_reports_missing_paddle_backend(monkeypatch) -> None:
    def fake_import(name: str, *args, **kwargs):
        if name == "paddleocr":
            raise ModuleNotFoundError("No module named 'paddle'", name="paddle")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr(ocr_service, "version", lambda package_name: "2.10.0")
    monkeypatch.setattr("builtins.__import__", fake_import)

    try:
        ocr_service.load_paddleocr_class()
    except RuntimeError as exc:
        assert "Install PaddlePaddle to enable OCR" in str(exc)
        return
    raise AssertionError("missing PaddlePaddle backend accepted")


def test_original_mapping_rejects_absolute_and_parent_escape(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    _create_photo(source / "runner.jpg")
    process_bundle(
        source=source,
        event_slug="safe-event",
        event_name="Safe Event",
        event_date="2026-05-07",
        event_location=None,
        output=tmp_path / "dist",
        skip_ocr=True,
        skip_faces=True,
        force=True,
    )
    bundle_path = tmp_path / "dist" / "safe-event"
    mapping_path = bundle_path / "originals_mapping.json"
    mapping = json.loads(mapping_path.read_text())
    mapping["mappings"]["1"] = "../secret.jpg"
    mapping_path.write_text(json.dumps(mapping))

    event_bundle = EventBundle("safe-event", bundle_path)
    assert event_bundle.get_original_path(1) is None
