# Kiến trúc 2-App System: DaNang Vibes

## Tổng quan

DaNang Vibes gồm **2 ứng dụng độc lập** chạy trên 2 máy khác nhau:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MacBook M1 (Processing)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  APP 1: Processing CLI                                    │  │
│  │  - Scan JPG folder                                        │  │
│  │  - OCR bib numbers (PaddleOCR)                            │  │
│  │  - Face detection & embedding (InsightFace/DeepFace)      │  │
│  │  - Generate thumbnails                                    │  │
│  │  - Build FAISS index                                      │  │
│  │  - Export event bundle                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│                   [Export Bundle]                                │
│                            ↓                                     │
│              dist/events/ironman-danang-2026/                    │
│              ├── manifest.json                                   │
│              ├── event.db (SQLite)                               │
│              ├── faiss.index                                     │
│              ├── thumbnails/                                     │
│              └── originals/ (hoặc path mapping)                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                   [Copy qua SSD/LAN/AirDrop]
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              MacBook Pro 2017 (Serving)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  APP 2: Web Server (FastAPI)                              │  │
│  │  - Import event bundle                                    │  │
│  │  - Load SQLite + FAISS index                              │  │
│  │  - Serve web UI (Jinja + HTMX)                            │  │
│  │  - Search by bib number                                   │  │
│  │  - Search by selfie upload                                │  │
│  │  - Download original JPG                                  │  │
│  │  - Admin UI (publish/unpublish, OCR review)               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│                   [Cloudflare Tunnel]                            │
│                            ↓                                     │
│                   https://danangvibes.com                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## App 1: Processing CLI (MacBook M1)

### Mục đích
Xử lý nặng (AI inference) trên máy mạnh, export kết quả thành bundle sẵn sàng để serve.

### Tech Stack
- **Python 3.11+**
- **Click** - CLI framework
- **PaddleOCR** - Bib number OCR
- **InsightFace/DeepFace** - Face detection & embedding
- **FAISS** - Vector index builder
- **Pillow** - Thumbnail generation
- **SQLAlchemy** - SQLite ORM

### Commands

#### 1. Process Event
```bash
python -m processing_cli process \
  --source /Volumes/SSD/events/ironman-danang-2026/originals \
  --event-slug ironman-danang-2026 \
  --event-name "Ironman Da Nang 2026" \
  --event-date 2026-06-15 \
  --output ./dist/events
```

**Workflow:**
1. Scan tất cả JPG/JPEG trong `--source`
2. Tính checksum mỗi file (SHA256) để dedupe
3. Extract EXIF metadata (capture time, camera info)
4. Generate thumbnail 800x600px → `thumbnails/{photo_id}.jpg`
5. Resize ảnh xuống 1280px max dimension cho inference
6. Run PaddleOCR → extract bib candidates
7. Run face detection → extract face bounding boxes
8. Compute face embeddings → store vectors
9. Build FAISS index từ embeddings
10. Save metadata vào SQLite `event.db`
11. Write `manifest.json` với model versions, stats

**Output:**
```
dist/events/ironman-danang-2026/
├── manifest.json
├── event.db
├── faiss.index
├── thumbnails/
│   ├── photo_001.jpg
│   ├── photo_002.jpg
│   └── ...
└── originals_mapping.json  (nếu originals không copy)
```

#### 2. Rebuild Embeddings (khi đổi model)
```bash
python -m processing_cli rebuild-embeddings \
  --bundle ./dist/events/ironman-danang-2026 \
  --model-version v2
```

#### 3. Validate Bundle
```bash
python -m processing_cli validate \
  --bundle ./dist/events/ironman-danang-2026
```

### Configuration
File: `processing_cli/config.yaml`
```yaml
ocr:
  model: paddleocr
  lang: en
  confidence_threshold: 0.6

face:
  model: insightface  # hoặc deepface
  detector: retinaface
  embedding_model: arcface_r100_v1

processing:
  max_image_size: 1280
  thumbnail_size: [800, 600]
  batch_size: 1  # sequential cho máy yếu
  cache_embeddings: true

output:
  include_originals: false  # true = copy originals vào bundle
  compress_bundle: false    # true = zip bundle
```

---

