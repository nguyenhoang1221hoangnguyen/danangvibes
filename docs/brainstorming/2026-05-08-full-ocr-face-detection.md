# Brainstorming Session: Full OCR + Face Detection for Race Events

**Date:** 2026-05-08  
**Facilitator:** Scrum Master AI  
**Participants:** Product Owner (nguyenhoang)  
**Duration:** 45 minutes  
**Session Type:** Feature Planning & Architecture Design

---

## 1. Executive Summary

### Feature Overview
Implement production-ready OCR (bib number detection) and face detection system for race event photos with parallel processing, real-time tracking, and crash recovery capabilities.

### Key Decisions Made
- **Architecture:** Hybrid Pipeline (separate OCR and Face worker pools)
- **OCR Solution:** EasyOCR (M1-optimized, ~1-2s/image)
- **Face Solution:** InsightFace (lighter than DeepFace, ~2-3s/image)
- **Infrastructure:** Single M1 Pro 16GB, no cloud APIs
- **Accuracy Target:** 70-80% OCR accuracy with manual review UI
- **Performance Target:** 10,000 images in 4-5 hours

### Business Impact
- Enable athletes to search and download their race photos efficiently
- Support 1-10k images per event with same-day turnaround
- Zero-cost solution (no cloud API fees)
- Scalable to multiple events per month

---

## 2. Problem Statement & Context

### Current Situation
- **Existing System:** Batch processing with skip-ocr option
- **Pain Points:**
  - PaddleOCR too slow (~3 min/image = 500 hours for 10k images)
  - Tesseract fast but cannot detect bib numbers in race photos
  - Face detection works but needs optimization (3-4s/image)
  - No parallel processing capability
  - No crash recovery mechanism

### User Needs
- **Primary Users:** Race event organizers, photographers
- **Use Case:** Import 1-10k race photos, process OCR + face detection, enable athlete search
- **Timeline Requirement:** "Vài giờ" (few hours) - interpreted as 4-6 hours acceptable
- **Quality Requirement:** 70-80% OCR accuracy acceptable with manual correction workflow

### Business Requirements
- Process 1-10k images per event
- Support multiple events per month
- Same-day turnaround (import → process → review → publish)
- Zero ongoing costs (no cloud API budget)
- Production-grade reliability (crash recovery, progress tracking)

---

## 3. Requirements & Constraints

### Functional Requirements

**FR1: OCR Processing**
- Detect bib numbers from race photos
- Target accuracy: 70-80%
- Processing speed: ~1-2s per image
- Support for various lighting conditions and angles
- Handle motion blur and partial occlusions

**FR2: Face Detection & Embedding**
- Detect faces in race photos
- Generate face embeddings for similarity search
- Processing speed: ~2-3s per image
- Handle helmets, sunglasses, side profiles
- Support multiple faces per image

**FR3: Parallel Processing**
- Run OCR and Face detection in parallel pipeline
- Utilize M1 Pro multi-core CPU (10 cores)
- Worker pool: 3 OCR workers + 2 Face workers
- Queue-based task distribution

**FR4: Real-time Progress Tracking**
- Live progress updates during processing
- Show: current image, completed count, estimated time remaining
- WebSocket or polling-based updates
- Accessible via web UI

**FR5: Crash Recovery**
- Checkpoint progress every 10 images
- Resume from last checkpoint on restart
- No data loss on unexpected shutdown
- Idempotent processing (can re-run safely)

**FR6: Manual Review UI**
- Web interface for reviewing OCR results
- Edit/correct bib numbers
- Verify face detections
- Batch approval workflow
- Export corrected data

### Non-Functional Requirements

**NFR1: Performance**
- 10,000 images processed in 4-5 hours
- Average throughput: 1.5-2s per image (combined OCR + Face)
- Memory usage: < 14GB (leave 2GB for system)
- CPU utilization: 80-90% during processing

**NFR2: Reliability**
- 99% uptime during processing
- Automatic retry on transient failures
- Graceful degradation (skip problematic images)
- Comprehensive error logging

**NFR3: Scalability**
- Support 1-10k images per event
- Handle multiple events sequentially
- Efficient storage management (100GB per project)
- External SSD support for large datasets

**NFR4: Maintainability**
- Modular architecture (easy to swap OCR/Face engines)
- Comprehensive logging and monitoring
- Clear error messages
- Documentation for operations

### Technical Constraints

**Hardware Constraints**
- Single machine: M1 Pro MacBook
- RAM: 16GB (shared with OS)
- Storage: 100GB internal per project + external SSD
- No GPU (use M1 Neural Engine instead)

