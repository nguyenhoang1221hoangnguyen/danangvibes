# Phase 07: Testing & Performance Validation

## Context Links

- Phase 02: `phase-02-processing-app-m1.md`
- Phase 04: `phase-04-web-server-core-macbook-2017.md`
- Phase 05: `phase-05-public-search-download-ui.md`
- Architecture: `ARCHITECTURE.md`

## Overview

**Priority:** High (BLOCKING before production)  
**Status:** Planned  
**Goal:** Validate the entire system with real data, benchmark performance, identify bottlenecks, and ensure production readiness.

## Requirements

### Functional Testing

- Unit tests for all services
- Integration tests for workflows
- End-to-end tests for user flows
- Manual testing on real devices

### Performance Testing

- Processing speed on M1
- Search latency on MacBook 2017
- Memory usage under load
- Concurrent user simulation
- Download speed via Cloudflare Tunnel

### Validation Criteria

- All performance targets met (from plan.md)
- No critical bugs
- Acceptable accuracy for OCR/face
- System stable under load

## Test Data

### Sample Event

**Source:** Real race photos (200-500 photos minimum)

**Characteristics:**
- Mix of clear/blurry photos
- Various lighting conditions
- Athletes with/without bibs visible
- Different face angles (front, side, helmet)
- Different sports (running, cycling, swimming)

**Acquisition:**
- Use photos from past event (with permission)
- Or generate synthetic test set
- Include edge cases: sunglasses, helmets, motion blur

## Test Suites

### 1. Unit Tests

File: `tests/test_processing/test_ocr_service.py`

```python
import pytest
from processing_cli.services.ocr import OCRService

def test_ocr_extracts_bib_numbers():
    """Test OCR extracts bib numbers from sample image"""
    ocr_service = OCRService()
    
    # Sample image with visible bib "1234"
    candidates = ocr_service.extract_bib_candidates("tests/fixtures/bib_1234.jpg")
    
    assert len(candidates) > 0
    assert any(c['text'] == '1234' for c in candidates)
    assert all(c['confidence'] > 0.5 for c in candidates)

def test_ocr_filters_non_digits():
    """Test OCR filters out non-digit text"""
    ocr_service = OCRService()
    
    # Image with text "FINISH" (should be filtered)
    candidates = ocr_service.extract_bib_candidates("tests/fixtures/finish_line.jpg")
    
    # Should not extract "FINISH" as bib candidate
    assert not any('FINISH' in c['text'] for c in candidates)
```

File: `tests/test_processing/test_face_service.py`

```python
import pytest
from processing_cli.services.face import FaceService
import numpy as np

def test_face_detection():
    """Test face detection on sample image"""
    face_service = FaceService()
    
    faces = face_service.detect_and_embed("tests/fixtures/athlete_face.jpg")
    
    assert len(faces) > 0
    assert faces[0]['confidence'] > 0.8
    assert len(faces[0]['embedding']) == 512  # embedding dimension

def test_face_embedding_consistency():
    """Test same face produces similar embeddings"""
    face_service = FaceService()
    
    faces1 = face_service.detect_and_embed("tests/fixtures/person_a_1.jpg")
    faces2 = face_service.detect_and_embed("tests/fixtures/person_a_2.jpg")
    
    emb1 = np.array(faces1[0]['embedding'])
    emb2 = np.array(faces2[0]['embedding'])
    
    # Cosine similarity should be high
    similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    assert similarity > 0.7
```

File: `tests/test_web_server/test_search_service.py`

```python
import pytest
from web_server.services.search_service import SearchService

def test_bib_search(test_bundle):
    """Test bib search returns correct photos"""
    search_service = SearchService(test_bundle)
    
    results = search_service.search_by_bib("1234")
    
    assert results['total_results'] > 0
    assert len(results['bib_matches']) > 0

def test_face_search(test_bundle):
    """Test face search returns similar faces"""
    search_service = SearchService(test_bundle)
    
    with open("tests/fixtures/selfie.jpg", "rb") as f:
        image_bytes = f.read()
    
    results = search_service.search_by_face(image_bytes)
    
    assert results['total_results'] > 0
    assert len(results['face_matches']) > 0
    assert all(r['similarity_score'] > 0.6 for r in results['face_matches'])
```

