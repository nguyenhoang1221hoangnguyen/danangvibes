# DaNang Vibes

DaNang Vibes là MVP local-first để xử lý ảnh sự kiện thể thao, tạo bundle metadata/thumbnail, rồi serve web UI nhẹ để tìm và tải ảnh.

Kiến trúc hiện tại gồm 2 ứng dụng:

1. **Processing Web App**: chạy trên máy xử lý ảnh, dùng browser UI để chọn folder ảnh local, chạy full OCR + face, tạo bundle SQLite/thumbnail/manifest/FAISS.
2. **Web Server App**: FastAPI server import bundle, publish event, serve event page, thumbnail, download ảnh gốc, admin OCR review và thống kê download.

> Processing Web App bật OCR/face mặc định và cần optional AI dependencies. Face search MVP hiện dùng **InsightFace (buffalo_l)** + FAISS - nhanh (~0.37s/ảnh), tốt với mũ/kính, ít false positives.

## Yêu cầu

- macOS/Linux shell
- Python 3.11+
- Ảnh input dạng `.jpg` hoặc `.jpeg`

## Setup môi trường

```bash
scripts/setup-local-env.sh
```

Script này sẽ:

- tạo `venv/` nếu chưa có
- cài dependencies trong `requirements.txt`

Nếu muốn dùng Python khác:

```bash
PYTHON_BIN_FALLBACK=python3.11 scripts/setup-local-env.sh
```

## Chạy tách riêng 2 app trên 2 máy

### Máy 1: Processing Web App

Dùng máy mạnh hơn để xử lý ảnh. App 1 tự dùng Python 3.11 và `venv-ai/` cho AI dependencies:

```bash
scripts/start-processing-app.sh
```

**Hoặc khởi động thủ công:**

```bash
cd /Users/nguyenhoang/Desktop/2026/ungDung/danangvibes
source venv-ai/bin/activate
python -m processing_web run
```

Nếu máy chưa có Python 3.11, cài một lần:

```bash
brew install python@3.11
```

Mở browser:

```text
http://127.0.0.1:8010
```

Trong UI:

1. Bấm **Chọn thư mục ảnh nhanh** hoặc nhập folder ảnh local, ví dụ `/Volumes/SSD/photos`.
2. Nhập event slug/name/date/location.
3. **Chọn OCR method:**
   - **Hybrid (YOLO + Tesseract)** - Nhanh nhất (~0.6s/ảnh), khuyến nghị cho production ✓
   - **PaddleOCR** - Chậm (~3-5s/ảnh) nhưng chính xác hơn
   - **Skip OCR** - Chỉ face detection, không OCR
4. Bấm **Start processing**.
5. Chờ job hoàn tất.
6. Copy bundle output vào USB/SSD.

Output mặc định:

```text
dist/events/test-event/
```

**Lưu ý:**
- Hybrid OCR (mặc định) nhanh gấp 24 lần PaddleOCR
- 10,000 ảnh: ~1.6 giờ với Hybrid, ~39 giờ với PaddleOCR
- Cần dataset có số bib visible để validate accuracy

### Máy 2: Web Server App

Copy bundle từ USB/SSD vào inbox của máy web:

```text
inbox/bundles/test-event/
```

Chạy web app bằng một lệnh:

```bash
ADMIN_TOKEN="dev-secret" scripts/start-web-app.sh
```

Mở Admin UI:

```text
http://127.0.0.1:8000/admin/
```

Trong Admin UI:

1. Chọn bundle trong mục **Import bundle từ USB/SSD**.
2. Bấm **Import bundle**.
3. Bấm **Publish** hoặc tick **Publish ngay sau khi import**.
4. Mở event public tại `/events/test-event`.

## Chạy Processing CLI thủ công / debug

Tạo bundle từ folder ảnh:

```bash
SOURCE_DIR=/path/to/photos \
EVENT_SLUG=test-event \
EVENT_NAME="Test Event" \
EVENT_DATE=2026-05-07 \
scripts/run-processing-cli.sh
```

**Hoặc dùng CLI trực tiếp với OCR method:**

```bash
source venv-ai/bin/activate

# Hybrid OCR (nhanh, khuyến nghị)
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events \
  --ocr-method hybrid

# PaddleOCR (chậm nhưng chính xác)
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events \
  --ocr-method paddle

# Skip OCR (chỉ face detection)
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events \
  --ocr-method skip
```

Output mặc định:

```text
dist/events/test-event/
├── manifest.json
├── event.db
├── faiss.index
├── thumbnails/
└── originals_mapping.json
```

Tuỳ chọn CLI:

```bash
--event-location "Da Nang"     # optional
--output dist/events           # default
--force                        # xoá và tạo lại bundle nếu đã tồn tại
--skip-ocr                     # skip OCR (deprecated, dùng --ocr-method skip)
--skip-faces                   # skip face detection
--ocr-method hybrid|paddle|skip  # OCR method (default: hybrid)
```

Ví dụ chạy lại từ đầu:

```bash
source venv-ai/bin/activate
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --force \
  --ocr-method hybrid
```

## Validate bundle thủ công

```bash
source venv/bin/activate
python -m processing_cli validate --bundle dist/events/test-event
```

## Import và publish bundle

```bash
BUNDLE_PATH=dist/events/test-event \
EVENT_SLUG=test-event \
scripts/import-and-publish-bundle.sh
```

Storage mặc định:

```text
storage/events/
├── server.db
└── test-event/
    ├── releases/
    │   └── v1/
    └── active -> releases/v1
```

Tuỳ chọn env:

```bash
STORAGE_PATH=storage/events
SERVER_DB_PATH=storage/events/server.db
VERSION=v2       # import version cụ thể
PUBLISH=0        # chỉ import, không publish
```

