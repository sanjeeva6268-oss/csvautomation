#!/usr/bin/env python3
"""
append_to_csv.py
----------------
Append a single new row to a CSV file in a Git repository.

Used by the Jenkins pipeline to safely add one record per run.

Features:
  * Dynamic row data via CLI args (--field name=value) or env vars.
  * Automatic header creation when the CSV does not yet exist.
  * Uses Python's standard `csv` library (no external deps required).
  * Validates that all provided values match the existing header columns.
  * Returns a non-zero exit code on failure (so Jenkins marks the build red).

Usage example:
    python append_to_csv.py \\
        --file data/metrics.csv \\
        --field timestamp="2026-07-06T10:00:00Z" \\
        --field service=api-gateway \\
        --field status=200 \\
        --field latency_ms=42
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_fields(pairs: List[str]) -> Dict[str, str]:
    """Parse a list of 'key=value' strings into a dict.

    Strips whitespace from both key and value. Raises SystemExit(2) if any
    argument is malformed so the Jenkins build fails fast with a clear error.
    """
    fields: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            print(
                f"[ERROR] Invalid --field argument: '{pair}'. "
                f"Expected format: key=value",
                file=sys.stderr,
            )
            sys.exit(2)
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            print(f"[ERROR] Empty key in --field argument: '{pair}'", file=sys.stderr)
            sys.exit(2)
        fields[key] = value
    return fields


def load_existing_header(csv_path: Path) -> List[str]:
    """Read the header row from an existing CSV file."""
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            # File exists but is empty — treat as no header.
            return []
    return [h.strip() for h in header]


def build_field_map(
    cli_fields: Dict[str, str],
    header: List[str],
    env: Dict[str, str],
) -> Dict[str, str]:
    """Merge CLI fields and environment variables into the final row.

    Precedence: CLI > environment. Missing values for required header
    columns raise a clear error so the operator knows what to fix.
    """
    merged: Dict[str, str] = {}
    # First, pull anything the operator passed on the CLI.
    merged.update(cli_fields)

    # Then fill in any blanks from environment variables (CSV_FIELD_<NAME>).
    for column in header:
        env_key = f"CSV_FIELD_{column.upper()}"
        if column not in merged and env_key in env and env[env_key]:
            merged[column] = env[env_key]

    # If there is no header yet, use the CLI keys as the header.
    if not header:
        return merged

    # Validate that all header columns are present.
    missing = [c for c in header if c not in merged]
    if missing:
        print(
            f"[ERROR] Missing values for required column(s): {', '.join(missing)}. "
            f"Pass them as --field {missing[0]}=<value> or set the "
            f"CSV_FIELD_{missing[0].upper()} environment variable.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Drop any extra keys not in the header (avoid silently misaligned rows).
    return {k: merged[k] for k in header}


def append_row(csv_path: Path, row: Dict[str, str], header: List[str]) -> None:
    """Append a single row to the CSV, creating the file if needed.

    Uses a temporary newline='' handle as recommended by the csv module
    docs to keep line endings consistent across platforms.
    """
    file_exists = csv_path.exists()
    needs_header = (not file_exists) or (not header)

    with csv_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a new row to a CSV file in a Git repository.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the CSV file (relative to the repo or absolute).",
    )
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Field to add to the new row. May be repeated. Example: status=200",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    csv_path = Path(args.file)
    cli_fields = parse_fields(args.field)

    try:
        if csv_path.exists() and csv_path.stat().st_size > 0:
            header = load_existing_header(csv_path)
        else:
            header = []

        # If we just created the file, the CLI fields define the header order.
        if not header:
            if not cli_fields:
                print(
                    "[ERROR] CSV does not exist and no --field arguments were given. "
                    "Provide at least one --field name=value to create the header.",
                    file=sys.stderr,
                )
                return 2
            header = list(cli_fields.keys())

        row = build_field_map(cli_fields, header, os.environ)
        append_row(csv_path, row, header)
    except OSError as exc:
        print(f"[ERROR] File I/O failure: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Appended row to {csv_path}: {row}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
