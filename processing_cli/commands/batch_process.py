from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from processing_cli.commands.process import run as process_run


def batch_process(
    batch_config_path: Path,
    output: Path,
    skip_ocr: bool,
    skip_faces: bool,
    force: bool,
    config_path: Path,
) -> None:
    """
    Batch process multiple event folders from a JSON config file.

    Config format:
    {
      "events": [
        {
          "source_path": "/path/to/event1",
          "event_slug": "event-1",
          "event_name": "Event 1",
          "event_date": "2026-05-01",
          "event_location": "Da Nang"
        },
        ...
      ]
    }
    """
    if not batch_config_path.exists():
        raise FileNotFoundError(f"Batch config not found: {batch_config_path}")

    config_data = json.loads(batch_config_path.read_text(encoding="utf-8"))
    events = config_data.get("events", [])

    if not events:
        print("No events found in batch config")
        return

    print(f"Found {len(events)} events to process")
    print(f"Skip OCR: {skip_ocr}, Skip Faces: {skip_faces}")
    print("-" * 60)

    results = []
    total_start = time.time()

    for idx, event in enumerate(events, start=1):
        source_path = Path(event["source_path"]).expanduser().resolve()
        event_slug = event["event_slug"]
        event_name = event["event_name"]
        event_date = event["event_date"]
        event_location = event.get("event_location")

        print(f"\n[{idx}/{len(events)}] Processing: {event_name} ({event_slug})")
        print(f"  Source: {source_path}")

        if not source_path.exists():
            print("  ❌ SKIP: Source path does not exist")
            results.append({"event": event_slug, "status": "skipped", "reason": "source not found"})
            continue

        event_start = time.time()
        try:
            process_run(
                source=source_path,
                event_slug=event_slug,
                event_name=event_name,
                event_date=event_date,
                event_location=event_location,
                output=output,
                skip_ocr=skip_ocr,
                skip_faces=skip_faces,
                force=force,
                config_path=config_path,
                isolate_ai_stages=False,  # Run in same process for batch
            )
            event_elapsed = time.time() - event_start
            print(f"  ✅ SUCCESS in {event_elapsed:.1f}s")
            results.append({"event": event_slug, "status": "success", "time": event_elapsed})
        except Exception as exc:
            event_elapsed = time.time() - event_start
            print(f"  ❌ FAILED in {event_elapsed:.1f}s: {exc}")
            results.append({"event": event_slug, "status": "failed", "error": str(exc), "time": event_elapsed})

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")

    print(f"Total events: {len(events)}")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  ⏭️  Skipped: {skipped_count}")
    print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes)")

    if failed_count > 0:
        print("\nFailed events:")
        for r in results:
            if r["status"] == "failed":
                print(f"  - {r['event']}: {r.get('error', 'unknown error')}")

    # Save results
    results_path = output / "batch_results.json"
    results_path.write_text(
        json.dumps(
            {
                "total": len(events),
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total_time_seconds": total_elapsed,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nResults saved to: {results_path}")


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("batch-process", help="Batch process multiple events from config file")
    parser.add_argument("--batch-config", required=True, type=Path, help="Path to batch config JSON file")
    parser.add_argument("--output", default=Path("dist/events"), type=Path, help="Output directory for all bundles")
    parser.add_argument("--config", default=Path(__file__).resolve().parents[1] / "config.yaml", type=Path)
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR processing (faster)")
    parser.add_argument("--skip-faces", action="store_true", help="Skip face detection")
    parser.add_argument("--force", action="store_true", help="Force rebuild existing bundles")
    parser.set_defaults(
        handler=lambda args: batch_process(
            args.batch_config,
            args.output,
            args.skip_ocr,
            args.skip_faces,
            args.force,
            args.config,
        )
    )