## Chạy Web Server

```bash
ADMIN_TOKEN="dev-secret" scripts/run-web-server.sh
```

Mặc định server chạy tại:

```text
http://127.0.0.1:8000
```

Các URL chính:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/events/test-event
http://127.0.0.1:8000/health
```

Admin route có thể đăng nhập bằng HTTP Basic, dùng password là admin token. Nếu gọi bằng API/curl thì truyền token qua header:

```bash
curl -H "Authorization: Bearer dev-secret" \
  http://127.0.0.1:8000/admin/
```

Hoặc:

```bash
curl -H "X-Admin-Token: dev-secret" \
  http://127.0.0.1:8000/admin/
```

## Chạy full local flow

Nếu muốn chạy từ ảnh nguồn tới web server trong một lệnh:

```bash
SOURCE_DIR=/path/to/photos \
EVENT_SLUG=test-event \
EVENT_NAME="Test Event" \
EVENT_DATE=2026-05-07 \
ADMIN_TOKEN="dev-secret" \
scripts/start-all-local.sh
```

Script sẽ chạy theo thứ tự:

1. `run-processing-cli.sh`
2. `import-and-publish-bundle.sh`
3. `run-web-server.sh`

Nếu đã có bundle và chỉ muốn import + chạy server:

```bash
EVENT_SLUG=test-event \
ADMIN_TOKEN="dev-secret" \
SKIP_PROCESSING=1 \
scripts/start-all-local.sh
```

Nếu event đã import/publish và chỉ muốn chạy server:

```bash
EVENT_SLUG=test-event \
ADMIN_TOKEN="dev-secret" \
SKIP_PROCESSING=1 \
SKIP_IMPORT=1 \
scripts/start-all-local.sh
```

## Environment variables chính

### Processing scripts

| Env | Mặc định | Mô tả |
|---|---:|---|
| `SOURCE_DIR` | required | Folder ảnh JPG/JPEG |
| `EVENT_SLUG` | required | Slug event, ví dụ `ironman-danang-2026` |
| `EVENT_NAME` | required | Tên event hiển thị |
| `EVENT_DATE` | required | Ngày event `YYYY-MM-DD` |
| `EVENT_LOCATION` | empty | Địa điểm event |
| `OUTPUT_DIR` | `dist/events` | Nơi xuất bundle |
| `FORCE` | `0` | `1` để xoá bundle cũ và process lại |
| `ENABLE_OCR` | `0` | `1` để bật PaddleOCR |
| `ENABLE_FACES` | `0` | `1` để bật DeepFace/FAISS |

### Web server scripts

| Env | Mặc định | Mô tả |
|---|---:|---|
| `ADMIN_TOKEN` | required | Token admin |
| `HOST` | `127.0.0.1` | Host bind server |
| `PORT` | `8000` | Port server |
| `STORAGE_PATH` | `storage/events` | Event storage |
| `SERVER_DB_PATH` | `$STORAGE_PATH/server.db` | SQLite metadata của server |

## Optional AI dependencies

Base install đủ để chạy pipeline không OCR/face. App 1 Processing Web App chạy full OCR/face nên script sẽ tự dùng Python 3.11 và `venv-ai/`, gồm PaddleOCR + PaddlePaddle backend:

```bash
scripts/start-processing-app.sh
```

Nếu muốn cài AI deps thủ công:

```bash
VENV_DIR=venv-ai PYTHON_BIN_FALLBACK=python3.11 INSTALL_AI=1 scripts/setup-local-env.sh
```

Hoặc cài thủ công:

```bash
source venv/bin/activate
pip install -r requirements-ai.txt
```

Sau đó chạy:

```bash
SOURCE_DIR=/path/to/photos \
EVENT_SLUG=test-event \
EVENT_NAME="Test Event" \
EVENT_DATE=2026-05-07 \
ENABLE_OCR=1 \
ENABLE_FACES=1 \
FORCE=1 \
scripts/run-processing-cli.sh
```

Lưu ý:

- Face model production vẫn cần chốt theo license/accuracy.
- Không log embeddings publicly.
- Nên test với 20-50 ảnh trước khi chạy event lớn.

## Validation

Compile Python:

```bash
python3 -m compileall shared processing_cli web_server tests
```

Chạy test nếu đã cài pytest:

```bash
venv/bin/python -m pytest tests -q
```

Nếu môi trường chưa có pytest, có thể chạy workflow test bằng stdlib runner:

```bash
python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from tests.test_bundle_workflow import (
    test_original_mapping_rejects_absolute_and_parent_escape,
    test_process_validate_import_publish_and_search,
)
for test in [test_process_validate_import_publish_and_search, test_original_mapping_rejects_absolute_and_parent_escape]:
    with TemporaryDirectory() as tmp:
        test(Path(tmp))
print('workflow-tests-ok')
PY
```

## Các lệnh CLI trực tiếp

Processing CLI:

```bash
python -m processing_cli process --help
python -m processing_cli validate --help
python -m processing_cli export --help
```

Web Server CLI:

```bash
python -m web_server import --help
python -m web_server publish --help
python -m web_server unpublish --help
python -m web_server list-versions --help
python -m web_server run --help
```

Rebuild face embeddings khi đổi model/version:

```bash
python -m processing_cli rebuild-embeddings --bundle dist/events/test-event --model-version v2
```

## Ghi chú bảo mật

- Không commit `.env`, admin token, Cloudflare token, Drive OAuth token.
- `ADMIN_TOKEN` nên dùng chuỗi random mạnh khi deploy thật:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

- `originals_mapping.json` chỉ chấp nhận relative path an toàn; absolute path hoặc `..` bị reject khi download.
- Với real users, face embeddings là biometric data, cần chính sách xoá/export dữ liệu rõ ràng.
