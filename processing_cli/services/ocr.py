from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TypedDict


class OCRCandidate(TypedDict):
    text: str
    confidence: float
    bbox: str
    is_bib: int


def _ensure_supported_paddleocr() -> None:
    try:
        installed_version = version("paddleocr")
    except PackageNotFoundError:
        return
    major_version = installed_version.split(".", 1)[0]
    if major_version.isdigit() and int(major_version) >= 3:
        raise RuntimeError(
            f"PaddleOCR {installed_version} is not supported yet. Recreate the AI env: rm -rf venv-ai && scripts/start-processing-app.sh"
        )


def load_paddleocr_class():
    _ensure_supported_paddleocr()
    try:
        from paddleocr import PaddleOCR
    except ModuleNotFoundError as exc:
        if exc.name == "paddle":
            raise RuntimeError(
                "Install PaddlePaddle to enable OCR: scripts/start-processing-app.sh installs it from requirements-ai.txt"
            ) from exc
        raise RuntimeError("Install PaddleOCR to enable OCR: scripts/start-processing-app.sh") from exc
    except ImportError as exc:
        raise RuntimeError("Install PaddleOCR to enable OCR: scripts/start-processing-app.sh") from exc
    return PaddleOCR


def load_tesseract_service():
    """Load Tesseract OCR service - much faster than PaddleOCR"""
    try:
        from processing_cli.services.ocr_tesseract import TesseractOCRService
        return TesseractOCRService
    except ImportError as exc:
        raise RuntimeError(
            "Install pytesseract: pip install pytesseract\n"
            "Also install Tesseract binary: brew install tesseract"
        ) from exc


class OCRService:
    def __init__(self, confidence_threshold: float = 0.6) -> None:
        # use_gpu=False: force CPU, det_db_box_thresh=0.5: faster detection
        # use_angle_cls=False: skip angle classification for speed
        self._ocr = load_paddleocr_class()(
            use_angle_cls=False,
            lang="en",
            show_log=False,
            use_gpu=False,
            det_db_box_thresh=0.5,
            max_batch_size=1
        )
        self.confidence_threshold = confidence_threshold

    def extract_bib_candidates(self, image_path: Path) -> list[OCRCandidate]:
        # Resize ảnh trước khi OCR để tăng tốc
        from PIL import Image
        import numpy as np

        img: Image.Image = Image.open(image_path)
        # Resize về max 1280px (giữ aspect ratio)
        max_size = 1280
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert PIL Image sang numpy array cho PaddleOCR
        img_array = np.array(img)
        result = self._ocr.ocr(img_array, cls=False)
        candidates: list[OCRCandidate] = []
        if not result or not result[0]:
            return candidates
        for line in result[0]:
            bbox, payload = line
            text, confidence = payload
            if float(confidence) < self.confidence_threshold:
                continue
            digits = re.sub(r"\D", "", str(text))
            if 2 <= len(digits) <= 5:
                import json

                candidates.append(
                    {"text": digits, "confidence": float(confidence), "bbox": json.dumps(bbox), "is_bib": 1}
                )
        return candidates
