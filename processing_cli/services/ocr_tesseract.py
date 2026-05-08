from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict


class OCRCandidate(TypedDict):
    text: str
    confidence: float
    bbox: str
    is_bib: int


class TesseractOCRService:
    """Lightweight OCR using Tesseract - much faster than PaddleOCR"""

    def __init__(self, confidence_threshold: float = 0.6) -> None:
        try:
            import pytesseract
        except ImportError as exc:
            raise RuntimeError(
                "Install pytesseract: pip install pytesseract\n"
                "Also install Tesseract binary: brew install tesseract"
            ) from exc
        self._pytesseract = pytesseract
        self.confidence_threshold = confidence_threshold

    def extract_bib_candidates(self, image_path: Path) -> list[OCRCandidate]:
        from PIL import Image, ImageEnhance
        import json

        img: Image.Image = Image.open(image_path)

        # Resize về max 1600px
        max_size = 1600
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Enhance contrast để text rõ hơn
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Convert to grayscale
        img = img.convert('L')

        # Try multiple PSM modes for better detection
        psm_modes = [6, 11, 3]  # 6=uniform block, 11=sparse text, 3=auto
        all_candidates: list[OCRCandidate] = []

        for psm in psm_modes:
            custom_config = f'--psm {psm} --oem 3'

            try:
                data = self._pytesseract.image_to_data(
                    img,
                    config=custom_config,
                    output_type=self._pytesseract.Output.DICT
                )

                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = float(data['conf'][i])

                    if not text or conf < 0:
                        continue

                    normalized_conf = conf / 100.0

                    if normalized_conf < self.confidence_threshold:
                        continue

                    # Extract digits
                    digits = re.sub(r"\D", "", text)

                    # Accept 2-5 digit numbers
                    if 2 <= len(digits) <= 5:
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

                        # Deduplicate by text
                        if not any(c['text'] == digits for c in all_candidates):
                            all_candidates.append({
                                "text": digits,
                                "confidence": normalized_conf,
                                "bbox": json.dumps(bbox),
                                "is_bib": 1
                            })
            except Exception:
                continue

        return all_candidates
