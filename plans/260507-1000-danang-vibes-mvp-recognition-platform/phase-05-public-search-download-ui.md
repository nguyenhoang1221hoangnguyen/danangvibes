# Phase 05: Public Search & Download UI

## Context Links

- Phase 04: `phase-04-web-server-core-macbook-2017.md`
- Architecture: `ARCHITECTURE.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Build the public-facing UI where customers search for their photos by bib number or selfie upload, view results, and download originals.

## Requirements

### Functional

**Search:**
- Event landing page with search form
- Bib number search (exact match)
- Selfie upload search (face similarity)
- Tabbed results: "Bib Match", "Face Match", "Suggested"
- Thumbnail grid with lazy loading
- Photo detail modal

**Download:**
- Original JPG download endpoint
- Download tracking (analytics)
- Donation prompt after download

**UX:**
- Mobile-friendly responsive design
- Fast thumbnail loading
- Clear "no results" messaging
- Loading states for searches

### Non-Functional

- Server-rendered HTML (Jinja2)
- Progressive enhancement with HTMX
- Minimal JavaScript
- Accessible (WCAG 2.1 AA)
- Fast initial load (< 2s)

## Architecture

```
User Request
  ↓
FastAPI Route
  ↓
Search Service
  ├─ Bib Search (SQLite query)
  └─ Face Search (FAISS + embedding)
  ↓
Jinja Template
  ↓
HTML Response (with HTMX)
  ↓
User clicks photo
  ↓
Download Service
  ↓
Stream original JPG
  ↓
Show donation prompt
```

## User Flow

```
1. User visits: https://danangvibes.com
2. Sees event list
3. Clicks "Ironman Da Nang 2026"
4. Event page with 2 search options:
   - Input bib number: [____] [Search]
   - Upload selfie: [Choose File] [Search]
5. Search results in tabs:
   - Bib Match (exact bib matches)
   - Face Match (face similarity > threshold)
   - Suggested (other photos from same time/location)
6. Click photo → modal with larger preview
7. Click "Download Original" → download JPG
8. See donation QR code prompt
```

## API Endpoints

### Public Routes

File: `web_server/api/public.py`

```python
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import logging

from web_server.services.event_loader import EventLoader
from web_server.services.search_service import SearchService
from web_server.services.download_service import DownloadService
from web_server.main import get_event_loader

router = APIRouter()
templates = Jinja2Templates(directory="web_server/templates")
logger = logging.getLogger(__name__)

# Request/Response models
class BibSearchRequest(BaseModel):
    bib_number: str

class SearchResult(BaseModel):
    photo_id: int
    thumbnail_url: str
    capture_time: Optional[str]
    similarity_score: Optional[float]  # for face search

class SearchResponse(BaseModel):
    bib_matches: List[SearchResult]
    face_matches: List[SearchResult]
    suggested: List[SearchResult]
    total_results: int

