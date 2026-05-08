# Implementation Plan: OCR + Face Improvements

**Created:** 2026-05-09
**Status:** in_progress
**Target:** Fix OCR missing bib + face index empty/disabled for all photos

---

## Overview

Fix 3 root causes causing incomplete OCR detection (3/95 photos) and face index being empty/crash:

1. Hybrid OCR missing 2 fallback stages
2. `rebuild-embeddings.py:_original_paths()` wrong logic for embedded mode
3. Scanner picks hidden files (already fixed)

Also simplify by removing isolate_ai_stages (already done in jobs.py).

---

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | pending | Fix OCR hybrid fallbacks (YOLO low conf + PaddleOCR) |
| Phase 2 | pending | Fix rebuild-embeddings _original_paths() |
| Phase 3 | pending | Cleanup: remove isolate_ai_stages from UI + CLI + fix labels |
| Phase 4 | pending | Validate: run full processing test |

---

## Phase 1: Fix OCR hybrid fallbacks

**File:** `processing_cli/services/ocr_hybrid.py`

Implement 2 missing fallbacks in `detect_bib_numbers()`:

### 1.1: Lower YOLO confidence fallback (currently documented but not implemented)
- After primary YOLO (conf=0.3) fails, re-run with conf=0.1
- Lines ~241-248

### 1.2: PaddleOCR fallback (currently stub `pass`)
- When both YOLO tiers fail, call PaddleOCR on full image
- Need to import `OCRService` from `processing_cli/services/ocr.py`
- Call `ocr_service.extract_bib_candidates()` and return results
- Lines ~254-258

---

## Phase 2: Fix rebuild-embeddings

**File:** `processing_cli/commands/rebuild_embeddings.py`

### 2.1: Fix `_original_paths()` 
- Current bug: uses `original_path` from DB (raw filename) for embedded mode
- Fix: always read from `originals_mapping.json` (both embedded and mapping modes)
- Already partially done in earlier session

### 2.2: Fix face model label
- Change hardcoded `"DeepFace"` → actual model name from config/service
- Line 96

---

## Phase 3: Cleanup

### 3.1: Remove isolate_ai_stages from CLI
- `processing_cli/commands/process.py`: remove `--isolate-ai-stages` argument
- Keep `_run_isolated_full_processing()` function for backward compat but not used

### 3.2: Remove isolate checkbox from UI
- `processing_web/templates/processing_dashboard.html`: remove the isolate fieldset

### 3.3: Verify jobs.py
- Already set `isolate_ai_stages=False` (done earlier)

---

## Phase 4: Validate

- Run processing on test-bib folder (35 images)
- Verify bib detection count improved
- Check manifest.json shows correct face model
- Test search works (bib + face)
- Test download originals from bundle

---

## Success Criteria

- [ ] OCR detects bib on >70% photos with visible bib numbers
- [ ] Face index not empty (faiss.index > 24 bytes)
- [ ] manifest.json: face_model is "InsightFace/buffalo_l/v1" (not "disabled")
- [ ] All 95 photos in hoa-bac-training have face embeddings
- [ ] Bundle download serves originals from embedded mode

---

## Files Modified

1. `processing_cli/services/ocr_hybrid.py` - Phase 1
2. `processing_cli/commands/rebuild_embeddings.py` - Phase 2
3. `processing_cli/commands/process.py` - Phase 3
4. `processing_web/templates/processing_dashboard.html` - Phase 3
5. `processing_web/jobs.py` - Already done
6. `processing_cli/services/scanner.py` - Already done