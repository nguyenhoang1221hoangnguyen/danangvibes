# Phase 4: Integration with Batch Pipeline

**Status:** 🔄 In Progress  
**Duration:** 1 day  
**Owner:** Developer

---

## Context

Hybrid OCR service complete with fallback logic. Now integrate with existing batch processing pipeline to enable OCR + Face detection in parallel.

---

## Objectives

1. Integrate HybridOCRService into batch processing
2. Enable parallel OCR + Face detection
3. Store OCR results in database
4. Update web UI to show OCR results
5. Add skip-ocr option (default: enabled)

---

## Implementation

### 1. Update Batch Processing Command

File: `processing_cli/commands/process.py`

Add hybrid OCR option:
```python
@click.option('--ocr-method', type=click.Choice(['hybrid', 'paddle', 'skip']), 
              default='hybrid', help='OCR method to use')
```

### 2. Database Schema

Add OCR results to photos table:
```sql
ALTER TABLE photos ADD COLUMN ocr_results JSONB;
ALTER TABLE photos ADD COLUMN bib_numbers TEXT[];
ALTER TABLE photos ADD COLUMN ocr_method TEXT;
ALTER TABLE photos ADD COLUMN ocr_confidence FLOAT;
```

### 3. Parallel Processing

```python
# Process OCR and Face in parallel
with multiprocessing.Pool(processes=2) as pool:
    ocr_future = pool.apply_async(process_ocr, (photo_path,))
    face_future = pool.apply_async(process_faces, (photo_path,))
    
    ocr_results = ocr_future.get()
    face_results = face_future.get()
```

### 4. Web UI Updates

- Display bib numbers on photo cards
- Add filter by bib number
- Show OCR confidence scores
- Highlight low-confidence results for review

---

## Success Criteria

- ✅ OCR integrated with batch pipeline
- ✅ Parallel OCR + Face processing works
- ✅ OCR results stored in database
- ✅ Web UI displays bib numbers
- ✅ Performance: <1s per image total

---

## Next Steps

1. Update process.py command
2. Add database migrations
3. Update web UI
4. Test end-to-end pipeline
5. Document usage
