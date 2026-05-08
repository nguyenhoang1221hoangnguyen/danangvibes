# Phase 02 - Switch Processing Web jobs to subprocess orchestration

## Context links
- Request entrypoint: `processing_web/routes.py:35-64`
- Job validation/runtime check: `processing_web/jobs.py:108-123`
- Current direct runner execution: `processing_web/jobs.py:125-155`
- AI import validators: `processing_web/jobs.py:69-80`
- Processing settings: `processing_web/config.py:18-24`

## Overview
- Priority: P1
- Status: pending
- File ownership: `processing_web/jobs.py`, `tests/test_processing_web.py`
- Goal: make App 1 full mode call isolated CLI stages in subprocesses instead of importing both AI stacks into web server process

## Data flow
1. UI sends form data -> `ProcessingJobRequest`: `processing_web/routes.py:35-54`
2. Job manager validates folder/slug/output path locally: `processing_web/jobs.py:108-116`
3. Runtime preflight spawns short-lived subprocesses for OCR import check and DeepFace import check separately; parent collects exit codes/stdout/stderr.
4. Worker thread spawns 3-4 subprocesses in order:
   - base stage
   - OCR stage
   - face stage
   - optional finalize stage if not implicit in previous stage
5. Child processes write bundle DB/files. Parent only tracks status and surfaces failures.
6. `/jobs/current/status` exposes success/failure unchanged: `processing_web/routes.py:94-108`

## Minimal design
- Replace default runner dependency in `ProcessingJobManager` with a command runner abstraction that can still be faked in tests.
- Add helper in `processing_web/jobs.py` to build `python -m processing_cli ...` args using current interpreter (`sys.executable`) to preserve `venv-ai` environment.
- Replace `validate_ai_runtime()` same-process import calls with `validate_ai_runtime_subprocess()` that executes isolated CLI sanity commands, one per library.
- Do not move job execution to multiprocessing inside web app; subprocess CLI chain is enough.

## Exact changes
1. Remove top-level imports of `load_deepface_class`, `load_paddleocr_class`, and `process_run` from `processing_web/jobs.py:6-15`; these imports themselves keep web process coupled to AI modules and process command module.
2. Keep `check_ai_dependencies()` as cheap `find_spec()` guard: `processing_web/jobs.py:69-75`.
3. Replace `validate_ai_runtime()` implementation at `processing_web/jobs.py:78-80` with subprocess-based checks, eg dedicated CLI subcommands or `python -c` imports. Prefer CLI subcommands for repo-owned error messages.
4. Replace `_runner(...)` invocation at `processing_web/jobs.py:128-139` with sequential subprocess executions. On first non-zero exit, capture stderr into `job.error`.
5. Keep `ProcessingJobManager.start_job/current_job/_update_job` contract stable to avoid route changes.
6. Ensure subprocess env inherits current env; no custom PYTHONPATH hacks if `python -m processing_cli` already works from project root.

## Failure modes / mitigation
- Child process hangs same as before -> still isolated; parent remains alive, UI keeps polling. Add timeout per stage only if repo already has timeout conventions; otherwise KISS keep no timeout in first pass and rely on manual stop/restart. Note as future work, not MVP.
- stderr too verbose for UI -> truncate stored error to useful tail if needed.
- Parent cwd mismatch breaks `python -m processing_cli` -> pass `cwd` explicitly to project root.
- Preflight passes but heavy model init later fails -> surface child stderr from processing stage.
- Windows quoting irrelevant now; current target macOS only, but use arg list not shell string for safer cross-platform behavior.

## Backwards compatibility
- UI route and job JSON unchanged.
- CLI users unaffected unless they opt into new stage subcommands.
- `check_ai_dependencies()` dashboard rendering still works because it only inspects installed packages.

## Test matrix
- Unit
  - request validation no longer imports AI modules in-process
  - subprocess command builder includes correct flags/paths
  - failed child process marks job failed with error text
- Integration
  - `test_processing_starts_full_ocr_face_job` updated to assert staged subprocess/runner calls in order
  - `test_processing_rejects_broken_ai_runtime` updated to simulate failed runtime check subprocess
  - current single-running-job guard still passes unchanged

## Rollback
- Restore direct `process_run` runner and same-process `validate_ai_runtime()`
- No bundle migration needed

## Success criteria
- Web app process can start full job without importing OCR + DeepFace together
- Failure in OCR or face child process reports deterministic error in `/jobs/current/status`
- UI remains responsive even when child crashes

## Open questions
- none
