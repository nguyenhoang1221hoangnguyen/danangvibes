CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  date TEXT NOT NULL,
  location TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS photos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  filename TEXT NOT NULL,
  checksum TEXT UNIQUE NOT NULL,
  original_path TEXT,
  file_size INTEGER,
  width INTEGER,
  height INTEGER,
  capture_time TEXT,
  exif_data TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS thumbnails (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  photo_id INTEGER NOT NULL,
  path TEXT NOT NULL,
  width INTEGER,
  height INTEGER,
  file_size INTEGER,
  FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ocr_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  photo_id INTEGER NOT NULL,
  text TEXT NOT NULL,
  confidence REAL,
  bbox TEXT,
  is_bib INTEGER DEFAULT 0,
  manual_correction TEXT,
  corrected_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS faces (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  photo_id INTEGER NOT NULL,
  bbox TEXT,
  confidence REAL,
  faiss_vector_id INTEGER,
  embedding_model TEXT,
  embedding_model_version TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_photos_event ON photos(event_id);
CREATE INDEX IF NOT EXISTS idx_photos_checksum ON photos(checksum);
CREATE INDEX IF NOT EXISTS idx_photos_capture_time ON photos(capture_time);
CREATE INDEX IF NOT EXISTS idx_ocr_photo ON ocr_candidates(photo_id);
CREATE INDEX IF NOT EXISTS idx_ocr_text ON ocr_candidates(text);
CREATE INDEX IF NOT EXISTS idx_ocr_manual_correction ON ocr_candidates(manual_correction);
CREATE INDEX IF NOT EXISTS idx_ocr_is_bib ON ocr_candidates(is_bib);
CREATE INDEX IF NOT EXISTS idx_faces_photo ON faces(photo_id);
CREATE INDEX IF NOT EXISTS idx_faces_vector ON faces(faiss_vector_id);
