# DaNang Vibes MVP Recognition Platform Plan

## Overview

Build a **2-app system** for post-event photo discovery at Ironman/sports events:

1. **Processing App** (MacBook M1): Heavy AI processing - OCR, face detection, embedding extraction, export bundle
2. **Web Server** (MacBook Pro 2017): Lightweight serving - import bundle, search UI, download, admin panel

**Workflow:** Process on M1 → Export bundle → Copy via SSD/LAN → Import to MacBook 2017 → Serve via Cloudflare Tunnel

**Read:** [ARCHITECTURE.md](ARCHITECTURE.md) for detailed 2-app design, commands, and deployment workflow.

## Key Decisions

### Architecture
- **2 separate apps**: Processing CLI (M1) + Web Server (MacBook 2017)
- **Bundle format**: SQLite + FAISS + thumbnails + manifest.json
- **Transfer method**: External SSD / rsync / AirDrop
- **Public access**: Cloudflare Tunnel (free tier)

### Tech Stack
- **Processing App**: Python CLI (Click) + PaddleOCR + InsightFace/DeepFace + FAISS
- **Web Server**: FastAPI + Jinja2 + HTMX + SQLAlchemy
- **Storage**: SQLite metadata + FAISS vector index
- **Input**: JPG/JPEG only

### Features
- **Search**: Bib number (exact match) + Selfie upload (face similarity)
- **Download**: Original full-resolution JPG
- **Admin**: OCR review, manual correction, publish/unpublish, donation config
- **Monetization**: Optional donation QR code (no payment gateway in MVP)

## Phase Status

Code-side MVP core is in repo now; benchmark, deployment, and hardware validation stay pending.

| Phase | File | Status |
|---|---|---|
| 00 | [License & Model Validation](phase-00-license-model-validation.md) | Planned |
| 01 | [Shared Foundation & Bundle Schema](phase-01-shared-foundation-bundle-schema.md) | Implemented |
| 02 | [Processing App (MacBook M1)](phase-02-processing-app-m1.md) | Implemented |
| 03 | [Bundle Import & Export Workflow](phase-03-bundle-import-export-workflow.md) | Implemented |
| 04 | [Web Server Core (MacBook 2017)](phase-04-web-server-core-macbook-2017.md) | Implemented |
| 05 | [Public Search & Download UI](phase-05-public-search-download-ui.md) | Implemented |
| 06 | [Admin UI & Manual Review](phase-06-admin-ui-manual-review.md) | Implemented |
| 07 | [Testing & Performance Validation](phase-07-testing-performance-validation.md) | Planned |
| 08 | [Deployment & Operations](phase-08-deployment-operations.md) | Planned |

## Key Dependencies

### Processing App (M1)
- **PaddleOCR** - Bib OCR (Apache 2.0)
- **InsightFace/DeepFace** - Face detection & embedding (license validation required)
- **FAISS** - Vector index builder (MIT)
- **Pillow** - Image processing & thumbnails
- **Click** - CLI framework
- **SQLAlchemy** - SQLite ORM

### Web Server (MacBook 2017)
- **FastAPI** - Web framework
- **Jinja2 + HTMX** - Server-rendered UI
- **FAISS** - Vector search (read-only)
- **SQLAlchemy** - SQLite ORM
- **Uvicorn** - ASGI server

### Infrastructure
- **Cloudflare Tunnel** - Public access (free tier)
- **External SSD** - Bundle transfer & storage

## Success Criteria

### Processing App (M1)
- [ ] Process 200-500 sample photos in < 30 minutes
- [ ] OCR accuracy ≥ 70% for visible bibs
- [ ] Face detection rate ≥ 80% for clear faces
- [ ] Export valid bundle with manifest, SQLite, FAISS, thumbnails
- [ ] Bundle validation passes

### Web Server (MacBook 2017)
- [ ] Import bundle without AI re-processing
- [ ] Bib search latency < 200ms
- [ ] Selfie search latency < 5s (nếu > 5s → move to async)
- [ ] Original download speed ≥ 1MB/s via Cloudflare Tunnel
- [ ] Memory usage ≤ 4GB during 10 concurrent users
- [ ] Admin can review/correct OCR mistakes
- [ ] Donation QR code displays correctly

