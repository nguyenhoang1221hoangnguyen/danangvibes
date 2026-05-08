# DaNang Vibes Bundle Format

Bundle là contract giữa Processing CLI và Web Server.

## Structure

```text
{event-slug}/
├── manifest.json
├── event.db
├── faiss.index
├── thumbnails/
│   └── photo_000001.jpg
└── originals_mapping.json
```

## Runtime flow

1. Processing CLI scan JPG/JPEG, tạo checksum, đọc metadata, tạo thumbnail.
2. Metadata lưu trong `event.db` theo `shared/schema.sql`.
3. `originals_mapping.json` map `photo_id` sang path ảnh gốc relative với `base_path`.
4. `manifest.json` lưu stats, file names, checksum `event.db` và `faiss.index`.
5. Web Server import bundle vào `{storage}/{event}/releases/{version}` và trỏ `active` symlink.

## Security rules

- `manifest.json` không chứa token/secret.
- Import validate schema và checksum trước khi copy vào storage.
- Download chỉ dùng relative path trong mapping; absolute path hoặc `..` bị reject.
- Admin routes cần `Authorization: Bearer <DANANGVIBES_ADMIN_TOKEN>` hoặc `X-Admin-Token`.

## Commands

```bash
python -m processing_cli process \
  --source /path/to/photos \
  --event-slug test-event \
  --event-name "Test Event" \
  --event-date 2026-05-07 \
  --output dist/events \
  --skip-ocr \
  --skip-faces

python -m processing_cli validate --bundle dist/events/test-event

python -m web_server import \
  --bundle dist/events/test-event \
  --storage-path storage/events

python -m web_server publish --event-slug test-event
python -m web_server run --storage-path storage/events
```

## Optional AI dependencies

OCR, face embedding, and FAISS indexing are real runtime integrations but optional in base install. If enabled without dependencies, commands fail with explicit install guidance instead of silently mocking results.
