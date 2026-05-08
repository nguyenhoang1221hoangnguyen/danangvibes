# Phase 04: Admin UI and Manual Review

## Context Links

- Phase 03: `phase-03-public-search-and-download-ui.md`

## Overview

**Priority:** Medium  
**Status:** Planned  
**Goal:** Add basic admin UI for event publishing, OCR review, manual bib correction, and donation config.

## Requirements

### Functional

- Admin event list.
- Import/publish bundle.
- Public/private event toggle.
- OCR candidate review page.
- Manual bib correction.
- Donation QR/config fields.
- Basic processing summary.

### Non-Functional

- Simple password-protected admin area or local-only admin first.
- Keep admin UI minimal.
- Use server-rendered templates.

## Architecture

```text
Admin UI
  -> event service
  -> OCR review service
  -> donation config service
  -> SQLite updates
```

## Related Code Files

### Create

- `app/web/admin-routes.py`
- `app/services/admin-event-service.py`
- `app/services/bib-correction-service.py`
- `app/templates/admin/event-list.html`
- `app/templates/admin/ocr-review.html`
- `app/templates/admin/donation-config.html`

## Implementation Steps

1. Add admin route group.
2. Add event list and status page.
3. Add bundle import/publish action.
4. Add OCR review table/grid.
5. Add manual bib correction form.
6. Add donation config form.
7. Add minimal admin protection.

## Todo List

- [ ] Event list.
- [ ] Bundle publish.
- [ ] Event public/private toggle.
- [ ] OCR review.
- [ ] Manual correction.
- [ ] Donation config.
- [ ] Admin protection.

## Success Criteria

- Admin can publish/unpublish event.
- Admin can correct bib OCR mistakes.
- Donation QR/config is reflected on public page.

## Risk Assessment

- Admin auth can grow into full user system. Keep it minimal for MVP.
- Manual review can be slow if UI is poor. Focus on uncertain OCR rows first.

## Security Considerations

- Do not expose admin routes publicly without protection.
- Store admin secret in env var.

## Next Steps

Finalize deployment workflow and validation checklist.

## Unresolved Questions

- Should admin UI be accessible through Cloudflare Tunnel with protection, or local-only?
