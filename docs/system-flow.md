# DaNang Vibes - System Flow

**Last Updated:** 2026-05-09

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING MACHINE (M1/Mạnh)                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           Processing Web App (Port 8010)                   │ │
│  │  - Browser UI để chọn folder ảnh local                     │ │
│  │  - Job queue management                                    │ │
│  │  - Real-time progress tracking                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Processing Pipeline                           │ │
│  │                                                            │ │
│  │  1. Photo Scanner                                          │ │
│  │     - Filter .jpg/.jpeg files                              │ │
│  │     - Compute checksums (dedupe)                           │ │
│  │     - Extract EXIF metadata                                │ │
│  │                                                            │ │
│  │  2. Thumbnail Generator                                    │ │
│  │     - Resize to max 800px                                  │ │
│  │     - JPEG quality 85                                      │ │
│  │     - Save to thumbnails/                                  │ │
│  │                                                            │ │
│  │  3. OCR Service (Hybrid - Default)                         │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ YOLOv8n Text Detection              │               │ │
│  │     │  - Detect text regions (bibs)       │               │ │
│  │     │  - Confidence threshold: 0.25       │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Crop & Preprocess                   │               │ │
│  │     │  - CLAHE (contrast enhancement)     │               │ │
│  │     │  - Denoise (fastNlMeansDenoising)  │               │ │
│  │     │  - Sharpen (kernel filter)          │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Tesseract OCR                       │               │ │
│  │     │  - Extract text from crops          │               │ │
│  │     │  - Regex: \b\d{2,5}\b (bib numbers) │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Fallback Strategy                   │               │ │
│  │     │  1. Lower YOLO threshold            │               │ │
│  │     │  2. Full-image Tesseract            │               │ │
│  │     │  3. PaddleOCR (if enabled)          │               │ │
│  │     └─────────────────────────────────────┘               │ │
│  │                                                            │ │
│  │  4. Face Recognition (InsightFace buffalo_l)               │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Face Detection                      │               │ │
│  │     │  - Detect faces in photo            │               │ │
│  │     │  - Extract bounding boxes           │               │ │
│  │     │  - Confidence scores                │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Face Embedding                      │               │ │
│  │     │  - Generate 512-dim vectors         │               │ │
│  │     │  - Model: buffalo_l                 │               │ │
│  │     │  - Version: v1                      │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ FAISS Index Builder                 │               │ │
│  │     │  - IndexFlatIP (Inner Product)      │               │ │
│  │     │  - L2 normalization                 │               │ │
│  │     │  - Track vector_id → photo_id       │               │ │
│  │     └─────────────────────────────────────┘               │ │
│  │                                                            │ │
│  │  5. Bundle Export                                          │ │
│  │     - event.db (SQLite)                                    │ │
│  │     - faiss.index                                          │ │
│  │     - thumbnails/ (JPEG)                                   │ │
│  │     - manifest.json (metadata)                             │ │
│  │     - originals_mapping.json (path mapping)                │ │
│  │     - checksums (SHA256)                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│                    dist/events/{slug}/                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ Transfer via USB/SSD
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              WEB SERVER MACHINE (MacBook Pro 2017)              │
│                                                                  │
│                    inbox/bundles/{slug}/                         │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           Web Server App (Port 8000)                       │ │
│  │                                                            │ │
│  │  1. Admin UI (/admin/)                                     │ │
│  │     - Bundle import from inbox/                            │ │
│  │     - Validate bundle integrity                            │ │
│  │     - Publish/unpublish events                             │ │
│  │     - OCR review & correction                              │ │
│  │     - Download statistics                                  │ │
│  │                                                            │ │
│  │  2. Bundle Import Service                                  │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Validation                          │               │ │
│  │     │  - Check manifest.json              │               │ │
│  │     │  - Verify checksums                 │               │ │
│  │     │  - Validate database schema         │               │ │
│  │     │  - Check FAISS index                │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Import to Storage                   │               │ │
│  │     │  - Copy to storage/events/{slug}/   │               │ │
│  │     │  - Create version directory         │               │ │
│  │     │  - Symlink to active/               │               │ │
│  │     └──────────────┬──────────────────────┘               │ │
│  │                    ▼                                       │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Publish Event                       │               │ │
│  │     │  - Update server_events table       │               │ │
│  │     │  - Set is_published = 1             │               │ │
│  │     │  - Load into memory                 │               │ │
│  │     └─────────────────────────────────────┘               │ │
│  │                                                            │ │
│  │  3. Event Loader Service                                   │ │
│  │     - Load published events on startup                     │ │
│  │     - Load FAISS index into memory                         │ │
│  │     - Connect to bundle SQLite database                    │ │
│  │     - Cache originals_mapping.json                         │ │
│  │                                                            │ │
│  │  4. Public Event Pages (/events/{slug}/)                   │ │
│  │     - Event info & stats                                   │ │
│  │     - Photo grid (thumbnails)                              │ │
│  │     - Search interface                                     │ │
│  │                                                            │ │
│  │  5. Search Service                                         │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Search by Bib Number                │               │ │
│  │     │  - Query: ocr_candidates table      │               │ │
│  │     │  - Filter: is_bib = 1               │               │ │
│  │     │  - Match: text or manual_correction │               │ │
│  │     │  - Return: photo_ids + thumbnails   │               │ │
│  │     └─────────────────────────────────────┘               │ │
│  │                                                            │ │
│  │     ┌─────────────────────────────────────┐               │ │
│  │     │ Search by Face (Selfie Upload)      │               │ │
│  │     │  1. Validate model compatibility    │               │ │
│  │     │     - Check embedding_model in DB   │               │ │
│  │     │     - Must be consistent            │               │ │
│  │     │                                     │               │ │
│  │     │  2. Detect face in uploaded selfie  │               │ │
│  │     │     - InsightFaceService            │               │ │
│  │     │     - Same model as processing      │               │ │
│  │     │     - Extract best face             │               │ │
│  │     │                                     │               │ │
│  │     │  3. Generate query embedding        │               │ │
│  │     │     - 512-dim vector                │               │ │
│  │     │     - L2 normalization              │               │ │
│  │     │                                     │               │ │
│  │     │  4. FAISS similarity search         │               │ │
│  │     │     - Load FAISS index              │               │ │
│  │     │     - Search top-k (default: 50)    │               │ │
│  │     │     - Convert distance to similarity│               │ │
│  │     │     - Filter by threshold (0.6)     │               │ │
│  │     │                                     │               │ │
│  │     │  5. Lookup photos                   │               │ │
│  │     │     - Map vector_id → photo_id      │               │ │
│  │     │     - Deduplicate by photo_id       │               │ │
│  │     │     - Return thumbnails + scores    │               │ │
│  │     └─────────────────────────────────────┘               │ │
│  │                                                            │ │
│  │  6. Photo Download Service                                 │ │
│  │     - Resolve original path from mapping                   │ │
│  │     - Validate path safety (no ..)                         │ │
│  │     - Stream file to browser                               │ │
│  │     - Track download stats                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Processing Phase (Máy Mạnh)

