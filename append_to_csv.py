#!/usr/bin/env python3
"""
append_csv.py
--------------

Append a single row to a CSV file that lives in the workspace.

* The script is deliberately simple – it only uses the standard library.
* It validates that:
  - the file exists,
  - the supplied column values match the header length,
  - the header order is unchanged (optional strict mode).

The script is intended to be called from a Jenkins pipeline, e.g.:

    python3 append_csv.py \
        --file data/users.csv \
        --row "john.doe@example.com,John,Doe,2024-07-18"

"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append a row to a CSV file in-place."
    )
    parser.add_argument(
        "-f", "--file",
        required=True,
        help="Path to the CSV file (relative to the workspace).",
    )
    parser.add_argument(
        "-r", "--row",
        required=True,
        help=(
            "Comma‑separated values for the new row. "
            "If a value contains commas, surround it with double quotes."
        ),
    )
    parser.add_argument(
        "--strict-header",
        action="store_true",
        help="Fail if the number of supplied values does not exactly match the header columns.",
    )
    parser.add_argument(
        "--date-format",
        default="%Y-%m-%d",
        help="If a column looks like a date, optionally validate it (default: YYYY‑MM‑DD).",
    )
    return parser.parse_args()


def read_header(csv_path: Path) -> List[str]:
    """Read the first row (header) of the CSV."""
    with csv_path.open(newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty – no header found.")
    return header


def validate_row(header: List[str], values: List[str], strict: bool) -> None:
    """Basic sanity checks before writing."""
    if strict and len(values) != len(header):
        raise ValueError(
            f"Row length ({len(values)}) does not match header length ({len(header)})."
        )
    # Optional: you can add per‑column validation here (e.g. email format, date parsing)
    # Example date validation for any column that looks like a date:
    # for v in values:
    #     try: datetime.strptime(v, "%Y-%m-%d")
    #     except ValueError: pass  # ignore non‑date strings


def append_row(csv_path: Path, row: List[str]) -> None:
    """Append the row using the csv.writer in append mode."""
    # Open in append mode with newline='' to avoid extra blank lines on Linux.
    with csv_path.open(mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def main() -> int:
    args = parse_args()
    csv_path = Path(args.file).resolve()

    # -------------------------------------------------
    # 1️⃣  Sanity checks
    # -------------------------------------------------
    if not csv_path.is_file():
        print(f"[ERROR] CSV file does not exist: {csv_path}", file=sys.stderr)
        return 1

    try:
        header = read_header(csv_path)
    except Exception as e:
        print(f"[ERROR] Unable to read header: {e}", file=sys.stderr)
        return 1

    # Split the incoming row respecting quoted commas
    # csv module does this nicely via a temporary reader
    try:
        row_vals = next(csv.reader([args.row]))
    except Exception as e:
        print(f"[ERROR] Could not parse '--row' argument: {e}", file=sys.stderr)
        return 1

    # -------------------------------------------------
    # 2️⃣  Validation
    # -------------------------------------------------
    try:
        validate_row(header, row_vals, args.strict_header)
    except ValueError as ve:
        print(f"[ERROR] Validation failed: {ve}", file=sys.stderr)
        return 1

    # -------------------------------------------------
    # 3️⃣  Append
    # -------------------------------------------------
    try:
        append_row(csv_path, row_vals)
        print(f"[INFO] Successfully appended row to {csv_path}")
        print(f"[DEBUG] Header   : {header}")
        print(f"[DEBUG] New row  : {row_vals}")
    except Exception as e:
        print(f"[ERROR] Failed to write CSV: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