# Routes
@router.get("/events/{event_slug}")
async def event_page(
    request: Request,
    event_slug: str,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Event landing page with search form"""
    bundle = event_loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return templates.TemplateResponse("public/event.html", {
        "request": request,
        "event": bundle.manifest.event,
        "stats": bundle.manifest.stats
    })

@router.post("/events/{event_slug}/search/bib")
async def search_by_bib(
    request: Request,
    event_slug: str,
    bib_request: BibSearchRequest,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Search photos by bib number"""
    bundle = event_loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    
    search_service = SearchService(bundle)
    results = search_service.search_by_bib(bib_request.bib_number)
    
    return templates.TemplateResponse("public/results.html", {
        "request": request,
        "event_slug": event_slug,
        "search_type": "bib",
        "query": bib_request.bib_number,
        "results": results
    })

@router.post("/events/{event_slug}/search/face")
async def search_by_face(
    request: Request,
    event_slug: str,
    selfie: UploadFile = File(...),
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Search photos by selfie upload"""
    bundle = event_loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Validate upload
    if selfie.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG allowed")
    
    # Read file
    contents = await selfie.read()
    
    # Search
    search_service = SearchService(bundle)
    results = search_service.search_by_face(contents)
    
    return templates.TemplateResponse("public/results.html", {
        "request": request,
        "event_slug": event_slug,
        "search_type": "face",
        "results": results
    })

@router.get("/events/{event_slug}/photos/{photo_id}/thumbnail")
async def get_thumbnail(
    event_slug: str,
    photo_id: int,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Serve thumbnail image"""
    bundle = event_loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    
    thumbnail_path = bundle.bundle_path / "thumbnails" / f"photo_{photo_id:06d}.jpg"
    
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(thumbnail_path, media_type="image/jpeg")

@router.get("/events/{event_slug}/photos/{photo_id}/download")
async def download_original(
    event_slug: str,
    photo_id: int,
    request: Request,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Download original photo"""
    bundle = event_loader.get_event(event_slug)
    if not bundle:
        raise HTTPException(status_code=404, detail="Event not found")
    
    download_service = DownloadService(bundle)
    
    # Get original path
    original_path = bundle.get_original_path(photo_id)
    if not original_path or not original_path.exists():
        raise HTTPException(status_code=404, detail="Original not found")
    
    # Track download
    download_service.track_download(
        photo_id=photo_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Stream file
    return FileResponse(
        original_path,
        media_type="image/jpeg",
        filename=f"{event_slug}_{photo_id}.jpg"
    )
```

## Search Service

File: `web_server/services/search_service.py`

```python
from typing import List, Dict
import numpy as np
import logging
from io import BytesIO
from PIL import Image
import cv2

from shared.db_models import Photo, OCRCandidate, Face
from web_server.services.event_loader import EventBundle

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, bundle: EventBundle):
        self.bundle = bundle
    
    def search_by_bib(self, bib_number: str) -> Dict:
        """Search photos by bib number"""
        session = self.bundle.get_session()
        
        try:
            # Find OCR candidates matching bib
            candidates = session.query(OCRCandidate).filter(
                OCRCandidate.text == bib_number,
                OCRCandidate.is_bib == True
            ).all()
            
            # Get unique photos
            photo_ids = list(set([c.photo_id for c in candidates]))
            
            photos = session.query(Photo).filter(
                Photo.id.in_(photo_ids)
            ).order_by(Photo.capture_time).all()
            
            results = {
                "bib_matches": [
                    {
                        "photo_id": p.id,
                        "thumbnail_url": f"/events/{self.bundle.slug}/photos/{p.id}/thumbnail",
                        "capture_time": p.capture_time.isoformat() if p.capture_time else None
                    }
                    for p in photos
                ],
                "face_matches": [],
                "suggested": [],
                "total_results": len(photos)
            }
            
            return results
        finally:
            session.close()
    
    def search_by_face(self, image_bytes: bytes) -> Dict:
        """Search photos by face similarity"""
        # Load face model (same as processing)
        from processing_cli.services.face import FaceService
        face_service = FaceService()
        
        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            # Extract embedding from selfie
            faces = face_service.detect_and_embed(tmp_path)
            
            if not faces:
                return {
                    "bib_matches": [],
                    "face_matches": [],
                    "suggested": [],
                    "total_results": 0
                }
            
            # Use first face
            query_embedding = np.array([faces[0]["embedding"]], dtype='float32')
            
            # Search FAISS
            k = 50  # top 50 results
            distances, indices = self.bundle.faiss_index.search(query_embedding, k)
            
            # Get photos from face vector IDs
            session = self.bundle.get_session()
            
            try:
                results = []
                for idx, distance in zip(indices[0], distances[0]):
                    # Convert distance to similarity (lower distance = higher similarity)
                    similarity = 1.0 / (1.0 + float(distance))
                    
                    # Filter by threshold
                    if similarity < 0.6:
                        continue
                    
                    # Get face record
                    face = session.query(Face).filter_by(
                        faiss_vector_id=int(idx)
                    ).first()
                    
                    if face:
                        photo = session.query(Photo).filter_by(
                            id=face.photo_id
                        ).first()
                        
                        if photo:
                            results.append({
                                "photo_id": photo.id,
                                "thumbnail_url": f"/events/{self.bundle.slug}/photos/{photo.id}/thumbnail",
                                "capture_time": photo.capture_time.isoformat() if photo.capture_time else None,
                                "similarity_score": round(similarity, 2)
                            })
                
                return {
                    "bib_matches": [],
                    "face_matches": results,
                    "suggested": [],
                    "total_results": len(results)
                }
            finally:
                session.close()
        finally:
            import os
            os.unlink(tmp_path)
```

## Download Service

File: `web_server/services/download_service.py`

```python
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web_server.config import settings
from web_server.services.event_loader import EventBundle

class DownloadService:
    def __init__(self, bundle: EventBundle):
        self.bundle = bundle
        
        # Server database for tracking
        self.server_engine = create_engine(f"sqlite:///{settings.server_db_path}")
        self.ServerSession = sessionmaker(bind=self.server_engine)
    
    def track_download(self, photo_id: int, ip_address: str, user_agent: str):
        """Track download for analytics"""
        from web_server.models.server_models import DownloadLog
        
        session = self.ServerSession()
        try:
            log = DownloadLog(
                event_slug=self.bundle.slug,
                photo_id=photo_id,
                ip_address=ip_address,
                user_agent=user_agent,
                downloaded_at=datetime.utcnow()
            )
            session.add(log)
            session.commit()
        finally:
            session.close()
```

## Templates

### Event Page

File: `web_server/templates/public/event.html`

```html
{% extends "base.html" %}

{% block title %}{{ event.name }} - DaNang Vibes{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
  <h1 class="text-4xl font-bold mb-4">{{ event.name }}</h1>
  <p class="text-gray-600 mb-8">{{ event.date }} • {{ event.location }}</p>
  
  <div class="grid md:grid-cols-2 gap-8 mb-12">
    <!-- Bib Search -->
    <div class="bg-white rounded-lg shadow-lg p-6">
      <h2 class="text-2xl font-semibold mb-4">Search by Bib Number</h2>
      <form hx-post="/events/{{ event.slug }}/search/bib" 
            hx-target="#results"
            hx-indicator="#loading">
        <div class="mb-4">
          <label class="block text-gray-700 mb-2">Bib Number</label>
          <input type="text" 
                 name="bib_number" 
                 class="w-full px-4 py-2 border rounded-lg"
                 placeholder="e.g., 1234"
                 required>
        </div>
        <button type="submit" 
                class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700">
          Search
        </button>
      </form>
    </div>
    
    <!-- Face Search -->
    <div class="bg-white rounded-lg shadow-lg p-6">
      <h2 class="text-2xl font-semibold mb-4">Search by Selfie</h2>
      <form hx-post="/events/{{ event.slug }}/search/face" 
            hx-encoding="multipart/form-data"
            hx-target="#results"
            hx-indicator="#loading">
        <div class="mb-4">
          <label class="block text-gray-700 mb-2">Upload Selfie</label>
          <input type="file" 
                 name="selfie" 
                 accept="image/jpeg,image/png"
                 class="w-full px-4 py-2 border rounded-lg"
                 required>
          <p class="text-sm text-gray-500 mt-2">
            Upload a clear photo of your face. Max 10MB.
          </p>
        </div>
        <button type="submit" 
                class="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700">
          Search
        </button>
      </form>
    </div>
  </div>
  
  <!-- Loading indicator -->
  <div id="loading" class="htmx-indicator text-center py-8">
    <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    <p class="mt-4 text-gray-600">Searching...</p>
  </div>
  
  <!-- Results container -->
  <div id="results"></div>
  
  <!-- Event stats -->
  <div class="mt-12 bg-gray-100 rounded-lg p-6">
    <h3 class="text-xl font-semibold mb-4">Event Statistics</h3>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div>
        <p class="text-3xl font-bold text-blue-600">{{ stats.total_photos }}</p>
        <p class="text-gray-600">Total Photos</p>
      </div>
      <div>
        <p class="text-3xl font-bold text-green-600">{{ stats.photos_with_faces }}</p>
        <p class="text-gray-600">With Faces</p>
      </div>
      <div>
        <p class="text-3xl font-bold text-purple-600">{{ stats.photos_with_bib_candidates }}</p>
        <p class="text-gray-600">With Bibs</p>
      </div>
      <div>
        <p class="text-3xl font-bold text-orange-600">{{ stats.total_faces_detected }}</p>
        <p class="text-gray-600">Faces Detected</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

### Results Page

File: `web_server/templates/public/results.html`

```html
<div class="bg-white rounded-lg shadow-lg p-6">
  <h2 class="text-2xl font-semibold mb-4">
    Search Results
    {% if search_type == 'bib' %}
      for Bib #{{ query }}
    {% else %}
      by Face Match
    {% endif %}
  </h2>
  
  {% if results.total_results == 0 %}
    <div class="text-center py-12">
      <p class="text-gray-600 text-lg">No photos found.</p>
      <p class="text-gray-500 mt-2">Try a different search or check your bib number.</p>
    </div>
  {% else %}
    <!-- Tabs -->
    <div class="border-b mb-6">
      <nav class="flex space-x-4">
        {% if results.bib_matches %}
        <button class="tab-button active" data-tab="bib">
          Bib Match ({{ results.bib_matches|length }})
        </button>
        {% endif %}
        {% if results.face_matches %}
        <button class="tab-button" data-tab="face">
          Face Match ({{ results.face_matches|length }})
        </button>
        {% endif %}
        {% if results.suggested %}
        <button class="tab-button" data-tab="suggested">
          Suggested ({{ results.suggested|length }})
        </button>
        {% endif %}
      </nav>
    </div>
    
    <!-- Bib Match Tab -->
    {% if results.bib_matches %}
    <div id="tab-bib" class="tab-content">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        {% for photo in results.bib_matches %}
        <div class="relative group cursor-pointer" 
             onclick="openModal('{{ event_slug }}', {{ photo.photo_id }})">
          <img src="{{ photo.thumbnail_url }}" 
               alt="Photo {{ photo.photo_id }}"
               class="w-full h-48 object-cover rounded-lg"
               loading="lazy">
          <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition rounded-lg"></div>
        </div>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    
    <!-- Face Match Tab -->
    {% if results.face_matches %}
    <div id="tab-face" class="tab-content hidden">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        {% for photo in results.face_matches %}
        <div class="relative group cursor-pointer" 
             onclick="openModal('{{ event_slug }}', {{ photo.photo_id }})">
          <img src="{{ photo.thumbnail_url }}" 
               alt="Photo {{ photo.photo_id }}"
               class="w-full h-48 object-cover rounded-lg"
               loading="lazy">
          <div class="absolute top-2 right-2 bg-green-600 text-white px-2 py-1 rounded text-sm">
            {{ (photo.similarity_score * 100)|int }}% match
          </div>
          <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition rounded-lg"></div>
        </div>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    
    <!-- Donation prompt -->
    <div class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
      <h3 class="text-lg font-semibold mb-2">Found your photos?</h3>
      <p class="text-gray-700 mb-4">
        This service is free, but donations help us cover costs and improve the platform.
      </p>
      <a href="/donate" class="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
        Support Us
      </a>
    </div>
  {% endif %}
</div>

<!-- Photo Modal -->
<div id="photoModal" class="hidden fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
  <div class="bg-white rounded-lg max-w-4xl w-full p-6">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-xl font-semibold">Photo Preview</h3>
      <button onclick="closeModal()" class="text-gray-500 hover:text-gray-700">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>
    <img id="modalImage" src="" alt="Photo" class="w-full rounded-lg mb-4">
    <a id="downloadButton" href="" download 
       class="block w-full bg-green-600 text-white text-center py-3 rounded-lg hover:bg-green-700">
      Download Original (Full Resolution)
    </a>
  </div>
</div>

<script>
// Tab switching
document.querySelectorAll('.tab-button').forEach(button => {
  button.addEventListener('click', () => {
    const tab = button.dataset.tab;
    
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
    button.classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    document.getElementById(`tab-${tab}`).classList.remove('hidden');
  });
});

// Modal
function openModal(eventSlug, photoId) {
  const modal = document.getElementById('photoModal');
  const image = document.getElementById('modalImage');
  const downloadBtn = document.getElementById('downloadButton');
  
  image.src = `/events/${eventSlug}/photos/${photoId}/thumbnail`;
  downloadBtn.href = `/events/${eventSlug}/photos/${photoId}/download`;
  
  modal.classList.remove('hidden');
}

function closeModal() {
  document.getElementById('photoModal').classList.add('hidden');
}
</script>
```

## Implementation Steps

1. **Implement search service** (2 days)
2. **Implement download service** (1 day)
3. **Implement public API routes** (2 days)
4. **Create event page template** (1 day)
5. **Create results template** (2 days)
6. **Add HTMX interactions** (1 day)
7. **Style with Tailwind CSS** (1 day)
8. **Test search flows** (1 day)
9. **Test on mobile** (1 day)

## Todo List

- [ ] Implement SearchService
- [ ] Implement DownloadService
- [ ] Implement public API routes
- [ ] Create base template
- [ ] Create event page template
- [ ] Create results template
- [ ] Add HTMX for dynamic search
- [ ] Add photo modal
- [ ] Add donation prompt
- [ ] Style with Tailwind CSS
- [ ] Test bib search
- [ ] Test face search
- [ ] Test download
- [ ] Test on mobile devices

## Success Criteria

- [ ] Bib search returns results in < 200ms
- [ ] Face search returns results in < 5s
- [ ] Thumbnail grid loads smoothly
- [ ] Download works for original JPG
- [ ] Donation prompt displays
- [ ] Mobile responsive
- [ ] WCAG 2.1 AA compliant
- [ ] No JavaScript errors in console

## Risk Assessment

- **High:** Face search too slow on MacBook 2017 → benchmark in Phase 07, fallback to async queue
- **Medium:** Large result sets slow to render → add pagination
- **Low:** HTMX conflicts → test thoroughly

## Security Considerations

- Validate file uploads (size, type, magic bytes)
- Rate limit face search (5/minute)
- Rate limit downloads (20/minute)
- Sanitize user inputs
- No path traversal in download endpoint

## Next Steps

After public UI works, proceed to Phase 06 (Admin UI & Manual Review).

## Unresolved Questions

- Should we add pagination for large result sets? → YES if > 100 results
- Should we cache face embeddings from selfies? → NO for MVP (privacy concern)
