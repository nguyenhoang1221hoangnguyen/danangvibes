from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from web_server.paths import QR_UPLOAD_DIR
from web_server.server_database import connect_server_database
from web_server.services.event_loader import EventLoader


class AdminService:
    def __init__(self, event_loader: EventLoader) -> None:
        self.event_loader = event_loader

    def list_events(self) -> list[dict[str, object]]:
        connection = connect_server_database(self.event_loader.server_db_path)
        try:
            rows = connection.execute(
                """
                SELECT
                  e.slug,
                  e.name,
                  e.active_version,
                  e.is_published,
                  e.storage_path,
                  e.updated_at,
                  COUNT(d.id) AS download_count,
                  COUNT(DISTINCT d.photo_id) AS unique_downloaded_photos,
                  MAX(d.downloaded_at) AS last_downloaded_at
                FROM server_events e
                LEFT JOIN download_logs d ON d.event_slug = e.slug
                GROUP BY e.id
                ORDER BY e.created_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def set_published(self, event_slug: str, is_published: bool) -> None:
        if is_published:
            self.event_loader.reload_event(event_slug)
        connection = connect_server_database(self.event_loader.server_db_path)
        try:
            cursor = connection.execute(
                "UPDATE server_events SET is_published = ?, updated_at = ? WHERE slug = ?",
                (1 if is_published else 0, datetime.utcnow().isoformat(), event_slug),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Event not found")
            connection.commit()
        finally:
            connection.close()
        if not is_published:
            self.event_loader.unload_event(event_slug)

    def low_confidence_ocr(self, event_slug: str, threshold: float) -> list[dict[str, object]]:
        bundle = self.event_loader.get_event(event_slug)
        if not bundle:
            return []
        connection = bundle.get_connection(readonly=False)
        try:
            rows = connection.execute(
                """
                SELECT o.id, o.photo_id, o.text, o.confidence, o.manual_correction
                FROM ocr_candidates o
                WHERE o.is_bib = 1 AND COALESCE(o.confidence, 0) < ?
                ORDER BY o.confidence ASC
                LIMIT 100
                """,
                (threshold,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def correct_ocr(self, event_slug: str, candidate_id: int, corrected_text: str) -> None:
        bundle = self.event_loader.get_event(event_slug)
        if not bundle:
            raise FileNotFoundError(f"Event not loaded: {event_slug}")
        connection = bundle.get_connection(readonly=False)
        try:
            connection.execute(
                "UPDATE ocr_candidates SET manual_correction = ?, corrected_at = ? WHERE id = ?",
                (corrected_text, datetime.utcnow().isoformat(), candidate_id),
            )
            connection.commit()
        finally:
            connection.close()

    def save_donation_message(self, event_slug: str, message: str) -> None:
        connection = connect_server_database(self.event_loader.server_db_path)
        try:
            connection.execute(
                """
                INSERT INTO donation_config (event_slug, message, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(event_slug) DO UPDATE SET message = excluded.message, updated_at = excluded.updated_at
                """,
                (event_slug, message, datetime.utcnow().isoformat()),
            )
            connection.commit()
        finally:
            connection.close()

    def save_qr_file(self, event_slug: str, filename: str, content: bytes) -> Path:
        if len(content) > 2 * 1024 * 1024:
            raise ValueError("QR image must be smaller than 2MB")
        extension = Path(filename).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("QR image must be JPG or PNG")
        if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise ValueError("QR image content is not a valid JPEG")
        if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("QR image content is not a valid PNG")
        QR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        target = QR_UPLOAD_DIR / f"{event_slug}-qr{extension}"
        target.write_bytes(content)
        connection = connect_server_database(self.event_loader.server_db_path)
        try:
            connection.execute(
                """
                INSERT INTO donation_config (event_slug, qr_code_path, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(event_slug) DO UPDATE SET qr_code_path = excluded.qr_code_path, updated_at = excluded.updated_at
                """,
                (event_slug, str(target), datetime.utcnow().isoformat()),
            )
            connection.commit()
        finally:
            connection.close()
        return target
