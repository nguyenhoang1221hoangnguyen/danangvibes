# Scout Report: DaNang Vibes Architecture Analysis

**Date:** 2026-05-09  
**Scope:** Face indexing, OCR implementation, và sự thống nhất giữa 2 app

---

## 1. Face Indexing Method

### Hiện tại đang sử dụng: **FAISS (Facebook AI Similarity Search)**

**Implementation:**
- **Library:** `faiss-cpu` (IndexFlatIP - Inner Product index)
- **Location:** `processing_cli/services/faiss_builder.py`
- **Dimension:** Dynamic (phụ thuộc vào face model)
- **Normalization:** L2 normalization trước khi add và search
- **Empty index handling:** Sentinel value `b"danangvibes-empty-faiss\n"` khi không có faces

**Face Recognition Model:**
- **MVP Decision (docs):** DeepFace
- **Actual Implementation:** **InsightFace (buffalo_l)** ✓
- **Model Version:** v1
- **Embedding dimension:** 512 (InsightFace buffalo_l standard)

**Lý do chọn InsightFace:**
```python
# processing_cli/services/face_insightface.py:32-39
"""
InsightFace service - better for race photos with occlusions (helmets, sunglasses).

Advantages over DeepFace:
- More robust with partial face occlusion
- Better with side profiles and angles
- Faster processing (2-3x)
- Higher accuracy in challenging conditions
"""
```

**Performance:**
- ~0.37s/ảnh (theo README.md:10)
- Tốt với mũ/kính, ít false positives

**Search Algorithm:**
```python
# web_server/services/search_service.py:111-124
# 1. Normalize query vector với L2
# 2. FAISS search top-k (default: settings.face_top_k)
# 3. Convert distance to cosine similarity: similarity = 1 - (distance^2 / 2)
# 4. Filter by threshold (settings.face_similarity_threshold)
# 5. Deduplicate by photo_id
```

---

## 2. OCR Implementation

### Hiện tại hỗ trợ 3 methods:

#### A. **Hybrid OCR (YOLO + Tesseract)** - Khuyến nghị ✓

**Pipeline:**
```
YOLO text detection → Crop regions → Preprocess → Tesseract OCR → Extract bib numbers
```

**Implementation:** `processing_cli/services/ocr_hybrid.py`

**Components:**
- **Text Detection:** YOLOv8n (nano) via `TextDetectionService`
- **OCR Engine:** Tesseract (pytesseract)
- **Preprocessing:** CLAHE + denoise + sharpen (OpenCV)
- **Bib Extraction:** Regex `\b\d{2,5}\b` (2-5 digits)

**Fallback Strategy:**
1. Primary: YOLO + Tesseract
2. Fallback 1: Lower YOLO confidence threshold
3. Fallback 2: Full-image Tesseract
4. Fallback 3: PaddleOCR (nếu enabled)

**Performance:**
- ~0.6s/ảnh
- 10,000 ảnh: ~1.6 giờ
- **Nhanh gấp 24 lần PaddleOCR**

**Code location:**
- Service: `processing_cli/services/ocr_hybrid.py`
- Usage: `processing_cli/commands/process.py:186-191`

#### B. **PaddleOCR** - Chậm nhưng chính xác

**Performance:**
- ~3-5s/ảnh
- 10,000 ảnh: ~39 giờ

**Implementation:** `processing_cli/services/ocr.py`

#### C. **Tesseract Only** - Fallback

**Implementation:** `processing_cli/services/ocr_tesseract.py`

### OCR Method Selection (Processing CLI)

```python
# processing_cli/commands/process.py:186-203
if ocr_method == "hybrid":
    print("Using Hybrid OCR (YOLO + Tesseract)")
    HybridOCRService = load_hybrid_ocr_service()
    ocr_service = HybridOCRService(enable_paddle_fallback=False)
elif ocr_method == "paddle":
    print("Using PaddleOCR (slower but more accurate)")
    OCRService = load_ocr_service()
    ocr_service = OCRService(...)
else:  # skip
    ocr_service = None
```

---

## 3. Sự Thống Nhất Giữa 2 App

### Architecture Overview

```
┌─────────────────────────────────────┐
│   Processing CLI/Web (Máy mạnh)    │
│  - InsightFace face detection       │
│  - FAISS index builder              │
│  - Hybrid OCR (YOLO + Tesseract)    │
│  - SQLite database creation         │
│  - Thumbnail generation             │
│  - Bundle export                    │
└──────────────┬──────────────────────┘
               │ Bundle (USB/SSD)
               │ - event.db (SQLite)
               │ - faiss.index
               │ - thumbnails/
               │ - manifest.json
               │ - originals_mapping.json
               ▼
┌─────────────────────────────────────┐
│   Web Server (MacBook Pro 2017)    │
│  - Bundle import                    │
│  - FAISS index loading              │
│  - InsightFace search               │
│  - Event publishing                 │
│  - Photo serving                    │
└─────────────────────────────────────┘
```

### Shared Modules (`shared/`)

**Đảm bảo consistency giữa 2 app:**

| Module | Purpose | Used By |
|--------|---------|---------|
| `shared/models.py` | Bundle manifest schema, metadata models | Both apps |
| `shared/bundle.py` | Bundle validation, manifest I/O, FAISS sentinel | Both apps |
| `shared/database.py` | SQLite connection helper | Both apps |
| `shared/checksum.py` | File integrity verification | Both apps |

**Import pattern:**
```python
# Processing CLI
from shared.bundle import load_manifest, write_manifest
from shared.database import initialize_database
from shared.models import BundleManifest, EventMetadata, ...

# Web Server
from shared.bundle import EMPTY_FAISS_SENTINEL, load_manifest
from shared.database import connect_database
from shared.models import BundleManifest
```

