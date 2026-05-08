# Batch Processing - Xử lý hàng loạt nhiều events

## Tổng quan

Batch processing cho phép xử lý nhiều folders ảnh (events) một lúc, tự động tạo bundles với OCR + face detection.

## Cách sử dụng

### Bước 1: Tạo batch config tự động

Scan một thư mục chứa nhiều folders ảnh:

```bash
# Scan thư mục hiện tại
python scripts/generate-batch-config.py /path/to/photos/root

# Scan đệ quy tất cả subfolders
python scripts/generate-batch-config.py /path/to/photos/root --recursive

# Chỉ lấy folders có >= 20 ảnh
python scripts/generate-batch-config.py /path/to/photos/root --min-photos 20

# Lưu vào file khác
python scripts/generate-batch-config.py /path/to/photos/root -o my-batch.json
```

**Ví dụ:**

```bash
python scripts/generate-batch-config.py "/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output" --recursive
```

Output: `batch-config.json`

### Bước 2: Review và chỉnh sửa config

Mở `batch-config.json` và kiểm tra:

```json
{
  "events": [
    {
      "source_path": "/path/to/event1",
      "event_slug": "event-1",
      "event_name": "Event 1",
      "event_date": "2026-05-01",
      "event_location": "Đà Nẵng"
    },
    {
      "source_path": "/path/to/event2",
      "event_slug": "event-2",
      "event_name": "Event 2",
      "event_date": "2026-05-15",
      "event_location": "Hội An"
    }
  ]
}
```

Chỉnh sửa:
- `event_slug`: URL-friendly slug (lowercase, hyphens)
- `event_name`: Tên hiển thị
- `event_date`: Ngày sự kiện (YYYY-MM-DD)
- `event_location`: Địa điểm (optional)

### Bước 3: Chạy batch processing

```bash
# Activate venv
source venv-ai/bin/activate

# Skip OCR (khuyến nghị - nhanh hơn)
python -m processing_cli batch-process \
  --batch-config batch-config.json \
  --skip-ocr

# Full OCR + Face (chậm - ~3 phút/ảnh)
python -m processing_cli batch-process \
  --batch-config batch-config.json

# Force rebuild tất cả bundles
python -m processing_cli batch-process \
  --batch-config batch-config.json \
  --skip-ocr \
  --force

# Custom output directory
python -m processing_cli batch-process \
  --batch-config batch-config.json \
  --skip-ocr \
  --output /path/to/output
```

### Bước 4: Xem kết quả

Sau khi chạy xong:

```
dist/events/
├── event-1/
│   ├── event.db
│   ├── faiss.index
│   ├── thumbnails/
│   └── manifest.json
├── event-2/
│   ├── event.db
│   ├── faiss.index
│   ├── thumbnails/
│   └── manifest.json
└── batch_results.json  ← Summary report
```

Xem summary:

```bash
cat dist/events/batch_results.json
```

## Thời gian xử lý ước tính

**Skip OCR (khuyến nghị):**
- ~20-30 giây/ảnh (chỉ face detection)
- 100 ảnh: ~30-50 phút
- 1000 ảnh: ~5-8 giờ

**Full OCR + Face:**
- ~3 phút/ảnh (PaddleOCR rất chậm trên CPU)
- 100 ảnh: ~5 giờ
- 1000 ảnh: ~50 giờ

## Tips

### 1. Chạy qua đêm

```bash
# Chạy background với nohup
nohup python -m processing_cli batch-process \
  --batch-config batch-config.json \
  --skip-ocr \
  > batch-processing.log 2>&1 &

# Xem progress
tail -f batch-processing.log
```

### 2. Chia nhỏ batches

Nếu có quá nhiều events, chia thành nhiều batch configs:

```bash
# batch-1.json: events 1-10
# batch-2.json: events 11-20
# ...

python -m processing_cli batch-process --batch-config batch-1.json --skip-ocr
python -m processing_cli batch-process --batch-config batch-2.json --skip-ocr
```

### 3. Resume sau khi fail

Batch processing tự động skip bundles đã tồn tại. Nếu process bị gián đoạn, chạy lại command để resume:

```bash
# Chỉ xử lý events chưa có bundle
python -m processing_cli batch-process --batch-config batch-config.json --skip-ocr

# Force rebuild tất cả (kể cả đã có)
python -m processing_cli batch-process --batch-config batch-config.json --skip-ocr --force
```

## Troubleshooting

### Lỗi "Source path does not exist"

Kiểm tra paths trong config file có đúng không:

```bash
# Test từng path
ls "/path/from/config"
```

### Process bị chậm

- Đảm bảo dùng `--skip-ocr`
- Kiểm tra CPU/RAM usage: `htop` hoặc Activity Monitor
- Đóng các app khác để giải phóng RAM

### Out of memory

Giảm số events trong một batch, hoặc tăng RAM swap:

```bash
# macOS: check memory pressure
vm_stat

# Linux: check swap
free -h
```

## Ví dụ thực tế

```bash
# 1. Scan tất cả folders trong Desktop/2026
python scripts/generate-batch-config.py \
  "/Users/nguyenhoang/Desktop/2026/Tháng 5/dap xe/dap/Output" \
  --recursive \
  --min-photos 20 \
  -o my-events.json

# 2. Review config
cat my-events.json

# 3. Chạy batch processing (skip OCR)
source venv-ai/bin/activate
python -m processing_cli batch-process \
  --batch-config my-events.json \
  --skip-ocr

# 4. Xem kết quả
cat dist/events/batch_results.json
```
