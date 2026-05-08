from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class FaceDetection(TypedDict):
    bbox: str
    confidence: float
    faiss_vector_id: int | None
    embedding_model: str
    embedding_model_version: str
    embedding: list[float]


def load_deepface_class():
    try:
        from deepface import DeepFace
    except ValueError as exc:
        if "tf-keras" in str(exc):
            raise RuntimeError(
                "Install tf-keras to enable DeepFace: scripts/start-processing-app.sh installs it from requirements-ai.txt"
            ) from exc
        raise
    except ImportError as exc:
        raise RuntimeError("Install DeepFace to enable face embeddings: scripts/start-processing-app.sh") from exc
    return DeepFace


class FaceService:
    def __init__(self, model_name: str = "VGG-Face", model_version: str = "v1") -> None:
        self._deepface = load_deepface_class()
        self.model_name = model_name
        self.model_version = model_version

    def detect_and_embed(self, image_path: Path) -> list[FaceDetection]:
        import json
        import tempfile
        import shutil

        # DeepFace has bug with non-ASCII paths - copy to temp file if needed
        img_path_str = str(image_path)
        temp_file = None

        try:
            # Check if path contains non-ASCII characters
            img_path_str.encode('ascii')
            use_path = img_path_str
        except UnicodeEncodeError:
            # Path has non-ASCII chars - copy to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix=image_path.suffix, delete=False)
            temp_file.close()
            shutil.copy2(image_path, temp_file.name)
            use_path = temp_file.name

        try:
            rows = self._deepface.represent(
                img_path=use_path,
                model_name=self.model_name,
                enforce_detection=False,
            )
        finally:
            # Clean up temp file
            if temp_file:
                try:
                    Path(temp_file.name).unlink()
                except Exception:
                    pass

        faces: list[FaceDetection] = []
        for row in rows:
            area = row.get("facial_area") or {}
            bbox = [area.get("x", 0), area.get("y", 0), area.get("w", 0), area.get("h", 0)]
            faces.append(
                {
                    "bbox": json.dumps(bbox),
                    "confidence": float(row.get("face_confidence") or 0.0),
                    "faiss_vector_id": None,
                    "embedding_model": self.model_name,
                    "embedding_model_version": self.model_version,
                    "embedding": [float(value) for value in row["embedding"]],
                }
            )
        return faces