## App 2: Web Server (MacBook Pro 2017)

### Mục đích
Serve web UI nhẹ, chỉ load dữ liệu đã xử lý sẵn, không chạy AI inference nặng.

### Tech Stack
- **FastAPI** - Web framework
- **Jinja2** - Template engine
- **HTMX** - Dynamic UI without heavy JS
- **SQLAlchemy** - SQLite ORM
- **FAISS** - Vector search (read-only)
- **Uvicorn** - ASGI server

### API Endpoints

#### Public Routes
```
GET  /                          → Landing page (list events)
GET  /events/{slug}             → Event search page
POST /events/{slug}/search/bib  → Search by bib number
POST /events/{slug}/search/face → Search by selfie upload
GET  /events/{slug}/photos/{id}/thumbnail → Serve thumbnail
GET  /events/{slug}/photos/{id}/download  → Download original JPG
GET  /donate                    → Donation page (QR code)
```

#### Admin Routes (protected)
```
GET  /admin/                    → Admin dashboard
GET  /admin/events              → Event list
POST /admin/events/import       → Import bundle
POST /admin/events/{slug}/publish   → Publish event
POST /admin/events/{slug}/unpublish → Unpublish event
GET  /admin/events/{slug}/ocr-review → OCR review page
POST /admin/events/{slug}/ocr-correct → Manual bib correction
GET  /admin/events/{slug}/config     → Donation config
POST /admin/events/{slug}/config     → Update donation config
```

### Commands

#### 1. Import Bundle
```bash
python -m web_server import \
  --bundle /Volumes/SSD/incoming/ironman-danang-2026 \
  --storage-path /Volumes/SSD/events
```

**Workflow:**
1. Validate `manifest.json`
2. Check SQLite integrity
3. Check FAISS index integrity
4. Verify thumbnails exist
5. Verify originals accessible (nếu dùng mapping)
6. Copy/move bundle vào `storage-path/ironman-danang-2026/releases/v1/`
7. Create symlink `active → releases/v1`
8. Register event trong server database

**Directory structure sau import:**
```
/Volumes/SSD/events/
├── ironman-danang-2026/
│   ├── releases/
│   │   ├── v1/  (imported bundle)
│   │   │   ├── manifest.json
│   │   │   ├── event.db
│   │   │   ├── faiss.index
│   │   │   └── thumbnails/
│   │   └── v2/  (nếu có update)
│   ├── active → releases/v1  (symlink)
│   └── originals/  (nếu copy originals)
└── server.db  (server metadata: events, publish status, admin config)
```

#### 2. Run Server
```bash
python -m web_server run \
  --host 0.0.0.0 \
  --port 8000 \
  --storage-path /Volumes/SSD/events
```

#### 3. Publish Event
```bash
python -m web_server publish \
  --event-slug ironman-danang-2026
```

#### 4. Rollback Event
```bash
python -m web_server rollback \
  --event-slug ironman-danang-2026 \
  --version v1
```

### Configuration
File: `web_server/config.yaml`
```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 2
  storage_path: /Volumes/SSD/events

search:
  bib_exact_match: true
  face_top_k: 50
  face_similarity_threshold: 0.6

upload:
  max_selfie_size_mb: 10
  allowed_mime_types: [image/jpeg, image/png]

rate_limit:
  selfie_search: 5/minute
  download: 20/minute

admin:
  secret_token: ${ADMIN_TOKEN}  # from env var

cloudflare:
  tunnel_name: danangvibes
  tunnel_token: ${CF_TUNNEL_TOKEN}
```

---

## Bundle Format (Contract giữa 2 app)

### manifest.json
```json
{
  "bundle_version": "1.0",
  "event": {
    "slug": "ironman-danang-2026",
    "name": "Ironman Da Nang 2026",
    "date": "2026-06-15",
    "created_at": "2026-05-10T10:30:00Z"
  },
  "processing": {
    "app_version": "0.1.0",
    "ocr_model": "paddleocr-v2.7",
    "face_model": "insightface-arcface_r100_v1",
    "processed_at": "2026-05-10T10:30:00Z",
    "processing_machine": "MacBook-M1"
  },
  "stats": {
    "total_photos": 5420,
    "photos_with_bib": 3890,
    "photos_with_faces": 4120,
    "total_faces": 8340,
    "total_bib_candidates": 4200
  },
  "files": {
    "database": "event.db",
    "faiss_index": "faiss.index",
    "thumbnails_dir": "thumbnails",
    "originals_mode": "mapping",  // "mapping" hoặc "included"
    "originals_mapping": "originals_mapping.json"
  },
  "checksums": {
    "event.db": "sha256:abc123...",
    "faiss.index": "sha256:def456..."
  }
}
```

