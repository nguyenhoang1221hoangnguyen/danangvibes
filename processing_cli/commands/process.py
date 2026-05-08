from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from processing_cli.services.face_insightface import InsightFaceService
from processing_cli.services.faiss_builder import FaissBuilder
from processing_cli.services.scanner import PhotoScanner
from processing_cli.services.thumbnail import ThumbnailService
from shared.bundle import load_manifest, write_manifest
from shared.checksum import compute_checksum
from shared.database import initialize_database
from shared.models import (
    BundleFiles,
    BundleManifest,
    BundleStats,
    EventMetadata,
    ProcessingMetadata,
    normalize_date,
    utc_now_iso,
)

APP_VERSION = "0.1.0"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
EVENT_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load_processing_config(config_path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install PyYAML to read processing config: pip install pyyaml") from exc
    if not config_path.exists():
        raise FileNotFoundError(f"Missing processing config: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Processing config must be a YAML mapping")
    return data


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name, {})
    return value if isinstance(value, dict) else {}


def _tuple_ints(value: object, default: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, list | tuple) and len(value) == 2:
        return int(value[0]), int(value[1])
    return default


def _validate_event_slug(event_slug: str) -> None:
    if not EVENT_SLUG_PATTERN.fullmatch(event_slug):
        raise ValueError("event_slug must contain only lowercase letters, numbers, and hyphens")


def _create_event(connection, slug: str, name: str, event_date: str, location: str | None) -> int:
    created_at = utc_now_iso()
    connection.execute(
        "INSERT INTO events (slug, name, date, location, created_at) VALUES (?, ?, ?, ?, ?)",
        (slug, name, normalize_date(event_date), location, created_at),
    )
    return int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])


def _build_manifest(
    bundle_path: Path,
    event_slug: str,
    event_name: str,
    event_date: str,
    event_location: str | None,
    started: float,
    ocr_model: str,
    ocr_model_version: str,
    face_model: str,
    face_model_version: str,
    *,
    originals_dir: Path | None = None,
) -> BundleManifest:
    db_path = bundle_path / "event.db"
    faiss_path = bundle_path / "faiss.index"
    connection = initialize_database(db_path)
    try:
        stats = BundleStats(
            total_photos=int(connection.execute("SELECT COUNT(*) FROM photos").fetchone()[0]),
            photos_with_bib_candidates=int(connection.execute("SELECT COUNT(DISTINCT photo_id) FROM ocr_candidates WHERE is_bib = 1").fetchone()[0]),
            photos_with_faces=int(connection.execute("SELECT COUNT(DISTINCT photo_id) FROM faces").fetchone()[0]),
            total_faces_detected=int(connection.execute("SELECT COUNT(*) FROM faces").fetchone()[0]),
            total_bib_candidates=int(connection.execute("SELECT COUNT(*) FROM ocr_candidates WHERE is_bib = 1").fetchone()[0]),
            total_thumbnails=len(list((bundle_path / "thumbnails").glob("*.jpg"))),
        )
    finally:
        connection.close()
    return BundleManifest(
        bundle_version="1.0",
        event=EventMetadata(
            slug=event_slug,
            name=event_name,
            date=normalize_date(event_date),
            location=event_location,
            created_at=utc_now_iso(),
        ),
        processing=ProcessingMetadata(
            app_version=APP_VERSION,
            ocr_model=ocr_model,
            ocr_model_version=ocr_model_version,
            face_model=face_model,
            face_model_version=face_model_version,
            processed_at=utc_now_iso(),
            processing_machine=platform.node() or platform.machine(),
            processing_duration_seconds=int(time.time() - started),
        ),
        stats=stats,
        files=BundleFiles(
            database="event.db",
            faiss_index="faiss.index",
            thumbnails_dir="thumbnails",
            originals_mode="embedded" if originals_dir else "mapping",
            originals_mapping="originals_mapping.json",
        ),
        checksums={
            "event.db": compute_checksum(db_path),
            "faiss.index": compute_checksum(faiss_path),
        },
    )


