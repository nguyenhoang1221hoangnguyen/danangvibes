# Hướng Dẫn Sử Dụng DaNang Vibes

**Version:** 1.0  
**Last Updated:** 2026-05-09

---

## Tổng Quan

DaNang Vibes gồm 2 ứng dụng chạy trên 2 máy riêng biệt:

1. **Processing Web App** (Máy mạnh - M1/M2) - Xử lý ảnh, tạo bundle
2. **Web Server App** (MacBook Pro 2017) - Serve web, search, download

**Workflow:**
```
Máy 1: Xử lý ảnh → Tạo bundle → Copy vào USB/SSD
                                    ↓
Máy 2: Import bundle → Publish event → User search & download
```

---

## Phần 1: Processing Web App (Máy Xử Lý)

### 1.1. Setup Lần Đầu

#### Bước 1: Cài Python 3.11+

```bash
# macOS
brew install python@3.11

# Kiểm tra version
python3.11 --version
```

#### Bước 2: Setup môi trường

```bash
cd /Users/nguyenhoang/Desktop/2026/ungDung/danangvibes
scripts/setup-local-env.sh
```

Script này sẽ:
- Tạo `venv-ai/` với Python 3.11
- Cài dependencies: FastAPI, InsightFace, YOLO, Tesseract, etc.
- Tải models: InsightFace buffalo_l, YOLOv8n

**Thời gian:** ~5-10 phút (tùy tốc độ mạng)

#### Bước 3: Kiểm tra cài đặt

```bash
source venv-ai/bin/activate
python -c "import insightface; print('✅ InsightFace OK')"
python -c "from ultralytics import YOLO; print('✅ YOLO OK')"
python -c "import pytesseract; print('✅ Tesseract OK')"
```

