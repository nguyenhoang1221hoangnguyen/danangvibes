# Phase 03 - Validate workflow and regressions

## Context links
- Workflow tests: `tests/test_bundle_workflow.py:62-228`
- Processing web tests: `tests/test_processing_web.py:36-290`
- Current health endpoint: `processing_web/routes.py:111-113`

## Overview
- Priority: P1
- Status: pending
- File ownership: `tests/test_bundle_workflow.py`, `tests/test_processing_web.py`
- Goal: prove the isolation fix works without breaking bundle generation or web job UX

## Validation plan

### Unit tests
- `tests/test_processing_web.py`
  - Add fake subprocess executor to assert runtime preflight runs OCR and DeepFace checks in separate calls
  - Assert full job executes staged commands in exact order: base -> OCR -> faces -> finalize
  - Assert first failed stage marks job `failed` and exposes stderr tail in status payload
  - Keep current guards for invalid source, duplicate running jobs, and dependency absence

### Integration tests
- `tests/test_bundle_workflow.py`
  - Add staged-process path test with monkeypatched fake OCR/face services and FAISS builder; validate manifest stats equal expectations
  - Re-run existing rebuild embeddings test to ensure face-only rebuild still independent: `tests/test_bundle_workflow.py:173-228`

### Manual validation on target env
1. Activate `venv-ai` on macOS arm64.
2. Run isolated preflights individually from new CLI/runtime helpers.
3. Start Processing Web App.
4. Submit one small folder from UI with full mode.
5. Confirm job reaches `succeeded`, bundle contains `event.db`, `faiss.index`, `manifest.json`, `thumbnails/`.
6. Inspect logs: no `mutex lock failed` or `[mutex.cc] RAW: Lock blocking` in parent web process.

## Risk assessment
- High likelihood / high impact: test doubles too coupled to old direct runner API. Mitigation: move tests to fake command executor interface, not monkeypatching AI imports.
- Medium likelihood / medium impact: staged manifests diverge from monolithic output. Mitigation: assert exact stats rows and model metadata.
- Low likelihood / high impact: hidden caller of `validate_ai_runtime()` expects same-process side effect. Mitigation: grep shows only `processing_web/jobs.py:121` caller.

## Rollback verification
- If regressions appear, disable subprocess orchestration patch and rerun existing tests; old path should pass because data model untouched.

## Done definition
- Updated tests pass locally in non-AI env with fakes
- Manual macOS arm64 smoke run passes in `venv-ai`
- User can trigger full OCR + face from App 1 UI without parent-process hang

## Open questions
- none
