from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import tempfile
import shutil
import json


class FaceDetection(TypedDict):
    bbox: str
    confidence: float
    faiss_vector_id: int | None
    embedding_model: str
    embedding_model_version: str
    embedding: list[float]


def load_face_recognition():
    try:
        import face_recognition
    except ImportError as exc:
        raise RuntimeError(
            "Install face_recognition: pip install face_recognition"
        ) from exc
    return face_recognition


class FaceRecognitionService:
    """
    face_recognition service - simple and effective for race photos.

    Advantages:
    - Very easy to install and use
    - Good accuracy (85-90%)
    - Handles occlusions reasonably well
    - Fast enough for production
    - Large community support
    """

    def __init__(self, model_name: str = "hog", model_version: str = "v1") -> None:
        """
        Args:
            model_name: "hog" (faster, CPU) or "cnn" (more accurate, needs GPU)
        """
        self.face_recognition = load_face_recognition()
        self.model_name = model_name  # "hog" or "cnn"
        self.model_version = model_version

    def detect_and_embed(self, image_path: Path) -> list[FaceDetection]:
        import numpy as np

        # Handle non-ASCII paths
        img_path_str = str(image_path)
        temp_file = None

        try:
            img_path_str.encode('ascii')
            use_path = img_path_str
        except UnicodeEncodeError:
            temp_file = tempfile.NamedTemporaryFile(suffix=image_path.suffix, delete=False)
            temp_file.close()
            shutil.copy2(image_path, temp_file.name)
            use_path = temp_file.name

        try:
            # Load image
            image = self.face_recognition.load_image_file(use_path)

            # Detect face locations
            # model can be "hog" (faster) or "cnn" (more accurate)
            face_locations = self.face_recognition.face_locations(
                image,
                model=self.model_name,
                number_of_times_to_upsample=1  # 1 is good balance
            )

            if not face_locations:
                return []

            # Get face encodings (128-dim embeddings)
            face_encodings = self.face_recognition.face_encodings(
                image,
                known_face_locations=face_locations,
                num_jitters=1  # 1 is faster, 10 is more accurate
            )

            faces: list[FaceDetection] = []
            for location, encoding in zip(face_locations, face_encodings):
                # face_locations returns (top, right, bottom, left)
                top, right, bottom, left = location

                # Convert to [x, y, w, h] format
                x = left
                y = top
                w = right - left
                h = bottom - top

                # face_recognition doesn't provide confidence scores
                # Use face size as proxy (larger faces = more confident)
                area = w * h
                confidence = min(0.99, 0.5 + (area / 100000))  # Heuristic

                faces.append({
                    "bbox": json.dumps([x, y, w, h]),
                    "confidence": confidence,
                    "faiss_vector_id": None,
                    "embedding_model": f"face_recognition_{self.model_name}",
                    "embedding_model_version": self.model_version,
                    "embedding": encoding.tolist(),
                })

            return faces

        finally:
            if temp_file:
                try:
                    Path(temp_file.name).unlink()
                except Exception:
                    pass
