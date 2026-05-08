#!/usr/bin/env python3
"""
Test YOLO bib detection on race photos
Validates detection rate and speed
"""
import time
from pathlib import Path
from PIL import Image, ImageDraw
import sys

sys.path.insert(0, str(Path(__file__).parent))

from processing_cli.services.bib_detection import BibDetectionService

# Test dataset
RACE_PHOTOS_DIR = Path("/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output/20260703 dapxe")
NUM_SAMPLES = 10
OUTPUT_DIR = Path("test_output/bib_detection")


def visualize_detections(image_path: Path, detections: list, output_path: Path):
    """Draw bounding boxes on image for visual validation"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    for det in detections:
        bbox = det['bbox']
        x, y, w, h = bbox
        # Draw rectangle
        draw.rectangle([x, y, x + w, y + h], outline="red", width=3)
        # Draw confidence
        text = f"{det['confidence']:.2f}"
        draw.text((x, y - 20), text, fill="red")

    img.save(output_path)


def main():
    print("=" * 60)
    print("YOLO Bib Detection Test")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize service
    print("\n[1/4] Initializing YOLO model...")
    start_init = time.time()
    service = BibDetectionService(model_name="yolov8n.pt")
    init_time = time.time() - start_init
    print(f"✓ Initialization completed in {init_time:.2f}s")

    # Get sample photos
    print(f"\n[2/4] Loading {NUM_SAMPLES} sample photos...")
    photo_files = sorted(list(RACE_PHOTOS_DIR.glob("*.jpg")))[:NUM_SAMPLES]
    print(f"✓ Found {len(photo_files)} photos")

    # Process photos
    print(f"\n[3/4] Detecting bib regions...")
    results = []
    total_time = 0

    for i, photo_path in enumerate(photo_files, 1):
        print(f"\n  [{i}/{len(photo_files)}] {photo_path.name}")

        # Run detection
        start = time.time()
        detections = service.detect_bib_regions(photo_path)
        elapsed = time.time() - start
        total_time += elapsed

        results.append({
            'file': photo_path.name,
            'time': elapsed,
            'detections': len(detections),
            'bib_regions': detections
        })

        print(f"    Time: {elapsed:.2f}s")
        print(f"    Bib regions detected: {len(detections)}")

        if detections:
            for j, det in enumerate(detections[:3], 1):  # Show top 3
                bbox = det['bbox']
                print(f"      Region {j}: bbox={bbox}, conf={det['confidence']:.2f}")

            # Visualize first detection
            output_path = OUTPUT_DIR / f"{photo_path.stem}_detected.jpg"
            visualize_detections(photo_path, detections, output_path)
            print(f"    Saved visualization: {output_path}")

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
    else:
        print(f"  ⚠️  WARNING - Slower than target ({avg_time:.2f}s > 0.5s)")

    print(f"\n🔍 Detection Results:")
    photos_with_detections = sum(1 for r in results if r['detections'] > 0)
    total_detections = sum(r['detections'] for r in results)
    print(f"  Photos with detections: {photos_with_detections}/{len(results)}")
    print(f"  Total bib regions found: {total_detections}")
    print(f"  Average detections per photo: {total_detections / len(results):.1f}")

    detection_rate = photos_with_detections / len(results) * 100
    print(f"  Detection rate: {detection_rate:.0f}%")
    print(f"  Target: >60%")

    if detection_rate >= 60:
        print(f"  ✅ PASS - Meets target")
    else:
        print(f"  ⚠️  FAIL - Below target ({detection_rate:.0f}% < 60%)")

    print(f"\n📊 Detailed Results:")
    for r in results:
        status = "✓" if r['detections'] > 0 else "✗"
        print(f"  {status} {r['file']}: {r['time']:.2f}s, {r['detections']} regions")

    # Estimate for 10k images
    print(f"\n📈 Projection for 10,000 images:")
    estimated_seconds = avg_time * 10000
    estimated_hours = estimated_seconds / 3600
    print(f"  Estimated time: {estimated_hours:.1f} hours ({estimated_seconds/60:.0f} minutes)")
    print(f"  Target: <1.4 hours (0.5s/image)")

    print(f"\n💡 Next Steps:")
    print(f"  1. Review visualizations in {OUTPUT_DIR}/")
    print(f"  2. Validate bounding boxes contain bib numbers")
    print(f"  3. If detection rate <60%, consider fine-tuning")
    print(f"  4. Proceed to Phase 2: Tesseract OCR on cropped regions")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
