# Phase 01: Shared Foundation & Bundle Schema

## Context Links

- Phase 00: `phase-00-license-model-validation.md`
- Architecture: `ARCHITECTURE.md`
- Research: `research/ocr-face-search-stack-research.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Define shared data structures, bundle format, and SQLite schema used by BOTH Processing App and Web Server.

## Why This Phase

Both apps need to agree on:
- Bundle directory structure
- SQLite schema
- Manifest format
- File naming conventions

This phase creates the **contract** between Processing App (M1) and Web Server (MacBook 2017).

## Requirements

### Functional

- Define bundle directory structure
- Define SQLite schema for events, photos, OCR, faces
- Define manifest.json format
- Define originals storage modes (included vs mapping)
- Create Python models (Pydantic/SQLAlchemy) shared by both apps

### Non-Functional

- Schema must support versioning (future migrations)
- Bundle must be portable across machines
- Paths must be relative where possible
- Schema must be simple (no over-engineering)

## Bundle Directory Structure

```
{event-slug}/
├── manifest.json           # Bundle metadata
├── event.db                # SQLite database
├── faiss.index             # FAISS vector index
├── thumbnails/             # Thumbnail images
│   ├── photo_001.jpg
│   ├── photo_002.jpg
│   └── ...
└── originals/              # (Optional) Original JPG files
    ├── IMG_1234.JPG
    ├── IMG_1235.JPG
    └── ...
```

**OR** (if originals not included):

```
{event-slug}/
├── manifest.json
├── event.db
├── faiss.index
├── thumbnails/
└── originals_mapping.json  # Maps photo IDs to external paths
```

## Manifest Schema

File: `manifest.json`

```json
{
  "bundle_version": "1.0",
  "event": {
    "slug": "ironman-danang-2026",
    "name": "Ironman Da Nang 2026",
    "date": "2026-06-15",
    "location": "Da Nang, Vietnam",
    "created_at": "2026-05-10T10:30:00Z"
  },
  "processing": {
    "app_version": "0.1.0",
    "ocr_model": "paddleocr-v2.7",
    "ocr_model_version": "v1",
    "face_model": "insightface-arcface_r100_v1",
    "face_model_version": "v1",
    "processed_at": "2026-05-10T10:30:00Z",
    "processing_machine": "MacBook-M1",
    "processing_duration_seconds": 12450
  },
  "stats": {
    "total_photos": 5420,
    "photos_with_bib_candidates": 3890,
    "photos_with_faces": 4120,
    "total_faces_detected": 8340,
    "total_bib_candidates": 4200,
    "total_thumbnails": 5420
  },
  "files": {
    "database": "event.db",
    "faiss_index": "faiss.index",
    "thumbnails_dir": "thumbnails",
    "originals_mode": "mapping",
    "originals_mapping": "originals_mapping.json"
  },
  "checksums": {
    "event.db": "sha256:abc123...",
    "faiss.index": "sha256:def456..."
  }
}
```

## SQLite Schema

File: `shared/schema.sql`

```sql
-- Events
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  date DATE NOT NULL,
  location TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Photos
