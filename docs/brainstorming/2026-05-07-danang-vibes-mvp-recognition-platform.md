# Brainstorming Session: DaNang Vibes MVP Recognition Platform

## 1. Session Overview

**Date:** 2026-05-07  
**Feature:** Post-event athlete photo discovery for Ironman/sports events  
**Facilitator:** Claude Code  
**Primary goal:** Replace slow Google Drive browsing with a self-service search/download app for customers.

## 2. Problem Statement

Event photos are currently uploaded to Google Drive. Customers browse manually, which is slow, labor-intensive, and still misses relevant photos. The product should let customers find their own photos faster after an event using bib number OCR and selfie-based face search, then download original JPG files.

## 3. Target Users

### Admin / Photographer

- Uploads or imports event photos.
- Processes event photos before publishing.
- Publishes a searchable event after processing.
- Reviews/fixes OCR mistakes when needed.
- Configures donation information.

### Customer / Athlete

- Opens public event page after the event.
- Searches using bib number and/or selfie upload.
- Reviews result tabs.
- Downloads original full-resolution JPG photos.
- Can donate voluntarily.

## 4. Key Decisions

| Area | Decision |
|---|---|
| Event scale | 1,000-20,000 JPG photos per event; few hundred to ~1,000 athletes |
| Hardware | Heavy processing on separate processing machine, preferably MacBook M1; serving on MacBook Pro 2017, 8GB RAM, 512GB SSD |
| Access model | Customers access via internet after event through Cloudflare Tunnel; MacBook acts like self-hosted server |
| Expected concurrency | 10-50 concurrent users |
| Monetization | Free original download with optional donation prompt |
| Download quality | Full-resolution original JPG |
| Input format | JPG/JPEG only for MVP |
| Event structure | One event = one image folder |
| Search signals | Bib OCR + selfie-based face search for MVP |
| Result UX | Separate tabs: Bib Match, Face Match, Suggested |
| Donation UX | Light prompt on result page; stronger prompt after download |
| Admin tooling | CLI + basic admin UI |
| Stack | FastAPI + server-rendered HTML/HTMX |

## 5. Proposed Solution

Use a two-machine workflow:

1. **Processing machine, preferably MacBook M1**
   - Scan one SSD/local event folder of JPG files.
   - Generate thumbnails.
   - Run bib OCR.
   - Detect faces and create embeddings.
   - Build SQLite metadata and FAISS vector index.
   - Export a portable event bundle.

2. **Serving machine: MacBook Pro 2017**
   - Import/publish the copied event bundle from SSD-backed storage.
   - Serve public search UI via FastAPI + HTML/HTMX.
   - Handle bib search and selfie search queries.
   - Serve thumbnails for browsing.
   - Stream original JPG files from SSD for download.
   - Show donation prompt/QR.
   - Expose public access through Cloudflare Tunnel.

Heavy AI inference should not run on the public serving machine while customers are using the site.

## 6. MVP Scope

### Must Have

- Create/import event from a single JPG folder.
- Generate thumbnails.
- Run bib OCR during batch processing.
- Run face detection/embedding during batch processing.
- Store event metadata in SQLite.
- Store face embeddings in FAISS.
- Export/import event bundle.
- Public event search page.
- Bib number search.
- Selfie upload face search.
- Result tabs: Bib Match, Face Match, Suggested.
- Original JPG download.
- Donation QR/prompt on result page and post-download.
- Basic admin UI for events, publish status, OCR review, donation config.
- CLI for process/export/import/publish.

### Should Have

- Manual bib correction UI.
- Confidence labels: High / Medium / Low.
- Search result deduplication.
- Simple rate limit for downloads/search.
- Event enable/disable switch.

### Could Have Later

- Vehicle/bike/object recognition.
- Clothing/helmet color matching.
- RAW/HEIC support.
- Google Drive API import.
- Online payment/cart.
- User accounts.
- Cloud/VPS deployment.
- Multi-folder event structure.

### Won't Have in MVP

- Real-time processing.
- Drive as live hot path.
- Mandatory payment before download.
- React/Next.js frontend.
- Full SaaS multi-tenant architecture.

## 7. Architecture Notes

```text
[SSD / Local JPG Event Folder]
        |
        v
[Processing Machine CLI]
        |
        |-- thumbnails
        |-- SQLite metadata
        |-- FAISS face index
        |-- original JPG storage/mapping
        v
[Portable Event Bundle]
        |
        | copy via SSD/LAN/AirDrop/rsync
        v
[MacBook Pro 2017 FastAPI Server]
        |
        |-- SSD-backed bundle import
        |-- Public Search UI
        |-- Admin UI
        |-- Original JPG download
        |-- Donation QR
        v
[Customer via Cloudflare Tunnel]
```

Recommended AI/search stack:

- **Bib OCR:** PaddleOCR first.
- **Face search:** InsightFace technically strong, but license/model-use must be checked before commercial use.
- **Vector search:** FAISS.
- **Metadata:** SQLite.
- **Web:** FastAPI + Jinja + HTMX.

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Face search fails due to helmet/sunglasses/blur | Missed photos | Treat face as secondary signal; combine with bib; show confidence |
| Bib OCR misreads numbers | Wrong/missing results | Digit-only post-processing, confidence thresholds, manual correction UI |
| MacBook 2017 overloads during downloads | Slow site | No AI processing on server; thumbnails for browsing; stream originals; soft rate limits |
| Cloudflare Tunnel instability | Users cannot access site | Keep Cloudflare setup documented; prepare restart checklist and local fallback testing process |
| InsightFace license uncertainty | Commercial risk | Verify model license before commercial use; keep model abstraction swappable |
| Large original JPG storage | Disk pressure | Event bundle per event on SSD-backed storage; archive old events; use external SSD if internal SSD is insufficient |

## 9. Suggested Backlog

### Epic 1: Event Processing Pipeline

- Import JPG folder.
- Generate checksums and thumbnails.
- Extract EXIF capture time.
- Run OCR and save bib candidates.
- Run face embeddings and save FAISS index.
- Export event bundle.

### Epic 2: Public Search and Download

- Event landing page.
- Bib search form.
- Selfie upload form.
- Tabbed result view.
- Original download endpoint.
- Donation prompt.

### Epic 3: Admin and Publishing

- Admin event list.
- Bundle import/publish.
- OCR review/correction.
- Donation config.
- Event public/private toggle.

### Epic 4: Hardening

- Rate limits.
- Error pages.
- Basic logs.
- Backup/restore event bundle.
- Cloudflare Tunnel deployment guide.

## 10. Next Steps

1. Validate PaddleOCR and face search on 200-500 real race photos.
2. Confirm whether InsightFace model license is acceptable for intended use.
3. Implement bundle schema and SQLite tables.
4. Build CLI processing path first.
5. Build public search UI after the bundle can be generated.
6. Add admin UI only for operations that need visual review.

## Unresolved Questions

- Is InsightFace acceptable for commercial/donation-based use, or should another face model be selected?
- Should first deployment assume internal SSD only, or require external SSD for large events?
- Is selfie embedding latency acceptable on the MacBook Pro 2017 during public access?
