#!/usr/bin/env python3
"""
Test Hybrid YOLO + Tesseract OCR on race photos
Validates combined detection + OCR performance
"""
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys

sys.path.insert(0, str(Path(__file__).parent))

from processing_cli.services.ocr_hybrid import HybridOCRService

# Test dataset
RACE_PHOTOS_DIR = Path("/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output/20260703 dapxe")
NUM_SAMPLES = 10
OUTPUT_DIR = Path("test_output/hybrid_ocr")


def visualize_ocr_results(image_path: Path, results: list, output_path: Path):
    """Draw bounding boxes and OCR results on image"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    for i, result in enumerate(results, 1):
        bbox = result['bbox']
        x, y, w, h = bbox

        # Draw rectangle
        color = "green" if result['bib_number'] else "orange"
        draw.rectangle([x, y, x + w, y + h], outline=color, width=4)

        # Draw bib number and confidence
        if result['bib_number']:
            text = f"#{result['bib_number']} ({result['confidence']:.2f})"
            # Draw text background
            text_bbox = draw.textbbox((x, y - 30), text)
            draw.rectangle(text_bbox, fill="green")
            draw.text((x, y - 30), text, fill="white")

    img.save(output_path)


def main():
    print("=" * 60)
    print("Hybrid YOLO + Tesseract OCR Test")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize service
    print("\n[1/4] Initializing Hybrid OCR service...")
    start_init = time.time()
    service = HybridOCRService()
    init_time = time.time() - start_init
    print(f"✓ Initialization completed in {init_time:.2f}s")

    # Get sample photos
    print(f"\n[2/4] Loading {NUM_SAMPLES} sample photos...")
    photo_files = sorted(list(RACE_PHOTOS_DIR.glob("*.jpg")))[:NUM_SAMPLES]
    print(f"✓ Found {len(photo_files)} photos")

    # Process photos
    print(f"\n[3/4] Running hybrid detection + OCR...")
    results = []
    total_time = 0
    total_bib_numbers = 0

    for i, photo_path in enumerate(photo_files, 1):
        print(f"\n  [{i}/{len(photo_files)}] {photo_path.name}")

        # Run hybrid OCR
        start = time.time()
        ocr_results = service.detect_bib_numbers(photo_path)
        elapsed = time.time() - start
        total_time += elapsed

        bib_numbers = [r['bib_number'] for r in ocr_results if r['bib_number']]
        total_bib_numbers += len(bib_numbers)

        results.append({
            'file': photo_path.name,
            'time': elapsed,
            'detections': len(ocr_results),
            'bib_numbers': bib_numbers,
            'ocr_results': ocr_results
        })

        print(f"    Time: {elapsed:.2f}s")
        print(f"    Bib numbers found: {len(bib_numbers)}")

        if bib_numbers:
            for j, bib in enumerate(bib_numbers[:5], 1):  # Show top 5
                ocr_result = ocr_results[j-1]
                print(f"      #{bib} (confidence: {ocr_result['confidence']:.2f})")

            # Visualize
            output_path = OUTPUT_DIR / f"{photo_path.stem}_ocr.jpg"
            visualize_ocr_results(photo_path, ocr_results, output_path)
            print(f"    Saved visualization: {output_path}")
        else:
            print(f"    ⚠️  No bib numbers detected")

    # Summary
    print("\n" + "=" * 60)
    print("[4/4] TEST SUMMARY")
    print("=" * 60)

    avg_time = total_time / len(results)
    print(f"\n⏱️  Performance:")
    print(f"  Total processing time: {total_time:.2f}s")
    print(f"  Average time per image: {avg_time:.2f}s")
    print(f"  Target: <0.5s per image")

    if avg_time <= 0.5:
        print(f"  ✅ PASS - Within target range")
    elif avg_time <= 1.0:
        print(f"  ⚠️  ACCEPTABLE - Slightly over target ({avg_time:.2f}s)")
    else:
        print(f"  ❌ FAIL - Exceeds target ({avg_time:.2f}s > 0.5s)")

    print(f"\n🔍 OCR Results:")
    photos_with_bibs = sum(1 for r in results if r['bib_numbers'])
    print(f"  Photos with bib numbers: {photos_with_bibs}/{len(results)}")
    print(f"  Total bib numbers found: {total_bib_numbers}")
    print(f"  Average bibs per photo: {total_bib_numbers / len(results):.1f}")

    detection_rate = photos_with_bibs / len(results) * 100
    print(f"  Detection rate: {detection_rate:.0f}%")
    print(f"  Target: 60-70%")

    if detection_rate >= 60:
        print(f"  ✅ PASS - Meets target")
    else:
        print(f"  ⚠️  BELOW TARGET - {detection_rate:.0f}% < 60%")

    print(f"\n📊 Detailed Results:")
    for r in results:
        status = "✓" if r['bib_numbers'] else "✗"
        bibs_str = ", ".join(r['bib_numbers']) if r['bib_numbers'] else "none"
        print(f"  {status} {r['file']}: {r['time']:.2f}s, bibs=[{bibs_str}]")

    # Estimate for 10k images
    print(f"\n📈 Projection for 10,000 images:")
    estimated_seconds = avg_time * 10000
    estimated_hours = estimated_seconds / 3600
    estimated_minutes = estimated_seconds / 60
    print(f"  Estimated time: {estimated_hours:.1f} hours ({estimated_minutes:.0f} minutes)")
    print(f"  Target: 2-4 hours")

    if estimated_hours <= 4.0:
        print(f"  ✅ PASS - Within target range")
    else:
        print(f"  ⚠️  EXCEEDS TARGET - {estimated_hours:.1f}h > 4.0h")

    print(f"\n💡 Analysis:")
    print(f"  - YOLO detection: ~0.11s/image (from Phase 1)")
    print(f"  - Tesseract OCR: ~{avg_time - 0.11:.2f}s/image")
    print(f"  - Combined pipeline: {avg_time:.2f}s/image")

    print(f"\n📋 Next Steps:")
    print(f"  1. Review visualizations in {OUTPUT_DIR}/")
    print(f"  2. Manually verify bib numbers are correct")
    print(f"  3. If accuracy <60%, tune preprocessing/Tesseract config")
    print(f"  4. Proceed to Phase 3: Fallback logic & error handling")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
