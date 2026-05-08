# Phase 03: Bundle Import & Export Workflow

## Context Links

- Phase 01: `phase-01-shared-foundation-bundle-schema.md`
- Phase 02: `phase-02-processing-app-m1.md`
- Architecture: `ARCHITECTURE.md`

## Overview

**Priority:** High  
**Status:** Planned  
**Goal:** Implement the operational bridge between Processing App (M1) and Web Server (MacBook 2017): export, transfer, import, verify, and version management.

## Requirements

### Functional

**Processing App (M1):**
- Export bundle to portable directory
- Generate originals mapping (if not copying originals)
- Compute bundle checksums
- Optional: compress bundle to zip

**Web Server (MacBook 2017):**
- Import bundle from incoming directory
- Validate bundle integrity
- Copy/move to versioned storage
- Switch active version pointer
- Rollback to previous version
- List available versions

### Non-Functional

- Import must be atomic (incomplete import not visible)
- Paths must be relative where possible
- Support multiple bundle versions per event
- Rollback must be instant (symlink switch)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ MacBook M1 (Processing)                                     │
│                                                              │
│  processing_cli export                                      │
│    ↓                                                         │
│  dist/events/ironman-danang-2026/                           │
│    ├── manifest.json                                        │
│    ├── event.db                                             │
│    ├── faiss.index                                          │
│    ├── thumbnails/                                          │
│    └── originals_mapping.json                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
        [Copy via SSD/rsync/AirDrop]
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ MacBook Pro 2017 (Serving)                                  │
│                                                              │
│  /Volumes/SSD/incoming/ironman-danang-2026/                 │
│    ↓                                                         │
│  web_server import                                          │
│    ↓                                                         │
│  /Volumes/SSD/events/                                       │
│    ├── ironman-danang-2026/                                 │
│    │   ├── releases/                                        │
│    │   │   ├── v1/  (imported bundle)                       │
│    │   │   └── v2/  (updated bundle)                        │
│    │   ├── active -> releases/v2  (symlink)                 │
│    │   └── originals/  (if copied)                          │
│    └── server.db  (server metadata)                         │
└─────────────────────────────────────────────────────────────┘
```

## Bundle Storage Structure

```
/Volumes/SSD/events/
├── ironman-danang-2026/
│   ├── releases/
│   │   ├── v1/
│   │   │   ├── manifest.json
│   │   │   ├── event.db
│   │   │   ├── faiss.index
│   │   │   ├── thumbnails/
│   │   │   └── originals_mapping.json
│   │   └── v2/
│   │       └── ... (same structure)
│   ├── active -> releases/v2  (symlink to active version)
│   └── originals/  (optional: shared across versions)
│       ├── IMG_1234.JPG
│       └── ...
├── marathon-danang-2026/
│   └── ...
└── server.db  (server-level metadata)
```

## Server Database Schema

File: `web_server/server_schema.sql`

```sql
-- Server-level event registry
CREATE TABLE server_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  active_version TEXT,  -- e.g., "v2"
  is_published BOOLEAN DEFAULT 0,
  storage_path TEXT NOT NULL,  -- e.g., "/Volumes/SSD/events/ironman-danang-2026"
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Version history
CREATE TABLE event_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_slug TEXT NOT NULL,
  version TEXT NOT NULL,  -- e.g., "v1", "v2"
  bundle_path TEXT NOT NULL,
  imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  imported_by TEXT,
  manifest_checksum TEXT,
  UNIQUE(event_slug, version),
  FOREIGN KEY (event_slug) REFERENCES server_events(slug) ON DELETE CASCADE
);

-- Donation config (per event)
CREATE TABLE donation_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_slug TEXT UNIQUE NOT NULL,
  qr_code_path TEXT,
  message TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_slug) REFERENCES server_events(slug) ON DELETE CASCADE
);

-- Download tracking (optional analytics)
CREATE TABLE download_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_slug TEXT NOT NULL,
  photo_id INTEGER NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_downloads_event ON download_logs(event_slug);
CREATE INDEX idx_downloads_photo ON download_logs(photo_id);
```

## CLI Commands

### Processing App (M1)

#### Export Bundle

```bash
python -m processing_cli export \
  --bundle ./dist/events/ironman-danang-2026 \
  --output ./exports/ironman-danang-2026.zip \
  --compress
```

**Options:**
- `--bundle`: Path to processed bundle (required)
- `--output`: Output path (optional, default: same as bundle)
- `--compress`: Create zip file (optional)
- `--include-originals`: Copy originals into bundle (optional, default: false)

**Output:**
- If `--compress`: `ironman-danang-2026.zip`
- Else: `ironman-danang-2026/` directory ready to copy

### Web Server (MacBook 2017)

#### Import Bundle

```bash
python -m web_server import \
  --bundle /Volumes/SSD/incoming/ironman-danang-2026 \
  --storage-path /Volumes/SSD/events \
  --version v1
