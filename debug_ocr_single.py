#!/usr/bin/env python3
"""
Debug OCR trên 1 ảnh để xem tại sao không detect được bib numbers.
"""

import sys
from pathlib import Path
from PIL import Image

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from processing_cli.services.ocr_hybrid import HybridOCRService as HybridOCR
from processing_cli.services.text_detection import TextDetectionService


def debug_single_image(image_path: str):
    """Debug OCR pipeline trên 1 ảnh."""

    print(f"\n{'='*60}")
    print(f"DEBUG OCR: {Path(image_path).name}")
    print(f"{'='*60}\n")

    # Load image
    img = Image.open(image_path)
    print(f"✅ Image loaded: {img.size[0]}x{img.size[1]} pixels")

    # Step 1: YOLO Text Detection
    print(f"\n[Step 1] YOLO Text Detection")
    print("-" * 40)

    text_detector = TextDetectionService(model_name="yolov8n.pt")
    detections = text_detector.detect_text_regions(Path(image_path), confidence=0.2)

    print(f"Detections found: {len(detections)}")
    for i, det in enumerate(detections, 1):
        bbox = det['bbox']
        conf = det['confidence']
        print(f"  {i}. BBox: {bbox}, Confidence: {conf:.2f}")

    if not detections:
        print("❌ No text regions detected by YOLO!")
        print("\nPossible reasons:")
        print("  - Bib numbers quá nhỏ")
        print("  - Góc chụp nghiêng")
        print("  - Confidence threshold quá cao (default: 0.2)")
        print("\nTrying with lower threshold...")

        # Try lower threshold
        detections_low = text_detector.detect_text_regions(Path(image_path), confidence=0.1)
        print(f"\nWith threshold=0.1: {len(detections_low)} detections")
        for i, det in enumerate(detections_low, 1):
            bbox = det['bbox']
            conf = det['confidence']
            print(f"  {i}. BBox: {bbox}, Confidence: {conf:.2f}")

    # Step 2: Hybrid OCR
    print(f"\n[Step 2] Hybrid OCR Service")
    print("-" * 40)

    ocr_service = HybridOCR(enable_paddle_fallback=False)
    results = ocr_service.detect_bib_numbers(Path(image_path))

    print(f"OCR Results: {len(results)} candidates")
    for i, result in enumerate(results, 1):
        text = result['text']
        bib = result['bib_number']
        conf = result['confidence']
        method = result['method']
        print(f"  {i}. Text: '{text}' → Bib: {bib}, Confidence: {conf:.2f}, Method: {method}")

    if not results:
        print("❌ No bib numbers extracted!")
        print("\nTrying full-image Tesseract fallback...")

        # Try Tesseract directly
        import pytesseract

        processed = ocr_service.preprocess_for_ocr(img)

        custom_config = r'--psm 6 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(processed, config=custom_config)

        print(f"\nTesseract full-image output:")
        print(f"  Raw text: '{text.strip()}'")

        bib = ocr_service.extract_bib_number(text)
        print(f"  Extracted bib: {bib}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_ocr_single.py <image_path>")
        print("\nExample:")
        print('  python debug_ocr_single.py "/Users/nguyenhoang/Desktop/2026/Tháng 5/test bib/027849f42fc88daf8f0f8089ddc324bf.jpg"')
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"❌ File not found: {image_path}")
        sys.exit(1)

    debug_single_image(image_path)
