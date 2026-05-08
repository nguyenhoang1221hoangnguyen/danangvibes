#!/usr/bin/env python3
"""
Comprehensive face recognition test on challenging race photos
Tests 3 models on 5 difficult cases with helmets/occlusions
"""
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

# Test photos with different challenges
TEST_PHOTOS = [
    ("HOD_5240.jpg", "Cúi đầu xuống, mặt hướng xuống - Cực khó"),
    ("HOD_5346.jpg", "Góc chụp từ sau lưng - Cực khó"),
    ("HOD_5259.jpg", "Chụp từ xa 30-40m, khuôn mặt nhỏ - Rất khó"),
    ("HOD_5280.jpg", "Chụp từ xa, nhiều VĐV - Rất khó"),
    ("HOD_5229.jpg", "Mũ che trán, góc nghiêng 3/4 - Khó"),
]

BASE_DIR = Path("/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output/20260703 dapxe")

def test_model(model_name, service_class, *args):
    """Test a face recognition model on all test photos"""
    print(f"\n{'='*70}")
    print(f"Testing: {model_name}")
    print(f"{'='*70}")

    try:
        service = service_class(*args)
    except Exception as e:
        print(f"❌ Cannot initialize {model_name}: {e}")
        return None

    results = []
    total_time = 0

    for filename, challenge in TEST_PHOTOS:
        photo_path = BASE_DIR / filename
        if not photo_path.exists():
            print(f"\n⚠️  {filename}: File not found")
            continue

        print(f"\n📷 {filename}")
        print(f"   Challenge: {challenge}")

        try:
            start = time.time()
            faces = service.detect_and_embed(photo_path)
            elapsed = time.time() - start
            total_time += elapsed

            if faces:
                print(f"   ✅ Detected {len(faces)} face(s) in {elapsed:.2f}s")
                print(f"      Confidence: {faces[0]['confidence']:.3f}")
                print(f"      Embedding dim: {len(faces[0]['embedding'])}")
                results.append({
                    'file': filename,
                    'success': True,
                    'faces': len(faces),
                    'time': elapsed,
                    'confidence': faces[0]['confidence']
                })
            else:
                print(f"   ❌ No faces detected in {elapsed:.2f}s")
                results.append({
                    'file': filename,
                    'success': False,
                    'faces': 0,
                    'time': elapsed,
                    'confidence': 0.0
                })

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                'file': filename,
                'success': False,
                'faces': 0,
                'time': 0,
                'confidence': 0.0
            })

    # Summary
    success_count = sum(1 for r in results if r['success'])
    avg_time = total_time / len(results) if results else 0

    print(f"\n{'─'*70}")
    print(f"Summary for {model_name}:")
    print(f"  Success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
    print(f"  Average time: {avg_time:.2f}s per image")
    print(f"  Total time: {total_time:.2f}s")

    return {
        'model': model_name,
        'results': results,
        'success_rate': success_count / len(results) if results else 0,
        'avg_time': avg_time,
        'total_time': total_time
    }

def main():
    print("="*70)
    print("FACE RECOGNITION COMPARISON - CHALLENGING RACE PHOTOS")
    print("="*70)
    print("\nTest cases:")
    for i, (filename, challenge) in enumerate(TEST_PHOTOS, 1):
        print(f"{i}. {filename}: {challenge}")

    all_results = []

    # Test 1: DeepFace (VGG-Face)
    try:
        from processing_cli.services.face import FaceService
        result = test_model("DeepFace (VGG-Face)", FaceService, "VGG-Face", "v1")
        if result:
            all_results.append(result)
    except Exception as e:
        print(f"\n❌ DeepFace test failed: {e}")

    # Test 2: face_recognition (dlib)
    try:
        from processing_cli.services.face_recognition_service import FaceRecognitionService
        result = test_model("face_recognition (dlib HOG)", FaceRecognitionService, "hog", "v1")
        if result:
            all_results.append(result)
    except Exception as e:
        print(f"\n❌ face_recognition test failed: {e}")
        print("Install with: pip install face_recognition")

    # Test 3: InsightFace (buffalo_l)
    try:
        from processing_cli.services.face_insightface import InsightFaceService
        result = test_model("InsightFace (buffalo_l)", InsightFaceService, "buffalo_l", "v1")
        if result:
            all_results.append(result)
    except Exception as e:
        print(f"\n❌ InsightFace test failed: {e}")
        print("Install with: pip install insightface onnxruntime")

    # Final comparison
    if len(all_results) > 1:
        print("\n" + "="*70)
        print("FINAL COMPARISON")
        print("="*70)

        print(f"\n{'Model':<35} {'Success Rate':<15} {'Avg Time':<12} {'Total Time'}")
        print("─"*70)
        for result in all_results:
            print(f"{result['model']:<35} "
                  f"{result['success_rate']*100:>6.0f}% ({int(result['success_rate']*len(TEST_PHOTOS))}/{len(TEST_PHOTOS)})      "
                  f"{result['avg_time']:>6.2f}s       "
                  f"{result['total_time']:>6.2f}s")

        # Winner
        best_accuracy = max(all_results, key=lambda x: x['success_rate'])
        fastest = min(all_results, key=lambda x: x['avg_time'])

        print("\n" + "="*70)
        print("WINNER")
        print("="*70)
        print(f"🏆 Best Accuracy: {best_accuracy['model']} ({best_accuracy['success_rate']*100:.0f}%)")
        print(f"⚡ Fastest: {fastest['model']} ({fastest['avg_time']:.2f}s)")

        print("\n" + "="*70)
        print("RECOMMENDATION FOR RACE PHOTOS WITH HELMETS")
        print("="*70)

        if best_accuracy['success_rate'] >= 0.6:
            print(f"✅ Use {best_accuracy['model']}")
            print(f"   - Best success rate: {best_accuracy['success_rate']*100:.0f}%")
            print(f"   - Good enough for production")
        else:
            print("⚠️  All models struggle with these challenging photos")
            print("   Consider:")
            print("   - Using bib number OCR as primary search")
            print("   - Face search as secondary/fallback")
            print("   - Manual tagging for difficult cases")

if __name__ == "__main__":
    main()
