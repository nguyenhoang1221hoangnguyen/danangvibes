# Phase 05: Deployment and Validation

## Context Links

- Phase 01: `phase-01-foundation-and-schema.md`
- Phase 02: `phase-02-processing-cli-and-bundle-export.md`
- Phase 03: `phase-03-public-search-and-download-ui.md`
- Phase 04: `phase-04-admin-ui-and-manual-review.md`

## Overview

**Priority:** High before real event  
**Status:** Planned  
**Goal:** Validate the full two-machine workflow: processing machine scans/processes JPG photos, exports a bundle, the MacBook Pro 2017 imports it from SSD storage, then serves publicly through Cloudflare Tunnel.

## Requirements

### Functional

- Process sample event on a separate processing machine, preferably MacBook M1.
- Export event bundle with SQLite, thumbnails, FAISS index, manifest, and original JPG storage/mapping.
- Copy/import bundle to SSD storage used by the MacBook Pro 2017 server.
- Serve through Cloudflare Tunnel.
- Search by bib and selfie.
- Download original JPG.
- Show donation prompts.

### Non-Functional

- Keep setup repeatable.
- Avoid fragile manual steps where possible.
- Measure basic performance.

## Architecture

```text
Processing machine
  -> SSD/local JPG event folder
  -> process/export event bundle
  -> copy via external SSD/LAN/AirDrop/rsync
  -> MacBook Pro 2017 SSD import directory
  -> FastAPI server loads imported bundle
  -> Cloudflare Tunnel exposes public URL
  -> customer search/download access
```

## Related Files

### Create

- `docs/deployment-guide.md`
- `docs/codebase-summary.md`
- `scripts/` if needed for local operations

## Implementation Steps

1. Standardize Cloudflare Tunnel as the MVP tunnel provider.
2. Define server SSD directory layout for imported event bundles.
3. Write processing-machine export command.
4. Write server-machine import/publish command.
5. Write local server run command.
6. Write Cloudflare Tunnel run/config steps.
7. Test 200-500 real photos on processing machine.
8. Copy/import bundle to server SSD.
9. Benchmark search latency and original JPG download on server.
10. Test concurrent browsing/download manually through Cloudflare Tunnel.
11. Document operations.

## Todo List

- [ ] Configure Cloudflare Tunnel.
- [ ] Define server SSD bundle directory.
- [ ] Validate processing on real sample.
- [ ] Validate copy/import into server SSD.
- [ ] Validate public Cloudflare Tunnel access.
- [ ] Validate original JPG download speed.
- [ ] Write deployment guide.

## Success Criteria

- Full two-machine workflow works end-to-end.
- Event bundle copied/imported from processing machine to server SSD without rescanning.
- Cloudflare Tunnel public URL can search and download.
- MacBook Pro 2017 remains responsive during browsing/download tests.
- Deployment guide is accurate enough to repeat.

## Risk Assessment

- Cloudflare Tunnel bandwidth may be the bottleneck for original JPG downloads.
- SSD capacity may limit number of active full-resolution event bundles.
- Selfie query embedding may be slow on server.

## Security Considerations

- Admin secret must be env var.
- Do not expose filesystem paths.
- Set max upload size for selfie.
- Avoid logging sensitive biometric data.

## Next Steps

Use validation results to decide whether to optimize face model, download handling, or storage.

## Unresolved Questions

- Whether SSD storage is internal or external for large events.
- Whether selfie embedding latency on MacBook Pro 2017 is acceptable during public access.
