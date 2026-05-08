# Phase 02: Processing App (MacBook M1)

## Context Links

- Phase 00: `phase-00-license-model-validation.md`
- Phase 01: `phase-01-shared-foundation-bundle-schema.md`
- Architecture: `ARCHITECTURE.md`
- Research: `research/ocr-face-search-stack-research.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Build the heavy-lifting CLI app that runs on MacBook M1 to process event photos, extract OCR/face data, and export portable bundles.

## Requirements

### Functional

- CLI command to process event from JPG folder
- Scan JPG/JPEG files recursively
- Generate checksums for deduplication
- Extract EXIF metadata (capture time, camera info)
- Generate thumbnails (800x600px)
- Run PaddleOCR for bib number extraction
- Run face detection and embedding extraction
- Build FAISS vector index
- Export bundle with manifest, SQLite, FAISS, thumbnails
- Support incremental processing (skip cached photos)
- Validate bundle before export

### Non-Functional

- Process sequentially (batch_size=1) for memory efficiency
- Resize images before inference (max 1280px)
- Cache embeddings by checksum + model version
- Log progress and errors
- Handle corrupt/invalid images gracefully

## Architecture

```
CLI Command
  ↓
Scan JPG folder
  ↓
For each photo:
  ├─ Compute checksum
  ├─ Check cache (skip if exists)
  ├─ Extract EXIF
  ├─ Generate thumbnail
  ├─ Resize for inference
  ├─ Run OCR → extract bib candidates
  ├─ Run face detection → extract faces
  ├─ Compute face embeddings
  └─ Save to SQLite
  ↓
Build FAISS index from embeddings
  ↓
Write manifest.json
  ↓
Validate bundle
  ↓
Export complete
```

## Related Code Files

### Create

- `processing_cli/__init__.py`
- `processing_cli/__main__.py`
- `processing_cli/commands/process.py`
- `processing_cli/commands/validate.py`
- `processing_cli/commands/rebuild_embeddings.py`
- `processing_cli/services/scanner.py`
- `processing_cli/services/thumbnail.py`
- `processing_cli/services/ocr.py`
- `processing_cli/services/face.py`
- `processing_cli/services/faiss_builder.py`
- `processing_cli/services/exporter.py`
- `processing_cli/utils/image.py`
- `processing_cli/utils/checksum.py`
- `processing_cli/config.yaml`

## CLI Commands

### 1. Process Event

```bash
python -m processing_cli process \
  --source /Volumes/SSD/events/ironman-2026/originals \
  --event-slug ironman-danang-2026 \
  --event-name "Ironman Da Nang 2026" \
  --event-date 2026-06-15 \
  --event-location "Da Nang, Vietnam" \
  --output ./dist/events \
  --config ./processing_cli/config.yaml
```

**Options:**
- `--source`: Path to JPG folder (required)
- `--event-slug`: URL-safe event identifier (required)
- `--event-name`: Display name (required)
- `--event-date`: Event date YYYY-MM-DD (required)
- `--event-location`: Event location (optional)
- `--output`: Output directory for bundles (default: `./dist/events`)
- `--config`: Config file path (default: `./processing_cli/config.yaml`)
- `--skip-ocr`: Skip OCR processing (for testing)
- `--skip-faces`: Skip face processing (for testing)
- `--force`: Reprocess all photos (ignore cache)

### 2. Validate Bundle

```bash
python -m processing_cli validate \
  --bundle ./dist/events/ironman-danang-2026
```

**Checks:**
- manifest.json exists and valid
- event.db exists and schema correct
- faiss.index exists and loadable
- thumbnails/ directory exists
- All referenced files exist
- Checksums match

### 3. Rebuild Embeddings

```bash
python -m processing_cli rebuild-embeddings \
  --bundle ./dist/events/ironman-danang-2026 \
  --model-version v2
```

**Use case:** When switching face models or updating model version.

## Implementation Steps

### Step 1: CLI Framework (1 day)

```python
# processing_cli/__main__.py
import click
from processing_cli.commands import process, validate, rebuild_embeddings

@click.group()
def cli():
    """DaNang Vibes Processing CLI"""
    pass

cli.add_command(process.process)
cli.add_command(validate.validate)
cli.add_command(rebuild_embeddings.rebuild_embeddings)

if __name__ == '__main__':
    cli()
```

### Step 2: Scanner Service (1 day)

```python
# processing_cli/services/scanner.py
from pathlib import Path
from typing import List, Iterator
import logging

logger = logging.getLogger(__name__)

class PhotoScanner:
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.JPG', '.JPEG'}
    
    def scan(self, source_path: Path) -> Iterator[Path]:
        """Scan directory for JPG files"""
        logger.info(f"Scanning {source_path}")
        
        for file_path in source_path.rglob('*'):
            if file_path.suffix in self.ALLOWED_EXTENSIONS:
                if file_path.is_file():
                    yield file_path