**Software Constraints**
- Python-based stack (existing codebase)
- No cloud APIs (zero budget)
- Must handle non-ASCII file paths (Vietnamese characters)
- Compatible with existing batch processing tool

**Operational Constraints**
- Single operator (no 24/7 monitoring)
- Same-day processing requirement
- Manual review step required
- Must integrate with existing web server

---

## 4. Proposed Solution Architecture

### Architecture Overview: Hybrid Pipeline

```
┌─────────────┐
│   Import    │
│   Photos    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         SQLite Job Queue                │
│  (images to process, checkpoints)       │
└──────┬──────────────────────────────┬───┘
       │                              │
       ▼                              ▼
┌─────────────────┐          ┌──────────────────┐
│  OCR Workers    │          │  Face Workers    │
│  (3 workers)    │──────────▶  (2 workers)     │
│  EasyOCR        │  Queue   │  InsightFace     │
│  ~1-2s/image    │          │  ~2-3s/image     │
└─────────────────┘          └──────────────────┘
       │                              │
       └──────────────┬───────────────┘
                      ▼
              ┌───────────────┐
              │   SQLite DB   │
              │  + FAISS Index│
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │   Review UI   │
              │ (Manual Edit) │
              └───────────────┘
```

### Component Specifications

**1. Job Queue System**
- Technology: SQLite-based queue
- Schema: `jobs(id, image_path, status, ocr_result, face_result, checkpoint, error)`
- Status: pending → ocr_processing → face_processing → completed → reviewed
- Checkpoint: Save every 10 images

**2. OCR Worker Pool**
- Workers: 3 parallel processes
- Engine: EasyOCR with M1 Metal acceleration
- Input: Image path from queue
- Output: List of detected bib numbers with confidence scores
- Error handling: Skip image on failure, log error, continue

**3. Face Worker Pool**
- Workers: 2 parallel processes  
- Engine: InsightFace (lighter than DeepFace)
- Input: Image path from OCR-completed queue
- Output: Face embeddings + bounding boxes
- Error handling: Non-ASCII path workaround (temp file copy)

**4. Progress Tracking**
- Real-time updates via WebSocket (FastAPI)
- Metrics: processed count, success rate, current speed, ETA
- Dashboard: Web UI showing live progress
- Persistence: SQLite for historical data

**5. Review UI**
- Framework: FastAPI + HTMX (lightweight)
- Features: Grid view, edit bib numbers, verify faces, batch approve
- Workflow: Filter by confidence, prioritize low-confidence results
- Export: Update database with corrections

### Data Flow

1. **Import Phase**
   - User selects folder via web UI
   - System scans for JPG files
   - Creates job records in queue (status: pending)
   - Returns job ID to user

2. **OCR Phase**
   - OCR workers poll queue for pending jobs
   - Process image with EasyOCR
   - Extract bib number candidates (2-5 digits)
   - Save results to database
   - Update job status: ocr_processing → face_processing
   - Checkpoint every 10 images

3. **Face Phase**
   - Face workers poll queue for face_processing jobs
   - Detect faces with InsightFace
   - Generate embeddings
   - Save to FAISS index
   - Update job status: face_processing → completed

4. **Review Phase**
   - Admin opens review UI
   - System shows low-confidence OCR results first
   - Admin corrects bib numbers
   - Admin verifies face detections
   - Batch approve → status: reviewed

5. **Publish Phase**
   - Generate manifest.json
   - Create bundle for web server
   - Deploy to search interface

---

## 5. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
**Goal:** Build foundation for parallel processing

**Tasks:**
- [ ] Design SQLite queue schema
- [ ] Implement job queue manager (enqueue, dequeue, checkpoint)
- [ ] Create worker pool architecture (multiprocessing)
- [ ] Implement checkpoint/resume mechanism
- [ ] Add progress tracking to database
- [ ] Unit tests for queue operations

**Deliverables:**
- Working job queue system
- Worker pool framework
- Checkpoint system
- 80% test coverage

**Estimated Effort:** 3-4 days

---

### Phase 2: OCR Integration (Week 1-2)
**Goal:** Integrate and optimize EasyOCR

**Tasks:**
- [ ] Install EasyOCR with M1 dependencies
- [ ] Create OCR service wrapper
- [ ] Implement bib number extraction logic (2-5 digits)
- [ ] Add image preprocessing (resize, enhance contrast)
- [ ] Optimize for M1 Metal acceleration
- [ ] Benchmark performance (target: 1-2s/image)
- [ ] Error handling and retry logic
- [ ] Integration tests with sample race photos