### event.db Schema (SQLite)
```sql
-- Events
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Photos
CREATE TABLE photos (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL,
  filename TEXT NOT NULL,
  checksum TEXT UNIQUE NOT NULL,
  original_path TEXT,  -- relative hoặc absolute
  file_size INTEGER,
  width INTEGER,
  height INTEGER,
  capture_time TIMESTAMP,
  exif_data JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES events(id)
);

-- Thumbnails
CREATE TABLE thumbnails (
  id INTEGER PRIMARY KEY,
  photo_id INTEGER NOT NULL,
  path TEXT NOT NULL,  -- relative path trong bundle
  width INTEGER,
  height INTEGER,
  FOREIGN KEY (photo_id) REFERENCES photos(id)
);

-- OCR Candidates
CREATE TABLE ocr_candidates (
  id INTEGER PRIMARY KEY,
  photo_id INTEGER NOT NULL,
  text TEXT NOT NULL,
  confidence REAL,
  bbox JSON,  -- [x, y, w, h]
  is_bib BOOLEAN DEFAULT 0,
  manual_correction TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (photo_id) REFERENCES photos(id)
);

-- Faces
CREATE TABLE faces (
  id INTEGER PRIMARY KEY,
  photo_id INTEGER NOT NULL,
  bbox JSON,  -- [x, y, w, h]
  confidence REAL,
  faiss_vector_id INTEGER,  -- mapping to FAISS index
  embedding_model TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (photo_id) REFERENCES photos(id)
);

-- Indexes
CREATE INDEX idx_photos_event ON photos(event_id);
CREATE INDEX idx_photos_checksum ON photos(checksum);
CREATE INDEX idx_ocr_photo ON ocr_candidates(photo_id);
CREATE INDEX idx_ocr_text ON ocr_candidates(text);
CREATE INDEX idx_faces_photo ON faces(photo_id);
CREATE INDEX idx_faces_vector ON faces(faiss_vector_id);
```

### originals_mapping.json (nếu không copy originals)
```json
{
  "base_path": "/Volumes/SSD/events/ironman-danang-2026/originals",
  "mappings": {
    "photo_001": "IMG_1234.JPG",
    "photo_002": "IMG_1235.JPG"
  }
}
```

---

## Workflow Triển khai Chi tiết

### Bước 1: Setup Processing App (MacBook M1)

```bash
# Clone repo
git clone <repo-url>
cd danangvibes

# Setup processing app
cd processing_cli
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download AI models (one-time)
python -m processing_cli download-models

# Test với sample photos
python -m processing_cli process \
  --source ./samples/ironman-sample \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-01 \
  --output ./dist/events

# Validate bundle
python -m processing_cli validate \
  --bundle ./dist/events/test-event
```

### Bước 2: Copy Bundle sang MacBook Pro 2017

**Option A: External SSD**
```bash
# Trên M1: copy bundle ra SSD
cp -r ./dist/events/test-event /Volumes/ExternalSSD/bundles/

# Rút SSD, cắm vào MacBook 2017
# Trên MacBook 2017:
cp -r /Volumes/ExternalSSD/bundles/test-event /Users/admin/incoming/
```

**Option B: AirDrop** (nếu bundle nhỏ < 5GB)
```bash
# Trên M1: zip bundle
cd ./dist/events
zip -r test-event.zip test-event/

# AirDrop test-event.zip sang MacBook 2017
# Trên MacBook 2017: unzip
unzip test-event.zip -d /Users/admin/incoming/
```

**Option C: rsync qua LAN**
```bash
# Trên MacBook 2017: enable Remote Login (SSH)
# System Preferences → Sharing → Remote Login

# Trên M1: rsync
rsync -avz --progress \
  ./dist/events/test-event/ \
  admin@192.168.1.100:/Users/admin/incoming/test-event/
```

