#!/usr/bin/env python3
"""
Debug hybrid OCR - check what's happening in the pipeline
"""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

from processing_cli.services.ocr_hybrid import HybridOCRService

# Test with one image that had YOLO detections
TEST_IMAGE = Path("/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output/20260703 dapxe/HOD_5224 1.jpg")
OUTPUT_DIR = Path("test_output/debug_ocr")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 60)
    print("Debug Hybrid OCR Pipeline")
    print("=" * 60)

    service = HybridOCRService()

    print(f"\nTesting: {TEST_IMAGE.name}")

    # Step 1: YOLO detection
    print("\n[Step 1] YOLO Text Detection...")
    detections = service.text_detector.detect_text_regions(TEST_IMAGE)
    print(f"  Found {len(detections)} text regions")

    if not detections:
        print("  ❌ No detections - cannot proceed")
        return

    # Load image
    img = Image.open(TEST_IMAGE)
    print(f"  Image size: {img.size}")

    # Step 2: Process each detection
    for i, detection in enumerate(detections, 1):
        print(f"\n[Step 2.{i}] Processing detection {i}/{len(detections)}")
        bbox = detection['bbox']
        x, y, w, h = bbox
        print(f"  BBox: x={x}, y={y}, w={w}, h={h}")
        print(f"  Confidence: {detection['confidence']:.2f}")

        # Crop
        crop = img.crop((x, y, x + w, y + h))
        print(f"  Crop size: {crop.size}")

        # Save original crop
        crop_path = OUTPUT_DIR / f"crop_{i}_original.jpg"
        crop.save(crop_path)
        print(f"  Saved original crop: {crop_path}")

        # Preprocess
        print(f"\n  [Step 2.{i}.1] Preprocessing...")
        processed = service.preprocess_for_ocr(crop)
        processed_path = OUTPUT_DIR / f"crop_{i}_processed.jpg"
        processed.save(processed_path)
        print(f"  Saved processed crop: {processed_path}")

        # OCR
        print(f"\n  [Step 2.{i}.2] Running Tesseract OCR...")
        custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789'

        try:
            # Get detailed OCR data
            ocr_data = service.pytesseract.image_to_data(
                processed,
                config=custom_config,
                output_type=service.pytesseract.Output.DICT
            )

            print(f"  OCR returned {len(ocr_data['text'])} items")

            # Show all detections
            for j, text in enumerate(ocr_data['text']):
                conf = ocr_data['conf'][j]
                if text.strip():
                    print(f"    [{j}] text='{text}', conf={conf}")

            # Try without whitelist
            print(f"\n  [Step 2.{i}.3] Trying without digit whitelist...")
            ocr_data_full = service.pytesseract.image_to_data(
                processed,
                config='--psm 7',
                output_type=service.pytesseract.Output.DICT
            )

            print(f"  OCR returned {len(ocr_data_full['text'])} items")
            for j, text in enumerate(ocr_data_full['text']):
                conf = ocr_data_full['conf'][j]
                if text.strip():
                    print(f"    [{j}] text='{text}', conf={conf}")

        except Exception as e:
            print(f"  ❌ OCR failed: {e}")

    print("\n" + "=" * 60)
    print("Debug complete. Check test_output/debug_ocr/ for crops")
    print("=" * 60)


if __name__ == "__main__":
    main()
