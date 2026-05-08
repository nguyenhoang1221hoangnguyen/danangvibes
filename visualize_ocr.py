#!/usr/bin/env python3
"""
Visualize YOLO detections và Tesseract OCR results.
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))

from processing_cli.services.text_detection import TextDetectionService
from processing_cli.services.ocr_hybrid import HybridOCRService as HybridOCR


def visualize_detections(image_path: str, output_dir: str = "debug_output"):
    """Visualize YOLO detections và save crops."""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"VISUALIZE: {Path(image_path).name}")
    print(f"{'='*60}\n")

    # Load image
    img = Image.open(image_path)
    img_draw = img.copy()
    draw = ImageDraw.Draw(img_draw)

    # YOLO detection
    print("[1] Running YOLO text detection...")
    text_detector = TextDetectionService(model_name="yolov8n.pt")
    detections = text_detector.detect_text_regions(Path(image_path), confidence=0.2)

    print(f"Found {len(detections)} detections\n")

    # Draw boxes and save crops
    ocr_service = HybridOCR(enable_paddle_fallback=False)

    for i, det in enumerate(detections, 1):
        bbox = det['bbox']
        conf = det['confidence']
        x, y, w, h = bbox

        # Draw rectangle
        draw.rectangle([x, y, x+w, y+h], outline="red", width=3)
        draw.text((x, y-20), f"#{i} ({conf:.2f})", fill="red")

        # Save crop
        crop = img.crop((x, y, x+w, y+h))
        crop_path = output_path / f"crop_{i:02d}_conf{conf:.2f}.jpg"
        crop.save(crop_path)

        # Try OCR on crop
        processed_crop = ocr_service.preprocess_for_ocr(crop)
        processed_path = output_path / f"crop_{i:02d}_processed.jpg"
        processed_crop.save(processed_path)

        # Tesseract OCR
        import pytesseract
        custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(processed_crop, config=custom_config).strip()
        bib = ocr_service.extract_bib_number(text)

        print(f"Detection #{i}:")
        print(f"  BBox: [{x}, {y}, {w}, {h}]")
        print(f"  Confidence: {conf:.2f}")
        print(f"  OCR Text: '{text}'")
        print(f"  Bib Number: {bib}")
        print(f"  Saved: {crop_path.name}, {processed_path.name}")
        print()

    # Save annotated image
    annotated_path = output_path / f"annotated_{Path(image_path).name}"
    img_draw.save(annotated_path)
    print(f"✅ Annotated image saved: {annotated_path}")
    print(f"✅ All crops saved to: {output_path}/")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_ocr.py <image_path> [output_dir]")
        print("\nExample:")
        print('  python visualize_ocr.py "/path/to/photo.jpg"')
        print('  python visualize_ocr.py "/path/to/photo.jpg" "my_debug"')
        sys.exit(1)

    image_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "debug_output"

    if not Path(image_path).exists():
        print(f"❌ File not found: {image_path}")
        sys.exit(1)

    visualize_detections(image_path, output_dir)
