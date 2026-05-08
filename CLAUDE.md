# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan Project

**DaNang Vibes** - Hệ thống nhận diện khuôn mặt/vật thể cho ảnh sự kiện thể thao (chạy/đạp xe/Ironman). Local-first, batch processing, tối ưu cho Mac Pro/MacBook Pro 2017.

## Tech Stack

### Backend & AI
- **Python FastAPI** - API server
- **DeepFace** (MVP) → **InsightFace** (production) - Face recognition
- **YOLO nano/small** (Ultralytics) - Object detection
- **FAISS** (MVP) → **Qdrant** (scale) - Vector search
- **SQLite** (prototype) → **Postgres** (deploy) - Metadata storage
- **Pillow/OpenCV** - Image processing

### Frontend
- React/Next.js hoặc server-rendered UI (chưa quyết định)

### Deployment
- Local filesystem storage (không dùng Drive làm hot path)
- Docker optional (máy yếu có thể chạy trực tiếp Python service)

## Architecture Pipeline

```
[Local/Drive Import] 
  → Ingest (dedupe, EXIF, thumbnail)
  → AI Queue (face detect, embedding, object detect, OCR)
  → [Postgres/SQLite + FAISS/Qdrant]
  → Search API
  → Web UI
```

**Nguyên tắc thiết kế:**
- Batch processing, không real-time
- Resize ảnh trước inference (max 1280/1600px)
- Cache mọi kết quả theo file checksum
- Store embeddings một lần, track `model_version` trong DB
- Thumbnail cho UI grid, không load originals
- Queue concurrency thấp (1-2 workers) do hardware constraint

## Commands

### Development
```bash
# Setup environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Run API server
uvicorn app.main:app --reload

# Run worker (khi có)
python -m app.worker

# Type checking
mypy app/

# Linting
ruff check app/
black app/ --check

# Tests
pytest tests/ -v
pytest tests/test_face_detection.py -v  # Single test file
```

### AI Processing
```bash
# Ingest photos (khi CLI ready)
python -m app.cli ingest --source /path/to/photos

# Rebuild embeddings (khi model version thay đổi)
python -m app.cli rebuild-embeddings --model-version v2
```

## Code Organization

```
app/
├── main.py              # FastAPI app entry
├── api/                 # API routes
│   ├── events.py
│   ├── photos.py
│   └── search.py
├── services/            # Business logic
│   ├── ingest.py        # File import, dedupe, thumbnail
│   ├── face_detection.py
│   ├── object_detection.py
│   ├── embedding.py
│   └── search.py
├── models/              # DB models (SQLAlchemy/Pydantic)
├── vector/              # FAISS/Qdrant wrapper
├── worker/              # Background job queue
└── utils/               # Helpers (image resize, checksum, etc.)
```

## Critical Constraints

### Hardware (Mac Pro 2017)
- **Không** promise real-time processing
- **Luôn** resize ảnh trước inference
- **Luôn** dùng model nano/small
- **Luôn** cache kết quả
- **Tránh** load nhiều ảnh vào memory cùng lúc

### Storage
- **Local disk** là nguồn chính cho processing
- **Google Drive** chỉ dùng import/archive, không làm hot path
- **Thumbnail cache** bắt buộc cho UI

### AI Accuracy
- Face recognition sẽ fail với: sunglasses, helmet, side face, motion blur
- **Cần** bib number OCR để tăng accuracy
- **Cần** review UI cho human correction
- Combine signals: face similarity + bib OCR + timestamp + manual labels

## License Considerations

- **DeepFace**: MIT ✓
- **Ultralytics YOLO**: AGPL-3.0 (ảnh hưởng thương mại/SaaS)
- **InsightFace**: License unclear, cần check trước production
- **FAISS/Qdrant**: Check license trước commercial use

Nếu app thương mại → cân nhắc LibreYOLO (MIT) thay vì Ultralytics.

## Development Workflow

### Phase 1: Technical Spike
1. Test với 200-500 ảnh race
2. Benchmark DeepFace + YOLO trên target Mac
3. Đo time/photo, accuracy failures
4. Quyết định model final

### Phase 2: MVP
1. Ingest CLI
2. Local media folder
3. SQLite metadata
4. Worker queue
5. Basic web UI (event list, photo grid, face cluster, search)

### Phase 3: Race-Specific
1. Bib number OCR
2. Multi-signal search
3. Review/correction UI

### Phase 4: Drive Integration
1. One-way import từ Drive
2. Local cache
3. Retry/resume jobs

## Security & Privacy

- Face embeddings là **biometric data** - sensitive
- **Không** log embeddings publicly
- **Không** commit Drive OAuth tokens (dùng env vars)
- Cần delete/export data path nếu có real users
- Check biometric privacy laws nếu commercial

## Anti-Patterns

- ❌ Fork Immich/PhotoPrism ngay từ đầu (codebase lớn, wrong target)
- ❌ Process ảnh full resolution (quá chậm)
- ❌ Dùng Drive làm live filesystem (unstable)
- ❌ Chỉ dựa vào face recognition (helmets/sunglasses phá recall)
- ❌ Bỏ qua review UI (AI sẽ sai, cần human correction)

## Model Version Tracking

Khi thay đổi model (DeepFace → InsightFace, YOLO v8 → v11):
1. Bump `model_version` trong config
2. Chạy migration script để rebuild embeddings
3. Keep old embeddings với version tag (rollback nếu cần)
4. Log performance comparison

## Unresolved Questions

Cần clarify trước khi implement:
1. Máy chính xác: Mac Pro / iMac Pro / MacBook Pro 2017? CPU/RAM/GPU specs?
2. Số lượng ảnh mỗi event: 1k / 10k / 100k?
3. Search method: selfie upload / bib number / tên VĐV?
4. Deployment: cá nhân/local hay SaaS?
5. Drive: import một chiều hay sync hai chiều?
