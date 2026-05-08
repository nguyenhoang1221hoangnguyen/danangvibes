# Phase 06: Admin UI & Manual Review

## Context Links

- Phase 04: `phase-04-web-server-core-macbook-2017.md`
- Phase 05: `phase-05-public-search-download-ui.md`
- Architecture: `ARCHITECTURE.md`

## Overview

**Priority:** Medium  
**Status:** Planned  
**Goal:** Build admin interface for event management, OCR review/correction, donation config, and analytics.

## Requirements

### Functional

**Event Management:**
- List all events (published/unpublished)
- Publish/unpublish events
- View event details and stats
- Switch/rollback versions

**OCR Review:**
- List photos with OCR candidates
- Filter by confidence threshold
- Manual bib correction
- Bulk correction

**Donation Config:**
- Upload QR code image
- Set donation message
- Preview donation prompt

**Analytics:**
- Download statistics
- Popular photos
- Search queries log

### Non-Functional

- Simple password/token authentication
- Server-rendered UI (Jinja2)
- Mobile-friendly
- Fast operations (< 1s)

## Architecture

```
Admin Request
  ↓
Auth Middleware (bearer token)
  ↓
Admin API Route
  ↓
Admin Service
  ↓
Server Database / Event Bundle
  ↓
Jinja Template
  ↓
Admin UI
```

## Authentication

**Simple bearer token approach:**
- Token stored in env var: `ADMIN_TOKEN`
- Admin enters token once → stored in session cookie
- Middleware checks token on admin routes

File: `web_server/utils/auth.py`

```python
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from web_server.config import settings

security = HTTPBearer()

def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Verify admin bearer token"""
    if credentials.credentials != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token"
        )
    return True

# Alternative: session-based auth
def get_admin_session(request: Request):
    """Check admin session cookie"""
    token = request.session.get("admin_token")
    if token != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    return True
```

## Admin API Routes

File: `web_server/api/admin.py`

```python
from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List

from web_server.services.event_loader import EventLoader
from web_server.services.admin_service import AdminService
from web_server.utils.auth import verify_admin_token
from web_server.main import get_event_loader

router = APIRouter(dependencies=[Depends(verify_admin_token)])
templates = Jinja2Templates(directory="web_server/templates")

# Models
class PublishRequest(BaseModel):
    is_published: bool

class OCRCorrectionRequest(BaseModel):
    ocr_candidate_id: int
    corrected_text: str

class DonationConfigRequest(BaseModel):
    message: str

# Routes
@router.get("/")
async def admin_dashboard(
    request: Request,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Admin dashboard"""
    admin_service = AdminService(event_loader)
    stats = admin_service.get_dashboard_stats()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats
    })

@router.get("/events")
async def admin_events_list(
    request: Request,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """List all events"""
    admin_service = AdminService(event_loader)
    events = admin_service.list_all_events()
    
    return templates.TemplateResponse("admin/events.html", {
        "request": request,
        "events": events
    })

@router.post("/events/{event_slug}/publish")
async def publish_event(
    event_slug: str,
    publish_req: PublishRequest,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Publish/unpublish event"""
    admin_service = AdminService(event_loader)
    admin_service.set_published(event_slug, publish_req.is_published)
    
    # Reload event if published
    if publish_req.is_published:
        event_loader.load_event(event_slug)
    else:
        event_loader.unload_event(event_slug)
    
    return {"status": "success"}

@router.get("/events/{event_slug}/ocr-review")
async def ocr_review_page(
    request: Request,
    event_slug: str,
    confidence_threshold: float = 0.7,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """OCR review page"""
    bundle = event_loader.get_event(event_slug)
    admin_service = AdminService(event_loader)
    
    candidates = admin_service.get_low_confidence_ocr(
        event_slug,
        confidence_threshold
    )
    
    return templates.TemplateResponse("admin/ocr_review.html", {
        "request": request,
        "event_slug": event_slug,
        "candidates": candidates,
        "threshold": confidence_threshold
    })

@router.post("/events/{event_slug}/ocr-correct")
async def correct_ocr(
    event_slug: str,
    correction: OCRCorrectionRequest,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Correct OCR candidate"""
    admin_service = AdminService(event_loader)
    admin_service.correct_ocr(
        event_slug,
        correction.ocr_candidate_id,
        correction.corrected_text
    )
    
    return {"status": "success"}

@router.get("/events/{event_slug}/config")
async def donation_config_page(
    request: Request,
    event_slug: str,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Donation config page"""
    admin_service = AdminService(event_loader)
    config = admin_service.get_donation_config(event_slug)
    
    return templates.TemplateResponse("admin/donation_config.html", {
        "request": request,
        "event_slug": event_slug,
        "config": config
    })

@router.post("/events/{event_slug}/config/qr")
async def upload_qr_code(
    event_slug: str,
    qr_image: UploadFile = File(...),
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Upload donation QR code"""
    admin_service = AdminService(event_loader)
    
    # Save QR image
    qr_path = await admin_service.save_qr_code(event_slug, qr_image)
    
    return {"status": "success", "qr_path": str(qr_path)}

@router.post("/events/{event_slug}/config/message")
async def update_donation_message(
    event_slug: str,
    config: DonationConfigRequest,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Update donation message"""
    admin_service = AdminService(event_loader)
    admin_service.update_donation_message(event_slug, config.message)
    
    return {"status": "success"}

@router.get("/analytics")
async def analytics_page(
    request: Request,
    event_loader: EventLoader = Depends(get_event_loader)
):
    """Analytics dashboard"""
    admin_service = AdminService(event_loader)
    analytics = admin_service.get_analytics()
    
    return templates.TemplateResponse("admin/analytics.html", {
        "request": request,
        "analytics": analytics
    })
```