```
Input: /path/to/photos/*.jpg
  │
  ├─→ Scanner
  │    └─→ Filter JPG/JPEG
  │         └─→ Compute checksums
  │              └─→ Extract EXIF
  │
  ├─→ Thumbnail Generator
  │    └─→ Resize to 800px
  │         └─→ Save thumbnails/photo_XXXXXX.jpg
  │
  ├─→ OCR Service (Hybrid)
  │    └─→ YOLO detect text regions
  │         └─→ Crop & preprocess
  │              └─→ Tesseract OCR
  │                   └─→ Extract bib numbers
  │                        └─→ INSERT INTO ocr_candidates
  │
  ├─→ Face Service (InsightFace)
  │    └─→ Detect faces
  │         └─→ Generate embeddings (512-dim)
  │              └─→ Add to FAISS index
  │                   └─→ INSERT INTO faces (faiss_vector_id)
  │
  └─→ Bundle Export
       ├─→ event.db (SQLite)
       ├─→ faiss.index (FAISS binary)
       ├─→ thumbnails/ (JPEG files)
       ├─→ manifest.json (metadata)
       └─→ originals_mapping.json (path mapping)

Output: dist/events/{slug}/
```

### 2. Transfer Phase

```
dist/events/{slug}/  →  USB/SSD  →  inbox/bundles/{slug}/
```

### 3. Import Phase (Web Server)

