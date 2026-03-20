#!/usr/bin/env python3
"""One-time import of delivery reports from a fallback SQLite database into the main delivery database."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from delivery_app.config import load_settings
from delivery_app.report_recovery import import_reports_from_sqlite


def main() -> None:
    settings = load_settings()
    source_sqlite_path = Path(settings.source_sqlite_path).expanduser().resolve()
    if not source_sqlite_path.exists():
        raise SystemExit(
            "Source SQLite file not found. Set SOURCE_SQLITE_PATH to the fallback delivery_app.db you want to recover."
        )

    result = import_reports_from_sqlite(
        str(source_sqlite_path),
        settings.delivery_database_url,
    )
    print(
        "Recovered delivery reports: "
        f"{result['reports_imported']} imported, "
        f"{result['reports_skipped']} skipped, "
        f"{result['source_reports']} source reports scanned, "
        f"{result['users_imported']} users imported, "
        f"{result['customers_imported']} customers imported, "
        f"{result['locations_imported']} locations imported"
    )


if __name__ == "__main__":
    main()
