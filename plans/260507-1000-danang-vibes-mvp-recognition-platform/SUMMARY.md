# Tóm tắt: Kiến trúc & Workflow DaNang Vibes

## Tổng quan 1 câu

**2 ứng dụng riêng biệt:** Processing App (M1) xử lý ảnh nặng → export bundle → Web Server (MacBook 2017) import bundle → serve web UI cho user.

---

## Kiến trúc 2-App System

### App 1: Processing CLI (MacBook M1)
**Vai trò:** Xử lý AI nặng (OCR + face recognition)

**Input:** Folder chứa JPG photos  
**Output:** Event bundle (SQLite + FAISS + thumbnails + manifest)

**Công việc:**
1. Scan JPG files
2. Generate thumbnails (800x600px)
3. OCR bib numbers (PaddleOCR)
4. Detect faces + compute embeddings (InsightFace/DeepFace)
5. Build FAISS vector index
6. Export bundle

**Thời gian:** ~2-3s/photo → 5000 photos = 3-4 giờ

---

### App 2: Web Server (MacBook Pro 2017)
**Vai trò:** Serve web UI nhẹ, không chạy AI

**Input:** Event bundle (đã xử lý sẵn)  
**Output:** Public website qua Cloudflare Tunnel

**Công việc:**
1. Import bundle
2. Load SQLite + FAISS (read-only)
3. Serve search UI (bib number + selfie upload)
4. Serve thumbnails
5. Download original JPG
6. Admin UI (OCR review, publish/unpublish)

**Performance:** 
- Bib search: < 200ms
- Selfie search: < 5s
- 10-50 concurrent users OK

---

## Bundle Format (Contract giữa 2 app)

```
ironman-danang-2026/
├── manifest.json           # Metadata: model versions, stats, checksums
├── event.db                # SQLite: photos, OCR, faces, thumbnails
├── faiss.index             # Vector index cho face search
├── thumbnails/             # Thumbnail images
│   ├── photo_001.jpg
│   └── ...
└── originals_mapping.json  # Map photo IDs → original file paths
```

**Portable:** Copy toàn bộ folder này sang máy khác là chạy được.

---

## Workflow Vận hành Thực tế

### Khi có event mới (VD: Ironman Da Nang 2026)

#### Bước 1: Process trên MacBook M1

```bash
# Copy ảnh từ photographer vào SSD
cp -r /Volumes/PhotographerDrive/ironman-2026 /Volumes/SSD/events/ironman-danang-2026/originals

# Process event
cd ~/danangvibes/processing_cli
python -m processing_cli process \
  --source /Volumes/SSD/events/ironman-danang-2026/originals \
  --event-slug ironman-danang-2026 \
  --event-name "Ironman Da Nang 2026" \
  --event-date 2026-06-15 \
  --output ./dist/events

# Validate bundle
python -m processing_cli validate \
  --bundle ./dist/events/ironman-danang-2026
```

**Output:** `./dist/events/ironman-danang-2026/` (bundle sẵn sàng)

---

#### Bước 2: Transfer bundle sang MacBook Pro 2017

**Option A: External SSD** (khuyến nghị)
```bash
# Trên M1: copy ra SSD
cp -r ./dist/events/ironman-danang-2026 /Volumes/ExternalSSD/bundles/

# Rút SSD, cắm vào MacBook 2017
# Trên MacBook 2017: copy vào incoming
cp -r /Volumes/ExternalSSD/bundles/ironman-danang-2026 /Users/admin/incoming/
```

**Option B: rsync qua LAN** (nhanh hơn)
```bash
# Trên M1
rsync -avz --progress \
  ./dist/events/ironman-danang-2026/ \
  admin@macbook2017.local:/Users/admin/incoming/ironman-danang-2026/
```

---

#### Bước 3: Import trên MacBook Pro 2017

```bash
cd ~/danangvibes/web_server

# Import bundle
python -m web_server import \
  --bundle /Users/admin/incoming/ironman-danang-2026 \
  --storage-path /Volumes/SSD/events

# Kết quả: bundle được copy vào
# /Volumes/SSD/events/ironman-danang-2026/releases/v1/
```

---

#### Bước 4: Review & Publish

```bash
# Review OCR qua admin UI
# Mở browser: http://localhost:8000/admin/events/ironman-danang-2026/ocr-review
# Sửa các bib number bị OCR sai

# Config donation QR
# Mở browser: http://localhost:8000/admin/events/ironman-danang-2026/config
# Upload QR code VNPay/MoMo

# Publish event
python -m web_server publish --event-slug ironman-danang-2026
```

---

#### Bước 5: Run Server & Cloudflare Tunnel

```bash
# Terminal 1: Web server
python -m web_server run \
  --host 127.0.0.1 \
  --port 8000 \
  --storage-path /Volumes/SSD/events

# Terminal 2: Cloudflare tunnel
cloudflared tunnel run danangvibes
```

**Public URL:** https://danangvibes.com/events/ironman-danang-2026

---

### Khi cần update event (thêm ảnh, fix OCR)