```

**Options:**
- `--bundle`: Path to incoming bundle (required)
- `--storage-path`: Base storage path (required)
- `--version`: Version identifier (optional, auto-increment if not provided)
- `--originals-path`: Path to originals if using mapping (optional)

**Workflow:**
1. Validate manifest.json
2. Validate event.db schema
3. Validate faiss.index
4. Check thumbnails exist
5. If originals_mapping.json exists, verify originals accessible
6. Create `{storage-path}/{event-slug}/releases/{version}/`
7. Copy bundle files
8. Register in server.db
9. Create `active` symlink if first version

#### Publish Event

```bash
python -m web_server publish \
  --event-slug ironman-danang-2026
```

**Effect:** Set `is_published=1` in server.db → event visible on public site

#### Unpublish Event

```bash
python -m web_server unpublish \
  --event-slug ironman-danang-2026
```

**Effect:** Set `is_published=0` → event hidden from public

#### Switch Version

```bash
python -m web_server switch-version \
  --event-slug ironman-danang-2026 \
  --version v2
```

**Effect:** Update `active` symlink to point to `releases/v2`

#### Rollback

```bash
python -m web_server rollback \
  --event-slug ironman-danang-2026 \
  --version v1
```

**Effect:** Same as switch-version, but implies reverting to previous version

#### List Versions

```bash
python -m web_server list-versions \
  --event-slug ironman-danang-2026
```

**Output:**
```
Event: ironman-danang-2026
Active: v2
Published: Yes

Versions:
  v1 - Imported: 2026-05-10 10:30:00
  v2 - Imported: 2026-05-12 14:20:00 (active)
```

## Transfer Methods

### Option A: External SSD (Recommended)

**On M1:**
```bash
# Copy bundle to external SSD
cp -r ./dist/events/ironman-danang-2026 /Volumes/ExternalSSD/bundles/
```

**On MacBook 2017:**
```bash
# Copy from external SSD to incoming
cp -r /Volumes/ExternalSSD/bundles/ironman-danang-2026 /Volumes/SSD/incoming/

# Import
python -m web_server import \
  --bundle /Volumes/SSD/incoming/ironman-danang-2026 \
  --storage-path /Volumes/SSD/events
```

### Option B: rsync over LAN

**On MacBook 2017:**
```bash
# Enable Remote Login (SSH)
# System Preferences → Sharing → Remote Login
```

**On M1:**
```bash
# Sync bundle to MacBook 2017
rsync -avz --progress \
  ./dist/events/ironman-danang-2026/ \
  admin@macbook2017.local:/Volumes/SSD/incoming/ironman-danang-2026/
```

### Option C: AirDrop (for small bundles < 5GB)

**On M1:**
```bash
# Compress bundle
cd ./dist/events
zip -r ironman-danang-2026.zip ironman-danang-2026/

# AirDrop to MacBook 2017
```

**On MacBook 2017:**
```bash
# Unzip
unzip ~/Downloads/ironman-danang-2026.zip -d /Volumes/SSD/incoming/
```

## Implementation Steps

### Step 1: Processing App Export Command (1 day)

```python
# processing_cli/commands/export.py
import click
import shutil
import zipfile
from pathlib import Path

@click.command()
@click.option('--bundle', required=True, type=click.Path(exists=True))
@click.option('--output', default=None)
@click.option('--compress', is_flag=True)
@click.option('--include-originals', is_flag=True)
def export(bundle, output, compress, include_originals):
    """Export bundle for transfer to server"""
    bundle_path = Path(bundle)
    
    if not output:
        output = bundle_path.parent / f"{bundle_path.name}.zip" if compress else bundle_path
    
    output_path = Path(output)
    
    if compress:
        # Create zip
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in bundle_path.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(bundle_path.parent))
        
        click.echo(f"Bundle exported to {output_path}")
    else:
        # Already in correct format
        click.echo(f"Bundle ready at {bundle_path}")
        click.echo("Transfer methods:")
        click.echo("  1. External SSD: cp -r {bundle_path} /Volumes/ExternalSSD/")
        click.echo("  2. rsync: rsync -avz {bundle_path}/ user@server:/path/")
        click.echo("  3. AirDrop: zip first, then AirDrop")
```

### Step 2: Web Server Import Command (2 days)

```python
# web_server/commands/import_bundle.py
import click
import shutil
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web_server.models import ServerEvent, EventVersion
from shared.models import BundleManifest

