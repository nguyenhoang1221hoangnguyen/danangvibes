from __future__ import annotations

import tempfile
import json
from pathlib import Path

from processing_cli.services.face import FaceDetection
from web_server.config import settings
from web_server.services.event_loader import EventBundle


class SearchService:
    def __init__(self, bundle: EventBundle) -> None:
        self.bundle = bundle

    def _face_model_pair(self) -> tuple[str, str] | str:
        connection = self.bundle.get_connection()
        try:
            rows = connection.execute(
                """
                SELECT DISTINCT embedding_model, embedding_model_version
                FROM faces
                WHERE embedding_model IS NOT NULL AND embedding_model_version IS NOT NULL
                """
            ).fetchall()
        finally:
            connection.close()
        pairs = [(str(row["embedding_model"]), str(row["embedding_model_version"])) for row in rows]
        if not pairs:
            return "Event này chưa có face embeddings."
        if len(pairs) > 1:
            return "Face embeddings đang trộn nhiều model/version. Hãy rebuild embeddings trước khi search."
        return pairs[0]

    def _best_face(self, faces: list[FaceDetection]) -> FaceDetection | None:
        if not faces:
            return None

        def score(face: FaceDetection) -> tuple[float, float]:
            try:
                bbox = json.loads(face["bbox"])
                area = float(bbox[2]) * float(bbox[3]) if isinstance(bbox, list) and len(bbox) >= 4 else 0.0
            except (TypeError, ValueError, json.JSONDecodeError):
                area = 0.0
            return float(face["confidence"]), area

        return max(faces, key=score)

    def search_by_bib(self, bib_number: str) -> dict[str, object]:
        query = "".join(character for character in bib_number if character.isdigit())
        connection = self.bundle.get_connection()
        try:
            rows = connection.execute(
                """
                SELECT DISTINCT p.id, p.capture_time
                FROM photos p
                JOIN ocr_candidates o ON o.photo_id = p.id
                WHERE o.is_bib = 1 AND (o.text = ? OR o.manual_correction = ?)
                ORDER BY p.capture_time, p.id
                LIMIT 100
                """,
                (query, query),
            ).fetchall()
        finally:
            connection.close()
        matches = [
            {
                "photo_id": int(row["id"]),
                "thumbnail_url": f"/events/{self.bundle.slug}/photos/{int(row['id'])}/thumbnail",
                "capture_time": row["capture_time"],
            }
            for row in rows
        ]
        return {"bib_matches": matches, "face_matches": [], "suggested": [], "total_results": len(matches)}

    def search_by_face(self, image_bytes: bytes) -> dict[str, object]:
        index = self.bundle.load_faiss_index()
        if index is None:
            return {"bib_matches": [], "face_matches": [], "suggested": [], "total_results": 0, "message": "Event này chưa có face index."}

        model_pair = self._face_model_pair()
        if isinstance(model_pair, str):
            return {"bib_matches": [], "face_matches": [], "suggested": [], "total_results": 0, "message": model_pair}
        stored_model_name, stored_model_version = model_pair
        try:
            import numpy as np
            from processing_cli.services.face_insightface import InsightFaceService
        except ImportError as exc:
            raise RuntimeError("Install InsightFace, numpy, and faiss-cpu to enable face search") from exc

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(image_bytes)
            temp_path = Path(temp_file.name)
        try:
            faces = InsightFaceService(model_name=stored_model_name, model_version=stored_model_version).detect_and_embed(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
        face = self._best_face(faces)
        if not face:
            return {"bib_matches": [], "face_matches": [], "suggested": [], "total_results": 0, "message": "Không tìm thấy khuôn mặt rõ trong selfie."}

        query = np.array([face["embedding"]], dtype="float32")
        index_dimension = getattr(index, "d", None)
        if index_dimension is not None and int(index_dimension) != int(query.shape[1]):
            return {"bib_matches": [], "face_matches": [], "suggested": [], "total_results": 0, "message": "Face index không khớp dimension với model hiện tại. Hãy rebuild embeddings."}
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError("Install faiss-cpu to enable face search") from exc
        faiss.normalize_L2(query)
        distances, indices = index.search(query, settings.face_top_k)

        connection = self.bundle.get_connection()
        try:
            matches: list[dict[str, object]] = []
            seen_photo_ids: set[int] = set()
            for vector_id, distance in zip(indices[0], distances[0]):
                if int(vector_id) < 0:
                    continue
                # FAISS returns L2 distance after normalize_L2
                # Convert to similarity: similarity = 1 - (distance^2 / 2)
                # For normalized vectors: distance^2 = 2(1 - cosine_similarity)
                # So: cosine_similarity = 1 - (distance^2 / 2)
                similarity = 1.0 - (float(distance) ** 2 / 2.0)

                # Filter by similarity threshold (higher is better)
                if similarity < settings.face_similarity_threshold:
                    continue

                row = connection.execute(
                    """
                    SELECT p.id, p.capture_time
                    FROM faces f
                    JOIN photos p ON p.id = f.photo_id
                    WHERE f.faiss_vector_id = ?
                    LIMIT 1
                    """,
                    (int(vector_id),),
                ).fetchone()
                if not row:
                    continue
                photo_id = int(row["id"])
                if photo_id in seen_photo_ids:
                    continue
                seen_photo_ids.add(photo_id)
                matches.append(
                    {
                        "photo_id": photo_id,
                        "thumbnail_url": f"/events/{self.bundle.slug}/photos/{photo_id}/thumbnail",
                        "capture_time": row["capture_time"],
                        "similarity_score": round(similarity, 3),
                    }
                )
        finally:
            connection.close()
        return {"bib_matches": [], "face_matches": matches, "suggested": [], "total_results": len(matches)}