**Deliverables:**
- OCR service module
- Performance: 1-2s per image
- Accuracy: 70-80% on test dataset
- Comprehensive error handling

**Estimated Effort:** 4-5 days

---

### Phase 3: Face Detection Optimization (Week 2)
**Goal:** Optimize face detection for M1

**Tasks:**
- [ ] Evaluate InsightFace vs current DeepFace
- [ ] Install InsightFace with M1 optimization
- [ ] Migrate face detection code
- [ ] Optimize for batch processing
- [ ] Handle non-ASCII paths (already implemented)
- [ ] Benchmark performance (target: 2-3s/image)
- [ ] Integration with FAISS index
- [ ] Load testing with 1000 images

**Deliverables:**
- Optimized face service
- Performance: 2-3s per image
- Memory efficient (< 3GB per worker)
- Stable under load

**Estimated Effort:** 3-4 days

---

### Phase 4: Pipeline Integration (Week 3)
**Goal:** Connect OCR → Face pipeline with real-time tracking

**Tasks:**
- [ ] Implement pipeline coordinator
- [ ] Connect OCR workers to queue
- [ ] Connect Face workers to queue
- [ ] Add inter-stage communication
- [ ] Implement WebSocket server for progress updates
- [ ] Create progress tracking API endpoints
- [ ] Add real-time dashboard (simple HTML + JS)
- [ ] End-to-end testing with 100 images

**Deliverables:**
- Working pipeline OCR → Face
- Real-time progress tracking
- WebSocket updates
- Dashboard UI

**Estimated Effort:** 4-5 days

---

### Phase 5: Review UI (Week 3-4)
**Goal:** Build manual correction interface

**Tasks:**
- [ ] Design review UI mockup
- [ ] Implement grid view of processed images
- [ ] Add bib number editing interface
- [ ] Add face verification interface
- [ ] Implement filtering (by confidence, status)
- [ ] Add batch approval workflow
- [ ] Export corrected data to database
- [ ] User acceptance testing

**Deliverables:**
- Functional review UI
- Edit and approve workflow
- < 5 min to review 100 images
- Mobile-responsive design

**Estimated Effort:** 5-6 days

---

### Phase 6: Testing & Production (Week 4)
**Goal:** Validate performance and deploy

**Tasks:**
- [ ] Load test with 10,000 images
- [ ] Measure actual throughput and timing
- [ ] Stress test crash recovery
- [ ] Test resume from various checkpoints
- [ ] Performance tuning (worker count, batch size)
- [ ] Memory profiling and optimization
- [ ] Documentation (operations manual)
- [ ] Production deployment
- [ ] Monitor first real event

**Deliverables:**
- Validated 10k images in 4-5 hours
- Crash recovery tested
- Production-ready system
- Operations documentation

**Estimated Effort:** 5-6 days

---

**Total Timeline:** 4 weeks (20-25 working days)

---

## 6. Technical Specifications

### Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (web framework)
- SQLite (queue + database)
- Multiprocessing (worker pools)
- WebSocket (real-time updates)

**OCR:**
- EasyOCR 1.7+
- PyTorch with M1 Metal backend
- Pillow (image preprocessing)

**Face Detection:**
- InsightFace 0.7+
- ONNX Runtime (M1 optimized)
- FAISS (vector search)

**Frontend:**
- HTMX (lightweight interactivity)
- Tailwind CSS (styling)
- Vanilla JavaScript (WebSocket client)

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| OCR Speed | 1-2s/image | Average over 1000 images |
| Face Speed | 2-3s/image | Average over 1000 images |
| Total Throughput | 1.5-2s/image | Combined pipeline |
| 10k Images | 4-5 hours | End-to-end |
| Memory Usage | < 14GB | Peak during processing |
| CPU Utilization | 80-90% | During active processing |
| Crash Recovery | < 1 min | Time to resume |

### Storage Requirements

**Per Event (10k images):**
- Original images: ~50GB (on external SSD)
- Thumbnails: ~5GB
- Database: ~100MB
- FAISS index: ~500MB
- Temp files: ~10GB (during processing)
- **Total: ~65GB**

**Cleanup Strategy:**
- Delete temp files after processing
- Archive originals to external SSD
- Keep thumbnails + database + FAISS on internal storage

---

## 7. Risk Assessment & Mitigation

### High Priority Risks

**Risk 1: EasyOCR Accuracy < 70%**
- **Impact:** High - Core requirement not met
- **Probability:** Medium
- **Mitigation:**
  - Benchmark with real race photos before committing
  - Prepare fallback: Ensemble approach (EasyOCR + Tesseract + PaddleOCR vote)
  - Accept lower accuracy if review UI is efficient
