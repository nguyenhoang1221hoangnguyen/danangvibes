from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Literal

OriginalsMode = Literal["included", "mapping"]
OCRModel = Literal["hybrid", "paddle", "disabled"]
FaceModel = Literal["InsightFace", "disabled"]


@dataclass(frozen=True)
class EventMetadata:
    slug: str
    name: str
    date: str
    location: str | None
    created_at: str


@dataclass(frozen=True)
class ProcessingMetadata:
    app_version: str
    ocr_model: str  # Type: OCRModel ("hybrid", "paddle", "disabled")
    ocr_model_version: str
    face_model: str  # Type: FaceModel ("InsightFace", "disabled")
    face_model_version: str
    processed_at: str
    processing_machine: str
    processing_duration_seconds: int


@dataclass(frozen=True)
class BundleStats:
    total_photos: int
    photos_with_bib_candidates: int
    photos_with_faces: int
    total_faces_detected: int
    total_bib_candidates: int
    total_thumbnails: int


@dataclass(frozen=True)
class BundleFiles:
    database: str
    faiss_index: str
    thumbnails_dir: str
    originals_mode: OriginalsMode
    originals_mapping: str | None


@dataclass(frozen=True)
class BundleManifest:
    bundle_version: str
    event: EventMetadata
    processing: ProcessingMetadata
    stats: BundleStats
    files: BundleFiles
    checksums: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BundleManifest":
        return cls(
            bundle_version=str(data["bundle_version"]),
            event=EventMetadata(**data["event"]),
            processing=ProcessingMetadata(**data["processing"]),
            stats=BundleStats(**data["stats"]),
            files=BundleFiles(**data["files"]),
            checksums=dict(data.get("checksums", {})),
        )


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()