CREATE TABLE photos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  filename TEXT NOT NULL,
  checksum TEXT UNIQUE NOT NULL,
  original_path TEXT,
  file_size INTEGER,
  width INTEGER,
  height INTEGER,
  capture_time TIMESTAMP,
  exif_data TEXT,  -- JSON string
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Thumbnails
CREATE TABLE thumbnails (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  photo_id INTEGER NOT NULL,
  path TEXT NOT NULL,
  width INTEGER,
  height INTEGER,
  file_size INTEGER,
  FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

-- OCR Candidates
CREATE TABLE ocr_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  photo_id INTEGER NOT NULL,
  text TEXT NOT NULL,
  confidence REAL,
  bbox TEXT,  -- JSON: [x, y, w, h]
  is_bib BOOLEAN DEFAULT 0,
  manual_correction TEXT,
  corrected_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

-- Faces
CREATE TABLE faces (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  photo_id INTEGER NOT NULL,
  bbox TEXT,  -- JSON: [x, y, w, h]
  confidence REAL,
  faiss_vector_id INTEGER,
  embedding_model TEXT,
  embedding_model_version TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_photos_event ON photos(event_id);
CREATE INDEX idx_photos_checksum ON photos(checksum);
CREATE INDEX idx_photos_capture_time ON photos(capture_time);
CREATE INDEX idx_ocr_photo ON ocr_candidates(photo_id);
CREATE INDEX idx_ocr_text ON ocr_candidates(text);
CREATE INDEX idx_ocr_is_bib ON ocr_candidates(is_bib);
CREATE INDEX idx_faces_photo ON faces(photo_id);
CREATE INDEX idx_faces_vector ON faces(faiss_vector_id);
```

## Originals Mapping Schema

File: `originals_mapping.json` (if originals not included in bundle)

```json
{
  "base_path": "/Volumes/SSD/events/ironman-danang-2026/originals",
  "mappings": {
    "1": "IMG_1234.JPG",
    "2": "IMG_1235.JPG",
    "3": "IMG_1236.JPG"
  }
}
```

**Key:** photo.id  
**Value:** filename relative to base_path

## Python Models

### Pydantic Models (API/validation)

File: `shared/models.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Dict, List

class EventMetadata(BaseModel):
    slug: str
    name: str
    date: date
    location: Optional[str] = None
    created_at: datetime

class ProcessingMetadata(BaseModel):
    app_version: str
    ocr_model: str
    ocr_model_version: str
    face_model: str
    face_model_version: str
    processed_at: datetime
    processing_machine: str
    processing_duration_seconds: int

class BundleStats(BaseModel):
    total_photos: int
    photos_with_bib_candidates: int
    photos_with_faces: int
    total_faces_detected: int
    total_bib_candidates: int
    total_thumbnails: int

class BundleFiles(BaseModel):
    database: str = "event.db"
    faiss_index: str = "faiss.index"
    thumbnails_dir: str = "thumbnails"
    originals_mode: str  # "included" or "mapping"
    originals_mapping: Optional[str] = None

class BundleManifest(BaseModel):
    bundle_version: str = "1.0"
    event: EventMetadata
    processing: ProcessingMetadata
    stats: BundleStats
    files: BundleFiles
    checksums: Dict[str, str]
```

### SQLAlchemy Models (database)

File: `shared/db_models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    photos = relationship("Photo", back_populates="event", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    filename = Column(String, nullable=False)
    checksum = Column(String, unique=True, nullable=False, index=True)
    original_path = Column(String)
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    capture_time = Column(DateTime, index=True)
    exif_data = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("Event", back_populates="photos")
    thumbnails = relationship("Thumbnail", back_populates="photo", cascade="all, delete-orphan")
    ocr_candidates = relationship("OCRCandidate", back_populates="photo", cascade="all, delete-orphan")
    faces = relationship("Face", back_populates="photo", cascade="all, delete-orphan")

class Thumbnail(Base):
    __tablename__ = 'thumbnails'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(Integer, ForeignKey('photos.id'), nullable=False)
    path = Column(String, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    
    photo = relationship("Photo", back_populates="thumbnails")

class OCRCandidate(Base):
    __tablename__ = 'ocr_candidates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(Integer, ForeignKey('photos.id'), nullable=False, index=True)
    text = Column(String, nullable=False, index=True)
    confidence = Column(Float)
    bbox = Column(Text)  # JSON: [x, y, w, h]
    is_bib = Column(Boolean, default=False, index=True)
    manual_correction = Column(String)
    corrected_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    photo = relationship("Photo", back_populates="ocr_candidates")

class Face(Base):
    __tablename__ = 'faces'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(Integer, ForeignKey('photos.id'), nullable=False, index=True)
    bbox = Column(Text)  # JSON: [x, y, w, h]
    confidence = Column(Float)
    faiss_vector_id = Column(Integer, index=True)
    embedding_model = Column(String)
    embedding_model_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    photo = relationship("Photo", back_populates="faces")
```

## Project Structure

```
danangvibes/
├── shared/                 # Shared code between both apps
│   ├── __init__.py
│   ├── models.py           # Pydantic models
│   ├── db_models.py        # SQLAlchemy models
│   ├── schema.sql          # SQLite schema
│   └── bundle.py           # Bundle utilities
├── processing_cli/         # Processing App (M1)
│   ├── __init__.py
│   ├── __main__.py
│   ├── commands/
│   ├── services/
│   └── config.yaml
├── web_server/             # Web Server (MacBook 2017)
│   ├── __init__.py
│   ├── __main__.py
│   ├── api/
│   ├── services/
│   ├── templates/
│   └── config.yaml
├── tests/
│   ├── test_shared/
│   ├── test_processing/
│   └── test_web_server/
└── requirements.txt
```

## Implementation Steps

1. Create `shared/` directory
2. Write `schema.sql`
3. Write Pydantic models in `shared/models.py`
4. Write SQLAlchemy models in `shared/db_models.py`
5. Write bundle utilities in `shared/bundle.py`:
   - `create_manifest()`
   - `validate_manifest()`
   - `load_manifest()`
   - `validate_bundle()`
6. Write unit tests for models and bundle utilities
7. Document bundle format in `docs/bundle-format.md`

## Todo List

- [ ] Create project structure
- [ ] Write SQLite schema
- [ ] Write Pydantic models
- [ ] Write SQLAlchemy models
- [ ] Write bundle utilities
- [ ] Write unit tests
- [ ] Document bundle format

## Success Criteria

- SQLite schema creates without errors
- Pydantic models validate sample data
- SQLAlchemy models can create/query test database
- Bundle validation detects corrupt bundles
- Unit tests pass: `pytest tests/test_shared/ -v`
- Type checking passes: `mypy shared/`

## Risk Assessment

- **Low:** Schema too simple → may need migration later (acceptable for MVP)
- **Low:** Relative paths break across machines → test on both M1 and MacBook 2017

## Security Considerations

- Do not store sensitive data in manifest (no tokens, passwords)
- Validate all paths to prevent path traversal
- Checksum verification for bundle integrity

## Next Steps

After shared foundation is stable, split into:
- Phase 02: Processing App (M1)
- Phase 04: Web Server (MacBook 2017)

## Unresolved Questions

- Should bundle support compression (zip)? → NO for MVP (adds complexity)
- Should originals be included in bundle by default? → NO (too large, use mapping)