### Bundle Contract (`docs/bundle-format.md`)

**Manifest Structure:**
```json
{
  "bundle_version": "1.0",
  "event": { "slug", "name", "date", "location", "created_at" },
  "processing": {
    "app_version": "0.1.0",
    "ocr_model": "hybrid" | "paddle" | "disabled",
    "ocr_model_version": "v1",
    "face_model": "InsightFace",  // Actual: InsightFace, not DeepFace
    "face_model_version": "v1",
    "processed_at": "ISO8601",
    "processing_machine": "hostname",
    "processing_duration_seconds": 1234
  },
  "stats": { ... },
  "files": {
    "database": "event.db",
    "faiss_index": "faiss.index",
    "thumbnails_dir": "thumbnails",
    "originals_mode": "mapping",
    "originals_mapping": "originals_mapping.json"
  },
  "checksums": { "event.db": "sha256...", "faiss.index": "sha256..." }
}
```

### Model Version Compatibility Check

**Web Server kiểm tra model compatibility trước khi search:**

```python
# web_server/services/search_service.py:16-33
def _face_model_pair(self) -> tuple[str, str] | str:
    # Query distinct embedding_model + version từ faces table
    # Return error nếu:
    # - Không có embeddings
    # - Trộn nhiều model/version
    # Return (model_name, version) nếu consistent
```

**Search flow:**
```python
# web_server/services/search_service.py:81-95
stored_model_name, stored_model_version = model_pair
# Khởi tạo InsightFaceService với ĐÚNG model/version từ bundle
faces = InsightFaceService(
    model_name=stored_model_name,
    model_version=stored_model_version
).detect_and_embed(temp_path)
```

### Database Schema Consistency

**Shared schema:** `shared/schema.sql`

**Key tables:**
- `events` - Event metadata
- `photos` - Photo metadata (capture_time, checksum, dimensions)
- `faces` - Face detections với `faiss_vector_id`, `embedding_model`, `embedding_model_version`
- `ocr_candidates` - OCR results với `is_bib`, `text`, `manual_correction`
- `thumbnails` - Thumbnail metadata

**Validation:**
```python
# shared/bundle.py:30-44
def validate_database_schema(db_path: Path) -> None:
    REQUIRED_TABLES = {"events", "photos", "thumbnails", "ocr_candidates", "faces"}
    # Check all tables exist
    # Run PRAGMA integrity_check
```

---

## 4. Potential Issues & Recommendations

### ⚠️ Documentation vs Implementation Mismatch

**Issue:**
- `docs/codebase-summary.md:32` says "DeepFace for MVP"
- `README.md:10` says "InsightFace (buffalo_l)"
- Actual code uses **InsightFace**

**Recommendation:**
- Update `docs/codebase-summary.md` line 32 to reflect InsightFace

### ⚠️ Face Model Naming Inconsistency

**Issue:**
```python
# processing_cli/commands/process.py:208
"disabled" if skip_faces else "DeepFace",  # ← Wrong!
```

Manifest ghi "DeepFace" nhưng thực tế dùng InsightFace.

**Recommendation:**
```python
"disabled" if skip_faces else "InsightFace",
```

### ⚠️ OCR Method in Manifest

**Issue:**
Manifest field `ocr_model` nhận giá trị:
- "hybrid" (YOLO + Tesseract)
- "paddle" (PaddleOCR)
- "disabled"

Nhưng không có validation rõ ràng.

**Recommendation:**
- Add type hint: `Literal["hybrid", "paddle", "disabled"]`
- Validate trong `shared/models.py`

### ✅ Strengths

1. **Shared modules đảm bảo consistency** - Bundle format, database schema, checksums
2. **Model version tracking** - Web server check compatibility trước khi search
3. **FAISS empty index handling** - Sentinel value tránh crash
4. **Hybrid OCR performance** - 24x nhanh hơn PaddleOCR
5. **InsightFace choice** - Phù hợp với race photos (helmets, sunglasses)

---

## 5. File References

### Face Indexing
- `processing_cli/services/faiss_builder.py` - FAISS index builder
- `processing_cli/services/face_insightface.py` - InsightFace service
- `web_server/services/search_service.py` - Face search logic
- `web_server/services/event_loader.py` - FAISS index loading

### OCR
- `processing_cli/services/ocr_hybrid.py` - Hybrid OCR (YOLO + Tesseract)
- `processing_cli/services/ocr.py` - PaddleOCR service
- `processing_cli/services/ocr_tesseract.py` - Tesseract-only service
- `processing_cli/services/text_detection.py` - YOLO text detection

### Shared Infrastructure
- `shared/models.py` - Bundle manifest schema
- `shared/bundle.py` - Bundle validation, I/O
- `shared/database.py` - SQLite helpers
- `shared/checksum.py` - File integrity
- `shared/schema.sql` - Database schema

### Processing
- `processing_cli/commands/process.py` - Main processing pipeline
- `processing_cli/commands/rebuild_embeddings.py` - Rebuild face embeddings

### Web Server
- `web_server/services/event_loader.py` - Bundle loading
- `web_server/services/search_service.py` - Search API
- `web_server/services/importer.py` - Bundle import

---

## Unresolved Questions

1. **InsightFace model download:** Có cache model files ở đâu? Có cần download mỗi lần chạy?
2. **FAISS index size:** Với 10,000 ảnh, FAISS index file size bao nhiêu?
3. **OCR accuracy validation:** Có dataset test với ground truth bib numbers không?
4. **Face similarity threshold tuning:** `settings.face_similarity_threshold` được tune như thế nào?
5. **Processing Web App:** Có dùng chung `shared/` modules không hay duplicate code?
