---
title: Sports Event Face/Object Recognition Research
created: 2026-05-07 09:47
report_type: research
topic: face and object recognition for running cycling ironman photos
---

# Research Report: Nhận diện khuôn mặt/vật thể cho ảnh sự kiện chạy/đạp xe/Ironman

## Executive Summary

Khuyến nghị: làm **custom app nhẹ**, không fork Immich/PhotoPrism ngay. Dùng pipeline batch: ingest ảnh từ local/Drive → tạo thumbnail → detect face/object → sinh embedding → lưu metadata/search index → UI tìm kiếm. Với máy Mac Pro/MacBook Pro 2017 làm VPS, không nên kỳ vọng real-time AI nặng. Chạy batch background, model nhỏ, resize ảnh trước inference.

Stack MVP thực dụng nhất:

- Face: **InsightFace** nếu cần chất lượng; **DeepFace** nếu cần dễ code hơn.
- Object: **YOLO nano/small qua Ultralytics** cho MVP; cân nhắc license AGPL nếu thương mại.
- Vector search: **FAISS** nếu single-machine đơn giản; **Qdrant** nếu muốn API/service và mở rộng sau.
- Storage: **local disk là nguồn xử lý chính**; Google Drive chỉ làm import/archive/sync, không dùng làm hot path.

Brutal truth: bài toán “tìm đúng vận động viên trong hàng chục nghìn ảnh race” khó không phải vì code, mà vì ảnh thể thao nhiều góc nghiêng, kính, mũ, bib che mặt, motion blur. Cần thêm **bib number OCR** hoặc tag thủ công/review UI nếu muốn accuracy tốt.

## Research Methodology

- Timestamp: 2026-05-07
- Sources consulted: WebSearch + GitHub metadata via `gh repo view`
- Search terms:
  - open source face recognition photo search local self hosted GitHub python face_recognition insightface DeepFace
  - open source object detection photo tagging sports events marathon cycling triathlon YOLO GitHub
  - self hosted photo management face recognition object detection local storage Google Drive
  - Mac Pro 2017 machine learning inference object detection CPU GPU OpenVINO Core ML YOLO performance
  - image similarity search face embeddings FAISS Qdrant Milvus self hosted photo retrieval
- Caveat: một số WebSearch query bị chặn anti-bot/Gemini auth; kết luận dựa trên kết quả có được + repo metadata + kiến thức kỹ thuật phổ biến.

## Key Findings

### 1. Nên tự build MVP thay vì bắt đầu từ photo app lớn

| Option | Ưu | Nhược | Kết luận |
|---|---|---|---|
| Immich | Self-host mạnh, photo/video management, rất nhiều sao | AGPL-3.0, app lớn, mục tiêu Google Photos alternative, custom workflow race có thể nặng | Dùng để học kiến trúc, không nên fork sớm |
| PhotoPrism | Self-host photo AI, Go/TensorFlow, private cloud | License “Other”, product lớn, khó tùy biến sâu | Tham khảo, không phải nền MVP |
| Custom app | Đúng workflow race, dễ tối ưu batch, dễ thêm bib/OCR | Phải tự làm UI/index/storage | Khuyến nghị MVP |

### 2. Face recognition

| Repo/library | Metadata | Điểm mạnh | Điểm yếu | Fit |
|---|---:|---|---|---|
| `deepinsight/insightface` | ~28.6k stars, state-of-the-art face analysis | Chất lượng tốt, RetinaFace/ArcFace, production-grade | Setup/model/runtime phức tạp hơn, license repo metadata không rõ qua `gh` | Best quality |
| `serengil/deepface` | MIT, ~22.7k stars, latest release 2026-03 | Dễ dùng, nhiều model backend, Python-friendly | Có thể chậm hơn/khó tối ưu hơn cho batch lớn | Best developer speed |
| `ageitgey/face_recognition` | Python face recognition phổ biến | API đơn giản | Dựa dlib, cũ hơn, CPU install/perf có thể khó trên macOS | Chỉ dùng prototype nhỏ |

Khuyến nghị: bắt đầu **DeepFace** nếu muốn chạy nhanh demo; chuyển **InsightFace ONNXRuntime** khi cần accuracy/performance.

