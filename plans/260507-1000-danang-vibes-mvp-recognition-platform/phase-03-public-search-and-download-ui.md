# Phase 03: Public Search and Download UI

## Context Links

- Phase 01: `phase-01-foundation-and-schema.md`
- Phase 02: `phase-02-processing-cli-and-bundle-export.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Let customers search published events by bib number and selfie upload, view tabbed results, download original JPGs, and see donation prompts.

## Requirements

### Functional

- Public event landing page.
- Bib number input.
- Selfie upload input.
- Tabbed results: Bib Match, Face Match, Suggested.
- Thumbnail grid.
- Original JPG download endpoint.
- Donation prompt on result page and after download.

### Non-Functional

- Use server-rendered HTML/Jinja + HTMX.
- Avoid loading original images in grid.
- Stream original files safely.
- Keep UI mobile-friendly.

## Architecture

```text
Customer request
  -> FastAPI route
  -> SQLite/FAISS search services
  -> Jinja templates
  -> thumbnails + original download endpoint
```

## Related Code Files

### Create

- `app/web/public-routes.py`
- `app/services/search-service.py`
- `app/services/download-service.py`
- `app/templates/public/event-page.html`
- `app/templates/public/search-results.html`
- `app/templates/public/photo-grid.html`
- `app/static/`

## Implementation Steps

1. Add public event route.
2. Implement bib search query.
3. Implement selfie upload route and face search.
4. Implement tabbed result template.
5. Implement thumbnail serving.
6. Implement safe original download endpoint.
7. Add donation prompt components.
8. Add basic rate limiting if needed.

## Todo List

- [ ] Public event page.
- [ ] Bib search form.
- [ ] Selfie upload form.
- [ ] Result tabs.
- [ ] Download endpoint.
- [ ] Donation prompt.
- [ ] Mobile layout check.

## Success Criteria

- Customer can find photos by bib.
- Customer can upload selfie and get face match results.
- Customer can download original JPG.
- Donation prompt appears on result page and after download.

## Risk Assessment

- Selfie embedding may be too slow on MacBook 2017. Benchmark query latency.
- Direct original download can saturate tunnel. Add soft limits if needed.

## Security Considerations

- Validate event/photo IDs.
- Prevent path traversal.
- Limit selfie upload size and file type.
- Avoid storing selfie uploads longer than needed unless explicitly required.

## Next Steps

Add admin UI for publish/review/correction.

## Unresolved Questions

- Should selfie uploads be deleted immediately after query?