def run(
    source: Path,
    event_slug: str,
    event_name: str,
    event_date: str,
    event_location: str | None,
    output: Path,
    skip_ocr: bool,
    skip_faces: bool,
    force: bool,
    config_path: Path = DEFAULT_CONFIG_PATH,
    isolate_ai_stages: bool = False,
    ocr_method: str = "hybrid",  # "hybrid", "paddle", or "skip"
    copy_originals: bool = True,  # Copy ảnh gốc vào bundle
) -> None:
    if isolate_ai_stages and not skip_ocr and not skip_faces:
        _run_isolated_full_processing(source, event_slug, event_name, event_date, event_location, output, force, config_path)
        return
    _validate_event_slug(event_slug)
    started = time.time()
    config = load_processing_config(config_path)
    ocr_config = _section(config, "ocr")
    face_config = _section(config, "face")
    processing_config = _section(config, "processing")
    thumbnail_size = _tuple_ints(processing_config.get("thumbnail_size"), (800, 600))
    thumbnail_quality = int(processing_config.get("thumbnail_quality", 85))
    face_model_name = str(face_config.get("model_name", "buffalo_l"))
    face_model_version = str(face_config.get("model_version", "v1"))
    bundle_path = output / event_slug
    db_path = bundle_path / "event.db"
    thumbnails_dir = bundle_path / "thumbnails"
    originals_dir = bundle_path / "originals" if copy_originals else None
    if force and bundle_path.exists():
        import shutil

        shutil.rmtree(bundle_path)
    bundle_path.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    if originals_dir:
        originals_dir.mkdir(parents=True, exist_ok=True)

    connection = initialize_database(db_path)
    scanner = PhotoScanner()
    thumbnail_service = ThumbnailService(size=thumbnail_size, quality=thumbnail_quality)

    # Initialize OCR service based on method
    ocr_service = None
    if not skip_ocr and ocr_method != "skip":
        if ocr_method == "hybrid":
            # Use Hybrid YOLO + Tesseract (fastest, recommended)
            try:
                from processing_cli.services.ocr_hybrid import HybridOCRService
                ocr_service = HybridOCRService(enable_paddle_fallback=False)
                print("Using Hybrid OCR (YOLO + Tesseract)")
            except RuntimeError as e:
                print(f"Warning: Hybrid OCR not available: {e}")
                print("Falling back to Tesseract")
                from processing_cli.services.ocr import load_tesseract_service
                TesseractOCRService = load_tesseract_service()
                ocr_service = TesseractOCRService(confidence_threshold=float(ocr_config.get("confidence_threshold", 0.6)))
        elif ocr_method == "paddle":
            # Use PaddleOCR (slower but more accurate)
            try:
                from processing_cli.services.ocr import OCRService
                ocr_service = OCRService(
                    confidence_threshold=float(ocr_config.get("confidence_threshold", 0.6))
                )
                print("Using PaddleOCR (slow but accurate)")
            except RuntimeError as e:
                print(f"Warning: PaddleOCR not available: {e}")
                ocr_service = None
        else:
            # Fallback to Tesseract
            try:
                from processing_cli.services.ocr import load_tesseract_service
                TesseractOCRService = load_tesseract_service()
                ocr_service = TesseractOCRService(confidence_threshold=float(ocr_config.get("confidence_threshold", 0.6)))
                print("Using Tesseract OCR (fast)")
            except RuntimeError as e:
                print(f"Warning: Tesseract not available: {e}")
                ocr_service = None

    face_service = None if skip_faces else InsightFaceService(model_name=face_model_name, model_version=face_model_version)
    faiss_builder = FaissBuilder()
    mappings: dict[str, str] = {}

    try:
        event_id = _create_event(connection, event_slug, event_name, event_date, event_location)
        photos = list(scanner.scan(source))
        print(f"Found {len(photos)} JPG photos")
        for index, photo_path in enumerate(photos, start=1):
            checksum = compute_checksum(photo_path)
            existing = connection.execute("SELECT id FROM photos WHERE checksum = ?", (checksum,)).fetchone()
            if existing and not force:
                continue
            width, height, capture_time, exif_data = thumbnail_service.image_metadata(photo_path)
            relative_original = str(photo_path.relative_to(source))
            connection.execute(
                """
                INSERT INTO photos (event_id, filename, checksum, original_path, file_size, width, height, capture_time, exif_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, photo_path.name, checksum, relative_original, photo_path.stat().st_size, width, height, capture_time, exif_data),
            )
            photo_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
            thumb_path = thumbnails_dir / f"photo_{photo_id:06d}.jpg"
            thumb_meta = thumbnail_service.generate(photo_path, thumb_path)
            connection.execute(
                "INSERT INTO thumbnails (photo_id, path, width, height, file_size) VALUES (?, ?, ?, ?, ?)",
                (photo_id, str(thumb_path.relative_to(bundle_path)), thumb_meta["width"], thumb_meta["height"], thumb_meta["file_size"]),
            )

            # Copy ảnh gốc vào bundle nếu copy_originals=True
            if copy_originals and originals_dir:
                import shutil
                original_filename = f"photo_{photo_id:06d}{photo_path.suffix}"
                original_dest = originals_dir / original_filename
                shutil.copy2(photo_path, original_dest)
                mappings[str(photo_id)] = original_filename  # Lưu tên file trong bundle
            else:
                mappings[str(photo_id)] = relative_original  # Lưu relative path từ source
            if ocr_service:
                # Check if hybrid OCR service
                if hasattr(ocr_service, 'detect_bib_numbers'):
                    # Hybrid OCR returns list of OCRResult
                    ocr_results = ocr_service.detect_bib_numbers(photo_path)
                    for result in ocr_results:
                        connection.execute(
                            "INSERT INTO ocr_candidates (photo_id, text, confidence, bbox, is_bib) VALUES (?, ?, ?, ?, ?)",
                            (photo_id, result["bib_number"], result["confidence"], json.dumps(result["bbox"]), 1),
                        )
                else:
                    # Legacy OCR service (Tesseract/PaddleOCR)
                    for candidate in ocr_service.extract_bib_candidates(photo_path):
                        connection.execute(
                            "INSERT INTO ocr_candidates (photo_id, text, confidence, bbox, is_bib) VALUES (?, ?, ?, ?, ?)",
                            (photo_id, candidate["text"], candidate["confidence"], candidate["bbox"], candidate["is_bib"]),
                        )
            if face_service:
                for face in face_service.detect_and_embed(photo_path):
                    vector_id = faiss_builder.add_embedding(face["embedding"])
                    connection.execute(
                        """
                        INSERT INTO faces (photo_id, bbox, confidence, faiss_vector_id, embedding_model, embedding_model_version)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (photo_id, face["bbox"], face["confidence"], vector_id, face["embedding_model"], face["embedding_model_version"]),
                    )
            connection.commit()
            print(f"Processed {index}/{len(photos)}: {photo_path.name}")
        faiss_builder.save(bundle_path / "faiss.index")
    finally:
        connection.close()

    (bundle_path / "originals_mapping.json").write_text(
        json.dumps({
            "base_path": str(source.resolve()) if not copy_originals else None,
            "mode": "embedded" if copy_originals else "mapping",
            "mappings": mappings
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    manifest = _build_manifest(
        bundle_path,
        event_slug,
        event_name,
        event_date,
        event_location,
        started,
        "disabled" if skip_ocr else (ocr_method if ocr_method != "skip" else "disabled"),
        "disabled" if skip_ocr else str(ocr_config.get("model_version", "v1")),
        "disabled" if skip_faces else "InsightFace",
        "disabled" if skip_faces else f"{face_model_name}/{face_model_version}",
        originals_dir=originals_dir,
    )
    write_manifest(bundle_path, manifest)
    print(f"Bundle exported: {bundle_path}")


def _bundle_can_resume_face_stage(bundle_path: Path) -> bool:
    try:
        manifest = load_manifest(bundle_path)
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        return False
    return manifest.processing.ocr_model == "PaddleOCR" and manifest.processing.face_model == "disabled"


def _run_isolated_full_processing(
    source: Path,
    event_slug: str,
    event_name: str,
    event_date: str,
    event_location: str | None,
    output: Path,
    force: bool,
    config_path: Path,
) -> None:
    _validate_event_slug(event_slug)
    bundle_path = output / event_slug
    should_run_ocr_stage = force or not _bundle_can_resume_face_stage(bundle_path)
    command = [
        sys.executable,
        "-m",
        "processing_cli",
        "process",
        "--source",
        str(source),
        "--event-slug",
        event_slug,
        "--event-name",
        event_name,
        "--event-date",
        event_date,
        "--output",
        str(output),
        "--config",
        str(config_path),
        "--skip-faces",
    ]
    if event_location:
        command.extend(["--event-location", event_location])
    if force:
        command.append("--force")
    if should_run_ocr_stage:
        subprocess.run(command, check=True)

    config = load_processing_config(config_path)
    face_config = _section(config, "face")
    face_model_name = str(face_config.get("model_name", "VGG-Face"))
    face_model_version = str(face_config.get("model_version", "v1"))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "processing_cli",
            "rebuild-embeddings",
            "--bundle",
            str(output / event_slug),
            "--model-version",
            face_model_version,
            "--model-name",
            face_model_name,
            "--config",
            str(config_path),
        ],
        check=True,
    )


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("process", help="Process JPG photos into an event bundle")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--event-slug", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--event-date", required=True)
    parser.add_argument("--event-location")
    parser.add_argument("--output", default=Path("dist/events"), type=Path)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=Path)
    parser.add_argument("--skip-ocr", action="store_true")
    parser.add_argument("--skip-faces", action="store_true")
    parser.add_argument("--ocr-method", choices=["hybrid", "paddle", "skip"], default="hybrid",
                       help="OCR method: hybrid (YOLO+Tesseract, fast), paddle (PaddleOCR, accurate), skip (no OCR)")
    parser.add_argument("--copy-originals", action="store_true", default=True,
                       help="Copy ảnh gốc vào bundle (default: True)")
    parser.add_argument("--no-copy-originals", dest="copy_originals", action="store_false",
                       help="Không copy ảnh gốc, chỉ lưu mapping")
    parser.add_argument("--force", action="store_true")
    parser.set_defaults(
        handler=lambda args: run(
            args.source,
            args.event_slug,
            args.event_name,
            args.event_date,
            args.event_location,
            args.output,
            args.skip_ocr,
            args.skip_faces,
            args.force,
            args.config,
            False,  # isolate_ai_stages removed from CLI
            args.ocr_method,
            args.copy_originals,
        )
    )