### 2. Integration Tests

File: `tests/integration/test_processing_workflow.py`

```python
import pytest
from pathlib import Path
from processing_cli.commands.process import process
from processing_cli.commands.validate import validate

def test_full_processing_workflow(tmp_path):
    """Test full processing workflow: scan → process → validate"""
    # Setup test event
    source_dir = Path("tests/fixtures/sample_event")
    output_dir = tmp_path / "output"
    
    # Process event
    process.invoke(
        source=str(source_dir),
        event_slug="test-event",
        event_name="Test Event",
        event_date="2026-05-01",
        output=str(output_dir)
    )
    
    bundle_path = output_dir / "test-event"
    
    # Validate bundle
    assert (bundle_path / "manifest.json").exists()
    assert (bundle_path / "event.db").exists()
    assert (bundle_path / "faiss.index").exists()
    assert (bundle_path / "thumbnails").exists()
    
    # Validate command should pass
    result = validate.invoke(bundle=str(bundle_path))
    assert result.exit_code == 0
```

File: `tests/integration/test_import_workflow.py`

```python
import pytest
from web_server.commands.import_bundle import import_bundle

def test_bundle_import(test_bundle_path, tmp_path):
    """Test bundle import workflow"""
    storage_path = tmp_path / "storage"
    storage_path.mkdir()
    
    # Import bundle
    import_bundle.invoke(
        bundle=str(test_bundle_path),
        storage_path=str(storage_path)
    )
    
    # Check imported structure
    event_dir = storage_path / "test-event"
    assert event_dir.exists()
    assert (event_dir / "releases" / "v1").exists()
    assert (event_dir / "active").is_symlink()
```

### 3. End-to-End Tests

File: `tests/e2e/test_user_flow.py`

```python
import pytest
from fastapi.testclient import TestClient
from web_server.main import app

client = TestClient(app)

def test_user_search_and_download_flow():
    """Test complete user flow: search → view → download"""
    
    # 1. Visit event page
    response = client.get("/events/test-event")
    assert response.status_code == 200
    assert b"Test Event" in response.content
    
    # 2. Search by bib
    response = client.post(
        "/events/test-event/search/bib",
        json={"bib_number": "1234"}
    )
    assert response.status_code == 200
    assert b"photo" in response.content.lower()
    
    # 3. Get thumbnail
    response = client.get("/events/test-event/photos/1/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    
    # 4. Download original
    response = client.get("/events/test-event/photos/1/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
```

## Performance Benchmarks

### Benchmark Script

File: `tests/benchmarks/benchmark_processing.py`

```python
import time
import psutil
from pathlib import Path
from processing_cli.services.ocr import OCRService
from processing_cli.services.face import FaceService

def benchmark_processing():
    """Benchmark processing performance on M1"""
    
    ocr_service = OCRService()
    face_service = FaceService()
    
    test_images = list(Path("tests/fixtures/sample_event").glob("*.jpg"))
    
    print(f"Benchmarking {len(test_images)} images...")
    
    # Measure OCR
    start = time.time()
    for img in test_images:
        ocr_service.extract_bib_candidates(str(img))
    ocr_time = time.time() - start
    ocr_per_image = ocr_time / len(test_images)
    
    print(f"OCR: {ocr_time:.2f}s total, {ocr_per_image:.2f}s/image")
    
    # Measure face detection
    start = time.time()
    for img in test_images:
        face_service.detect_and_embed(str(img))
    face_time = time.time() - start
    face_per_image = face_time / len(test_images)
    
    print(f"Face: {face_time:.2f}s total, {face_per_image:.2f}s/image")
    
    # Total
    total_per_image = ocr_per_image + face_per_image
    print(f"Total: {total_per_image:.2f}s/image")
    
    # Memory
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory: {memory_mb:.0f}MB")
    
    # Validate targets
    assert ocr_per_image <= 1.0, "OCR too slow"
    assert face_per_image <= 0.5, "Face detection too slow"
    assert total_per_image <= 3.0, "Total processing too slow"
    
    print("✓ All performance targets met")

if __name__ == "__main__":
    benchmark_processing()
```

