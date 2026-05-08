# EasyOCR Validation Report - M1 Pro

**Date:** 2026-05-08  
**Test Dataset:** 20260703-dapxe (10 race photos)  
**Hardware:** Apple M1 Pro 16GB RAM  
**Status:** ❌ FAILED - Does not meet performance targets

---

## Executive Summary

EasyOCR tested on M1 Pro with 10 race photos. **Result: 14.17s/image average, 7x slower than 1-2s target.** Projected 39.4 hours for 10k images vs 4-5 hour target. **Not viable for production without optimization.**

---

## Test Results

### Performance Metrics

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Avg time/image | 14.17s | 1-2s | ❌ FAIL (7x slower) |
| Total time (10 images) | 141.75s | 10-20s | ❌ FAIL |
| Projection (10k images) | 39.4 hours | 4-5 hours | ❌ FAIL (8x slower) |
| Initialization time | ~30s | N/A | ⚠️ One-time cost |

### Detection Accuracy

| Metric | Result |
|--------|--------|
| Photos with bib candidates | 4/10 (40%) |
| Total bib candidates found | 8 |
| False positives | High (95808, 85808 detected) |
| Confidence scores | Very low (0.06-0.33) |

### Detailed Per-Image Results

```
✓ HOD_5218 1.jpg: 17.26s, 2 bibs (94, 18) - confidence 0.08-0.06
✓ HOD_5218.jpg:   14.97s, 2 bibs (94, 48) - confidence 0.33-0.25
✓ HOD_5219 1.jpg: 15.14s, 3 bibs (10, 34, 95808) - confidence 0.19-0.33
✓ HOD_5219.jpg:   14.65s, 1 bib (85808) - confidence 0.17
✗ HOD_5224 1.jpg: 13.88s, 0 bibs
✗ HOD_5224.jpg:   13.17s, 0 bibs
✗ HOD_5229 1.jpg: 12.75s, 0 bibs
✗ HOD_5229.jpg:   13.50s, 0 bibs
✗ HOD_5237 1.jpg: 13.02s, 0 bibs
✗ HOD_5237.jpg:   13.42s, 0 bibs
```

---

## Root Cause Analysis

### Why So Slow?

1. **CPU-only execution**: EasyOCR defaulted to CPU, no GPU/Neural Engine acceleration detected
2. **Model size**: Downloaded full detection model (~100MB+), likely heavy transformer-based
3. **No M1 optimization**: PyTorch 2.11.0 installed but may not be using Metal backend
4. **Image size**: Even after resize to 1280px, still processing large images

### Why Low Accuracy?

1. **Motion blur**: Race photos have athletes in motion
2. **Angle/perspective**: Bibs not always front-facing
3. **Occlusion**: Arms, gear covering bib numbers
4. **Low confidence**: All detections <0.35 confidence, indicating uncertainty
5. **False positives**: Detecting random numbers (95808, 85808) not valid bibs

---

## Optimization Paths

### Path A: Optimize EasyOCR (Estimated 2-3x speedup)

1. **Enable Metal backend for PyTorch**
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   # Then configure Metal acceleration
   ```

2. **Use smaller model**
   - Try `craft_mlt_25k.pth` instead of default
   - Trade accuracy for speed

3. **Reduce image size further**
   - Test 800px instead of 1280px
   - May lose small bib numbers

4. **Batch processing**
   - Process multiple images in single GPU batch
   - Amortize model loading overhead

**Estimated result:** 5-7s/image → 14-19 hours for 10k images (still 3-4x over target)

### Path B: Switch to Lighter OCR (Recommended)

1. **PaddleOCR with optimizations**
   - Already installed, known to work
   - Enable `use_angle_cls=False`, `use_gpu=False`
   - Aggressive image preprocessing (crop to bib region first)

2. **Tesseract with preprocessing**
   - Already tested, very fast but low accuracy
   - Add preprocessing: contrast enhancement, edge detection, bib region detection
   - Use YOLO to detect bib region first, then OCR only that region

3. **Hybrid approach: YOLO + Tesseract**
   - YOLO detects bib bounding box (~0.5s)
   - Crop to bib region
   - Tesseract OCR on small crop (~0.2s)
   - Total: ~0.7s/image → 2 hours for 10k images ✅

**Estimated result:** 0.7-1.5s/image → 2-4 hours for 10k images (meets target)

### Path C: Cloud API Fallback

- Google Vision API: $1.50/1000 images = $15 for 10k
- AWS Textract: $1.50/1000 images = $15 for 10k
- Fast (<1s/image) but requires budget approval

---

## Recommendation

**Proceed with Path B: Hybrid YOLO + Tesseract**

### Rationale

1. **Speed**: YOLO bib detection (0.5s) + Tesseract OCR (0.2s) = 0.7s/image
2. **Accuracy**: Cropping to bib region dramatically improves Tesseract accuracy
3. **Cost**: Zero additional cost, uses existing dependencies
4. **Proven**: YOLO already validated for object detection in race photos
5. **Fallback**: Can still use PaddleOCR for failed cases

### Implementation Plan

1. **Phase 1: YOLO Bib Detector (2 days)**
   - Train/fine-tune YOLO nano on bib detection
   - Or use generic "text region" detection
   - Target: 0.5s/image, 80%+ detection rate

2. **Phase 2: Tesseract Integration (1 day)**
   - Crop to bib bounding box
   - Preprocess: grayscale, contrast, denoise
   - Run Tesseract with optimized PSM mode
   - Target: 0.2s/image, 60%+ accuracy on crops

3. **Phase 3: Fallback Logic (1 day)**
   - If YOLO fails to detect bib → skip or use full-image PaddleOCR
   - If Tesseract confidence <0.5 → flag for manual review
   - Track success/failure rates

4. **Phase 4: Testing (1 day)**
   - Test on 100 images
   - Validate 0.7-1.5s/image average
   - Validate 60-70% accuracy (acceptable with manual review)

**Total timeline:** 5 days  
**Expected result:** 2-4 hours for 10k images, 60-70% accuracy

---

## Alternative: Abandon OCR for MVP

If timeline is critical, consider:

1. **MVP without OCR**: Launch with face detection only
2. **Manual bib entry**: Athletes enter their bib number when searching
3. **Photographer tagging**: Photographer manually tags bibs for key photos
4. **Phase 2 OCR**: Add OCR in next iteration after validating face search works

This unblocks face detection pipeline immediately while OCR solution is refined.

---

## Next Steps

**Decision Required:**

1. ✅ **Proceed with Hybrid YOLO + Tesseract** (5 days, meets targets)
2. ⏸️ **Optimize EasyOCR further** (3 days, uncertain outcome)
3. 💰 **Use Cloud API** (immediate, requires budget)
4. 🚀 **MVP without OCR** (immediate, defer OCR to Phase 2)

**Awaiting user decision to proceed.**
