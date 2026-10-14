"""Download and cache all primary data sources locally.

Run this before ingestion to pre-fetch large files.
Respects rate limits; caches under data/raw/<source>/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cybersense.config import get_settings
from cybersense.logging import setup_logging
from cybersense.scripts_lib import SOURCES, get_loader_for_source


def main() -> None:
    settings = get_settings()
    setup_logging()
    print("Pre-caching data sources…")

    for source in SOURCES:
        if source in ("nvd", "owasp", "nist"):
            # These are either paginated (nvd) or require local files (owasp/nist)
            print(f"  {source}: skipped (run ingest directly, or place files in data/raw/{source}/)")
            continue
        try:
            loader = get_loader_for_source(source, settings)
            count = sum(1 for _ in loader.load(limit=1))  # just triggers cache download
            print(f"  {source}: cached ✓")
        except Exception as exc:
            print(f"  {source}: FAILED — {exc}")


if __name__ == "__main__":
    main()
