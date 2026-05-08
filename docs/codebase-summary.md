# Codebase Summary

_Last updated: 2026-05-07_

## Overview

DaNang Vibes is a local-first MVP for event sports photo search. It processes JPG/JPEG photos into per-event bundles, then imports and publishes those bundles through a FastAPI web server.

## Main Flow

1. Scan source photos and filter supported files.
2. Generate thumbnails, checksums, and metadata.
3. Extract optional OCR bib candidates and face embeddings.
4. Build a FAISS index and export an event bundle.
5. Import the bundle into server storage and publish it.
6. Serve event pages, safe original downloads, and admin tools.

## Current Structure

| Area | Purpose |
|---|---|
| `processing_cli/` | Offline bundle generation and rebuild commands |
| `web_server/` | FastAPI app, public pages, admin tools, and search |
| `shared/` | Bundle schema, database helpers, checksums, shared models |
| `tests/` | Bundle workflow coverage |
| `docs/` | User-facing project documentation |

## Current MVP Decisions

| Topic | Current choice |
|---|---|
| Face recognition | InsightFace (buffalo_l) |
| Face search storage | FAISS (IndexFlatIP) |
| OCR | Hybrid (YOLO + Tesseract) default, PaddleOCR optional |
| Metadata DB | SQLite |
| Storage | Local disk first |
| UI | FastAPI server-rendered pages |

## Notable Runtime Features

- `processing_cli process` creates event bundles from source photos.
- `processing_cli rebuild-embeddings` rebuilds face embeddings for an existing bundle.
- Web server imports/publishes bundles and tracks download activity.
- Search flow checks face-model compatibility before running face search.
- Admin dashboard surfaces OCR review items and download stats.

## Operational Notes

- OCR and face search are optional at install time through `requirements-ai.txt` and `INSTALL_AI.md`.
- Face embeddings are treated as sensitive biometric data.
- Original photo downloads use safe relative-path mapping only.
- The bundle contract is documented in `docs/bundle-format.md`.

## Relevant Docs

- [README](../README.md)
- [Bundle Format](./bundle-format.md)
