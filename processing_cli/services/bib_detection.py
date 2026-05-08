from __future__ import annotations

from pathlib import Path
from typing import TypedDict
import tempfile
import shutil


class BibDetection(TypedDict):
    bbox: list[int]  # [x, y, w, h]
    confidence: float
    class_name: str


def load_yolo_class():
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "Install ultralytics to enable YOLO: pip install ultralytics"
        ) from exc
    return YOLO


class BibDetectionService:
    """
    YOLO-based bib number detection service.
    Detects rectangular regions likely to contain bib numbers.
    """

    def __init__(self, model_name: str = "yolov8n.pt") -> None:
        """
        Initialize YOLO model for bib detection.

        Args:
            model_name: YOLO model to use (yolov8n.pt = nano, fastest)
        """
        YOLO = load_yolo_class()
        self.model = YOLO(model_name)
        self.model_name = model_name

    def detect_bib_regions(self, image_path: Path) -> list[BibDetection]:
        """
        Detect bib regions in race photo.

        Strategy:
        1. Run YOLO object detection
        2. Filter for person detections
        3. Extract torso region (likely bib location)
        4. Return bounding boxes for OCR cropping

        Args:
            image_path: Path to race photo

        Returns:
            List of bib detections with bbox and confidence
        """
        # Handle non-ASCII paths (same as face detection)
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
            # Run YOLO detection
            results = self.model(use_path, verbose=False)

            detections: list[BibDetection] = []

            # Process results
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get class name
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    confidence = float(box.conf[0])

                    # Filter for person detections (class 0 in COCO)
                    # Bibs are on people, so we detect people first
                    if class_name == "person" and confidence > 0.3:
                        # Get bounding box in xyxy format
                        xyxy = box.xyxy[0].tolist()
                        x1, y1, x2, y2 = map(int, xyxy)

                        # Convert to xywh format
                        x = x1
                        y = y1
                        w = x2 - x1
                        h = y2 - y1

                        # Extract torso region (middle 40% of person height)
                        # Bibs are typically on chest/torso
                        torso_y_start = y + int(h * 0.2)  # Start 20% down
                        torso_y_end = y + int(h * 0.6)    # End 60% down
                        torso_h = torso_y_end - torso_y_start

                        # Keep full width, focus on torso height
                        detections.append({
                            "bbox": [x, torso_y_start, w, torso_h],
                            "confidence": confidence,
                            "class_name": "bib_region"
                        })

            return detections

        finally:
            # Clean up temp file
            if temp_file:
                try:
                    Path(temp_file.name).unlink()
                except Exception:
                    pass
