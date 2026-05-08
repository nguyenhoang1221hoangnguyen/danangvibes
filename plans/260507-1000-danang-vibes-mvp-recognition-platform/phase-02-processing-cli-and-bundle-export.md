# Phase 02: Processing CLI and Bundle Export

## Context Links

- Research: `research/ocr-face-search-stack-research.md`
- Phase 01: `phase-01-foundation-and-schema.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Build the processing-machine path that scans JPG files from SSD/local storage, creates thumbnails, extracts bib OCR/face data, and exports a portable event bundle for the MacBook Pro 2017 server.

## Requirements

### Functional

- CLI command to create/process event from one JPG folder.
- Generate checksums for dedupe/cache.
- Generate thumbnails for UI.
- Extract EXIF capture time when available.
- Run PaddleOCR for bib candidates.
- Run face detection/embedding and build FAISS index.
- Export event bundle with DB, thumbnails, FAISS index, manifest, and original JPG files or relative SSD-backed original mappings.
- Produce bundle format that can be copied by external SSD, LAN, AirDrop, or rsync into the server import directory.

### Non-Functional

- Batch processing only.
- Resize before inference.
- Process one image at a time or low concurrency.
- Cache by checksum/model version.

## Architecture

```text
Processing machine
  -> SSD/local JPG event folder
  -> ingest service
  -> thumbnail service
  -> OCR service
  -> face embedding service
  -> SQLite + FAISS
  -> portable event bundle
  -> copy to server SSD import directory
```

## Related Code Files

### Create

- `app/cli/process-event-command.py`
- `app/services/photo-ingest-service.py`
- `app/services/thumbnail-service.py`
- `app/services/bib-ocr-service.py`
- `app/services/face-index-service.py`
- `app/services/bundle-export-service.py`
- `app/vector/faiss-index-store.py`

## Implementation Steps

1. Add CLI entrypoint for processing machine.
2. Scan one JPG/JPEG event folder from SSD/local storage.
3. Store photo metadata, relative original path, checksum, and EXIF capture time.
4. Generate thumbnails into bundle `thumbnails/`.
5. Add PaddleOCR integration behind a service interface.
6. Add face embedding integration behind a service interface.
7. Build FAISS index and vector mapping.
8. Write bundle manifest with model versions, source summary, original storage mode, and import instructions.
9. Add export command that creates a portable folder or zip for server import.
10. Add small-sample integration test with fixture JPGs.

## Todo List

- [ ] Implement JPG scanner.
- [ ] Implement checksum cache.
- [ ] Implement thumbnail generation.
- [ ] Implement OCR service.
- [ ] Implement face service.
- [ ] Implement FAISS store.
- [ ] Implement bundle export.
- [ ] Implement portable folder/zip output for server import.
- [ ] Document copy/import command for SSD/LAN transfer.
- [ ] Test with sample photos.

## Success Criteria

- Processing 200-500 sample photos completes on the processing machine.
- Bundle includes SQLite DB, thumbnails, FAISS index, manifest, and original JPG storage/mapping.
- Bundle can be copied to the server SSD and imported without rescanning originals.
- Re-running processing skips cached photos.

## Risk Assessment

- OCR/face dependencies may be heavy. Isolate behind service modules.
- InsightFace license unresolved. Keep model abstraction swappable.
- Selfie embedding on server may be slow. Benchmark before public release.

## Security Considerations

- Do not log embeddings or uploaded selfie content publicly.
- Keep model version in metadata for reproducibility.

## Next Steps

Build public search UI after bundle format is usable.

## Unresolved Questions

- Which face model is legally acceptable for first public event?