### 3. Object detection

| Repo/library | Metadata | Điểm mạnh | Điểm yếu | Fit |
|---|---:|---|---|---|
| `ultralytics/ultralytics` | AGPL-3.0, ~56.8k stars, latest release 2026-05 | Dễ train/infer/export, YOLO phổ biến, detect person/bicycle/helmet etc | AGPL ảnh hưởng thương mại/SaaS; PyTorch nặng trên máy cũ | MVP nhanh nếu license OK |
| LibreYOLO | MIT-focused | License thân thiện hơn | Ecosystem nhỏ hơn Ultralytics | Cân nhắc nếu thương mại |
| OpenCV DNN + ONNX | Không phải repo app | Nhẹ hơn runtime PyTorch | Cần tự export/tune | Tốt cho deploy CPU |

Object cần detect tối thiểu:

- `person`
- `bicycle`
- `helmet` nếu model/custom dataset có
- `bib/race number` nên là module riêng: object detector + OCR
- `finish line`, `swim/bike/run context` nếu cần tagging cảnh

### 4. Vector search / indexing

| Option | Ưu | Nhược | Fit |
|---|---|---|---|
| FAISS | Nhanh, local, đơn giản, không cần service | App tự quản index persistence/API | MVP single-machine |
| Qdrant | Vector DB có API, filter metadata tốt | Thêm service cần vận hành | MVP+ hoặc nhiều người dùng |
| Milvus | Mạnh cho scale lớn | Nặng, overkill cho Mac 2017 | Không khuyến nghị ban đầu |

Khuyến nghị: **FAISS trước**, nếu cần filter/search phức tạp thì đổi sang **Qdrant**.

### 5. Storage local / Drive

Không dùng Google Drive làm storage nóng cho inference. Lý do:

- Latency/network/API limit.
- File sync không ổn định cho batch lớn.
- Dễ lỗi duplicate/partial file.

Thiết kế tốt hơn:

```text
Google Drive / local import folder
  -> ingest job copies/symlinks into local media store
  -> checksum dedupe
  -> thumbnail cache
  -> AI processing queue
  -> metadata DB + vector index
  -> search UI/API
```

Local disk nên giữ:

- Original hoặc path tới original.
- Thumbnail/webp preview.
- JSON metadata per image hoặc Postgres rows.
- Vector index.

Drive dùng:

- Import source.
- Backup/archive.
- Optional export gallery.

## Recommended Architecture

```text
[Local Folder / Google Drive]
        |
        v
[Ingest Worker]
 - scan files
 - checksum dedupe
 - EXIF parse
 - create thumbnails
        |
        v
[AI Queue]
 - face detection
 - face embeddings
 - object detection
 - optional bib OCR
        |
        +------------------+
        |                  |
        v                  v
[Postgres/SQLite]      [FAISS/Qdrant]
metadata/tags          face/image vectors
        |                  |
        +--------+---------+
                 v
          [Search API]
                 v
       [Web UI for event search]
```

## Implementation Recommendation

### MVP scope

1. Local import folder only.
2. Process JPG/PNG.
3. Generate thumbnail.
4. Detect faces.
5. Cluster similar faces.
6. User labels one face cluster/person.
7. Search returns matching photos.
8. Add object tags: person, bicycle, runner/cyclist context.

Delay these until MVP works:

- Google Drive two-way sync.
- Payment/gallery sales.
- Mobile app.
- Real-time processing.
- Multi-node scale.

### Suggested stack

| Layer | Recommendation |
|---|---|
| Backend | Python FastAPI |
| Worker | Python RQ/Celery or simple background process first |
| DB | SQLite for prototype, Postgres for deploy |
| Vector | FAISS first, Qdrant later |
| Face | DeepFace first, InsightFace later |
| Object | YOLO nano/small, exported ONNX if possible |
| Image processing | Pillow/OpenCV |
| Frontend | Simple React/Next or server-rendered UI |
| Storage | Local filesystem with relative paths |
| Deployment | Docker only if machine handles it; otherwise direct Python service + launchd |

## Mac Pro / MacBook Pro 2017 Optimization

