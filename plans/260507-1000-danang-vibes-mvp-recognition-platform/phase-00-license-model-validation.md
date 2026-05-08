# Phase 00: License & Model Validation

## Context Links

- Research: `research/ocr-face-search-stack-research.md`
- Architecture: `ARCHITECTURE.md`

## Overview

**Priority:** P0 - BLOCKING  
**Status:** Planned  
**Goal:** Validate AI model licenses for donation-based commercial use and select final face recognition model before implementation.

## Why This Phase Exists

InsightFace has unclear model license restrictions. Using it without validation risks legal issues if the app accepts donations. This phase MUST complete before Phase 02 (Processing App) to avoid rework.

## Requirements

### Functional

- Research InsightFace model pack licenses
- Research alternative face models with clear licenses
- Benchmark accuracy and performance of alternatives
- Document final model choice with license justification

### Non-Functional

- License must allow donation-based usage
- Model must run on MacBook M1 (no GPU required)
- Accuracy must be acceptable for sports event photos

## Model Candidates

### Option 1: InsightFace (Current)
- **Code License:** MIT ✓
- **Model License:** UNCLEAR ⚠️
  - Pre-trained models may have research-only restrictions
  - Need to check specific model pack license (e.g., `buffalo_l`, `antelopev2`)
- **Accuracy:** Excellent
- **Performance:** Fast on CPU
- **Action:** Check model pack license files and terms

### Option 2: DeepFace (Fallback)
- **License:** MIT ✓
- **Models:** Wraps multiple backends (VGG-Face, Facenet, ArcFace, etc.)
- **Accuracy:** Good (slightly lower than InsightFace)
- **Performance:** Slower than InsightFace
- **Action:** Benchmark if InsightFace fails license check

### Option 3: FaceNet (facenet-pytorch)
- **License:** MIT ✓
- **Accuracy:** Good
- **Performance:** Moderate
- **Action:** Benchmark if both above fail

### Option 4: face_recognition (dlib-based)
- **License:** MIT ✓
- **Accuracy:** Lower than above
- **Performance:** Slow
- **Action:** Last resort only

## Implementation Steps

1. **Research InsightFace licenses**
   - Check GitHub repo: https://github.com/deepinsight/insightface
   - Check model pack licenses in `model_zoo/`
   - Search for commercial use restrictions
   - Check if donation-based usage is considered commercial

2. **If InsightFace OK:**
   - Document license findings
   - Proceed to Phase 01

3. **If InsightFace NOT OK:**
   - Benchmark DeepFace with sample photos
   - Compare accuracy vs InsightFace
   - If acceptable → use DeepFace
   - If not → benchmark FaceNet

4. **Document decision**
   - Write `research/face-model-license-decision.md`
   - Include: license summary, benchmark results, final choice, justification

## Benchmark Protocol

Use 50-100 sample race photos with known athletes.

**Metrics:**
- Face detection rate (% photos with faces detected)
- Embedding extraction time (seconds/face)
- Search accuracy (manual validation of top-5 results)
- Memory usage during processing

**Acceptance criteria:**
- Detection rate ≥ 75%
- Embedding time ≤ 1s/face on M1
- Top-5 accuracy ≥ 60% (manual validation)

## Todo List

- [ ] Check InsightFace model pack licenses
- [ ] Contact InsightFace maintainers if unclear
- [ ] If needed: benchmark DeepFace
- [ ] If needed: benchmark FaceNet
- [ ] Document final decision
- [ ] Update `ARCHITECTURE.md` with chosen model

## Success Criteria

- Final face model chosen with clear license approval for donation-based use
- Benchmark results documented
- Decision documented in `research/face-model-license-decision.md`
- Team agrees on model choice

## Risk Assessment

- **High:** InsightFace license unclear → may need to switch models → delays Phase 02
- **Medium:** Alternative models have lower accuracy → may need to adjust search UX
- **Low:** All models fail license check → extremely unlikely (DeepFace/FaceNet are MIT)

## Security Considerations

- Ensure model weights are from official sources (no backdoors)
- Verify checksum of downloaded models

## Next Steps

After model validation, proceed to Phase 01 (Shared Foundation).

## Unresolved Questions

- Is donation-based usage considered "commercial use" under InsightFace terms?
- If InsightFace fails, is DeepFace accuracy acceptable for MVP?

## Decision Template

File: `research/face-model-license-decision.md`

```markdown
# Face Model License Decision

## Date
2026-05-XX

## Decision
Use [MODEL_NAME] for face recognition.

## License Summary
- Code: [LICENSE]
- Models: [LICENSE]
- Commercial use: [ALLOWED/NOT ALLOWED]
- Donation-based use: [ALLOWED/NOT ALLOWED]

## Benchmark Results
- Detection rate: X%
- Embedding time: Xs/face
- Top-5 accuracy: X%
- Memory usage: XMB

## Justification
[Why this model was chosen]

## Alternatives Considered
[Other models and why they were rejected]

## References
- [License URL]
- [Model documentation URL]
```
