# Research Report: OCR and Face Search Stack

## Context

DaNang Vibes is a local-first sports event photo discovery app. Heavy processing runs on a separate processing machine, preferably MacBook M1. Public serving runs on a MacBook Pro 2017 with 8GB RAM via Cloudflare Tunnel for 10-50 concurrent users. Original JPG files live in SSD-backed event bundle storage.

MVP requirements:

- JPG/JPEG only.
- 1,000-20,000 photos per event.
- Few hundred to ~1,000 athletes.
- One event folder.
- Search by bib OCR and selfie-based face search.
- Download original JPG.
- Optional donation.
- FastAPI + server-rendered HTML/HTMX.

## Recommended Stack

| Layer | Recommendation | Notes |
|---|---|---|
| Bib OCR | PaddleOCR | Best primary OCR choice; strong capability; Apache 2.0 |
| OCR fallback | EasyOCR | Simpler fallback; likely weaker primary accuracy |
| Face detection/embedding | InsightFace | Strong technically; model license/commercial use needs review |
| Vector search | FAISS | Local CPU-friendly; excellent for this event scale; MIT |
| Metadata | SQLite | Simple, fast enough, easy to bundle |
| Web/API | FastAPI | Matches Python AI pipeline and lightweight serving |
| UI | Jinja + HTMX | Avoid separate frontend build for MVP |

## Bib OCR Recommendation

Use **PaddleOCR** first.

Why:

- Better production fit than EasyOCR for accuracy-oriented OCR.
- Good deployment flexibility.
- Apache 2.0 license is cleaner for commercial use.
- Works in Python batch workflows.

MVP OCR pipeline:

1. Resize image for processing.
2. Run OCR.
3. Extract digit-only candidates.
4. Save candidate text, confidence, bounding box, source image.
5. Apply simple rules:
   - keep likely bib length ranges;
   - prefer higher confidence;
   - allow multiple candidates per photo;
   - mark low-confidence rows for manual review.

Fallback if accuracy poor:

1. Keep PaddleOCR.
2. Add stricter digit-only post-processing.
3. Add admin correction UI.
4. Later add bib-region detector if needed.

## Face Search Recommendation

Use **InsightFace** for technical spike, but verify model license before commercial release.

Why:

- Strong face detection and embedding quality.
- Suitable for embedding search.
- Good Python ecosystem.

Risk:

- InsightFace code may be MIT, but model packs/training data can carry non-commercial research restrictions.
- Do not assume it is safe for commercial/donation-based usage without review.

MVP face pipeline:

1. Detect faces during batch processing.
2. Store one embedding per detected face.
3. Link face rows to photo IDs and bounding boxes.
4. Build FAISS index from embeddings.
5. For selfie search, compute embedding from uploaded selfie, search top-k FAISS results, and return linked photos.

Fallback if face accuracy poor:

- Treat face as secondary signal, not absolute match.
- Show confidence labels.
- Combine with bib search when user provides both.
- Keep result tabs separate to avoid hiding uncertainty.

## Search Layer Recommendation

Use **SQLite + FAISS**.

SQLite stores:

- events;
- photos;
- thumbnails;
- OCR candidates;
- face records;
- manual corrections;
- download events;
- donation config.

FAISS stores:

- face embedding vectors;
- mapping from FAISS vector ID to face/photo row.

Why:

- Works offline.
- Easy to export/import as event bundle between processing machine and server machine.
- Fast enough for 20,000 photos.
- Low serving load on MacBook Pro 2017.

## Serving Constraints

Do not run batch OCR or face embedding extraction on the serving MacBook while customers are using the site.

Serving machine should only:

- load SQLite and FAISS;
- serve thumbnail pages;
- handle bib lookup;
- handle selfie search if face model is light enough, or optionally proxy/precompute query embedding on a processing machine later;
- stream original JPG download;
- show donation prompts.

Important note: selfie upload requires computing one face embedding at query time. This is much lighter than batch processing, but still should be benchmarked on the MacBook Pro 2017. If too slow, consider making selfie search admin-preprocessed or running the public server on the M1.

## License Considerations

| Tool | License Signal | Concern |
|---|---|---|
| PaddleOCR | Apache 2.0 | Low concern |
| EasyOCR | Apache 2.0 | Low concern |
| FAISS | MIT | Low concern |
| InsightFace | Code MIT, model restrictions possible | Must verify before commercial/donation use |

## MVP Recommendation

Implement in this order:

1. SQLite event/photo schema.
2. Thumbnail generation.
3. PaddleOCR bib extraction.
4. Manual bib review/correction.
5. FAISS index structure.
6. InsightFace technical spike.
7. Public search UI.
8. Original download + donation UX.

## Validation Plan

Use a real sample set of 200-500 race photos.

Measure:

- processing seconds/photo on M1;
- OCR hit rate for visible bibs;
- face detection rate for run/finish/bike photos;
- selfie query latency on MacBook Pro 2017;
- memory usage during serving;
- download speed through Cloudflare Tunnel from SSD-backed original storage.

## Unresolved Questions

- Is InsightFace acceptable for commercial/donation-based use?
- Should selfie embedding be computed on the serving MacBook or only on a stronger machine?
- What bib number length/ranges are common for the target events?