### Bước 3: Setup Web Server (MacBook Pro 2017)

```bash
# Clone repo (hoặc copy từ M1)
cd danangvibes

# Setup web server
cd web_server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set env vars
export ADMIN_TOKEN="your-secret-token-here"
export CF_TUNNEL_TOKEN="your-cloudflare-tunnel-token"

# Import bundle
python -m web_server import \
  --bundle /Users/admin/incoming/test-event \
  --storage-path /Volumes/SSD/events

# Publish event
python -m web_server publish --event-slug test-event

# Run server locally (test)
python -m web_server run \
  --host 127.0.0.1 \
  --port 8000 \
  --storage-path /Volumes/SSD/events
```

### Bước 4: Setup Cloudflare Tunnel

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Login
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create danangvibes

# Configure tunnel
cat > ~/.cloudflared/config.yml <<EOF
tunnel: danangvibes
credentials-file: /Users/admin/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: danangvibes.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run danangvibes
```

### Bước 5: Run Production

```bash
# Terminal 1: Web server
cd web_server
source venv/bin/activate
python -m web_server run \
  --host 127.0.0.1 \
  --port 8000 \
  --storage-path /Volumes/SSD/events

# Terminal 2: Cloudflare tunnel
cloudflared tunnel run danangvibes
```

**Hoặc dùng systemd/launchd để auto-start:**

File: `~/Library/LaunchAgents/com.danangvibes.server.plist`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.danangvibes.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/admin/danangvibes/web_server/venv/bin/python</string>
        <string>-m</string>
        <string>web_server</string>
        <string>run</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
        <string>--storage-path</string>
        <string>/Volumes/SSD/events</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/admin/logs/danangvibes.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/admin/logs/danangvibes.error.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.danangvibes.server.plist
```

---

## Workflow Vận hành Thực tế

### Khi có event mới (VD: Ironman Da Nang 2026)

**Trên MacBook M1:**
```bash
# 1. Copy ảnh từ photographer vào SSD
cp -r /Volumes/PhotographerDrive/ironman-2026 /Volumes/SSD/events/ironman-danang-2026/originals

# 2. Process event
cd ~/danangvibes/processing_cli
source venv/bin/activate
python -m processing_cli process \
  --source /Volumes/SSD/events/ironman-danang-2026/originals \
  --event-slug ironman-danang-2026 \
  --event-name "Ironman Da Nang 2026" \
  --event-date 2026-06-15 \
  --output ./dist/events

# 3. Validate
python -m processing_cli validate \
  --bundle ./dist/events/ironman-danang-2026

# 4. Copy sang MacBook 2017 qua rsync
rsync -avz --progress \
  ./dist/events/ironman-danang-2026/ \
  admin@macbook2017.local:/Users/admin/incoming/ironman-danang-2026/
```

**Trên MacBook Pro 2017:**
```bash
# 5. Import bundle
cd ~/danangvibes/web_server
source venv/bin/activate
python -m web_server import \
  --bundle /Users/admin/incoming/ironman-danang-2026 \
  --storage-path /Volumes/SSD/events

# 6. Review OCR qua admin UI
# Mở browser: http://localhost:8000/admin/events/ironman-danang-2026/ocr-review
# Sửa các bib number bị OCR sai

# 7. Config donation QR
# Mở browser: http://localhost:8000/admin/events/ironman-danang-2026/config
# Upload QR code VNPay/MoMo

# 8. Publish event
python -m web_server publish --event-slug ironman-danang-2026

# 9. Test public URL
# https://danangvibes.com/events/ironman-danang-2026
```

### Khi cần update event (VD: thêm ảnh, fix OCR)

**Trên MacBook M1:**
```bash
# 1. Process lại với version mới
python -m processing_cli process \
  --source /Volumes/SSD/events/ironman-danang-2026/originals \
  --event-slug ironman-danang-2026 \
  --event-name "Ironman Da Nang 2026" \
  --event-date 2026-06-15 \
  --output ./dist/events \
  --version v2  # version mới

# 2. Copy sang MacBook 2017
rsync -avz --progress \
  ./dist/events/ironman-danang-2026/ \
  admin@macbook2017.local:/Users/admin/incoming/ironman-danang-2026-v2/
```