## Admin Service

File: `web_server/services/admin_service.py`

```python
from pathlib import Path
from datetime import datetime
from sqlalchemy import func
from typing import List, Dict, Optional
import shutil

from web_server.services.event_loader import EventLoader
from web_server.models.server_models import ServerEvent, DonationConfig, DownloadLog
from shared.db_models import OCRCandidate, Photo

class AdminService:
    def __init__(self, event_loader: EventLoader):
        self.event_loader = event_loader
        self.server_session = event_loader.ServerSession()
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        total_events = self.server_session.query(ServerEvent).count()
        published_events = self.server_session.query(ServerEvent).filter_by(
            is_published=True
        ).count()
        
        total_downloads = self.server_session.query(DownloadLog).count()
        
        return {
            "total_events": total_events,
            "published_events": published_events,
            "unpublished_events": total_events - published_events,
            "total_downloads": total_downloads
        }
    
    def list_all_events(self) -> List[Dict]:
        """List all events with metadata"""
        events = self.server_session.query(ServerEvent).all()
        
        result = []
        for event in events:
            result.append({
                "slug": event.slug,
                "name": event.name,
                "is_published": event.is_published,
                "active_version": event.active_version,
                "created_at": event.created_at,
                "updated_at": event.updated_at
            })
        
        return result
    
    def set_published(self, event_slug: str, is_published: bool):
        """Publish/unpublish event"""
        event = self.server_session.query(ServerEvent).filter_by(
            slug=event_slug
        ).first()
        
        if event:
            event.is_published = is_published
            event.updated_at = datetime.utcnow()
            self.server_session.commit()
    
    def get_low_confidence_ocr(
        self,
        event_slug: str,
        confidence_threshold: float
    ) -> List[Dict]:
        """Get OCR candidates below confidence threshold"""
        bundle = self.event_loader.get_event(event_slug)
        if not bundle:
            return []
        
        session = bundle.get_session()
        
        try:
            candidates = session.query(OCRCandidate, Photo).join(
                Photo, OCRCandidate.photo_id == Photo.id
            ).filter(
                OCRCandidate.confidence < confidence_threshold,
                OCRCandidate.is_bib == True
            ).order_by(OCRCandidate.confidence).limit(100).all()
            
            result = []
            for ocr, photo in candidates:
                result.append({
                    "id": ocr.id,
                    "photo_id": photo.id,
                    "text": ocr.text,
                    "confidence": ocr.confidence,
                    "manual_correction": ocr.manual_correction,
                    "thumbnail_url": f"/events/{event_slug}/photos/{photo.id}/thumbnail"
                })
            
            return result
        finally:
            session.close()
    
    def correct_ocr(
        self,
        event_slug: str,
        ocr_candidate_id: int,
        corrected_text: str
    ):
        """Correct OCR candidate"""
        bundle = self.event_loader.get_event(event_slug)
        if not bundle:
            return
        
        session = bundle.get_session()
        
        try:
            candidate = session.query(OCRCandidate).filter_by(
                id=ocr_candidate_id
            ).first()
            
            if candidate:
                candidate.manual_correction = corrected_text
                candidate.corrected_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    def get_donation_config(self, event_slug: str) -> Optional[Dict]:
        """Get donation config"""
        config = self.server_session.query(DonationConfig).filter_by(
            event_slug=event_slug
        ).first()
        
        if config:
            return {
                "qr_code_path": config.qr_code_path,
                "message": config.message
            }
        return None
    
    async def save_qr_code(
        self,
        event_slug: str,
        qr_image
    ) -> Path:
        """Save QR code image"""
        # Create uploads directory
        uploads_dir = Path("web_server/static/uploads/qr")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        qr_path = uploads_dir / f"{event_slug}_qr.png"
        with open(qr_path, "wb") as f:
            content = await qr_image.read()
            f.write(content)
        
        # Update database
        config = self.server_session.query(DonationConfig).filter_by(
            event_slug=event_slug
        ).first()
        
        if not config:
            config = DonationConfig(event_slug=event_slug)
            self.server_session.add(config)
        
        config.qr_code_path = str(qr_path)
        config.updated_at = datetime.utcnow()
        self.server_session.commit()
        
        return qr_path
    
    def update_donation_message(self, event_slug: str, message: str):
        """Update donation message"""
        config = self.server_session.query(DonationConfig).filter_by(
            event_slug=event_slug
        ).first()
        
        if not config:
            config = DonationConfig(event_slug=event_slug)
            self.server_session.add(config)
        
        config.message = message
        config.updated_at = datetime.utcnow()
        self.server_session.commit()
    
    def get_analytics(self) -> Dict:
        """Get analytics data"""
        # Top downloaded photos
        top_photos = self.server_session.query(
            DownloadLog.event_slug,
            DownloadLog.photo_id,
            func.count(DownloadLog.id).label('download_count')
        ).group_by(
            DownloadLog.event_slug,
            DownloadLog.photo_id
        ).order_by(
            func.count(DownloadLog.id).desc()
        ).limit(10).all()
        
        # Downloads by event
        downloads_by_event = self.server_session.query(
            DownloadLog.event_slug,
            func.count(DownloadLog.id).label('download_count')
        ).group_by(
            DownloadLog.event_slug
        ).all()
        
        return {
            "top_photos": [
                {
                    "event_slug": p.event_slug,
                    "photo_id": p.photo_id,
                    "download_count": p.download_count
                }
                for p in top_photos
            ],
            "downloads_by_event": [
                {
                    "event_slug": e.event_slug,
                    "download_count": e.download_count
                }
                for e in downloads_by_event
            ]
        }
```

