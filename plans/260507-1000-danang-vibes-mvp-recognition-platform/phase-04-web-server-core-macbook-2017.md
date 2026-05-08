# Phase 04: Web Server Core (MacBook Pro 2017)

## Context Links

- Phase 01: `phase-01-shared-foundation-bundle-schema.md`
- Phase 03: `phase-03-bundle-import-export-workflow.md`
- Architecture: `ARCHITECTURE.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Build the core FastAPI web server that loads imported bundles, serves search functionality, and provides the foundation for public/admin UIs.

## Requirements

### Functional

- FastAPI application with proper structure
- Load event bundles from storage
- SQLite connection pooling (read-only)
- FAISS index loading and caching
- Health check endpoint
- Configuration management
- Logging and error handling
- Static file serving (CSS, JS)

### Non-Functional

- Memory efficient (≤ 4GB for 10-50 users)
- Fast startup (< 5s)
- Graceful shutdown
- Thread-safe FAISS access
- Connection pooling for SQLite

## Architecture

```
FastAPI App
  ↓
Startup: Load published events
  ↓
For each event:
  ├─ Load SQLite (read-only)
  ├─ Load FAISS index
  └─ Cache in memory
  ↓
Routes:
  ├─ Public routes (search, download)
  ├─ Admin routes (management)
  └─ Health check
```

## Project Structure

```
web_server/
├── __init__.py
├── __main__.py              # Entry point
├── main.py                  # FastAPI app
├── config.py                # Configuration
├── dependencies.py          # FastAPI dependencies
├── middleware.py            # Custom middleware
├── api/
│   ├── __init__.py
│   ├── public.py            # Public routes
│   ├── admin.py             # Admin routes
│   └── health.py            # Health check
├── services/
│   ├── __init__.py
│   ├── event_loader.py      # Load events from storage
│   ├── search_service.py    # Search logic
│   ├── download_service.py  # Download logic
│   └── admin_service.py     # Admin operations
├── models/
│   ├── __init__.py
│   ├── server_models.py     # Server database models
│   └── api_models.py        # API request/response models
├── templates/
│   ├── base.html
│   ├── public/
│   │   ├── index.html
│   │   ├── event.html
│   │   └── results.html
│   └── admin/
│       ├── dashboard.html
│       └── ...
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── utils/
│   ├── __init__.py
│   ├── auth.py              # Admin authentication
│   └── rate_limit.py        # Rate limiting
└── config.yaml
```

## Core Components

### 1. Configuration (1 day)

File: `web_server/config.py`

```python
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 2
    reload: bool = False
    
    # Storage
    storage_path: Path = Path("/Volumes/SSD/events")
    
    # Database
    server_db_path: Path = Path("/Volumes/SSD/events/server.db")
    
    # Search
    bib_exact_match: bool = True
    face_top_k: int = 50
    face_similarity_threshold: float = 0.6
    
    # Upload
    max_selfie_size_mb: int = 10
    allowed_mime_types: list[str] = ["image/jpeg", "image/png"]
    
    # Rate limiting
    rate_limit_selfie_search: str = "5/minute"
    rate_limit_download: str = "20/minute"
    
    # Admin
    admin_token: str
    
    # Cloudflare
    cloudflare_tunnel_name: Optional[str] = None
    cloudflare_tunnel_token: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    class Config:
        env_file = ".env"
        env_prefix = "DANANGVIBES_"

settings = Settings()
```

### 2. Event Loader Service (2 days)

File: `web_server/services/event_loader.py`

```python
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import faiss
import json
import logging
from typing import Dict, Optional
from shared.db_models import Base, Event
from shared.models import BundleManifest

logger = logging.getLogger(__name__)

