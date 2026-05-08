# Phase 01 - Add isolated CLI stages + shared manifest refresh

## Context links
- Main process command: `processing_cli/commands/process.py:132-237`
- Rebuild embeddings command: `processing_cli/commands/rebuild_embeddings.py:52-105`
- CLI entrypoint: `processing_cli/__main__.py:8-20`
- OCR service load point: `processing_cli/services/ocr.py:43-49`
- Face service load point: `processing_cli/services/face.py:30-36`

## Overview
- Priority: P1
- Status: pending
- File ownership: `processing_cli/commands/process.py`, `processing_cli/__main__.py`, optionally `processing_cli/commands/rebuild_embeddings.py`
- Goal: split bundle processing into safe stages callable from separate Python processes while preserving bundle format

## Data flow
1. Input: source folder + event metadata + flags enter process command.
2. Stage A/base writes DB schema, event row, thumbnails, originals mapping, manifest shell.
3. Stage B/OCR reads originals and DB, writes `ocr_candidates` rows only.
4. Stage C/faces reads originals and DB, writes `faces` rows + `faiss.index` only.
5. Finalizer recomputes manifest stats/checksums from bundle DB/files.

## Minimal design
- Refactor `process.run()` internals into reusable helpers rather than one monolith.
- Add stage-level command functions inside existing `processing_cli/commands/process.py`:
  - `run_base_stage(...)`
  - `run_ocr_stage(bundle, config_path)`
  - `run_face_stage(bundle, config_path, model_name, model_version)`
  - `finalize_bundle(bundle, ...)`
- Keep existing `run(...)` as compatibility wrapper:
  - OCR-only: may still call base + OCR in same process
  - face-only: may still call base + faces in same process
  - full direct CLI: either keep current behavior for compatibility or route to stage helpers sequentially in same process; Web fix does not depend on changing this path
- Prefer helper reuse from `rebuild_embeddings.run()` for original-path resolution + face DB rewrite. Existing helper `_original_paths()` already isolates mapping load: `processing_cli/commands/rebuild_embeddings.py:18-49`

## Exact changes
1. Extract bundle bootstrap logic from `run()` lines `144-197` into base-stage helper in same file.
2. Extract OCR insert loop from `run()` lines `198-203` into helper callable after base stage.
3. Extract face insert / FAISS save from `run()` lines `204-216` into helper callable after base stage.
4. Extract manifest/originals mapping write from `run()` lines `220-236` into finalizer helper so staged orchestration can refresh output after each isolated stage or once at end.
5. Register new CLI subcommands in `processing_cli/__main__.py:8-20`, likely under `process-base`, `process-ocr`, `process-faces`, or nested args if simpler.

## Failure modes / mitigation
- Partial base bundle exists, OCR stage fails -> leave bundle on disk, manifest should reflect disabled/incomplete stage or job reports failure before publish. Mitigation: finalizer runs only after successful chain from Web orchestration.
- Face stage rerun duplicates rows -> delete existing `faces` rows and rebuild FAISS before insert, same pattern as `rebuild_embeddings.py:64-81`.
- OCR stage rerun duplicates rows -> delete existing `ocr_candidates` rows for target photos before insert.
- Helper sprawl grows file >200 lines -> acceptable for plan, but implementation should consider splitting stage helpers into same existing command module only if still readable; do not create speculative modules.

## Test matrix
- Unit
  - staged helpers create bundle without OCR/faces
  - OCR stage writes candidates into existing bundle
  - face stage rewrites faces/faiss deterministically
  - finalizer updates manifest stats/checksums
- Integration
  - existing `test_process_validate_import_publish_and_search` still passes
  - config-driven face model metadata still preserved after staged face build

## Rollback
- Remove new subcommands and inline helpers back into `run()`
- Existing bundles unaffected; just rerun processing if needed

## Success criteria
- Can generate equivalent bundle by chaining base -> OCR -> face -> finalize
- `rebuild_embeddings` behavior unchanged
- No DB schema/file format changes

## Open questions
- none