```
inbox/bundles/{slug}/
  │
  ├─→ Validate Bundle
  │    ├─→ Check manifest.json
  │    ├─→ Verify checksums
  │    ├─→ Validate database schema
  │    └─→ Check FAISS index
  │
  ├─→ Import to Storage
  │    ├─→ Copy to storage/events/{slug}/v{timestamp}/
  │    └─→ Symlink active → v{timestamp}
  │
  └─→ Publish Event
       ├─→ INSERT INTO server_events (is_published=1)
       └─→ Load into EventLoader memory
```

### 4. Search Phase (Web Server)

#### A. Search by Bib Number

```
User Input: "1234"
  │
  └─→ Query Database
       └─→ SELECT photo_id FROM ocr_candidates
            WHERE is_bib = 1 AND (text = "1234" OR manual_correction = "1234")
       └─→ Return photo_ids
            └─→ Render thumbnails
```

#### B. Search by Face (Selfie)

```
User Upload: selfie.jpg
  │
  ├─→ Check Model Compatibility
  │    └─→ SELECT DISTINCT embedding_model, embedding_model_version FROM faces
  │         └─→ Must be consistent (InsightFace/v1)
  │
  ├─→ Detect Face in Selfie
  │    └─→ InsightFaceService.detect_and_embed()
  │         └─→ Extract best face (highest confidence + largest area)
  │              └─→ Generate 512-dim embedding
  │
  ├─→ FAISS Search
  │    └─→ Load FAISS index
  │         └─→ Normalize query vector (L2)
  │              └─→ index.search(query, top_k=50)
  │                   └─→ Convert distance to cosine similarity
  │                        └─→ Filter by threshold (>= 0.6)
  │
  └─→ Lookup Photos
       └─→ SELECT photo_id FROM faces WHERE faiss_vector_id = ?
            └─→ Deduplicate by photo_id
                 └─→ Return thumbnails + similarity scores
```

---

## Shared Infrastructure

### Shared Modules (`shared/`)

```
shared/
├── models.py
│   ├── EventMetadata
│   ├── ProcessingMetadata (ocr_model, face_model)
│   ├── BundleStats
│   ├── BundleFiles
│   └── BundleManifest
│
├── bundle.py
│   ├── write_manifest()
│   ├── load_manifest()
│   ├── validate_bundle()
│   └── EMPTY_FAISS_SENTINEL
│
├── database.py
│   ├── initialize_database()
│   └── connect_database()
│
├── checksum.py
│   └── compute_checksum() (SHA256)
│
└── schema.sql
    ├── events
    ├── photos
    ├── thumbnails
    ├── ocr_candidates
    └── faces
```

### Bundle Contract

```json
{
  "bundle_version": "1.0",
  "event": {
    "slug": "test-event",
    "name": "Test Event",
    "date": "2026-05-07",
    "location": "Da Nang",
    "created_at": "2026-05-07T10:00:00Z"
  },
  "processing": {
    "app_version": "0.1.0",
    "ocr_model": "hybrid",           // "hybrid" | "paddle" | "disabled"
    "ocr_model_version": "v1",
    "face_model": "InsightFace",     // "InsightFace" | "disabled"
    "face_model_version": "buffalo_l/v1",
    "processed_at": "2026-05-07T12:00:00Z",
    "processing_machine": "MacBook-Pro.local",
    "processing_duration_seconds": 3600
  },
  "stats": {
    "total_photos": 1000,
    "photos_with_bib_candidates": 850,
    "photos_with_faces": 920,
    "total_faces_detected": 1200,
    "total_bib_candidates": 900,
    "total_thumbnails": 1000
  },
  "files": {
    "database": "event.db",
    "faiss_index": "faiss.index",
    "thumbnails_dir": "thumbnails",
    "originals_mode": "mapping",
    "originals_mapping": "originals_mapping.json"
  },
  "checksums": {
    "event.db": "sha256:abc123...",
    "faiss.index": "sha256:def456..."
  }
}
```

---

## Performance Metrics

### Processing Speed (M1 Pro)

| Component | Time per Photo | 10,000 Photos |
|-----------|----------------|---------------|
| Scanner + Thumbnail | ~0.1s | ~16 min |
| Hybrid OCR (YOLO + Tesseract) | ~0.6s | ~1.6 hours |
| PaddleOCR (alternative) | ~3-5s | ~39 hours |
| InsightFace (buffalo_l) | ~0.37s | ~1 hour |
| **Total (Hybrid)** | **~1.07s** | **~3 hours** |