#### Trên MacBook M1:
```bash
# Process lại với version mới
python -m processing_cli process \
  --source /Volumes/SSD/events/ironman-danang-2026/originals \
  --event-slug ironman-danang-2026 \
  --event-name "Ironman Da Nang 2026" \
  --event-date 2026-06-15 \
  --output ./dist/events

# Transfer sang MacBook 2017 (rsync)
rsync -avz --progress \
  ./dist/events/ironman-danang-2026/ \
  admin@macbook2017.local:/Users/admin/incoming/ironman-danang-2026-v2/
```

#### Trên MacBook Pro 2017:
```bash
# Import version mới
python -m web_server import \
  --bundle /Users/admin/incoming/ironman-danang-2026-v2 \
  --storage-path /Volumes/SSD/events \
  --version v2

# Switch sang version mới
python -m web_server switch-version \
  --event-slug ironman-danang-2026 \
  --version v2

# Nếu có vấn đề, rollback
python -m web_server rollback \
  --event-slug ironman-danang-2026 \
  --version v1
```

---

## Storage Structure trên MacBook Pro 2017

```
/Volumes/SSD/events/
├── ironman-danang-2026/
│   ├── releases/
│   │   ├── v1/  (bundle version 1)
│   │   │   ├── manifest.json
│   │   │   ├── event.db
│   │   │   ├── faiss.index
│   │   │   └── thumbnails/
│   │   └── v2/  (bundle version 2)
│   │       └── ...
│   ├── active -> releases/v2  (symlink: version đang chạy)
│   └── originals/  (optional: ảnh gốc)
├── marathon-danang-2026/
│   └── ...
└── server.db  (server metadata: events, publish status, donation config)
```

**Rollback = switch symlink:** Instant, không cần copy lại data.

---

## User Flow (Người dùng tìm ảnh)

1. Vào https://danangvibes.com
2. Chọn event: "Ironman Da Nang 2026"
3. **Option A:** Nhập bib number (VD: 1234) → Search
4. **Option B:** Upload selfie → Search by face
5. Xem kết quả dạng grid (thumbnails)
6. Click ảnh → Download original JPG
7. Thấy donation QR code (optional)

---

## Tech Stack Summary

| Layer | Processing App (M1) | Web Server (MacBook 2017) |
|-------|---------------------|---------------------------|
| **Language** | Python 3.11+ | Python 3.11+ |
| **Framework** | Click (CLI) | FastAPI |
| **OCR** | PaddleOCR | - |
| **Face** | InsightFace/DeepFace | - |
| **Vector Search** | FAISS (write) | FAISS (read-only) |
| **Database** | SQLite (write) | SQLite (read-only) |
| **UI** | - | Jinja2 + HTMX |
| **Deployment** | - | Cloudflare Tunnel |

---

## Performance Targets

### Processing (M1)
- **2-3s/photo** → 5000 photos = 3-4 giờ
- OCR: ≤ 1s/photo
- Face: ≤ 0.5s/photo

### Serving (MacBook 2017)
- **Bib search:** < 200ms
- **Selfie search:** < 5s
- **Download:** 1-5MB/s
- **Memory:** 2-4GB
- **Concurrent users:** 10-50

---

## Cost Estimate

### One-time
- MacBook M1: $0 (đã có)
- MacBook Pro 2017: $0 (đã có)
- External SSD 1TB: ~$100

### Recurring
- Cloudflare Tunnel: $0 (free tier)
- Domain: ~$12/year
- Electricity: ~$5/month

**Total: ~$17/year** (sau khi mua SSD)

---

## Critical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| **Architecture** | 2 separate apps | M1 xử lý nặng, MacBook 2017 serve nhẹ |
| **Bundle format** | Folder (not zip) | Dễ inspect, không cần unzip |
| **Originals storage** | Mapping (not copy) | Bundle quá lớn nếu copy originals |
| **Transfer method** | External SSD / rsync | Reliable, không phụ thuộc internet |
| **Public access** | Cloudflare Tunnel | Free, không cần port forward |
| **Face model** | InsightFace/DeepFace | Pending license validation (Phase 00) |
| **OCR model** | PaddleOCR | Apache 2.0, accuracy tốt |
| **Vector search** | FAISS | Local, fast, MIT license |
| **Database** | SQLite | Simple, portable, no server needed |
| **UI** | Jinja + HTMX | Lightweight, no heavy JS build |

---

## Next Steps

1. **Phase 00:** Validate InsightFace license (BLOCKING)
2. **Phase 01:** Define shared schema & bundle format
3. **Phase 02:** Build Processing App (M1)
4. **Phase 03:** Build Import/Export workflow
5. **Phase 04:** Build Web Server core
6. **Phase 05:** Build Public Search UI
7. **Phase 06:** Build Admin UI
8. **Phase 07:** Testing & Performance validation
9. **Phase 08:** Deployment & Operations

---

## Unresolved Questions (Must answer before implementation)

- [ ] InsightFace license OK cho donation-based app? (Phase 00)
- [ ] Selfie embedding latency trên MacBook 2017 acceptable? (Phase 07)
- [ ] SSD storage: internal hay external? (Operations)

---

**Đọc chi tiết:** `ARCHITECTURE.md` và các phase files.
