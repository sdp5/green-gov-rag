#!/usr/bin/env python3
"""Helper script to review and manually download failed URLs.

This script reads the failed_downloads.txt log file and provides
guidance on how to manually download protected URLs.
"""

from __future__ import annotations

import sys
from pathlib import Path

from green_gov_rag.types import FAILED_DOWNLOADS_FILENAME

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

LOG_DIR = backend_dir / "logs"
FAILED_URLS_FILE = LOG_DIR / FAILED_DOWNLOADS_FILENAME


def review_failed_downloads() -> None:
    """Review failed download URLs and provide manual download instructions."""
    if not FAILED_URLS_FILE.exists():
        print("✅ No failed downloads found!")
        print(f"   (checked {FAILED_URLS_FILE})")
        return

    print("📋 Failed Downloads Review")
    print("=" * 80)
    print()

    with open(FAILED_URLS_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        print("✅ No failed downloads found!")
        return

    print(f"Found {len(lines)} failed download(s):\n")

    for i, line in enumerate(lines, 1):
        parts = line.strip().split(" | ")
        if len(parts) == 3:
            timestamp, url, title = parts
            print(f"{i}. {title}")
            print(f"   URL: {url}")
            print(f"   Time: {timestamp}")
            print()

    print("\n" + "=" * 80)
    print("💡 Manual Download Instructions:")
    print("=" * 80)
    print()
    print("1. Open each URL in your browser")
    print("2. Complete any CAPTCHA challenges")
    print(f"3. Save the downloaded file to: {backend_dir / 'data' / 'raw'}")
    print("4. Re-run the ingestion command:")
    print("   python -m green_gov_rag.cli etl ingest")
    print()
    print("Alternative: Use cloudscraper or Playwright for automated downloads")
    print("  pip install cloudscraper")
    print("  pip install playwright && playwright install")
    print()


def clear_failed_downloads() -> None:
    """Clear the failed downloads log."""
    if FAILED_URLS_FILE.exists():
        FAILED_URLS_FILE.unlink()
        print(f"✅ Cleared {FAILED_URLS_FILE}")
    else:
        print("No failed downloads file to clear")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Review failed document downloads")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the failed downloads log",
    )

    args = parser.parse_args()

    if args.clear:
        clear_failed_downloads()
    else:
        review_failed_downloads()