### Search Speed (MacBook Pro 2017)

| Operation | Time |
|-----------|------|
| Bib number search (DB query) | <50ms |
| Face search (FAISS + DB) | ~200-500ms |
| Thumbnail loading (grid) | ~1-2s (50 photos) |

---

## Model Compatibility

### Face Model Version Tracking

```python
# Processing: Save model info to database
INSERT INTO faces (
    photo_id, bbox, confidence, faiss_vector_id,
    embedding_model,           # "InsightFace"
    embedding_model_version    # "buffalo_l/v1"
)

# Web Server: Validate before search
SELECT DISTINCT embedding_model, embedding_model_version FROM faces
# Must return exactly 1 row (consistent model)
# Use same model for query embedding
```

### OCR Method Tracking

```python
# Processing: Save OCR method to manifest
"ocr_model": "hybrid",        # "hybrid" | "paddle" | "disabled"
"ocr_model_version": "v1"

# Web Server: Display in admin UI
# No validation needed (OCR is one-time processing)
```

---

## Security & Privacy

### Face Embeddings (Biometric Data)

- **Storage:** SQLite database (bundle-local)
- **Access:** Read-only after bundle creation
- **Transmission:** Never logged or transmitted to external services
- **Deletion:** Delete entire bundle to remove embeddings

### Original Photos

- **Mode 1 (mapping):** Path mapping only, originals stay on source disk
- **Mode 2 (embedded):** Copy originals into bundle (for USB transfer)
- **Download:** Path validation (no `..`, must be within base_path)
- **Tracking:** Download stats in server_events table

### Admin Access

- **Authentication:** `ADMIN_TOKEN` environment variable
- **Authorization:** Token required for `/admin/*` routes
- **Operations:** Import, publish, OCR review, stats

---

## Error Handling

### Processing Failures

| Error | Handling |
|-------|----------|
| OCR service unavailable | Skip OCR, continue with faces |
| Face service unavailable | Skip faces, continue with OCR |
| YOLO detection fails | Fallback to Tesseract full-image |
| Tesseract fails | Fallback to PaddleOCR (if enabled) |
| Non-ASCII file paths | Copy to temp file with ASCII name |

### Import Failures

| Error | Handling |
|-------|----------|
| Checksum mismatch | Reject bundle, show error |
| Missing files | Reject bundle, show error |
| Invalid database schema | Reject bundle, show error |
| FAISS index corrupt | Reject bundle, show error |

### Search Failures

| Error | Handling |
|-------|----------|
| No face in selfie | Return message: "Không tìm thấy khuôn mặt" |
| Model mismatch | Return message: "Hãy rebuild embeddings" |
| FAISS index empty | Return message: "Event chưa có face index" |
| Mixed model versions | Return message: "Face embeddings trộn nhiều model" |

---

## Future Enhancements

### Phase 2 (Planned)

- [ ] Multi-signal search (face + bib + timestamp)
- [ ] Face clustering (group similar faces)
- [ ] Manual face labeling UI
- [ ] Batch download (zip multiple photos)

### Phase 3 (Consideration)

- [ ] Google Drive integration (one-way import)
- [ ] Real-time processing (watch folder)
- [ ] Mobile app (React Native)
- [ ] Payment integration (donation model)

---

## Troubleshooting

### Common Issues

**Issue:** FAISS index dimension mismatch  
**Cause:** Changed face model after bundle creation  
**Fix:** Run `processing_cli rebuild-embeddings`

**Issue:** OCR không detect bib numbers  
**Cause:** Bib quá nhỏ, motion blur, hoặc occlusion  
**Fix:** Use manual correction in admin UI

**Issue:** Face search không tìm thấy  
**Cause:** Helmet, sunglasses, side profile, hoặc motion blur  
**Fix:** Combine with bib search, lower similarity threshold

**Issue:** Bundle import fails với checksum error  
**Cause:** File corrupted during USB transfer  
**Fix:** Re-export bundle from processing machine

---

## References

- [Bundle Format](./bundle-format.md)
- [Codebase Summary](./codebase-summary.md)
- [Batch Processing Guide](./batch-processing-guide.md)
- [Scout Report](../plans/reports/scout-260509-danangvibes-architecture-report.md)