**Trên MacBook Pro 2017:**
```bash
# 3. Import version mới
python -m web_server import \
  --bundle /Users/admin/incoming/ironman-danang-2026-v2 \
  --storage-path /Volumes/SSD/events

# 4. Switch sang version mới
python -m web_server switch-version \
  --event-slug ironman-danang-2026 \
  --version v2

# 5. Nếu có vấn đề, rollback
python -m web_server rollback \
  --event-slug ironman-danang-2026 \
  --version v1
```

---

## Performance Expectations

### Processing (MacBook M1)
- **OCR**: ~0.5-1s/photo
- **Face detection**: ~0.3-0.5s/photo
- **Face embedding**: ~0.2s/face
- **Thumbnail**: ~0.1s/photo
- **Total**: ~2-3s/photo
- **5000 photos**: ~3-4 giờ

### Serving (MacBook Pro 2017)
- **Bib search**: < 200ms
- **Selfie search**: 2-5s (nếu > 5s → cần optimize)
- **Thumbnail load**: < 100ms
- **Original download**: 1-5MB/s (tùy Cloudflare Tunnel bandwidth)
- **Memory usage**: 2-4GB
- **Concurrent users**: 10-50 OK

---

## Security Checklist

### Processing App
- [ ] Không log embeddings ra console/file
- [ ] Validate input paths (prevent path traversal)
- [ ] Checksum verification cho cache

### Web Server
- [ ] Admin token trong env var (không hardcode)
- [ ] Rate limiting cho selfie upload (5/minute/IP)
- [ ] File upload validation (magic bytes, size limit)
- [ ] Path traversal prevention cho download endpoint
- [ ] CORS config cho Cloudflare Tunnel
- [ ] HTTPS only (qua Cloudflare)
- [ ] Admin routes protected (bearer token)

---

## Monitoring & Logging

### Processing App
```python
# Log format
{
  "timestamp": "2026-05-10T10:30:00Z",
  "level": "INFO",
  "event_slug": "ironman-danang-2026",
  "stage": "ocr",
  "photo_id": "photo_001",
  "duration_ms": 850,
  "status": "success"
}
```

### Web Server
```python
# Log format
{
  "timestamp": "2026-05-10T10:30:00Z",
  "level": "INFO",
  "endpoint": "/events/ironman-danang-2026/search/bib",
  "method": "POST",
  "ip": "1.2.3.4",
  "user_agent": "Mozilla/5.0...",
  "duration_ms": 120,
  "status": 200,
  "bib_query": "1234"
}
```

### Health Check Endpoint
```
GET /health

Response:
{
  "status": "healthy",
  "uptime_seconds": 86400,
  "memory_usage_mb": 2048,
  "disk_usage_gb": 120,
  "active_events": 3,
  "total_photos": 15000
}
```

---

## Disaster Recovery

### Backup Strategy
```bash
# Backup server database (metadata)
cp /Volumes/SSD/events/server.db /Volumes/Backup/server.db.$(date +%Y%m%d)

# Backup event bundles (nếu cần)
rsync -avz /Volumes/SSD/events/ /Volumes/Backup/events/
```

### Rollback Procedure
```bash
# Nếu version mới có vấn đề
python -m web_server rollback \
  --event-slug ironman-danang-2026 \
  --version v1

# Nếu server database corrupt
cp /Volumes/Backup/server.db.20260510 /Volumes/SSD/events/server.db
python -m web_server run --storage-path /Volumes/SSD/events
```

---

## Cost Estimate

### One-time
- MacBook M1 (đã có): $0
- MacBook Pro 2017 (đã có): $0
- External SSD 1TB: ~$100
- Cloudflare Tunnel: $0 (free tier)

### Recurring
- Cloudflare Tunnel bandwidth: $0 (free tier, 10-50 users OK)
- Domain: ~$12/year
- Electricity: ~$5/month (MacBook 2017 chạy 24/7)

**Total: ~$17/year** (sau khi mua SSD)

---

Đây là kiến trúc chi tiết cho 2-app system. Tôi có cập nhật lại plan files với structure này không?
