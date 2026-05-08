# Phase 2: Tesseract OCR Integration

**Status:** 🔄 In Progress  
**Duration:** 1 day  
**Owner:** Developer

---

## Context

YOLO successfully detects bib regions at 0.11s/image with 60% detection rate. Now integrate Tesseract to OCR the cropped regions.

---

## Objectives

1. Crop images to bib regions detected by YOLO
2. Preprocess crops for optimal OCR
3. Run Tesseract with optimized settings
4. Extract and validate bib numbers (2-5 digits)
5. Achieve 0.2s/crop target

---

## Implementation Steps

### Step 1: Create Hybrid OCR Service

Combine YOLO detection + Tesseract OCR in single service.

File: `processing_cli/services/ocr_hybrid.py`

```python
class HybridOCRService:
    def __init__(self):
        self.bib_detector = BibDetectionService()
        self.tesseract = TesseractOCRService()
    
    def detect_bib_numbers(self, image_path: Path) -> list[OCRResult]:
        # 1. YOLO detect bib regions
        # 2. Crop to each region
        # 3. Tesseract OCR on crops
        # 4. Extract 2-5 digit numbers
        # 5. Return results with confidence
```

### Step 2: Optimize Preprocessing

- Grayscale conversion
- Contrast enhancement (CLAHE)
- Noise reduction
- Sharpening for motion blur

### Step 3: Tesseract Configuration

- PSM mode 7 (single line) or 8 (single word)
- Whitelist digits only: `--psm 7 -c tessedit_char_whitelist=0123456789`
- OEM 3 (default, best accuracy)

### Step 4: Post-processing

- Filter results by confidence >0.5
- Validate 2-5 digit pattern
- Remove duplicates
- Sort by confidence

---

## Success Criteria

- ✅ OCR speed: <0.2s per crop
- ✅ Combined speed: <0.5s per image (YOLO + Tesseract)
- ✅ Accuracy: 60-70% correct bib numbers
- ✅ Low false positive rate

---

## Testing Plan

1. Test on 10 images with YOLO detections
2. Manually verify OCR results
3. Measure speed and accuracy
4. Compare with ground truth bib numbers

---

## Next Steps

1. Create HybridOCRService
2. Test on sample images
3. Benchmark performance
4. Proceed to Phase 3 if success criteria met
