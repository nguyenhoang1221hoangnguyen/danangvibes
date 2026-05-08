from __future__ import annotations

import argparse
import json
import platform
import shutil
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from processing_cli.commands.process import DEFAULT_CONFIG_PATH, _build_manifest, _section, load_processing_config
from processing_cli.services.face_insightface import InsightFaceService
from processing_cli.services.faiss_builder import FaissBuilder
from shared.bundle import load_manifest, validate_bundle, write_manifest
from shared.database import connect_database
from shared.models import utc_now_iso


def _original_paths(bundle: Path) -> dict[int, Path]:
    manifest = load_manifest(bundle)
    if not manifest.files.originals_mapping:
        raise FileNotFoundError("Missing originals mapping in manifest")
    mapping = json.loads((bundle / manifest.files.originals_mapping).read_text(encoding="utf-8"))

    if manifest.files.originals_mode == "embedded":
        base_path = (bundle / "originals").resolve()
    else:
        base_path = Path(str(mapping.get("base_path", ""))).resolve()

    raw_mappings = mapping.get("mappings", {})
    if not isinstance(raw_mappings, dict):
        raise ValueError("Invalid originals_mapping.json")

    paths: dict[int, Path] = {}
    for photo_id_str, relative_str in raw_mappings.items():
        photo_id = int(photo_id_str)
        relative = Path(str(relative_str))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe original path for photo {photo_id}")
        candidate = (base_path / relative).resolve()
        if base_path != candidate and base_path not in candidate.parents:
            raise ValueError(f"Unsafe original path for photo {photo_id}")
        if not candidate.exists():
            raise FileNotFoundError(f"Original photo not found for photo {photo_id}: {candidate}")
        paths[photo_id] = candidate
    return paths


def run(bundle: Path, model_version: str, model_name: str | None = None, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    started = time.time()
    validate_bundle(bundle)
    config = load_processing_config(config_path)
    face_config = _section(config, "face")
    face_model_name = model_name or str(face_config.get("model_name", "VGG-Face"))
    face_service = InsightFaceService(model_name=face_model_name, model_version=model_version)
    faiss_builder = FaissBuilder()
    paths = _original_paths(bundle)
    manifest = load_manifest(bundle)
    db_path = bundle / manifest.files.database
    with tempfile.TemporaryDirectory(dir=bundle.parent) as tmpdir:
        staged_db_path = Path(tmpdir) / manifest.files.database
        staged_faiss_path = Path(tmpdir) / manifest.files.faiss_index
        shutil.copy2(db_path, staged_db_path)

        connection = connect_database(staged_db_path)
        try:
            connection.execute("DELETE FROM faces")
            for photo_id, photo_path in paths.items():
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
        finally:
            connection.close()

        faiss_builder.save(staged_faiss_path)
        shutil.move(str(staged_db_path), db_path)
        shutil.move(str(staged_faiss_path), bundle / manifest.files.faiss_index)
    originals_dir = (bundle / "originals") if manifest.files.originals_mode == "embedded" else None
    updated_manifest = _build_manifest(
        bundle,
        manifest.event.slug,
        manifest.event.name,
        manifest.event.date,
        manifest.event.location,
        started,
        manifest.processing.ocr_model,
        manifest.processing.ocr_model_version,
        "InsightFace",
        f"{face_model_name}/{model_version}",
        originals_dir=originals_dir,
    )
    updated_manifest = replace(
        updated_manifest,
        event=replace(updated_manifest.event, created_at=manifest.event.created_at),
        processing=replace(
            updated_manifest.processing,
            app_version=manifest.processing.app_version,
            processed_at=utc_now_iso(),
            processing_machine=platform.node() or platform.machine(),
        ),
    )
    write_manifest(bundle, updated_manifest)
    print(f"Embeddings rebuilt: {bundle}")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("rebuild-embeddings", help="Rebuild InsightFace embeddings for a bundle")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--model-name")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=Path)
    parser.set_defaults(handler=lambda args: run(args.bundle, args.model_version, args.model_name, args.config))
