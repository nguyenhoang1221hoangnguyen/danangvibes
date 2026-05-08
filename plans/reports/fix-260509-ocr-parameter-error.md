# Fix Applied: OCRService Parameter Error

**Date:** 2026-05-09  
**Issue:** `OCRService.__init__() got an unexpected keyword argument 'use_angle_cls'`

## Root Cause

`OCRService.__init__()` chỉ nhận 1 parameter:
```python
def __init__(self, confidence_threshold: float = 0.6)
```

Nhưng `process.py` đang pass 3 parameters:
```python
OCRService(
    use_angle_cls=...,  # ❌ Not accepted
    lang=...,           # ❌ Not accepted
    confidence_threshold=...
)
```

## Fix

**File:** `processing_cli/commands/process.py:199-202`

**Before:**
```python
ocr_service = OCRService(
    use_angle_cls=bool(ocr_config.get("use_angle_cls", True)),
    lang=str(ocr_config.get("lang", "en")),
)
```

**After:**
```python
ocr_service = OCRService(
    confidence_threshold=float(ocr_config.get("confidence_threshold", 0.6))
)
```

## Why This Works

`OCRService` internally hardcodes these settings:
```python
# processing_cli/services/ocr.py:59-66
self._ocr = load_paddleocr_class()(
    use_angle_cls=False,  # Hardcoded
    lang="en",            # Hardcoded
    show_log=False,
    use_gpu=False,
    det_db_box_thresh=0.5,
    max_batch_size=1
)
```

## Next Steps

1. **Restart Processing Web App:**
   ```bash
   # Ctrl+C to stop current server
   scripts/start-processing-app.sh
   ```

2. **Refresh browser:** `http://127.0.0.1:8010`

3. **Select PaddleOCR:**
   - OCR Method: [PaddleOCR]
   - Start processing

4. **Verify:** Check logs for "Using PaddleOCR (slow but accurate)"

## Status

✅ Fixed  
✅ Ready to test
