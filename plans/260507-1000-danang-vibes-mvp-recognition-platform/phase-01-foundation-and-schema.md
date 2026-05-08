# Phase 01: Foundation and Schema

## Context Links

- Brainstorm: `docs/brainstorming/2026-05-07-danang-vibes-mvp-recognition-platform.md`
- Research: `plans/260507-1000-danang-vibes-mvp-recognition-platform/research/ocr-face-search-stack-research.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Establish the minimal FastAPI/SQLite foundation and event bundle data model.

## Requirements

### Functional

- Create FastAPI app structure.
- Add SQLite connection/session layer.
- Define event bundle directory conventions.
- Define database tables for events, photos, thumbnails, OCR candidates, faces, downloads, donation config.
- Add basic health route.

### Non-Functional

- Keep modules small and simple.
- Use type hints.
- Support local filesystem paths.
- Avoid cloud dependency in MVP.

## Architecture

```text
app/
├── main.py
├── config.py
├── database.py
├── models/
├── services/
├── web/
├── cli/
└── templates/
```

## Related Code Files

### Create

- `app/main.py`
- `app/config.py`
- `app/database.py`
- `app/models/event.py`
- `app/models/photo.py`
- `app/models/search.py`
- `app/services/event-bundle-service.py`
- `requirements.txt`
- `tests/`

## Implementation Steps

1. Create Python project structure.
2. Add dependencies: FastAPI, Uvicorn, SQLAlchemy, Pydantic, Pillow, Jinja2, python-multipart.
3. Define SQLite schema.
4. Add basic app startup and health route.
5. Add event bundle path config.
6. Add unit tests for schema creation and bundle path validation.

## Todo List

- [ ] Create app folder structure.
- [ ] Add requirements.
- [ ] Add config module.
- [ ] Add database module.
- [ ] Add models.
- [ ] Add health route.
- [ ] Add basic tests.

## Success Criteria

- `mypy app/` passes.
- `pytest tests/ -v` passes.
- App can create/open SQLite database.

## Risk Assessment

- Schema may grow too early. Keep only MVP fields.
- Bundle path portability can break across machines. Store relative paths inside bundle.

## Security Considerations

- Do not store secrets in DB.
- Validate public download paths to prevent path traversal.

## Next Steps

Proceed to processing CLI after schema is stable.

## Unresolved Questions

- SQLAlchemy vs raw sqlite3 final choice.
