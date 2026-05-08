#!/usr/bin/env python3
"""
Benchmark tất cả phương pháp OCR và Face detection.
Test trên folder ảnh thật để tìm cấu hình tốt nhất.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import json

sys.path.insert(0, str(Path(__file__).parent))

from processing_cli.services.scanner import PhotoScanner


def benchmark_ocr_methods(test_folder: str, max_photos: int = 10):
    """Benchmark các phương pháp OCR."""

    test_path = Path(test_folder)
    if not test_path.exists():
        print(f"❌ Folder not found: {test_folder}")
        return

    # Scan photos
    scanner = PhotoScanner()
    photos = list(scanner.scan(test_path))[:max_photos]

    print(f"\n{'='*70}")
    print(f"BENCHMARK OCR METHODS")
    print(f"{'='*70}")
    print(f"Test folder: {test_folder}")
    print(f"Photos: {len(photos)}")
    print(f"{'='*70}\n")

    results = {}

    # Method 1: Hybrid (YOLO + Tesseract)
    print("[1/3] Testing Hybrid OCR (YOLO + Tesseract)...")
    print("-" * 70)

    try:
        from processing_cli.services.ocr_hybrid import HybridOCRService

        ocr_service = HybridOCRService(enable_paddle_fallback=False)

        start = time.time()
        total_bibs = 0
        bib_details = []

        for i, photo in enumerate(photos, 1):
            photo_start = time.time()
            bib_results = ocr_service.detect_bib_numbers(photo)
            photo_time = time.time() - photo_start

            bibs_found = [r['bib_number'] for r in bib_results if r['bib_number']]
            total_bibs += len(bibs_found)

            if bibs_found:
                bib_details.append({
                    'photo': photo.name,
                    'bibs': bibs_found,
                    'time': photo_time,
                    'method': bib_results[0]['method'] if bib_results else None
                })

            print(f"  {i}/{len(photos)}: {photo.name} - {len(bibs_found)} bibs in {photo_time:.2f}s")

        elapsed = time.time() - start
        avg_time = elapsed / len(photos)

        results['hybrid'] = {
            'method': 'Hybrid (YOLO + Tesseract)',
            'total_bibs': total_bibs,
            'photos_with_bibs': len(bib_details),
            'total_time': elapsed,
            'avg_time_per_photo': avg_time,
            'details': bib_details,
            'status': 'success'
        }

        print(f"\n✅ Hybrid: {total_bibs} bibs found, {avg_time:.2f}s/photo\n")

    except Exception as e:
        print(f"❌ Hybrid failed: {e}\n")
        results['hybrid'] = {'status': 'failed', 'error': str(e)}

    # Method 2: PaddleOCR
    print("[2/3] Testing PaddleOCR...")
    print("-" * 70)

    try:
        from processing_cli.services.ocr import OCRService

        ocr_service = OCRService(confidence_threshold=0.6)

        start = time.time()
        total_bibs = 0
        bib_details = []

        for i, photo in enumerate(photos, 1):
            photo_start = time.time()
            candidates = ocr_service.extract_bib_candidates(photo)
            photo_time = time.time() - photo_start

            bibs_found = [c['text'] for c in candidates if c['is_bib']]
            total_bibs += len(bibs_found)

            if bibs_found:
                bib_details.append({
                    'photo': photo.name,
                    'bibs': bibs_found,
                    'time': photo_time
                })

            print(f"  {i}/{len(photos)}: {photo.name} - {len(bibs_found)} bibs in {photo_time:.2f}s")

        elapsed = time.time() - start
        avg_time = elapsed / len(photos)

        results['paddle'] = {
            'method': 'PaddleOCR',
            'total_bibs': total_bibs,
            'photos_with_bibs': len(bib_details),
            'total_time': elapsed,
            'avg_time_per_photo': avg_time,
            'details': bib_details,
            'status': 'success'
        }

        print(f"\n✅ PaddleOCR: {total_bibs} bibs found, {avg_time:.2f}s/photo\n")

    except Exception as e:
        print(f"❌ PaddleOCR failed: {e}\n")
        results['paddle'] = {'status': 'failed', 'error': str(e)}

    # Method 3: Tesseract Only
    print("[3/3] Testing Tesseract Only...")
    print("-" * 70)

    try:
        from processing_cli.services.ocr_tesseract import TesseractOCRService

        ocr_service = TesseractOCRService(confidence_threshold=0.6)

        start = time.time()
        total_bibs = 0
        bib_details = []

        for i, photo in enumerate(photos, 1):
            photo_start = time.time()
            candidates = ocr_service.extract_bib_candidates(photo)
            photo_time = time.time() - photo_start

            bibs_found = [c['text'] for c in candidates if c['is_bib']]
            total_bibs += len(bibs_found)

            if bibs_found:
                bib_details.append({
                    'photo': photo.name,
                    'bibs': bibs_found,
                    'time': photo_time
                })

            print(f"  {i}/{len(photos)}: {photo.name} - {len(bibs_found)} bibs in {photo_time:.2f}s")

        elapsed = time.time() - start
        avg_time = elapsed / len(photos)

        results['tesseract'] = {
            'method': 'Tesseract Only',
            'total_bibs': total_bibs,
            'photos_with_bibs': len(bib_details),
            'total_time': elapsed,
            'avg_time_per_photo': avg_time,
            'details': bib_details,
            'status': 'success'
        }

        print(f"\n✅ Tesseract: {total_bibs} bibs found, {avg_time:.2f}s/photo\n")

    except Exception as e:
        print(f"❌ Tesseract failed: {e}\n")
        results['tesseract'] = {'status': 'failed', 'error': str(e)}

    return results


def benchmark_face_methods(test_folder: str, max_photos: int = 10):
    """Benchmark các phương pháp Face detection."""

    test_path = Path(test_folder)
    scanner = PhotoScanner()
    photos = list(scanner.scan(test_path))[:max_photos]

    print(f"\n{'='*70}")
    print(f"BENCHMARK FACE DETECTION METHODS")
    print(f"{'='*70}")
    print(f"Photos: {len(photos)}")
    print(f"{'='*70}\n")

    results = {}

    # Method 1: InsightFace (buffalo_l)
    print("[1/2] Testing InsightFace (buffalo_l)...")
    print("-" * 70)

    try:
        from processing_cli.services.face_insightface import InsightFaceService

        face_service = InsightFaceService(model_name="buffalo_l", model_version="v1")

        start = time.time()
        total_faces = 0
        face_details = []

        for i, photo in enumerate(photos, 1):
            photo_start = time.time()
            faces = face_service.detect_and_embed(photo)
            photo_time = time.time() - photo_start

            total_faces += len(faces)

            if faces:
                face_details.append({
                    'photo': photo.name,
                    'faces': len(faces),
                    'time': photo_time,
                    'avg_confidence': sum(f['confidence'] for f in faces) / len(faces)
                })

            print(f"  {i}/{len(photos)}: {photo.name} - {len(faces)} faces in {photo_time:.2f}s")

        elapsed = time.time() - start
        avg_time = elapsed / len(photos)

        results['insightface_buffalo_l'] = {
            'method': 'InsightFace (buffalo_l)',
            'total_faces': total_faces,
            'photos_with_faces': len(face_details),
            'total_time': elapsed,
            'avg_time_per_photo': avg_time,
            'details': face_details,
            'status': 'success'
        }

        print(f"\n✅ InsightFace: {total_faces} faces found, {avg_time:.2f}s/photo\n")

    except Exception as e:
        print(f"❌ InsightFace failed: {e}\n")
        results['insightface_buffalo_l'] = {'status': 'failed', 'error': str(e)}

    # Method 2: face_recognition (HOG)
    print("[2/2] Testing face_recognition (HOG)...")
    print("-" * 70)

    try:
        from processing_cli.services.face_recognition_service import FaceRecognitionService

        face_service = FaceRecognitionService(model_name="hog", model_version="v1")

        start = time.time()
        total_faces = 0
        face_details = []

        for i, photo in enumerate(photos, 1):
            photo_start = time.time()
            faces = face_service.detect_and_embed(photo)
            photo_time = time.time() - photo_start

            total_faces += len(faces)

            if faces:
                face_details.append({
                    'photo': photo.name,
                    'faces': len(faces),
                    'time': photo_time,
                    'avg_confidence': sum(f['confidence'] for f in faces) / len(faces)
                })

            print(f"  {i}/{len(photos)}: {photo.name} - {len(faces)} faces in {photo_time:.2f}s")

        elapsed = time.time() - start
        avg_time = elapsed / len(photos)

        results['face_recognition_hog'] = {
            'method': 'face_recognition (HOG)',
            'total_faces': total_faces,
            'photos_with_faces': len(face_details),
            'total_time': elapsed,
            'avg_time_per_photo': avg_time,
            'details': face_details,
            'status': 'success'
        }

        print(f"\n✅ face_recognition: {total_faces} faces found, {avg_time:.2f}s/photo\n")

    except Exception as e:
        print(f"❌ face_recognition failed: {e}\n")
        results['face_recognition_hog'] = {'status': 'failed', 'error': str(e)}

    return results


def print_summary(ocr_results: Dict, face_results: Dict):
    """In tổng kết và khuyến nghị."""

    print(f"\n{'='*70}")
    print("SUMMARY & RECOMMENDATIONS")
    print(f"{'='*70}\n")

    # OCR Summary
    print("📊 OCR METHODS COMPARISON")
    print("-" * 70)
    print(f"{'Method':<25} {'Bibs':<8} {'Photos':<10} {'Avg Time':<12} {'Status'}")
    print("-" * 70)

    for key, result in ocr_results.items():
        if result['status'] == 'success':
            method = result['method']
            bibs = result['total_bibs']
            photos = result['photos_with_bibs']
            avg_time = result['avg_time_per_photo']
            print(f"{method:<25} {bibs:<8} {photos:<10} {avg_time:<12.2f}s ✅")
        else:
            print(f"{key:<25} {'N/A':<8} {'N/A':<10} {'N/A':<12} ❌")

    # Face Summary
    print(f"\n📊 FACE DETECTION COMPARISON")
    print("-" * 70)
    print(f"{'Method':<30} {'Faces':<8} {'Photos':<10} {'Avg Time':<12} {'Status'}")
    print("-" * 70)

    for key, result in face_results.items():
        if result['status'] == 'success':
            method = result['method']
            faces = result['total_faces']
            photos = result['photos_with_faces']
            avg_time = result['avg_time_per_photo']
            print(f"{method:<30} {faces:<8} {photos:<10} {avg_time:<12.2f}s ✅")
        else:
            print(f"{key:<30} {'N/A':<8} {'N/A':<10} {'N/A':<12} ❌")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 70)

    # Best OCR
    best_ocr = None
    best_ocr_score = -1

    for key, result in ocr_results.items():
        if result['status'] == 'success':
            # Score = accuracy (bibs found) / time
            # Higher is better
            score = result['total_bibs'] / (result['avg_time_per_photo'] + 0.1)
            if score > best_ocr_score:
                best_ocr_score = score
                best_ocr = result

    if best_ocr:
        print(f"\n✅ BEST OCR METHOD: {best_ocr['method']}")
        print(f"   - Bibs found: {best_ocr['total_bibs']}")
        print(f"   - Speed: {best_ocr['avg_time_per_photo']:.2f}s/photo")
        print(f"   - Score: {best_ocr_score:.2f} (bibs/second)")

    # Best Face
    best_face = None
    best_face_score = -1

    for key, result in face_results.items():
        if result['status'] == 'success':
            # Score = faces found / time
            score = result['total_faces'] / (result['avg_time_per_photo'] + 0.1)
            if score > best_face_score:
                best_face_score = score
                best_face = result

    if best_face:
        print(f"\n✅ BEST FACE METHOD: {best_face['method']}")
        print(f"   - Faces found: {best_face['total_faces']}")
        print(f"   - Speed: {best_face['avg_time_per_photo']:.2f}s/photo")
        print(f"   - Score: {best_face_score:.2f} (faces/second)")

    print(f"\n{'='*70}\n")

    return best_ocr, best_face


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark_all_methods.py <test_folder> [max_photos]")
        print("\nExample:")
        print('  python benchmark_all_methods.py "/Users/nguyenhoang/Desktop/2026/Tháng 5/test bib" 10')
        sys.exit(1)

    test_folder = sys.argv[1]
    max_photos = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    # Run benchmarks
    ocr_results = benchmark_ocr_methods(test_folder, max_photos)
    face_results = benchmark_face_methods(test_folder, max_photos)

    # Print summary
    best_ocr, best_face = print_summary(ocr_results, face_results)

    # Save results
    output = {
        'test_folder': test_folder,
        'max_photos': max_photos,
        'ocr_results': ocr_results,
        'face_results': face_results,
        'recommendations': {
            'best_ocr': best_ocr['method'] if best_ocr else None,
            'best_face': best_face['method'] if best_face else None
        }
    }

    output_file = Path("benchmark_results.json")
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"📄 Results saved to: {output_file}")