- **Contingency:** If < 60%, switch to cloud API (Google Vision) temporarily

**Risk 2: M1 Memory Pressure with 5 Workers**
- **Impact:** Medium - System slowdown or crashes
- **Probability:** Medium
- **Mitigation:**
  - Start with 4 workers (2 OCR + 2 Face)
  - Monitor memory usage during testing
  - Implement dynamic worker scaling
- **Contingency:** Reduce to 3 workers if needed (accept longer processing time)

**Risk 3: External SSD I/O Bottleneck**
- **Impact:** Medium - Slower than expected throughput
- **Probability:** Low
- **Mitigation:**
  - Use fast external SSD (USB 3.1 or Thunderbolt)
  - Implement read-ahead caching
  - Batch load images into memory
- **Contingency:** Process in smaller batches (2k images at a time)

### Medium Priority Risks

**Risk 4: InsightFace Not Compatible with M1**
- **Impact:** Medium - Need alternative face detection
- **Probability:** Low
- **Mitigation:**
  - Test InsightFace installation early (Phase 3 start)
  - Have DeepFace as fallback (already working)
- **Contingency:** Optimize DeepFace instead (may be 4-5s/image)

**Risk 5: WebSocket Connection Instability**
- **Impact:** Low - Progress tracking unreliable
- **Probability:** Low
- **Mitigation:**
  - Implement polling fallback
  - Persist progress to database
  - Reconnect logic on client side
- **Contingency:** Use polling-only approach

**Risk 6: Checkpoint System Bugs**
- **Impact:** High - Data loss on crash
- **Probability:** Low
- **Mitigation:**
  - Extensive testing of crash scenarios
  - Atomic checkpoint writes
  - Validate checkpoint integrity on resume
- **Contingency:** Manual recovery from database state

---

## 8. Success Metrics & KPIs

### Performance Metrics

**Primary KPIs:**
- **Processing Time:** 10,000 images in ≤ 5 hours (target: 4-5 hours)
- **OCR Accuracy:** 70-80% correct bib number detection
- **Face Recall:** 80%+ faces detected per image
- **System Uptime:** 99% during processing (< 1% crash rate)

**Secondary KPIs:**
- **Review Efficiency:** < 5 minutes to review 100 images
- **Memory Efficiency:** Peak usage < 14GB
- **Storage Efficiency:** < 70GB per 10k image event
- **Resume Time:** < 1 minute from crash to resume

### Quality Metrics

**OCR Quality:**
- True Positive Rate: > 70% (correct bib numbers)
- False Positive Rate: < 10% (incorrect numbers detected)
- Miss Rate: < 30% (bib numbers not detected)

**Face Quality:**
- Detection Rate: > 80% (faces found in images with faces)
- False Positive Rate: < 5% (non-faces detected as faces)
- Embedding Quality: > 85% similarity for same person

### Operational Metrics

**Reliability:**
- Crash Recovery Success: 100% (always resume successfully)
- Data Loss: 0% (no lost images or results)
- Error Rate: < 2% (images that fail processing)

**Usability:**
- Review UI Load Time: < 2 seconds
- Correction Time: < 10 seconds per image
- Batch Approval: < 30 seconds for 100 images

---

## 9. Dependencies & Integration Points

### Internal Dependencies

**Existing Systems:**
- Batch processing CLI (`processing_cli`)
- Web server (`web_server`)
- Database schema (SQLite)
- FAISS index structure
- Thumbnail generation service

**Integration Points:**
- Reuse existing database schema (add queue tables)
- Extend batch processing with parallel workers
- Integrate with existing web UI (add review page)
- Use existing thumbnail service
- Compatible with current bundle format

### External Dependencies

**Software:**
- EasyOCR (pip install)
- InsightFace (pip install)
- PyTorch with M1 Metal support
- ONNX Runtime for M1

**Hardware:**
- External SSD (recommended: 500GB+, USB 3.1 or Thunderbolt)
- Stable power supply (UPS recommended for long processing)

### Team Dependencies

**Required Skills:**
- Python multiprocessing expertise
- FastAPI / WebSocket development
- ML model optimization (OCR, Face)
- SQLite database design
- Frontend development (HTMX)

**External Support:**
- None (zero-budget constraint)

---

## 10. Action Items & Next Steps

### Immediate Actions (This Week)

**Action 1: Validate EasyOCR on M1**
- **Owner:** Developer
- **Priority:** Critical
- **Deadline:** 2 days
- **Tasks:**
  - Install EasyOCR on M1 Pro
  - Test with 10 sample race photos
  - Measure speed and accuracy
  - Document results