File: `tests/benchmarks/benchmark_serving.py`

```python
import time
import requests
from concurrent.futures import ThreadPoolExecutor

def benchmark_search():
    """Benchmark search performance on MacBook 2017"""
    
    base_url = "http://localhost:8000"
    
    # Bib search
    start = time.time()
    response = requests.post(
        f"{base_url}/events/test-event/search/bib",
        json={"bib_number": "1234"}
    )
    bib_latency = (time.time() - start) * 1000
    
    print(f"Bib search: {bib_latency:.0f}ms")
    assert bib_latency < 200, "Bib search too slow"
    
    # Face search
    with open("tests/fixtures/selfie.jpg", "rb") as f:
        start = time.time()
        response = requests.post(
            f"{base_url}/events/test-event/search/face",
            files={"selfie": f}
        )
        face_latency = (time.time() - start) * 1000
    
    print(f"Face search: {face_latency:.0f}ms")
    assert face_latency < 5000, "Face search too slow"
    
    print("✓ Search performance acceptable")

def benchmark_concurrent_users():
    """Simulate concurrent users"""
    
    base_url = "http://localhost:8000"
    
    def user_session():
        # Visit event page
        requests.get(f"{base_url}/events/test-event")
        
        # Search
        requests.post(
            f"{base_url}/events/test-event/search/bib",
            json={"bib_number": "1234"}
        )
        
        # Download
        requests.get(f"{base_url}/events/test-event/photos/1/download")
    
    # Simulate 10 concurrent users
    with ThreadPoolExecutor(max_workers=10) as executor:
        start = time.time()
        futures = [executor.submit(user_session) for _ in range(10)]
        for future in futures:
            future.result()
        duration = time.time() - start
    
    print(f"10 concurrent users: {duration:.2f}s")
    print("✓ Concurrent load handled")

if __name__ == "__main__":
    benchmark_search()
    benchmark_concurrent_users()
```

## Validation Checklist

### Processing App (M1)

- [ ] Process 200-500 sample photos successfully
- [ ] Processing time ≤ 3s/photo
- [ ] OCR detection rate ≥ 70% for visible bibs
- [ ] Face detection rate ≥ 80% for clear faces
- [ ] Memory usage ≤ 8GB during processing
- [ ] Bundle validation passes
- [ ] Incremental processing works (skip cached)

### Web Server (MacBook 2017)

- [ ] Server starts in < 5s
- [ ] Published events load on startup
- [ ] Bib search latency < 200ms
- [ ] Face search latency < 5s
- [ ] Thumbnail load < 100ms
- [ ] Original download ≥ 1MB/s via Cloudflare Tunnel
- [ ] Memory usage ≤ 4GB with 3 events loaded
- [ ] 10 concurrent users handled smoothly
- [ ] No memory leaks after 1 hour

### End-to-End

- [ ] Full workflow: M1 process → export → copy → import → publish → public access
- [ ] Bib search returns correct results
- [ ] Face search returns similar faces
- [ ] Download works for originals
- [ ] Donation prompt displays
- [ ] Admin can review/correct OCR
- [ ] Version switching works
- [ ] Rollback works

### Accuracy Validation

**OCR Accuracy:**
- Manually label 100 photos with visible bibs
- Run OCR
- Calculate: correct detections / total visible bibs
- Target: ≥ 70%

**Face Search Accuracy:**
- Create 10 test queries (selfies of known athletes)
- Run face search
- Check if athlete appears in top-10 results
- Target: ≥ 60% (6/10 queries successful)