Nếu có lỗi, xem [Troubleshooting](#troubleshooting).

---

### 1.2. Khởi Động Processing Web App

```bash
scripts/start-processing-app.sh
```

**Hoặc khởi động thủ công:**

```bash
cd /Users/nguyenhoang/Desktop/2026/ungDung/danangvibes
source venv-ai/bin/activate
python -m processing_web run
```

**Output:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8010
```

Mở browser: **http://127.0.0.1:8010**

---

### 1.3. Xử Lý Ảnh Event

#### Bước 1: Chuẩn bị ảnh

Đảm bảo ảnh đã copy vào máy xử lý:
- Format: `.jpg` hoặc `.jpeg`
- Đường dẫn: `/Volumes/SSD/photos/event-name/` hoặc bất kỳ folder nào

**Lưu ý:** Không xử lý trực tiếp từ Google Drive (chậm). Copy về local trước.

#### Bước 2: Tạo job mới

Trong Processing Web UI:

1. **Chọn thư mục ảnh:**
   - Click **"Chọn thư mục ảnh nhanh"** để browse
   - Hoặc nhập path thủ công: `/Volumes/SSD/photos/ironman-danang-2026/`

2. **Nhập thông tin event:**
   ```
   Event Slug:     ironman-danang-2026
   Event Name:     Ironman Da Nang 2026
   Event Date:     2026-05-07
   Event Location: Da Nang, Vietnam
   ```

   **Event Slug Rules:**
   - Chỉ lowercase, số, và dấu gạch ngang
   - Ví dụ: `ironman-danang-2026`, `marathon-hcm-2026`

3. **Chọn OCR Method:**

   | Method | Speed | Accuracy | Khuyến nghị |
   |--------|-------|----------|-------------|
   | **Hybrid (YOLO + Tesseract)** | ⚡⚡⚡ Nhanh | ⭐⭐⭐ Tốt | ✅ Production |
   | PaddleOCR | 🐌 Chậm 24x | ⭐⭐⭐⭐ Rất tốt | Testing only |
   | Skip OCR | ⚡⚡⚡ Nhanh nhất | - | Nếu không cần bib |

   **Khuyến nghị:** Chọn **Hybrid** cho production.

4. **Options:**
   - ☑️ **Copy ảnh gốc vào bundle** - Tick nếu muốn bundle độc lập (USB transfer)
   - ☐ **Skip OCR** - Bỏ tick (đã chọn method ở trên)
   - ☐ **Skip Face Detection** - Bỏ tick (cần face search)

5. Click **"Start Processing"**

#### Bước 3: Theo dõi tiến độ

UI sẽ hiển thị:
```
Job Status: Running
Progress: 1234/10000 photos (12.34%)
Elapsed: 00:15:30
Estimated Remaining: 01:45:00

Current: Processing photo_001234.jpg
- Thumbnail: ✅
- OCR: ✅ Found bib: 1234
- Face: ✅ Detected 1 face
```

**Thời gian ước tính:**
- 1,000 ảnh: ~18 phút
- 5,000 ảnh: ~1.5 giờ
- 10,000 ảnh: ~3 giờ

#### Bước 4: Hoàn thành

Khi job hoàn tất:
```
✅ Job Completed!

Output: dist/events/ironman-danang-2026/

Stats:
- Total photos: 10,000
- Photos with bibs: 8,500
- Photos with faces: 9,200
- Total faces: 12,000
- Processing time: 02:58:45

Bundle size: 2.5 GB
```

---

### 1.4. Copy Bundle Sang Máy Server

#### Option 1: USB/SSD (Khuyến nghị)

```bash
# Copy bundle vào USB
cp -r dist/events/ironman-danang-2026 /Volumes/USB/bundles/

# Eject USB
diskutil eject /Volumes/USB
```

#### Option 2: Network Transfer

```bash
# Sử dụng rsync qua network
rsync -avz --progress \
  dist/events/ironman-danang-2026/ \
  user@server-ip:/path/to/danangvibes/inbox/bundles/ironman-danang-2026/
```

---

## Phần 2: Web Server App (Máy Serve)

### 2.1. Setup Lần Đầu

#### Bước 1: Cài Python 3.11+

```bash
brew install python@3.11
```

#### Bước 2: Setup môi trường

```bash
cd /Users/nguyenhoang/Desktop/2026/ungDung/danangvibes
scripts/setup-local-env.sh
```

**Lưu ý:** Web server KHÔNG cần AI dependencies nặng như processing app.

#### Bước 3: Tạo thư mục inbox

```bash
mkdir -p inbox/bundles
```

---

### 2.2. Khởi Động Web Server

```bash
ADMIN_TOKEN="your-secret-token" scripts/start-web-app.sh
```

**Hoặc thủ công:**

```bash
cd /Users/nguyenhoang/Desktop/2026/ungDung/danangvibes
source venv/bin/activate
ADMIN_TOKEN="your-secret-token" python -m web_server run
```

**Output:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**URLs:**
- Admin UI: **http://127.0.0.1:8000/admin/**
- Public: **http://127.0.0.1:8000/**

---

### 2.3. Import Bundle

#### Bước 1: Copy bundle vào inbox

```bash
# Từ USB
cp -r /Volumes/USB/bundles/ironman-danang-2026 inbox/bundles/

# Kiểm tra
ls -lh inbox/bundles/ironman-danang-2026/
```

Phải có các files:
```
manifest.json
event.db
faiss.index
thumbnails/
originals_mapping.json
```

#### Bước 2: Import qua Admin UI

1. Mở **http://127.0.0.1:8000/admin/**
2. Nhập **Admin Token** (đã set ở `ADMIN_TOKEN`)
3. Scroll xuống **"Import Bundle từ USB/SSD"**
4. Chọn bundle: `ironman-danang-2026`
5. Options:
   - ☑️ **Publish ngay sau khi import** (khuyến nghị)
   - ☑️ **Verify checksums** (khuyến nghị)
6. Click **"Import Bundle"**

#### Bước 3: Theo dõi import

```
Importing bundle: ironman-danang-2026
✅ Validating manifest...
✅ Verifying checksums...
✅ Checking database schema...
✅ Validating FAISS index...
✅ Copying to storage...
✅ Creating symlink...
✅ Publishing event...

Import completed in 45 seconds.
```

---

### 2.4. Quản Lý Events

#### Admin Dashboard

Mở **http://127.0.0.1:8000/admin/**

**Sections:**

1. **Published Events**
   - List các events đã publish
   - Stats: photos, bibs, faces, downloads
   - Actions: Unpublish, View, Delete

2. **Import Bundle**
   - Import bundles từ inbox/
   - Validate & publish

3. **OCR Review**
   - Review bib candidates
   - Manual correction
   - Mark as reviewed

4. **Download Statistics**
   - Top downloaded photos
   - Download trends
   - User activity

#### Publish/Unpublish Event

**Publish:**
```
Event: ironman-danang-2026
Status: Imported (not published)
Action: [Publish] ← Click
```

**Unpublish:**
```
Event: ironman-danang-2026
Status: Published
Action: [Unpublish] ← Click
```

**Lưu ý:** Unpublish sẽ ẩn event khỏi public, KHÔNG xóa data.

---

## Phần 3: User Experience (Public)

### 3.1. Truy Cập Event Page

URL: **http://127.0.0.1:8000/events/ironman-danang-2026**

**Event Page hiển thị:**
```
┌─────────────────────────────────────────┐
│  Ironman Da Nang 2026                   │
│  📅 2026-05-07  📍 Da Nang, Vietnam     │
│                                         │
│  📊 Stats:                              │
│  - 10,000 photos                        │
│  - 8,500 with bib numbers               │
│  - 9,200 with faces                     │
│                                         │
│  🔍 Search:                             │
│  ┌─────────────────────────────────┐   │
│  │ [Bib Number] [Face Upload]      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

### 3.2. Search by Bib Number

#### Bước 1: Nhập số bib

```
Search by Bib Number: [1234] [Search]
```

#### Bước 2: Xem kết quả

```
Found 12 photos with bib #1234

┌─────┬─────┬─────┬─────┐
│ 📷  │ 📷  │ 📷  │ 📷  │
│ 001 │ 002 │ 003 │ 004 │
└─────┴─────┴─────┴─────┘

Click vào ảnh để xem full size và download.
```

---

### 3.3. Search by Face (Selfie Upload)

#### Bước 1: Upload selfie

```
Search by Face:
┌─────────────────────────┐
│  [Choose File]          │
│  or drag & drop         │
└─────────────────────────┘

[Upload & Search]
```

**Tips cho selfie tốt:**
- ✅ Khuôn mặt rõ, nhìn thẳng
- ✅ Ánh sáng đủ
- ✅ Không đeo kính/mũ
- ❌ Tránh góc nghiêng
- ❌ Tránh mờ/motion blur

#### Bước 2: Xem kết quả

```
Found 8 similar faces (similarity > 60%)

┌─────────────┬─────────────┬─────────────┐
│ 📷 95%      │ 📷 87%      │ 📷 82%      │
│ photo_1234  │ photo_5678  │ photo_9012  │
└─────────────┴─────────────┴─────────────┘

Sorted by similarity score (highest first)
```

**Similarity Score:**
- 90-100%: Rất giống (likely same person)
- 70-89%: Giống (possible match)
- 60-69%: Hơi giống (check manually)
- <60%: Không hiển thị

---

### 3.4. Download Photos

#### Option 1: Download từng ảnh

```
Click vào thumbnail → Full size view → [Download] button
```

#### Option 2: Batch download (Future)

```
☑️ Select multiple photos
[Download Selected (5 photos)]
→ Downloads as ZIP file
```

---

## Phần 4: Troubleshooting

### 4.1. Processing App Issues

#### Issue: "InsightFace not found"

**Cause:** Chưa cài AI dependencies

**Fix:**
```bash
source venv-ai/bin/activate
pip install insightface onnxruntime
```

#### Issue: "YOLO model download failed"

**Cause:** Network issue hoặc disk full

**Fix:**
```bash
# Download manually
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

#### Issue: "Tesseract not found"

**Cause:** Chưa cài Tesseract binary

**Fix:**
```bash
# macOS
brew install tesseract

# Verify
tesseract --version
```

#### Issue: Job stuck at "Processing..."

**Cause:** Ảnh corrupt hoặc out of memory

**Fix:**
1. Check logs: `tail -f processing_web/logs/app.log`
2. Restart app
3. Skip ảnh lỗi bằng cách xóa khỏi source folder

---

### 4.2. Web Server Issues

#### Issue: "Bundle validation failed: checksum mismatch"

**Cause:** File corrupt trong quá trình transfer

**Fix:**
```bash
# Re-copy bundle từ processing machine
# Hoặc re-export bundle
```

#### Issue: "FAISS index dimension mismatch"

**Cause:** Bundle được tạo với model khác

**Fix:**
```bash
# Rebuild embeddings trên processing machine
python -m processing_cli rebuild-embeddings \
  --bundle dist/events/ironman-danang-2026
```

#### Issue: Face search returns "Model mismatch"

**Cause:** Bundle có mixed model versions

**Fix:**
```bash
# Check database
sqlite3 storage/events/ironman-danang-2026/active/event.db \
  "SELECT DISTINCT embedding_model, embedding_model_version FROM faces"

# Nếu có nhiều rows → rebuild embeddings
```

---

### 4.3. Performance Issues

#### Issue: Processing quá chậm

**Optimization:**
1. Giảm số ảnh mỗi batch
2. Skip OCR nếu không cần: `--skip-ocr`
3. Dùng SSD thay vì HDD
4. Close các apps khác

#### Issue: Face search chậm

**Optimization:**
1. Giảm `face_top_k` trong config (default: 50)
2. Tăng `face_similarity_threshold` (default: 0.6)
3. Restart web server để clear cache

---

## Phần 5: Tips & Best Practices

### 5.1. Processing Tips

✅ **DO:**
- Copy ảnh về local SSD trước khi xử lý
- Dùng Hybrid OCR cho production
- Test với 100-200 ảnh trước khi chạy full event
- Backup bundle sau khi tạo xong

❌ **DON'T:**
- Xử lý trực tiếp từ Google Drive (rất chậm)
- Dùng PaddleOCR cho events lớn (quá chậm)
- Force quit khi đang processing (corrupt database)
- Xóa bundle trước khi verify import thành công

---

### 5.2. Bundle Management

**Naming Convention:**
```
event-slug format: {sport}-{location}-{year}
Examples:
- ironman-danang-2026
- marathon-hcm-2026
- cycling-hanoi-2026
```

**Storage:**
```
Processing Machine:
  dist/events/{slug}/          ← Bundle output
  
Web Server:
  inbox/bundles/{slug}/        ← Import staging
  storage/events/{slug}/       ← Permanent storage
    ├── v20260507-120000/      ← Version 1
    ├── v20260508-150000/      ← Version 2 (if re-imported)
    └── active → v20260508-150000/  ← Symlink to latest
```

---

### 5.3. Security Best Practices

**Admin Token:**
```bash
# Generate strong token
openssl rand -hex 32

# Set in environment
export ADMIN_TOKEN="your-generated-token"

# Or in .env file (don't commit!)
echo "ADMIN_TOKEN=your-token" > .env
```

**Face Embeddings (Biometric Data):**
- ⚠️ Face embeddings là sensitive data
- Không log embeddings
- Không share bundles publicly
- Xóa bundle khi không cần nữa

**Original Photos:**
- Validate paths (no `..` traversal)
- Chỉ serve trong base_path
- Track downloads trong database

---

### 5.4. Backup Strategy

**Processing Machine:**
```bash
# Backup bundle sau khi tạo
cp -r dist/events/ironman-danang-2026 /Volumes/Backup/bundles/

# Hoặc tar + compress
tar -czf ironman-danang-2026.tar.gz dist/events/ironman-danang-2026/
```

**Web Server:**
```bash
# Backup server database
cp storage/server.db storage/server.db.backup

# Backup published events
rsync -av storage/events/ /Volumes/Backup/events/
```

---

## Phần 6: Advanced Usage

### 6.1. CLI Processing (Advanced)

```bash
source venv-ai/bin/activate

# Basic processing
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events

# With options
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --event-location "Da Nang" \
  --output dist/events \
  --ocr-method hybrid \
  --copy-originals

# Skip OCR
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events \
  --skip-ocr

# Skip faces
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events \
  --skip-faces
```

### 6.2. Rebuild Embeddings

Khi cần rebuild face embeddings (model upgrade, corruption, etc.):

```bash
python -m processing_cli rebuild-embeddings \
  --bundle dist/events/ironman-danang-2026 \
  --model-name buffalo_l \
  --model-version v2
```

**Use cases:**
- Upgrade InsightFace model
- Fix FAISS index corruption
- Change embedding dimension

---

### 6.3. Batch Processing

Xử lý nhiều events cùng lúc:

```bash
# Create batch config
cat > batch-config.json <<EOF
{
  "events": [
    {
      "slug": "ironman-danang-2026",
      "name": "Ironman Da Nang 2026",
      "date": "2026-05-07",
      "location": "Da Nang",
      "source": "/Volumes/SSD/photos/ironman/"
    },
    {
      "slug": "marathon-hcm-2026",
      "name": "Marathon HCM 2026",
      "date": "2026-05-14",
      "location": "Ho Chi Minh",
      "source": "/Volumes/SSD/photos/marathon/"
    }
  ]
}
EOF

# Run batch
python -m processing_cli batch-process \
  --config batch-config.json \
  --output dist/events \
  --ocr-method hybrid
```

---

## Phần 7: Monitoring & Logs

### 7.1. Processing App Logs

```bash
# Real-time logs
tail -f processing_web/logs/app.log

# Search errors
grep ERROR processing_web/logs/app.log

# Job history
cat processing_web/logs/jobs.log
```

### 7.2. Web Server Logs

```bash
# Real-time logs
tail -f web_server/logs/app.log

# Search requests
grep "GET /events" web_server/logs/access.log

# Download stats
grep "download" web_server/logs/app.log | wc -l
```

---

## Phần 8: FAQ

**Q: Có thể xử lý ảnh PNG không?**  
A: Không. Hiện tại chỉ hỗ trợ JPG/JPEG. Convert PNG → JPG trước khi xử lý.

**Q: Bundle có thể dùng lại trên máy khác không?**  
A: Có. Bundle là portable, copy sang máy nào cũng được.

**Q: Face search có chính xác không?**  
A: ~85-90% accuracy. Fail với helmet, sunglasses, side profile. Combine với bib search.

**Q: Có thể edit bib number sau khi xử lý không?**  
A: Có. Dùng Admin UI → OCR Review → Manual Correction.

**Q: Xóa event như thế nào?**  
A: Admin UI → Unpublish → Delete. Hoặc xóa thư mục `storage/events/{slug}/`.

**Q: Có thể re-import bundle không?**  
A: Có. Import lại sẽ tạo version mới, symlink `active` sẽ point đến version mới.

---

## Liên Hệ & Support

**Documentation:**
- [System Flow](./system-flow.md)
- [Bundle Format](./bundle-format.md)
- [Codebase Summary](./codebase-summary.md)

**Issues:**
- GitHub: [Report Issue](https://github.com/your-repo/issues)
- Email: support@danangvibes.com

---

**Happy Processing! 🎉**
