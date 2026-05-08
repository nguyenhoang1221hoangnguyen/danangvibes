#!/usr/bin/env python3
"""
Auto-generate batch config by scanning a root directory for photo folders.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


def count_jpegs(folder: Path) -> int:
    """Count JPG/JPEG files in folder (non-recursive)"""
    return sum(1 for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg"})


def extract_date_from_name(folder_name: str) -> str | None:
    """Try to extract date from folder name like '20260703 dapxe' or '2026-07-03'"""
    # Try YYYYMMDD format
    match = re.search(r"(\d{8})", folder_name)
    if match:
        date_str = match.group(1)
        try:
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            return f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            pass

    # Try YYYY-MM-DD format
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", folder_name)
    if match:
        return match.group(0)

    return None


def generate_slug(folder_name: str) -> str:
    """Generate event slug from folder name"""
    # Remove special chars, convert to lowercase, replace spaces with hyphens
    slug = re.sub(r"[^\w\s-]", "", folder_name.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def scan_and_generate_config(
    root_dir: Path,
    output_file: Path,
    min_photos: int = 10,
    recursive: bool = False,
) -> None:
    """
    Scan root directory for folders with photos and generate batch config.

    Args:
        root_dir: Root directory to scan
        output_file: Output JSON file path
        min_photos: Minimum number of photos to include folder
        recursive: Scan subdirectories recursively
    """
    if not root_dir.exists():
        raise FileNotFoundError(f"Root directory not found: {root_dir}")

    print(f"Scanning: {root_dir}")
    print(f"Recursive: {recursive}")
    print(f"Min photos: {min_photos}")
    print("-" * 60)

    events = []

    if recursive:
        folders = [p for p in root_dir.rglob("*") if p.is_dir()]
    else:
        folders = [p for p in root_dir.iterdir() if p.is_dir()]

    for folder in sorted(folders):
        jpeg_count = count_jpegs(folder)

        if jpeg_count < min_photos:
            continue

        folder_name = folder.name
        event_slug = generate_slug(folder_name)
        event_date = extract_date_from_name(folder_name) or date.today().isoformat()

        event = {
            "source_path": str(folder),
            "event_slug": event_slug,
            "event_name": folder_name,
            "event_date": event_date,
            "event_location": "Đà Nẵng",  # Default location
        }

        events.append(event)
        print(f"✓ {folder_name} ({jpeg_count} photos) → {event_slug}")

    if not events:
        print("\n⚠️  No folders with photos found")
        return

    config = {"events": events}

    output_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"Generated config with {len(events)} events")
    print(f"Saved to: {output_file}")
    print("\nNext steps:")
    print(f"  1. Review and edit: {output_file}")
    print(f"  2. Run batch processing:")
    print(f"     python -m processing_cli batch-process --batch-config {output_file} --skip-ocr")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-generate batch processing config")
    parser.add_argument("root_dir", type=Path, help="Root directory to scan for photo folders")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("batch-config.json"),
        help="Output config file (default: batch-config.json)",
    )
    parser.add_argument(
        "--min-photos",
        type=int,
        default=10,
        help="Minimum number of photos to include folder (default: 10)",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Scan subdirectories recursively",
    )

    args = parser.parse_args()

    try:
        scan_and_generate_config(args.root_dir, args.output, args.min_photos, args.recursive)
    except Exception as exc:
        print(f"Error: {exc}")
        exit(1)


if __name__ == "__main__":
    main()