## Admin Templates

### Dashboard

File: `web_server/templates/admin/dashboard.html`

```html
{% extends "admin/base.html" %}

{% block title %}Admin Dashboard{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
  <h1 class="text-3xl font-bold mb-8">Admin Dashboard</h1>
  
  <!-- Stats Cards -->
  <div class="grid md:grid-cols-4 gap-6 mb-8">
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600 mb-2">Total Events</p>
      <p class="text-4xl font-bold text-blue-600">{{ stats.total_events }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600 mb-2">Published</p>
      <p class="text-4xl font-bold text-green-600">{{ stats.published_events }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600 mb-2">Unpublished</p>
      <p class="text-4xl font-bold text-orange-600">{{ stats.unpublished_events }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600 mb-2">Total Downloads</p>
      <p class="text-4xl font-bold text-purple-600">{{ stats.total_downloads }}</p>
    </div>
  </div>
  
  <!-- Quick Actions -->
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-xl font-semibold mb-4">Quick Actions</h2>
    <div class="grid md:grid-cols-3 gap-4">
      <a href="/admin/events" class="block p-4 border rounded-lg hover:bg-gray-50">
        <h3 class="font-semibold mb-2">Manage Events</h3>
        <p class="text-sm text-gray-600">Publish, unpublish, and configure events</p>
      </a>
      <a href="/admin/analytics" class="block p-4 border rounded-lg hover:bg-gray-50">
        <h3 class="font-semibold mb-2">View Analytics</h3>
        <p class="text-sm text-gray-600">Download stats and popular photos</p>
      </a>
      <a href="/" class="block p-4 border rounded-lg hover:bg-gray-50">
        <h3 class="font-semibold mb-2">View Public Site</h3>
        <p class="text-sm text-gray-600">See what users see</p>
      </a>
    </div>
  </div>
</div>
{% endblock %}
```

