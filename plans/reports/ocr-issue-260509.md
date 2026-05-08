# Báo Cáo: OCR Không Detect Được Bib Numbers

**Date:** 2026-05-09  
**Issue:** Processing app chạy nhưng không tìm thấy bib numbers trong ảnh

---

## Vấn Đề

```
Processing: 5/35 photos
OCR: "No bib numbers found" ❌
Face: Detecting faces ✅
```

## Root Cause Analysis

### 1. YOLO Detection: ✅ Hoạt động
- Detect được 5 regions với confidence 0.22-0.80
- Nhưng detect **generic objects** (người, quần áo), không phải text

### 2. Tesseract OCR: ❌ Thất Bại
- Tất cả 5 crops trả về empty text
- Full-image Tesseract chỉ tìm được "07" (không phải bib)

### 3. Model Issue
**YOLOv8n.pt** là **generic object detection**, không chuyên cho text detection.

---

## Giải Pháp

### Option 1: Dùng Specialized Text Detection Model ✅ Khuyến nghị

Thay YOLOv8n bằng model chuyên text detection:

**A. PaddleOCR Text Detection (Built-in)**
```python
# Đã có trong requirements-ai.txt
# Dùng PaddleOCR thay vì Hybrid
```

**Ưu điểm:**
- Chuyên cho text detection
- Accuracy cao với bib numbers
- Đã cài sẵn

**Nhược điểm:**
- Chậm hơn (~3-5s/ảnh vs 0.6s)

**Cách dùng:**
```bash
# Trong Processing Web UI
OCR Method: [PaddleOCR] ← Chọn này thay vì Hybrid
```

---

### Option 2: Fine-tune YOLO Filters

Tăng filtering để chỉ giữ text-like regions:

```python
# processing_cli/services/text_detection.py:82-100

# Current filters:
min_size = int(img_width * 0.02)  # 2%
max_size = int(img_width * 0.3)   # 30%
aspect_ratio: 0.3-4.0

# Suggested: Stricter for bib numbers
min_size = int(img_width * 0.03)  # 3% (bibs không quá nhỏ)
max_size = int(img_width * 0.15)  # 15% (bibs không quá lớn)
aspect_ratio: 0.5-2.5  # Gần vuông hơn
```

**Ưu điểm:**
- Giữ được tốc độ Hybrid
- Giảm false positives

**Nhược điểm:**
- Vẫn có thể miss bibs nếu góc chụp khác thường

---

### Option 3: Fallback Strategy (Current Implementation)

Hybrid OCR đã có fallback:
1. YOLO + Tesseract (primary)
2. Lower YOLO confidence (fallback 1)
3. Full-image Tesseract (fallback 2)
4. PaddleOCR (fallback 3 - nếu enabled)

**Vấn đề:** Fallback 2 (full-image) chỉ tìm được "07", không phải bib thật.

**Fix:** Enable PaddleOCR fallback:
```python
# processing_cli/commands/process.py
ocr_service = HybridOCRService(enable_paddle_fallback=True)
```

---

## Khuyến Nghị Ngắn Hạn

### ✅ Immediate Fix: Dùng PaddleOCR

**Trong Processing Web UI:**
```
OCR Method: [PaddleOCR] ← Chọn này
```

**Hoặc CLI:**
```bash
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test \
  --event-name "Test" \
  --event-date 2026-05-09 \
  --ocr-method paddle  # ← Thay vì hybrid
```

**Trade-off:**
- ✅ Accuracy cao, detect được bibs
- ❌ Chậm hơn: 10,000 ảnh = ~39 giờ (vs 1.6 giờ với Hybrid)

---

## Khuyến Nghị Dài Hạn

### 1. Train Custom YOLO Model

Train YOLOv8 trên dataset race photos với bib annotations:

```bash
# Collect 500-1000 race photos
# Annotate bib regions (LabelImg, Roboflow)
# Train YOLOv8
yolo train data=bibs.yaml model=yolov8n.pt epochs=50
```

**Kết quả:**
- Model chuyên detect bibs
- Giữ được tốc độ Hybrid (~0.6s/ảnh)
- Accuracy cao

---

### 2. Hybrid Approach: YOLO + PaddleOCR

```python
# Primary: YOLO detect regions
# OCR: PaddleOCR thay vì Tesseract (chính xác hơn)

detections = yolo.detect_text_regions(image)
for det in detections:
    crop = image.crop(det['bbox'])
    text = paddle_ocr.ocr(crop)  # Thay vì tesseract
```

**Ưu điểm:**
- Nhanh hơn full PaddleOCR (chỉ OCR crops, không full image)
- Chính xác hơn Tesseract

---

## Action Items

### Ngay Bây Giờ

1. **Stop processing job hiện tại** (Ctrl+C)
2. **Chọn PaddleOCR** trong UI
3. **Re-run processing**

### Tuần Tới

1. Test PaddleOCR accuracy trên 100-200 ảnh
2. Measure processing time
3. Quyết định: PaddleOCR full-time hay train custom YOLO

### Tháng Tới

1. Collect race photos dataset (500-1000 ảnh)
2. Annotate bib regions
3. Train custom YOLOv8 model
4. Benchmark: Custom YOLO vs PaddleOCR

---

## Debug Files

Đã tạo debug tools:

```bash
# Debug single image
python debug_ocr_single.py "/path/to/photo.jpg"

# Visualize detections
python visualize_ocr.py "/path/to/photo.jpg"
# → Output: debug_output/annotated_*.jpg
# → Output: debug_output/crop_*.jpg
```

**Output location:**
```
debug_output/
├── annotated_027849f42fc88daf8f0f8089ddc324bf.jpg  ← Xem này
├── crop_01_conf0.80.jpg  ← YOLO detected regions
├── crop_01_processed.jpg  ← Sau preprocessing
└── ...
```

**Mở ảnh annotated để xem YOLO detect cái gì:**
```bash
open debug_output/annotated_027849f42fc88daf8f0f8089ddc324bf.jpg
```

---

## Kết Luận

**Vấn đề:** YOLOv8n (generic) không phù hợp cho text detection  
**Giải pháp ngắn hạn:** Dùng PaddleOCR (chậm nhưng chính xác)  
**Giải pháp dài hạn:** Train custom YOLO model cho bibs

**Next Step:** Stop job hiện tại, chọn PaddleOCR, re-run.
