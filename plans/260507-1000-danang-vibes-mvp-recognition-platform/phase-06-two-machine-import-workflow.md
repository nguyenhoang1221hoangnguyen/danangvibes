# Phase 06: Two-Machine Import Workflow

## Context Links

- Phase 02: `phase-02-processing-cli-and-bundle-export.md`
- Phase 05: `phase-05-deployment-and-validation.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Implement the operational bridge between the processing machine and MacBook Pro 2017 server: export, copy, import, verify, publish, and rollback event bundles.

## Requirements

### Functional

- Processing machine exports a portable event bundle.
- Bundle can be copied through external SSD, LAN, AirDrop, or rsync.
- Server imports bundle into SSD-backed event storage.
- Server verifies bundle manifest, DB, thumbnails, FAISS index, and original JPG availability.
- Server can publish/unpublish the imported event.
- Server can rollback to previous bundle version if import fails.

### Non-Functional

- Import must not require AI rescanning.
- Import should be atomic: incomplete copy must not become public.
- Paths inside bundle should be relative where possible.
- Original JPGs must be served from SSD-backed storage.

## Architecture

```text
Processing machine
  -> export bundle to `dist/events/{event-slug}/`
  -> optional zip/checksum manifest
  -> copy to server SSD `incoming/`
  -> server import command validates and moves to `events/{event-slug}/releases/{version}/`
  -> publish pointer switches active release
  -> FastAPI serves active release through Cloudflare Tunnel
```

## Related Code Files

### Create

- `app/cli/export-event-command.py`
- `app/cli/import-event-command.py`
- `app/services/bundle-manifest-service.py`
- `app/services/bundle-import-service.py`
- `app/services/event-publish-service.py`
- `docs/deployment-guide.md`

## Implementation Steps

1. Define bundle manifest fields: event slug, created time, app version, model versions, photo count, thumbnail count, FAISS index path, SQLite path, original storage mode, checksum summary.
2. Add processing export command that writes the bundle to a portable directory or zip.
3. Add server import command that reads from SSD `incoming/` path.
4. Validate manifest and required files before import.
5. Copy or move bundle into server `events/{slug}/releases/{version}/`.
6. Verify original JPG paths are readable from SSD.
7. Switch active event pointer only after validation passes.
8. Add rollback command by switching active pointer to previous release.
9. Document copy options: external SSD, LAN, AirDrop, rsync.
10. Document Cloudflare Tunnel publish flow after import.

## Todo List

- [ ] Define bundle manifest schema.
- [ ] Implement export command.
- [ ] Implement import validation.
- [ ] Implement active release pointer.
- [ ] Implement rollback pointer switch.
- [ ] Document SSD directory layout.
- [ ] Document copy/import/publish commands.

## Success Criteria

- A processed event can be exported on the processing machine.
- The bundle can be copied to server SSD and imported without AI processing.
- The event becomes public only after validation passes.
- Rollback can restore the previous active release.
- Cloudflare Tunnel can serve the active event after import.

## Risk Assessment

- Partial copies can corrupt public event state. Use `incoming/` + validation + atomic publish pointer.
- Absolute paths can break across machines. Store relative bundle paths and server base path config.
- Large JPG originals can make copies slow. Support folder-based import before requiring zip.

## Security Considerations

- Do not expose `incoming/` directory publicly.
- Validate file paths before serving originals.
- Keep admin import/publish commands protected.

## Next Steps

After this phase, deployment docs should become the operator checklist for every event.

## Unresolved Questions

- Should the first implementation use folder bundles only, or support zip bundles too?