### OCR Review

File: `web_server/templates/admin/ocr_review.html`

```html
{% extends "admin/base.html" %}

{% block title %}OCR Review - {{ event_slug }}{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
  <h1 class="text-3xl font-bold mb-4">OCR Review: {{ event_slug }}</h1>
  <p class="text-gray-600 mb-8">
    Showing OCR candidates with confidence < {{ threshold }}
  </p>
  
  {% if candidates|length == 0 %}
    <div class="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
      <p class="text-green-700">✓ No low-confidence OCR candidates found!</p>
    </div>
  {% else %}
    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
      {% for candidate in candidates %}
      <div class="bg-white rounded-lg shadow p-4">
        <img src="{{ candidate.thumbnail_url }}" 
             alt="Photo {{ candidate.photo_id }}"
             class="w-full h-48 object-cover rounded mb-4">
        
        <div class="mb-4">
          <p class="text-sm text-gray-600">OCR Result:</p>
          <p class="text-2xl font-bold">{{ candidate.text }}</p>
          <p class="text-sm text-gray-500">
            Confidence: {{ (candidate.confidence * 100)|int }}%
          </p>
        </div>
        
        {% if candidate.manual_correction %}
          <div class="mb-4 bg-green-50 border border-green-200 rounded p-2">
            <p class="text-sm text-gray-600">Corrected to:</p>
            <p class="font-semibold text-green-700">{{ candidate.manual_correction }}</p>
          </div>
        {% else %}
          <form hx-post="/admin/events/{{ event_slug }}/ocr-correct"
                hx-target="#candidate-{{ candidate.id }}"
                class="flex gap-2">
            <input type="hidden" name="ocr_candidate_id" value="{{ candidate.id }}">
            <input type="text" 
                   name="corrected_text"
                   placeholder="Correct bib number"
                   class="flex-1 px-3 py-2 border rounded"
                   required>
            <button type="submit" 
                    class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
              Save
            </button>
          </form>
        {% endif %}
        
        <div id="candidate-{{ candidate.id }}"></div>
      </div>
      {% endfor %}
    </div>
  {% endif %}
</div>
{% endblock %}
```

## Implementation Steps

1. **Implement authentication** (1 day)
2. **Implement AdminService** (2 days)
3. **Implement admin API routes** (2 days)
4. **Create admin templates** (3 days)
5. **Test admin workflows** (1 day)

## Todo List

- [ ] Implement bearer token auth
- [ ] Implement AdminService
- [ ] Implement admin API routes
- [ ] Create admin dashboard
- [ ] Create events list page
- [ ] Create OCR review page
- [ ] Create donation config page
- [ ] Create analytics page
- [ ] Test publish/unpublish
- [ ] Test OCR correction
- [ ] Test QR upload

## Success Criteria

- [ ] Admin can login with token
- [ ] Admin can publish/unpublish events
- [ ] Admin can review low-confidence OCR
- [ ] Admin can correct OCR mistakes
- [ ] Admin can upload QR code
- [ ] Admin can view analytics
- [ ] All operations < 1s

## Risk Assessment

- **Low:** Token leaked → rotate token, add IP whitelist if needed
- **Low:** OCR corrections lost → stored in event bundle DB

## Security Considerations

- Admin token in env var (not hardcoded)
- Admin routes protected by middleware
- File upload validation (QR code)
- No admin token in logs

## Next Steps

After admin UI works, proceed to Phase 07 (Testing & Performance Validation).

## Unresolved Questions

- Should admin UI be accessible via Cloudflare Tunnel? → YES with protection, or local-only for MVP
