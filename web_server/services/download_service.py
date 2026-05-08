from __future__ import annotations

from web_server.server_database import connect_server_database
from web_server.services.event_loader import EventBundle


class DownloadService:
    def __init__(self, bundle: EventBundle, server_db_path) -> None:
        self.bundle = bundle
        self.server_db_path = server_db_path

    def track_download(self, photo_id: int, ip_address: str | None, user_agent: str | None) -> None:
        connection = connect_server_database(self.server_db_path)
        try:
            connection.execute(
                "INSERT INTO download_logs (event_slug, photo_id, ip_address, user_agent) VALUES (?, ?, ?, ?)",
                (self.bundle.slug, photo_id, ip_address, user_agent),
            )
            connection.commit()
        finally:
            connection.close()