- **Success Criteria:** 1-2s/image, 70%+ accuracy

**Action 2: Design Database Schema**
- **Owner:** Developer
- **Priority:** High
- **Deadline:** 2 days
- **Tasks:**
  - Design job queue tables
  - Design checkpoint schema
  - Design progress tracking tables
  - Create migration script
- **Deliverable:** SQL schema file + migration

**Action 3: Create Project Plan**
- **Owner:** Product Owner
- **Priority:** High
- **Deadline:** 3 days
- **Tasks:**
  - Review this brainstorming doc
  - Approve architecture approach
  - Allocate 4-week timeline
  - Define acceptance criteria
- **Deliverable:** Approved project plan

### Sprint 1 Goals (Week 1)

**Goal:** Core infrastructure + OCR integration

**Sprint Backlog:**
- Implement SQLite job queue
- Create worker pool framework
- Integrate EasyOCR
- Benchmark OCR performance
- Implement checkpoint system

**Definition of Done:**
- All unit tests passing
- OCR processing 100 images successfully
- Checkpoint/resume tested
- Performance: 1-2s/image OCR

### Sprint 2 Goals (Week 2)

**Goal:** Face optimization + pipeline integration

**Sprint Backlog:**
- Integrate InsightFace
- Optimize face detection
- Connect OCR → Face pipeline
- Implement progress tracking
- Create simple dashboard

**Definition of Done:**
- Pipeline processes 1000 images end-to-end
- Real-time progress visible
- Performance: 1.5-2s/image combined
- Crash recovery working

### Sprint 3 Goals (Week 3)

**Goal:** Review UI + end-to-end testing

**Sprint Backlog:**
- Build review UI
- Implement manual correction
- Add batch approval
- Test with 5000 images
- Performance tuning

**Definition of Done:**
- Review UI functional
- 5000 images processed in < 3 hours
- Manual corrections saved correctly
- User acceptance testing passed

### Sprint 4 Goals (Week 4)

**Goal:** Production readiness

**Sprint Backlog:**
- Load test 10,000 images
- Stress test crash recovery
- Write operations manual
- Deploy to production
- Monitor first real event

**Definition of Done:**
- 10k images in 4-5 hours validated
- All tests passing
- Documentation complete
- Production deployment successful

---

## 11. Open Questions & Decisions Needed

### Resolved Questions
✅ Cloud APIs or local processing? → **Local (zero budget)**  
✅ Accuracy vs speed tradeoff? → **Speed priority, 70-80% accuracy OK**  
✅ Sequential or parallel? → **Parallel pipeline**  
✅ Real-time tracking needed? → **Yes**  
✅ Crash recovery needed? → **Yes**  

### Open Questions

**Q1: Review UI Priority**
- Should review UI be built in Phase 5, or can it wait until after MVP?
- Can we launch with basic correction workflow first?
- **Decision Needed By:** End of Week 1

**Q2: External SSD Specification**
- What brand/model external SSD to purchase?
- USB 3.1 or Thunderbolt?
- **Decision Needed By:** Before Phase 6 testing

**Q3: Monitoring & Alerting**
- Do we need email/SMS alerts on processing completion?
- Do we need error alerting?
- **Decision Needed By:** Week 3

**Q4: Multi-Event Handling**
- Process multiple events in parallel or sequential?
- Priority queue for urgent events?
- **Decision Needed By:** Week 2

---

## 12. Appendix

### Reference Materials

**Technical Documentation:**
- EasyOCR: https://github.com/JaidedAI/EasyOCR
- InsightFace: https://github.com/deepinsight/insightface
- M1 PyTorch: https://pytorch.org/get-started/locally/
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/

**Existing Codebase:**
- Batch processing: `processing_cli/commands/batch_process.py`
- Face service: `processing_cli/services/face.py`
- OCR service: `processing_cli/services/ocr.py`
- Database: `shared/database.py`

### Glossary

- **Bib Number:** Race number worn by athletes (2-5 digits)
- **Face Embedding:** 512-dimensional vector representing a face
- **FAISS:** Facebook AI Similarity Search (vector database)
- **M1 Neural Engine:** Apple's ML accelerator hardware
- **Checkpoint:** Saved progress state for crash recovery
- **Worker Pool:** Multiple parallel processes handling tasks

---

**Document Status:** ✅ Approved  
**Next Review:** End of Week 2 (Sprint 1 retrospective)  
**Version:** 1.0  
**Last Updated:** 2026-05-08

