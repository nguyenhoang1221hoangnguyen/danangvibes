---
title: "Fix Processing Web full OCR + face hang via isolation"
description: "KISS plan to isolate PaddleOCR and DeepFace so Processing Web can run full mode without same-process runtime lockups."
status: pending
priority: P1
effort: 5h
branch: no-git-repo
tags: [processing-web, ocr, deepface, subprocess, stability]
created: 2026-05-07
---

# Plan overview

Goal: giữ App 1 UI flow nguyên trạng nhưng tránh import/load PaddleOCR và DeepFace trong cùng Python process, vì full mode hiện gọi cả hai trong một process qua `process.run()` và runtime preflight cũng load cả hai. Citations: `processing_web/jobs.py:78-80`, `processing_web/jobs.py:128-139`, `processing_cli/commands/process.py:167-168`, `processing_cli/commands/process.py:198-213`.

## Proposed phases

1. [Phase 01 - Add isolated CLI stages + shared manifest refresh](./phase-01-add-isolated-cli-stages.md)
2. [Phase 02 - Switch Processing Web jobs to subprocess orchestration](./phase-02-switch-processing-web-to-subprocess-orchestration.md)
3. [Phase 03 - Validate workflow and regressions](./phase-03-validate-workflow-and-regressions.md)

## Dependency graph

- Phase 01 blocks Phase 02
- Phase 02 blocks Phase 03
- No parallel coding: shared ownership on `processing_cli/commands/process.py`, `processing_web/jobs.py`, tests

## Current traced flow

- UI POST `/process` builds `ProcessingJobRequest` then calls `job_manager.start_job(...)`: `processing_web/routes.py:35-64`
- `ProcessingJobManager._validate_request()` checks deps and calls `validate_ai_runtime()` which loads PaddleOCR then DeepFace in one process: `processing_web/jobs.py:108-123`, `processing_web/jobs.py:78-80`
- Worker thread calls `_runner`, defaulting to `process_run`: `processing_web/jobs.py:84`, `processing_web/jobs.py:125-139`
- `process.run()` instantiates `OCRService` then `FaceService` in one process before loop: `processing_cli/commands/process.py:167-168`
- OCR and face stages run sequentially per photo inside same process: `processing_cli/commands/process.py:198-213`

## Decision

Use process isolation, not threads, not lazy imports only.

Reason:
- crash already reproduced on import/load combination, so reordering/lazy-init weak mitigation
- current architecture already has CLI boundary (`processing_cli/__main__.py:8-20`), easiest place to isolate
- keeps UI contract stable: same form, same job status endpoints: `processing_web/routes.py:35-64`, `processing_web/routes.py:94-108`

## Success criteria

- Processing Web full mode completes without same-process OCR+DeepFace init in server job process
- `validate_ai_runtime()` no longer imports both libraries in one process
- Full pipeline still emits valid bundle: manifest, DB, thumbnails, FAISS index
- `rebuild-embeddings` still works unchanged or with only helper reuse
- Tests cover subprocess command construction, failure propagation, and bundle workflow compatibility

## Backwards compatibility

- Keep existing `python -m processing_cli process` contract working for callers/tests using OCR-only or face-only flags
- Add new optional isolated path for full mode from Processing Web; existing bundle schema unchanged because manifest/db writing still uses current tables/files: `processing_cli/commands/process.py:72-129`, `processing_cli/commands/process.py:220-236`
- No migration for existing bundles

## Rollback

- Revert Processing Web orchestration to direct `process_run` call
- Keep newly added CLI subcommands/helpers removable without data migration
- If subprocess path fails in prod, users can still run OCR-only or face-only CLI until rollback lands

## Validation summary

- Unit: command builder, preflight isolation checks, job error handling
- Integration: Processing Web start job -> spawned staged commands -> succeeded/failed status
- E2E-lite: bundle workflow with staged full run under fake services/subprocess stubs

## Open questions

- none