```

### Step 3: Checksum & Cache (1 day)

```python
# processing_cli/utils/checksum.py
import hashlib
from pathlib import Path

def compute_checksum(file_path: Path) -> str:
    """Compute SHA256 checksum of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"
```

### Step 4: Thumbnail Service (1 day)

```python
# processing_cli/services/thumbnail.py
from PIL import Image
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ThumbnailService:
    def __init__(self, size: tuple = (800, 600)):
        self.size = size
    
    def generate(self, source: Path, output: Path) -> dict:
        """Generate thumbnail and return metadata"""
        try:
            with Image.open(source) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize maintaining aspect ratio
                img.thumbnail(self.size, Image.Resampling.LANCZOS)
                
                # Save
                output.parent.mkdir(parents=True, exist_ok=True)
                img.save(output, 'JPEG', quality=85, optimize=True)
                
                return {
                    'width': img.width,
                    'height': img.height,
                    'file_size': output.stat().st_size
                }
        except Exception as e:
            logger.error(f"Thumbnail generation failed for {source}: {e}")
            raise
```

### Step 5: OCR Service (2 days)

```python
# processing_cli/services/ocr.py
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import re
import logging

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, lang: str = 'en', confidence_threshold: float = 0.6):
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        self.confidence_threshold = confidence_threshold
    
    def extract_bib_candidates(self, image_path: str) -> list:
        """Extract potential bib numbers from image"""
        try:
            result = self.ocr.ocr(image_path, cls=True)
            
            candidates = []
            if result and result[0]:
                for line in result[0]:
                    bbox, (text, confidence) = line
                    
                    # Filter by confidence
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Extract digits only
                    digits = re.sub(r'\D', '', text)
                    
                    # Filter by likely bib length (2-5 digits)
                    if 2 <= len(digits) <= 5:
                        candidates.append({
                            'text': digits,
                            'confidence': float(confidence),
                            'bbox': bbox,
                            'is_bib': True
                        })
            
            return candidates
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return []
```

### Step 6: Face Service (3 days)

```python
# processing_cli/services/face.py
from insightface.app import FaceAnalysis  # or DeepFace
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self, model_name: str = 'buffalo_l'):
        self.app = FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        self.model_name = model_name
    
    def detect_and_embed(self, image_path: str) -> list:
        """Detect faces and compute embeddings"""
        try:
            img = cv2.imread(image_path)
            faces = self.app.get(img)
            
            results = []
            for face in faces:
                results.append({
                    'bbox': face.bbox.tolist(),
                    'confidence': float(face.det_score),
                    'embedding': face.embedding.tolist(),
                    'embedding_model': self.model_name
                })
            
            return results
        except Exception as e:
            logger.error(f"Face detection failed for {image_path}: {e}")
            return []
```

### Step 7: FAISS Builder (2 days)

```python
# processing_cli/services/faiss_builder.py
import faiss
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FAISSBuilder:
    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
    
    def add_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Add embeddings to index and return vector IDs"""
        embeddings = embeddings.astype('float32')
        faiss.normalize_L2(embeddings)
        
        start_id = self.index.ntotal
        self.index.add(embeddings)
        
        return np.arange(start_id, self.index.ntotal)
    
    def save(self, output_path: Path):
        """Save index to disk"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(output_path))
        logger.info(f"FAISS index saved: {self.index.ntotal} vectors")
```

### Step 8: Main Process Command (3 days)

```python
# processing_cli/commands/process.py
import click
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.db_models import Base, Event, Photo, Thumbnail, OCRCandidate, Face
from shared.models import BundleManifest
from processing_cli.services import (
    PhotoScanner, ThumbnailService, OCRService, 
    FaceService, FAISSBuilder
)
import logging

logger = logging.getLogger(__name__)

@click.command()
@click.option('--source', required=True, type=click.Path(exists=True))
@click.option('--event-slug', required=True)
@click.option('--event-name', required=True)
@click.option('--event-date', required=True)
@click.option('--event-location', default=None)
@click.option('--output', default='./dist/events')
@click.option('--config', default='./processing_cli/config.yaml')
@click.option('--skip-ocr', is_flag=True)
@click.option('--skip-faces', is_flag=True)
@click.option('--force', is_flag=True)
def process(source, event_slug, event_name, event_date, event_location, 
            output, config, skip_ocr, skip_faces, force):
    """Process event photos and export bundle"""
    
    # Setup paths
    source_path = Path(source)
    output_path = Path(output) / event_slug
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Setup database
    db_path = output_path / 'event.db'
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create event
    event = Event(
        slug=event_slug,
        name=event_name,
        date=datetime.strptime(event_date, '%Y-%m-%d').date(),
        location=event_location
    )
    session.add(event)
    session.commit()
    
    # Initialize services
    scanner = PhotoScanner()
    thumbnail_service = ThumbnailService()
    ocr_service = OCRService() if not skip_ocr else None
    face_service = FaceService() if not skip_faces else None
    faiss_builder = FAISSBuilder()
    
    # Process photos
    photos = list(scanner.scan(source_path))
    logger.info(f"Found {len(photos)} photos")
    
    for idx, photo_path in enumerate(photos, 1):
        logger.info(f"Processing {idx}/{len(photos)}: {photo_path.name}")
        
        # Compute checksum
        checksum = compute_checksum(photo_path)
        
        # Check cache
        if not force:
            existing = session.query(Photo).filter_by(checksum=checksum).first()
            if existing:
                logger.info(f"  Skipped (cached)")
                continue
        
        # Create photo record
        photo = Photo(
            event_id=event.id,
            filename=photo_path.name,
            checksum=checksum,
            original_path=str(photo_path.relative_to(source_path)),
            file_size=photo_path.stat().st_size
        )
        session.add(photo)
        session.flush()
        
        # Generate thumbnail
        thumb_path = output_path / 'thumbnails' / f'photo_{photo.id:06d}.jpg'
        thumb_meta = thumbnail_service.generate(photo_path, thumb_path)
        
        thumbnail = Thumbnail(
            photo_id=photo.id,
            path=str(thumb_path.relative_to(output_path)),
            **thumb_meta
        )
        session.add(thumbnail)
        
        # OCR
        if ocr_service:
            candidates = ocr_service.extract_bib_candidates(str(photo_path))
            for cand in candidates:
                ocr = OCRCandidate(photo_id=photo.id, **cand)
                session.add(ocr)
        
        # Face detection
        if face_service:
            faces = face_service.detect_and_embed(str(photo_path))
            for face_data in faces:
                embedding = np.array([face_data.pop('embedding')])
                vector_ids = faiss_builder.add_embeddings(embedding)
                
                face = Face(
                    photo_id=photo.id,
                    faiss_vector_id=int(vector_ids[0]),
                    **face_data
                )
                session.add(face)
        
        session.commit()
    
    # Save FAISS index
    faiss_path = output_path / 'faiss.index'
    faiss_builder.save(faiss_path)
    
    # Write manifest
    manifest = create_manifest(event, session, output_path)
    manifest_path = output_path / 'manifest.json'
    with open(manifest_path, 'w') as f:
        f.write(manifest.model_dump_json(indent=2))
    
    logger.info(f"Bundle exported to {output_path}")
```

## Configuration

File: `processing_cli/config.yaml`

```yaml
ocr:
  model: paddleocr
  lang: en
  confidence_threshold: 0.6
  use_angle_cls: true

face:
  model: insightface  # or deepface
  model_name: buffalo_l
  det_size: [640, 640]
  embedding_dimension: 512

processing:
  max_image_size: 1280
  thumbnail_size: [800, 600]
  thumbnail_quality: 85
  batch_size: 1

cache:
  enabled: true
  check_model_version: true

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ./logs/processing.log
```

## Todo List

- [ ] Setup CLI framework (Click)
- [ ] Implement scanner service
- [ ] Implement checksum utility
- [ ] Implement thumbnail service
- [ ] Implement OCR service (PaddleOCR)
- [ ] Implement face service (InsightFace/DeepFace)
- [ ] Implement FAISS builder
- [ ] Implement process command
- [ ] Implement validate command
- [ ] Implement rebuild-embeddings command
- [ ] Write unit tests
- [ ] Test with 200-500 sample photos

## Success Criteria

- [ ] Process 200-500 sample photos successfully
- [ ] Processing time ≤ 3s/photo on M1
- [ ] OCR detection rate ≥ 70% for visible bibs
- [ ] Face detection rate ≥ 80% for clear faces
- [ ] Bundle validation passes
- [ ] Incremental processing works (skip cached)
- [ ] Type checking passes: `mypy processing_cli/`
- [ ] Tests pass: `pytest tests/test_processing/ -v`

## Risk Assessment

- **Medium:** PaddleOCR accuracy poor → add manual review UI (Phase 06)
- **Medium:** Face model slow → already using CPU-optimized models
- **Low:** Memory issues → processing sequentially (batch_size=1)

## Security Considerations

- Do not log embeddings or OCR text to console
- Validate input paths (prevent path traversal)
- Handle corrupt images gracefully (don't crash)

## Next Steps

After processing app works, proceed to Phase 03 (Bundle Import/Export Workflow).

## Unresolved Questions

- Should we support video files (extract frames)? → NO for MVP
- Should we support RAW formats? → NO for MVP (JPG only)