Assumption cần xác nhận: “Mac Pro 2017” có thể là **MacBook Pro 2017** hoặc **iMac Pro 2017**. Nếu là MacBook Pro 2017, CPU/GPU yếu cho AI hiện đại.

Rules:

- Batch processing, no real-time promise.
- Resize image before inference: e.g. max side 1280/1600 for detection.
- Use thumbnail preview, never load originals in UI grid.
- Use model nano/small.
- Cache every result by file checksum.
- Use queue concurrency low: 1–2 workers first.
- Store embeddings once; never recompute unless model version changes.
- Keep `model_version` in DB.
- Prefer ONNXRuntime/OpenCV DNN for CPU deploy once model chosen.
- Avoid Milvus/Elasticsearch/Kafka. Too heavy.

## Security / Privacy

- Face recognition data is sensitive biometric data.
- Need explicit local-first story.
- Do not log face embeddings publicly.
- If using Drive, OAuth tokens must be encrypted or stored only in environment/secure local config.
- Add delete/export data path early if app used with real users.
- If commercial/public, check biometric privacy laws in target region.

## Repo shortlist

| Repo | URL | Use for | License signal |
|---|---|---|---|
| Immich | https://github.com/immich-app/immich | self-host photo architecture reference | AGPL-3.0 |
| PhotoPrism | https://github.com/photoprism/photoprism | photo indexing/AI reference | Other |
| InsightFace | https://github.com/deepinsight/insightface | high-quality face recognition | unclear from metadata |
| DeepFace | https://github.com/serengil/deepface | quick Python face recognition MVP | MIT |
| Ultralytics | https://github.com/ultralytics/ultralytics | YOLO object detection MVP | AGPL-3.0 |
| FAISS | https://github.com/facebookresearch/faiss | local vector index | check current license before commercial |
| Qdrant | https://github.com/qdrant/qdrant | vector DB service | check current license before commercial |

## Quick Start Plan

### Phase 1: Technical spike, 1–2 days

- Pick 200–500 race photos.
- Run face detection/embedding with DeepFace.
- Cluster faces with FAISS or sklearn.
- Measure time/photo on target Mac.
- Run YOLO nano/small on same images.
- Record accuracy failures: sunglasses, helmet, side face, blur, crowd.

### Phase 2: MVP app

- `ingest` CLI command.
- Local media folder.
- SQLite/Postgres metadata.
- Worker queue.
- Basic web UI:
  - event list
  - photo grid
  - face cluster page
  - label person
  - search by uploaded selfie / selected cluster

### Phase 3: Race-specific accuracy

- Add bib number detection/OCR.
- Combine search signals:
  - face similarity
  - bib OCR
  - timestamp/location
  - object/context tags
  - manual cluster labels

### Phase 4: Drive integration

- One-way import from Drive folder.
- Local cache.
- Retry/resume jobs.
- No two-way sync until needed.

## Common Pitfalls

- Starting with Immich fork: huge codebase, wrong optimization target.
- Trying to process originals at full resolution: too slow.
- Using Drive as live filesystem: unstable pipeline.
- Depending only on face recognition for race photos: helmets/sunglasses ruin recall.
- Skipping review UI: AI will be wrong; humans need fast correction workflow.
- Ignoring license: AGPL libraries can affect deployment/commercial usage.

## Final Recommendation

Build a **local-first race photo search engine**. Start tiny:

```text
DeepFace + YOLO small + SQLite + FAISS + local folder + simple web UI
```

Then replace components only when bottleneck proven:

```text
DeepFace -> InsightFace
SQLite -> Postgres
FAISS -> Qdrant
PyTorch YOLO -> ONNXRuntime/OpenCV DNN
Local import -> Drive importer
```

## Unresolved Questions

1. Máy chính xác là Mac Pro, iMac Pro, hay MacBook Pro 2017? CPU/RAM/GPU bao nhiêu?
2. Số lượng ảnh mỗi event: 1k, 10k, 100k?
3. Cần tìm theo selfie, theo bib number, hay theo tên VĐV đã đăng ký?
4. App dùng cá nhân/local hay SaaS cho khách hàng? License/privacy phụ thuộc câu này.
5. Google Drive cần import một chiều hay sync hai chiều?