class EventBundle:
    """Represents a loaded event bundle"""
    
    def __init__(self, slug: str, bundle_path: Path):
        self.slug = slug
        self.bundle_path = bundle_path
        self.manifest: Optional[BundleManifest] = None
        self.db_engine = None
        self.SessionLocal = None
        self.faiss_index = None
        self.originals_mapping: Optional[Dict] = None
    
    def load(self):
        """Load bundle components"""
        logger.info(f"Loading bundle: {self.slug}")
        
        # Load manifest
        manifest_path = self.bundle_path / "manifest.json"
        with open(manifest_path) as f:
            self.manifest = BundleManifest.model_validate_json(f.read())
        
        # Load database (read-only)
        db_path = self.bundle_path / self.manifest.files.database
        self.db_engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.db_engine
        )
        
        # Load FAISS index
        faiss_path = self.bundle_path / self.manifest.files.faiss_index
        self.faiss_index = faiss.read_index(str(faiss_path))
        logger.info(f"  FAISS index loaded: {self.faiss_index.ntotal} vectors")
        
        # Load originals mapping if exists
        if self.manifest.files.originals_mode == "mapping":
            mapping_path = self.bundle_path / self.manifest.files.originals_mapping
            with open(mapping_path) as f:
                self.originals_mapping = json.load(f)
        
        logger.info(f"✓ Bundle loaded: {self.slug}")
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def get_original_path(self, photo_id: int) -> Optional[Path]:
        """Get original photo path"""
        if self.manifest.files.originals_mode == "included":
            # Originals in bundle
            return self.bundle_path / "originals" / f"photo_{photo_id:06d}.jpg"
        elif self.originals_mapping:
            # Originals via mapping
            base_path = Path(self.originals_mapping["base_path"])
            filename = self.originals_mapping["mappings"].get(str(photo_id))
            if filename:
                return base_path / filename
        return None


class EventLoader:
    """Manages loading and caching of event bundles"""
    
    def __init__(self, storage_path: Path, server_db_path: Path):
        self.storage_path = storage_path
        self.server_db_path = server_db_path
        self.bundles: Dict[str, EventBundle] = {}
        
        # Setup server database
        self.server_engine = create_engine(f"sqlite:///{server_db_path}")
        self.ServerSession = sessionmaker(bind=self.server_engine)
    
    def load_published_events(self):
        """Load all published events on startup"""
        from web_server.models.server_models import ServerEvent
        
        session = self.ServerSession()
        try:
            published_events = session.query(ServerEvent).filter_by(
                is_published=True
            ).all()
            
            logger.info(f"Loading {len(published_events)} published events")
            
            for event in published_events:
                try:
                    self.load_event(event.slug)
                except Exception as e:
                    logger.error(f"Failed to load event {event.slug}: {e}")
        finally:
            session.close()
    
    def load_event(self, slug: str) -> EventBundle:
        """Load a specific event bundle"""
        if slug in self.bundles:
            return self.bundles[slug]
        
        # Find active bundle path
        event_dir = self.storage_path / slug
        active_link = event_dir / "active"
        
        if not active_link.exists():
            raise FileNotFoundError(f"Active bundle not found for {slug}")
        
        bundle_path = active_link.resolve()
        
        # Load bundle
        bundle = EventBundle(slug, bundle_path)
        bundle.load()
        
        # Cache
        self.bundles[slug] = bundle
        
        return bundle
    
    def get_event(self, slug: str) -> Optional[EventBundle]:
        """Get cached event bundle"""
        return self.bundles.get(slug)
    
    def reload_event(self, slug: str):
        """Reload event bundle (after version switch)"""
        if slug in self.bundles:
            del self.bundles[slug]
        return self.load_event(slug)
    
    def unload_event(self, slug: str):
        """Unload event bundle from cache"""
        if slug in self.bundles:
            del self.bundles[slug]
            logger.info(f"Unloaded event: {slug}")
```

### 3. FastAPI Application (2 days)

File: `web_server/main.py`

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from web_server.config import settings
from web_server.services.event_loader import EventLoader
from web_server.api import public, admin, health
from web_server.middleware import LoggingMiddleware, RateLimitMiddleware

# Setup logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global event loader
event_loader: EventLoader = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global event_loader
    
    # Startup
    logger.info("Starting DaNang Vibes Web Server")
    logger.info(f"Storage path: {settings.storage_path}")
    
    # Initialize event loader
    event_loader = EventLoader(
        storage_path=settings.storage_path,
        server_db_path=settings.server_db_path
    )
    
    # Load published events
    event_loader.load_published_events()
    
    logger.info("✓ Server ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down server")

# Create FastAPI app
app = FastAPI(
    title="DaNang Vibes",
    description="Sports event photo discovery platform",
    version="0.1.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Static files
app.mount("/static", StaticFiles(directory="web_server/static"), name="static")

# Templates
templates = Jinja2Templates(directory="web_server/templates")

# Routes
app.include_router(health.router, tags=["health"])
app.include_router(public.router, tags=["public"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# Dependency injection
def get_event_loader() -> EventLoader:
    return event_loader

# Root route
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("public/index.html", {
        "request": request,
        "events": event_loader.bundles.values()
    })
```

