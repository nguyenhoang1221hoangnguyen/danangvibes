# Phase 1: YOLO Bib Detector

**Status:** 🔄 In Progress  
**Duration:** 2 days  
**Owner:** Developer

---

## Context

Need fast bib number detection to crop images before OCR. YOLO can detect text regions or bib-specific objects at ~0.5s/image on M1 Pro.

---

## Objectives

1. Evaluate pre-trained YOLO models for text/bib detection
2. Implement bib detection service
3. Benchmark speed and accuracy on race photos
4. Integrate with existing pipeline

---

## Approach Options

### Option A: Pre-trained Text Detection (Fastest - Recommended)
- Use YOLO pre-trained on text detection (COCO dataset has "text" class)
- Or use YOLOv8/v11 with generic object detection
- No training required, immediate deployment
- May have lower accuracy but acceptable for MVP

### Option B: Fine-tune on Race Photos
- Collect 50-100 race photos
- Manually annotate bib regions
- Fine-tune YOLOv8-nano on custom dataset
- Higher accuracy but requires 1-2 days training

### Option C: Generic Rectangle Detection
- Detect rectangular regions in images
- Filter by size/aspect ratio typical of bibs
- Fastest but lowest accuracy

**Decision: Start with Option A, fallback to Option B if accuracy <60%**

---

## Implementation Steps

### Step 1: Install Ultralytics YOLO
```bash
source venv-ai/bin/activate
pip install ultralytics
```

### Step 2: Create Bib Detection Service
File: `processing_cli/services/bib_detection.py`

```python
from ultralytics import YOLO
from pathlib import Path
from PIL import Image

class BibDetectionService:
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model = YOLO(model_name)
    
    def detect_bib_regions(self, image_path: Path) -> list[dict]:
        """
        Detect bib regions in image
        Returns: [{'bbox': [x, y, w, h], 'confidence': float}]
        """
        results = self.model(image_path)
        # Filter for text/person regions
        # Return bounding boxes
```

### Step 3: Test on Sample Photos
- Test with 10 race photos from dataset
- Measure detection rate and speed
- Validate bounding boxes contain bib numbers

### Step 4: Optimize Detection
- Adjust confidence threshold
- Filter by bbox size/position (bibs typically on torso)
- Handle multiple people in frame

---

## Success Criteria

- ✅ Detection speed: <0.5s per image
- ✅ Detection rate: >60% of images with visible bibs
- ✅ Bounding box accuracy: bbox contains bib number
- ✅ False positive rate: <20%

---

## Testing Plan

1. **Unit tests**: Test detection service with known images
2. **Benchmark**: Measure speed on 100 images
3. **Accuracy**: Manual review of 50 detections
4. **Edge cases**: Test with occlusions, angles, multiple people

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pre-trained model doesn't detect bibs | High | Fallback to Option B (fine-tuning) |
| Too many false positives | Medium | Add filtering by position/size |
| Too slow on M1 | High | Use YOLO nano, reduce image size |
| Multiple bibs per image | Low | Return all detections, OCR all |

---

## Next Steps

1. Install Ultralytics YOLO
2. Create bib detection service
3. Test on 10 sample photos
4. Benchmark and validate
5. Proceed to Phase 2 if success criteria met
