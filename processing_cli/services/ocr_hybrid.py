from __future__ import annotations

from pathlib import Path
from typing import TypedDict, Literal
import re
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import logging

from processing_cli.services.text_detection import TextDetectionService

logger = logging.getLogger(__name__)


class OCRResult(TypedDict):
    text: str
    confidence: float
    bbox: list[int]  # Original bbox from YOLO
    bib_number: str | None  # Extracted 2-5 digit number
    method: Literal["yolo_tesseract", "fallback_tesseract", "fallback_paddle"]  # Detection method used


def load_tesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "Install pytesseract to enable Tesseract OCR: pip install pytesseract"
        ) from exc
    return pytesseract


class HybridOCRService:
    """
    Hybrid OCR service combining YOLO text detection + Tesseract OCR.

    Pipeline:
    1. YOLO detects text regions (potential bibs)
    2. Crop image to each detected region
    3. Preprocess crop for OCR
    4. Tesseract OCR on preprocessed crop
    5. Extract and validate bib numbers
    6. Fallback to full-image OCR if no results

    Fallback strategy:
    - Primary: YOLO + Tesseract (fast)
    - Fallback 1: Lower YOLO confidence threshold
    - Fallback 2: Full-image Tesseract
    - Fallback 3: PaddleOCR (if available)
    """

    def __init__(self, enable_paddle_fallback: bool = False) -> None:
        self.text_detector = TextDetectionService(model_name="yolov8n.pt")
        self.pytesseract = load_tesseract()
        self.enable_paddle_fallback = enable_paddle_fallback
        self._paddle_ocr = None

    def preprocess_for_ocr(self, crop: Image.Image) -> Image.Image:
        """
        Preprocess cropped image for optimal Tesseract OCR.

        Steps:
        1. Convert to grayscale
        2. Enhance contrast (CLAHE)
        3. Denoise
        4. Sharpen (for motion blur)
        """
        # Convert to grayscale
        if crop.mode != 'L':
            crop = crop.convert('L')

        # Convert to numpy for OpenCV processing
        img_array = np.array(crop)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_array = clahe.apply(img_array)

        # Denoise
        img_array = cv2.fastNlMeansDenoising(img_array, h=10)

        # Sharpen
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        img_array = cv2.filter2D(img_array, -1, kernel)

        # Convert back to PIL
        crop = Image.fromarray(img_array)

        # Additional PIL enhancements
        enhancer = ImageEnhance.Contrast(crop)
        crop = enhancer.enhance(1.5)

        return crop

    def extract_bib_number(self, text: str) -> str | None:
        """
        Extract bib number (2-5 digits) from OCR text.

        Args:
            text: Raw OCR text

        Returns:
            Bib number string or None if not found
        """
        # Remove whitespace and non-digit characters
        cleaned = re.sub(r'[^\d]', '', text)

        # Find 2-5 digit sequences
        matches = re.findall(r'\d{2,5}', cleaned)

        if matches:
            # Return longest match (most likely to be bib number)
            return max(matches, key=len)

        return None

    def _ocr_with_tesseract(self, crop: Image.Image, bbox: list[int]) -> OCRResult | None:
        """Run Tesseract OCR on a cropped region."""
        processed_crop = self.preprocess_for_ocr(crop)
        custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789'

        try:
            ocr_data = self.pytesseract.image_to_data(
                processed_crop,
                config=custom_config,
                output_type=self.pytesseract.Output.DICT
            )

            texts = []
            confidences = []
            for i, conf in enumerate(ocr_data['conf']):
                if conf > 0:
                    text = ocr_data['text'][i]
                    if text.strip():
                        texts.append(text)
                        confidences.append(float(conf))

            if texts:
                full_text = ''.join(texts)
                avg_confidence = sum(confidences) / len(confidences) / 100.0
                bib_number = self.extract_bib_number(full_text)

                if bib_number:
                    return {
                        'text': full_text,
                        'confidence': avg_confidence,
                        'bbox': bbox,
                        'bib_number': bib_number,
                        'method': 'yolo_tesseract'
                    }
        except Exception as e:
            logger.debug(f"Tesseract OCR failed: {e}")

        return None

    def _fallback_full_image_tesseract(self, image_path: Path) -> list[OCRResult]:
        """Fallback: Run Tesseract on full image."""
        logger.info("Fallback: Running Tesseract on full image")

        try:
            img = Image.open(image_path)
            # Resize to reasonable size
            max_dim = 1280
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            processed = self.preprocess_for_ocr(img)
            custom_config = r'--psm 6 -c tessedit_char_whitelist=0123456789'

            ocr_data = self.pytesseract.image_to_data(
                processed,
                config=custom_config,
                output_type=self.pytesseract.Output.DICT
            )

            results = []
            for i, text in enumerate(ocr_data['text']):
                if text.strip() and ocr_data['conf'][i] > 50:
                    bib_number = self.extract_bib_number(text)
                    if bib_number:
                        x, y, w, h = (ocr_data['left'][i], ocr_data['top'][i],
                                     ocr_data['width'][i], ocr_data['height'][i])
                        results.append({
                            'text': text,
                            'confidence': float(ocr_data['conf'][i]) / 100.0,
                            'bbox': [x, y, w, h],
                            'bib_number': bib_number,
                            'method': 'fallback_tesseract'
                        })

            return results

        except Exception as e:
            logger.error(f"Full-image Tesseract failed: {e}")
            return []

    def detect_bib_numbers(self, image_path: Path) -> list[OCRResult]:
        """
        Detect and OCR bib numbers from race photo with fallback logic.

        Pipeline:
        1. Primary: YOLO text detection + Tesseract OCR
        2. Fallback 1: Lower YOLO confidence threshold
        3. Fallback 2: Full-image Tesseract
        4. Fallback 3: PaddleOCR (if enabled)

        Args:
            image_path: Path to race photo

        Returns:
            List of OCR results with bib numbers
        """
        # Primary: YOLO + Tesseract
        logger.debug(f"Processing {image_path.name} with YOLO + Tesseract")
        detections = self.text_detector.detect_text_regions(image_path)

        if detections:
            img = Image.open(image_path)
            results: list[OCRResult] = []

            for detection in detections:
                bbox = detection['bbox']
                x, y, w, h = bbox
                crop = img.crop((x, y, x + w, y + h))

                result = self._ocr_with_tesseract(crop, bbox)
                if result:
                    results.append(result)

            # Filter by confidence
            results = [r for r in results if r['confidence'] > 0.3]
            results.sort(key=lambda r: r['confidence'], reverse=True)

            if results:
                logger.info(f"Primary method found {len(results)} bib numbers")
                return results

        # Fallback 1: Try with lower YOLO confidence
        logger.info("Fallback 1: Trying lower YOLO confidence (0.1)")
        detections_low = self.text_detector.detect_text_regions(image_path, confidence=0.1)
        if detections_low:
            img = Image.open(image_path)
            results_low: list[OCRResult] = []
            for detection in detections_low:
                bbox = detection['bbox']
                x, y, w, h = bbox
                crop = img.crop((x, y, x + w, y + h))
                result = self._ocr_with_tesseract(crop, bbox)
                if result:
                    results_low.append(result)
            results_low = [r for r in results_low if r['confidence'] > 0.2]
            results_low.sort(key=lambda r: r['confidence'], reverse=True)
            if results_low:
                logger.info(f"Fallback 1 (low YOLO) found {len(results_low)} bib numbers")
                return results_low

        # Fallback 2: Full-image Tesseract
        results = self._fallback_full_image_tesseract(image_path)
        if results:
            logger.info(f"Fallback 2 (full-image Tesseract) found {len(results)} bib numbers")
            return results

        # Fallback 3: PaddleOCR (if enabled and available)
        if self.enable_paddle_fallback:
            logger.info("Fallback 3: Trying PaddleOCR")
            try:
                from processing_cli.services.ocr import OCRService
                if self._paddle_ocr is None:
                    self._paddle_ocr = OCRService(confidence_threshold=0.5)
                paddle_results = self._paddle_ocr.extract_bib_candidates(image_path)
                if paddle_results:
                    import json
                    ocr_results: list[OCRResult] = []
                    for candidate in paddle_results:
                        ocr_results.append({
                            'text': candidate["text"],
                            'confidence': candidate["confidence"],
                            'bbox': [int(v) for v in json.loads(candidate["bbox"]) if isinstance(v, (int, float))],
                            'bib_number': candidate["text"],
                            'method': 'fallback_paddle'
                        })
                    logger.info(f"Fallback 3 (PaddleOCR) found {len(ocr_results)} bib numbers")
                    return ocr_results
            except Exception as e:
                logger.warning(f"PaddleOCR fallback failed: {e}")

        logger.warning(f"No bib numbers found in {image_path.name}")
        return []