### 4. Health Check (1 day)

File: `web_server/api/health.py`

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import psutil
import time
from web_server.services.event_loader import EventLoader
from web_server.main import get_event_loader

router = APIRouter()

start_time = time.time()

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: int
    memory_usage_mb: int
    disk_usage_gb: float
    active_events: int
    total_photos: int

@router.get("/health", response_model=HealthResponse)
async def health_check(event_loader: EventLoader = Depends(get_event_loader)):
    """Health check endpoint"""
    
    # Memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    # Disk usage
    disk = psutil.disk_usage('/')
    disk_gb = disk.used / 1024 / 1024 / 1024
    
    # Count photos
    total_photos = 0
    for bundle in event_loader.bundles.values():
        if bundle.manifest:
            total_photos += bundle.manifest.stats.total_photos
    
    return HealthResponse(
        status="healthy",
        uptime_seconds=int(time.time() - start_time),
        memory_usage_mb=int(memory_mb),
        disk_usage_gb=round(disk_gb, 2),
        active_events=len(event_loader.bundles),
        total_photos=total_photos
    )
```

### 5. Middleware (1 day)

File: `web_server/middleware.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration_ms}ms "
            f"ip={request.client.host}"
        )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting"""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Only rate limit specific endpoints
        if "/search/face" in request.url.path:
            limit = 5  # 5 requests
            window = 60  # per minute
        elif "/download" in request.url.path:
            limit = 20
            window = 60
        else:
            return await call_next(request)
        
        # Check rate limit
        ip = request.client.host
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)
        
        # Clean old requests
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[ip]) >= limit:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Record request
        self.requests[ip].append(now)
        
        return await call_next(request)
```

## Implementation Steps

1. **Setup project structure** (1 day)
2. **Implement configuration** (1 day)
3. **Implement EventLoader service** (2 days)
4. **Implement FastAPI app** (2 days)
5. **Implement health check** (1 day)
6. **Implement middleware** (1 day)
7. **Write unit tests** (2 days)
8. **Test with imported bundle** (1 day)

## Todo List

- [ ] Create project structure
- [ ] Implement configuration
- [ ] Implement EventBundle class
- [ ] Implement EventLoader service
- [ ] Implement FastAPI app with lifespan
- [ ] Implement health check endpoint
- [ ] Implement logging middleware
- [ ] Implement rate limiting middleware
- [ ] Setup static files and templates
- [ ] Write unit tests
- [ ] Test loading published events
- [ ] Test memory usage with multiple events

## Success Criteria

- [ ] Server starts in < 5s
- [ ] Published events loaded on startup
- [ ] Health check returns correct metrics
- [ ] Memory usage ≤ 4GB with 3 events loaded
- [ ] FAISS index accessible from routes
- [ ] SQLite queries work (read-only)
- [ ] Rate limiting works for selfie/download
- [ ] Graceful shutdown works
- [ ] Type checking passes: `mypy web_server/`
- [ ] Tests pass: `pytest tests/test_web_server/ -v`

## Risk Assessment

- **Medium:** Memory usage too high with many events → lazy load events on first access
- **Low:** FAISS thread safety issues → use locks if needed
- **Low:** SQLite connection pool exhaustion → tune pool size

## Security Considerations

- Admin routes protected by bearer token
- Rate limiting on expensive endpoints
- Input validation on all endpoints
- No sensitive data in logs
- CORS configured properly

## Next Steps

After web server core works, proceed to Phase 05 (Public Search & Download UI).

## Unresolved Questions

- Should events be lazy-loaded or all loaded on startup? → Load published events on startup
- Should we use Redis for rate limiting? → NO for MVP (in-memory OK)