### End-to-End
- [ ] Full workflow: M1 process → export → copy → import → publish → public access
- [ ] Rollback to previous bundle version works
- [ ] Server remains responsive during concurrent browsing/download

## Performance Targets

### Processing (M1)
- OCR: ≤ 1s/photo
- Face detection: ≤ 0.5s/photo
- Face embedding: ≤ 0.3s/face
- Total: ≤ 3s/photo
- 5000 photos: ≤ 4 hours

### Serving (MacBook 2017)
- Bib search: < 200ms
- Selfie search: < 5s
- Thumbnail load: < 100ms
- Original download: 1-5MB/s
- Memory: 2-4GB
- Concurrent users: 10-50

## Implementation Timeline

**Total estimated time:** 8-10 weeks

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 00 | 3-5 days | None (BLOCKING) |
| Phase 01 | 5-7 days | Phase 00 |
| Phase 02 | 10-12 days | Phase 01 |
| Phase 03 | 5-7 days | Phase 01, 02 |
| Phase 04 | 8-10 days | Phase 01, 03 |
| Phase 05 | 10-12 days | Phase 04 |
| Phase 06 | 8-10 days | Phase 04, 05 |
| Phase 07 | 12-15 days | All previous |
| Phase 08 | 8-10 days | Phase 07 |

**Critical path:** Phase 00 → 01 → 02 → 03 → 04 → 05 → 07 → 08

**Parallel work possible:**
- Phase 06 (Admin UI) can start after Phase 04 completes
- Documentation can be written throughout

## Quick Start Guide

### For Developers

1. **Read first:**
   - `SUMMARY.md` - 1-page overview
   - `ARCHITECTURE.md` - Detailed design
   - `phase-00-license-model-validation.md` - BLOCKING decision

2. **Start with Phase 00:**
   - Validate InsightFace license
   - Choose face model
   - Document decision

3. **Then Phase 01:**
   - Define shared schema
   - Create bundle format
   - Write Python models

4. **Proceed sequentially through phases**

### For Project Managers

1. **Understand the 2-app architecture:**
   - Processing App (M1) = heavy AI work
   - Web Server (MacBook 2017) = lightweight serving

2. **Key milestones:**
   - Phase 00 complete = can start coding
   - Phase 02 complete = can process first event
   - Phase 05 complete = MVP functional
   - Phase 07 complete = production-ready
   - Phase 08 complete = deployed

3. **Risk management:**
   - Phase 00: InsightFace license unclear → use DeepFace
   - Phase 07: Performance issues → optimize or adjust targets

## Critical Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| InsightFace license unclear | Cannot use for commercial/donation | Phase 00: Validate license OR use DeepFace (MIT) |
| Selfie embedding too slow on MacBook 2017 | Poor UX | Benchmark in Phase 07; fallback: async queue or admin-only |
| Cloudflare Tunnel bandwidth limit | Slow downloads | Monitor usage; fallback: direct IP + port forward |
| Bundle transfer too slow | Operational friction | Use rsync incremental sync; compress thumbnails |
| OCR accuracy poor | Manual correction overhead | Admin review UI + confidence threshold tuning |

## Unresolved Questions

### Phase 00 (Must resolve before Phase 02)
- [ ] InsightFace model license acceptable for donation-based app?
- [ ] If not, switch to DeepFace or FaceNet?

### Phase 03 (Must resolve before Phase 04)
- [ ] Bundle originals mode: copy into bundle OR reference external path?
- [ ] Transfer method: External SSD (preferred) OR rsync over LAN?

### Phase 07 (Must resolve before Phase 08)
- [ ] Selfie embedding latency on MacBook 2017 acceptable?
- [ ] If not, move to async queue OR disable public selfie search?

### Operations
- [ ] SSD storage: internal OR external for MacBook 2017?
- [ ] Backup strategy: rsync to NAS OR cloud storage?