## Load Testing

### Scenario 1: Event Launch Day

**Simulation:**
- 50 concurrent users
- Each user: visit event → search → download 2 photos
- Duration: 10 minutes

**Metrics:**
- Response time p50, p95, p99
- Error rate
- Memory usage
- CPU usage

**Tool:** Apache Bench or Locust

```bash
# Apache Bench
ab -n 1000 -c 50 http://localhost:8000/events/test-event

# Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

File: `tests/load/locustfile.py`

```python
from locust import HttpUser, task, between

class EventUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def search_by_bib(self):
        self.client.post(
            "/events/test-event/search/bib",
            json={"bib_number": "1234"}
        )
    
    @task(1)
    def download_photo(self):
        self.client.get("/events/test-event/photos/1/download")
```

## Implementation Steps

1. **Write unit tests** (3 days)
2. **Write integration tests** (2 days)
3. **Write E2E tests** (2 days)
4. **Create benchmark scripts** (2 days)
5. **Run benchmarks on real hardware** (1 day)
6. **Validate accuracy with real data** (2 days)
7. **Run load tests** (1 day)
8. **Fix performance issues** (3 days)
9. **Re-test after fixes** (1 day)

## Todo List

- [ ] Setup test fixtures (sample photos)
- [ ] Write unit tests for all services
- [ ] Write integration tests for workflows
- [ ] Write E2E tests for user flows
- [ ] Create benchmark scripts
- [ ] Run processing benchmark on M1
- [ ] Run serving benchmark on MacBook 2017
- [ ] Validate OCR accuracy
- [ ] Validate face search accuracy
- [ ] Run load tests
- [ ] Profile memory usage
- [ ] Profile CPU usage
- [ ] Fix bottlenecks
- [ ] Re-test after optimizations

## Success Criteria

### Must Pass (BLOCKING)

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Processing ≤ 3s/photo on M1
- [ ] Bib search < 200ms
- [ ] Face search < 5s
- [ ] Memory ≤ 4GB on MacBook 2017
- [ ] 10 concurrent users OK

### Should Pass (HIGH PRIORITY)

- [ ] OCR accuracy ≥ 70%
- [ ] Face accuracy ≥ 60%
- [ ] Download ≥ 1MB/s
- [ ] No memory leaks

### Nice to Have

- [ ] 50 concurrent users OK
- [ ] OCR accuracy ≥ 80%
- [ ] Face accuracy ≥ 70%

## Risk Assessment

- **HIGH:** Face search > 5s on MacBook 2017 → move to async queue or disable public selfie search
- **MEDIUM:** OCR accuracy < 70% → improve preprocessing or add manual review workflow
- **MEDIUM:** Memory usage > 4GB → optimize FAISS index loading or lazy load events
- **LOW:** Download speed < 1MB/s → Cloudflare Tunnel bandwidth limit, acceptable for MVP

## Optimization Strategies

### If Face Search Too Slow

1. **Option A:** Async queue
   - User uploads selfie → job queued
   - Email/SMS notification when ready
   - Pros: No blocking, better UX
   - Cons: More complex

2. **Option B:** Pre-compute embeddings
   - Admin uploads athlete selfies beforehand
   - Public search only by bib
   - Pros: Fast, simple
   - Cons: Less flexible

3. **Option C:** Smaller FAISS index
   - Reduce embedding dimension (512 → 256)
   - Use quantization
   - Pros: Faster search
   - Cons: Lower accuracy

### If Memory Usage Too High

1. Lazy load events (load on first access)
2. Unload inactive events after timeout
3. Use FAISS memory-mapped index
4. Reduce thumbnail cache size

## Next Steps

After testing passes, proceed to Phase 08 (Deployment & Operations).

## Unresolved Questions

- What is acceptable face search latency for users? → < 5s ideal, < 10s acceptable
- Should we cache selfie embeddings? → NO for MVP (privacy concern)
