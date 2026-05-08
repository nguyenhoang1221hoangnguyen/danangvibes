from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import tempfile
import shutil


class TextDetection(TypedDict):
    bbox: list[int]  # [x, y, w, h]
    confidence: float


def load_yolo_class():
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "Install ultralytics to enable YOLO: pip install ultralytics"
        ) from exc
    return YOLO


class TextDetectionService:
    """
    YOLO-based text region detection for bib numbers.

    Strategy: Detect ALL text regions in image, filter by size/position
    to find likely bib numbers.
    """

    def __init__(self, model_name: str = "yolov8n.pt") -> None:
        YOLO = load_yolo_class()
        self.model = YOLO(model_name)
        self.model_name = model_name

    def detect_text_regions(self, image_path: Path, confidence: float = 0.2) -> list[TextDetection]:
        """
        Detect text regions that could be bib numbers.

        Uses generic object detection to find rectangular regions,
        then filters by size and aspect ratio typical of bib numbers.

        Args:
            image_path: Path to the photo
            confidence: YOLO detection confidence threshold (0.0-1.0)
        """
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
            results = self.model(use_path, verbose=False, conf=confidence)

            detections: list[TextDetection] = []

            for result in results:
                boxes = result.boxes
                img_height, img_width = result.orig_shape

                for box in boxes:
                    confidence = float(box.conf[0])

                    # Get bounding box
                    xyxy = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = map(int, xyxy)

                    x = x1
                    y = y1
                    w = x2 - x1
                    h = y2 - y1

                    # Filter by size and aspect ratio
                    # Bib numbers are typically:
                    # - Width: 50-300px (at 1280px image width)
                    # - Height: 50-200px
                    # - Aspect ratio: 0.5-3.0 (roughly square to rectangular)

                    # Scale thresholds based on image size
                    min_size = int(img_width * 0.02)  # 2% of image width
                    max_size = int(img_width * 0.3)   # 30% of image width

                    if w < min_size or h < min_size:
                        continue  # Too small

                    if w > max_size or h > max_size:
                        continue  # Too large

                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio < 0.3 or aspect_ratio > 4.0:
                        continue  # Wrong shape

                    # Add some padding around detection
                    padding = int(min(w, h) * 0.1)
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(img_width - x, w + 2 * padding)
                    h = min(img_height - y, h + 2 * padding)

                    detections.append({
                        "bbox": [x, y, w, h],
                        "confidence": confidence
                    })

            # Sort by confidence
            detections.sort(key=lambda d: d['confidence'], reverse=True)

            # Return top 10 candidates
            return detections[:10]

        finally:
            if temp_file:
                try:
                    Path(temp_file.name).unlink()
                except Exception:
                    pass