@click.command()
@click.option('--bundle', required=True, type=click.Path(exists=True))
@click.option('--storage-path', required=True, type=click.Path(exists=True))
@click.option('--version', default=None)
@click.option('--originals-path', default=None)
def import_bundle(bundle, storage_path, version, originals_path):
    """Import bundle into server storage"""
    bundle_path = Path(bundle)
    storage_path = Path(storage_path)
    
    # Load manifest
    manifest_path = bundle_path / 'manifest.json'
    if not manifest_path.exists():
        raise click.ClickException("manifest.json not found")
    
    with open(manifest_path) as f:
        manifest = BundleManifest.model_validate_json(f.read())
    
    event_slug = manifest.event.slug
    
    # Auto-increment version if not provided
    if not version:
        version = get_next_version(event_slug, storage_path)
    
    # Validate bundle
    validate_bundle(bundle_path, manifest)
    
    # Create storage structure
    event_dir = storage_path / event_slug
    releases_dir = event_dir / 'releases'
    version_dir = releases_dir / version
    
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy bundle files
    click.echo(f"Copying bundle to {version_dir}...")
    shutil.copytree(bundle_path, version_dir, dirs_exist_ok=True)
    
    # Handle originals
    if originals_path:
        originals_dir = event_dir / 'originals'
        originals_dir.mkdir(exist_ok=True)
        # Update originals_mapping.json with new base_path
        update_originals_mapping(version_dir, originals_dir)
    
    # Register in server database
    register_event_version(event_slug, version, version_dir, manifest)
    
    # Create/update active symlink if first version
    active_link = event_dir / 'active'
    if not active_link.exists():
        active_link.symlink_to(f'releases/{version}')
        click.echo(f"Created active symlink → {version}")
    
    click.echo(f"✓ Bundle imported: {event_slug} {version}")

def validate_bundle(bundle_path: Path, manifest: BundleManifest):
    """Validate bundle integrity"""
    # Check required files
    required = [
        bundle_path / manifest.files.database,
        bundle_path / manifest.files.faiss_index,
        bundle_path / manifest.files.thumbnails_dir
    ]
    
    for file in required:
        if not file.exists():
            raise click.ClickException(f"Missing required file: {file}")
    
    # Validate checksums
    for file, expected_checksum in manifest.checksums.items():
        file_path = bundle_path / file
        actual_checksum = compute_checksum(file_path)
        if actual_checksum != expected_checksum:
            raise click.ClickException(f"Checksum mismatch: {file}")
    
    click.echo("✓ Bundle validation passed")
```

### Step 3: Version Management Commands (1 day)

```python
# web_server/commands/version.py
import click
from pathlib import Path
from web_server.models import ServerEvent

@click.command()
@click.option('--event-slug', required=True)
@click.option('--version', required=True)
def switch_version(event_slug, version):
    """Switch active version"""
    event = get_event(event_slug)
    version_dir = Path(event.storage_path) / 'releases' / version
    
    if not version_dir.exists():
        raise click.ClickException(f"Version {version} not found")
    
    active_link = Path(event.storage_path) / 'active'
    active_link.unlink(missing_ok=True)
    active_link.symlink_to(f'releases/{version}')
    
    # Update database
    event.active_version = version
    session.commit()
    
    click.echo(f"✓ Switched to version {version}")

@click.command()
@click.option('--event-slug', required=True)
@click.option('--version', required=True)
def rollback(event_slug, version):
    """Rollback to previous version"""
    switch_version.invoke(click.Context(switch_version), 
                          event_slug=event_slug, version=version)
    click.echo(f"✓ Rolled back to {version}")
```

### Step 4: Publish/Unpublish Commands (1 day)

```python
# web_server/commands/publish.py
import click
from web_server.models import ServerEvent

@click.command()
@click.option('--event-slug', required=True)
def publish(event_slug):
    """Publish event to public"""
    event = get_event(event_slug)
    event.is_published = True
    session.commit()
    click.echo(f"✓ Event published: {event_slug}")

@click.command()
@click.option('--event-slug', required=True)
def unpublish(event_slug):
    """Unpublish event from public"""
    event = get_event(event_slug)
    event.is_published = False
    session.commit()
    click.echo(f"✓ Event unpublished: {event_slug}")
```

## Todo List

- [ ] Implement export command (processing_cli)
- [ ] Implement import command (web_server)
- [ ] Implement switch-version command
- [ ] Implement rollback command
- [ ] Implement publish/unpublish commands
- [ ] Implement list-versions command
- [ ] Create server database schema
- [ ] Write bundle validation logic
- [ ] Write originals mapping update logic
- [ ] Test full workflow: export → transfer → import
- [ ] Test version switching
- [ ] Test rollback
- [ ] Document transfer methods

## Success Criteria

- [ ] Bundle exported from M1 successfully
- [ ] Bundle transferred via SSD/rsync/AirDrop
- [ ] Bundle imported to MacBook 2017 without errors
- [ ] Active symlink points to correct version
- [ ] Version switching works instantly
- [ ] Rollback restores previous version
- [ ] Publish/unpublish toggles visibility
- [ ] Multiple versions coexist without conflicts

## Risk Assessment

- **Medium:** Large bundles slow to transfer → use rsync incremental sync
- **Low:** Symlink breaks across machines → test on both macOS versions
- **Low:** Partial import corrupts state → validate before moving to releases/

## Security Considerations

- Validate all paths to prevent path traversal
- Check bundle checksums before import
- Restrict import command to admin only
- Do not expose incoming/ directory publicly

## Next Steps

After import/export workflow works, proceed to Phase 04 (Web Server Core).

## Unresolved Questions

- Should we support automatic cleanup of old versions? → NO for MVP (manual cleanup)
- Should we support bundle compression by default? → NO (optional flag)
