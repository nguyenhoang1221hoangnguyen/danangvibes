CREATE TABLE IF NOT EXISTS server_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  active_version TEXT,
  is_published INTEGER DEFAULT 0,
  storage_path TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_slug TEXT NOT NULL,
  version TEXT NOT NULL,
  bundle_path TEXT NOT NULL,
  imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
  manifest_checksum TEXT,
  UNIQUE(event_slug, version),
  FOREIGN KEY (event_slug) REFERENCES server_events(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS donation_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_slug TEXT UNIQUE NOT NULL,
  qr_code_path TEXT,
  message TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_slug) REFERENCES server_events(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS download_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_slug TEXT NOT NULL,
  photo_id INTEGER NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_downloads_event ON download_logs(event_slug);
CREATE INDEX IF NOT EXISTS idx_downloads_photo ON download_logs(photo_id);
