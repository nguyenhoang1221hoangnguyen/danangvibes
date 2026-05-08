#!/usr/bin/env python3
"""
EasyOCR Validation Script for M1 Pro
Tests EasyOCR performance on race photos to validate 1-2s/image target
"""
import time
from pathlib import Path
import easyocr
from PIL import Image
import re

# Test dataset
RACE_PHOTOS_DIR = Path("/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output/20260703 dapxe")
NUM_SAMPLES = 10

def extract_bib_numbers(text_results):
    """Extract potential bib numbers (2-5 digits) from OCR results"""
    bib_candidates = []
    for detection in text_results:
        text = detection[1]
        # Look for 2-5 digit numbers
        matches = re.findall(r'\b\d{2,5}\b', text)
        for match in matches:
            bib_candidates.append({
                'number': match,
                'confidence': detection[2],
                'bbox': detection[0]
            })
    return bib_candidates

def main():
    print("=" * 60)
    print("EasyOCR Validation on M1 Pro")
    print("=" * 60)

    # Initialize EasyOCR reader
    print("\n[1/4] Initializing EasyOCR reader...")
    start_init = time.time()
    reader = easyocr.Reader(['en'], gpu=False)  # M1 uses CPU/Neural Engine
    init_time = time.time() - start_init
    print(f"✓ Initialization completed in {init_time:.2f}s")

    # Get sample photos
    print(f"\n[2/4] Loading {NUM_SAMPLES} sample photos...")
    photo_files = sorted(list(RACE_PHOTOS_DIR.glob("*.jpg")))[:NUM_SAMPLES]
    print(f"✓ Found {len(photo_files)} photos")

    # Process photos
    print(f"\n[3/4] Processing photos with EasyOCR...")
    results = []
    total_time = 0

    for i, photo_path in enumerate(photo_files, 1):
        print(f"\n  [{i}/{len(photo_files)}] {photo_path.name}")

        # Load and resize image
        img = Image.open(photo_path)
        original_size = img.size

        # Resize to max 1280px (same as production pipeline)
        max_dim = 1280
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"    Resized: {original_size} → {img.size}")

        # Run OCR
        start = time.time()
        ocr_results = reader.readtext(str(photo_path))
        elapsed = time.time() - start
        total_time += elapsed

        # Extract bib numbers
        bib_candidates = extract_bib_numbers(ocr_results)

        results.append({
            'file': photo_path.name,
            'time': elapsed,
            'total_detections': len(ocr_results),
            'bib_candidates': bib_candidates
        })

        print(f"    Time: {elapsed:.2f}s")
        print(f"    Total text detections: {len(ocr_results)}")
        print(f"    Bib candidates: {len(bib_candidates)}")
        if bib_candidates:
            for bib in bib_candidates[:3]:  # Show top 3
                print(f"      - {bib['number']} (confidence: {bib['confidence']:.2f})")

    # Summary
    print("\n" + "=" * 60)
    print("[4/4] VALIDATION SUMMARY")
    print("=" * 60)

    avg_time = total_time / len(results)
    print(f"\n⏱️  Performance:")
    print(f"  Total processing time: {total_time:.2f}s")
    print(f"  Average time per image: {avg_time:.2f}s")
    print(f"  Target: 1-2s per image")

    if avg_time <= 2.0:
        print(f"  ✅ PASS - Within target range")
    else:
        print(f"  ⚠️  FAIL - Exceeds target ({avg_time:.2f}s > 2.0s)")

    print(f"\n🔍 Detection Results:")
    total_bibs = sum(len(r['bib_candidates']) for r in results)
    photos_with_bibs = sum(1 for r in results if r['bib_candidates'])
    print(f"  Photos with bib candidates: {photos_with_bibs}/{len(results)}")
    print(f"  Total bib candidates found: {total_bibs}")

    print(f"\n📊 Detailed Results:")
    for r in results:
        status = "✓" if r['bib_candidates'] else "✗"
        print(f"  {status} {r['file']}: {r['time']:.2f}s, {len(r['bib_candidates'])} bibs")

    # Estimate for 10k images
    print(f"\n📈 Projection for 10,000 images:")
    estimated_hours = (avg_time * 10000) / 3600
    print(f"  Estimated time: {estimated_hours:.1f} hours")
    print(f"  Target: 4-5 hours")

    if estimated_hours <= 5.0:
        print(f"  ✅ PASS - Within target range")
    else:
        print(f"  ⚠️  FAIL - Exceeds target ({estimated_hours:.1f}h > 5.0h)")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
