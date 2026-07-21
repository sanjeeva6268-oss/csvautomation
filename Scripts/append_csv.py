#!/usr/bin/env python3
"""
append_csv.py
-------------
Append a new row to data/my_data.csv, commit the change, and push to GitHub.

Usage (CLI):
    python append_csv.py --col1 VALUE1 --col2 VALUE2 ...

Or via environment variables:
    COL1=VALUE1 COL2=VALUE2 python append_csv.py
"""

import os
import sys
import argparse
import datetime
from pathlib import Path

import pandas as pd
from git import Repo, GitCommandError
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# 1️⃣ Load env (Git credentials, optional)
# ----------------------------------------------------------------------
load_dotenv()  # reads .env if present

# ----------------------------------------------------------------------
# 2️⃣ Configurable constants (feel free to move to a config file)
# ----------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]               # my‑csv‑updater/
CSV_PATH = REPO_ROOT / "data" / "metrics.csv"
BRANCH = os.getenv("GIT_BRANCH", "main")                     # target branch
COMMIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "ci-bot")
COMMIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "ci@example.com")
REMOTE_NAME = "origin"

# ----------------------------------------------------------------------
# 3️⃣ Parse incoming row data
# ----------------------------------------------------------------------
def parse_cli():
    parser = argparse.ArgumentParser(description="Append a row to the CSV.")
    # Define as many columns as you need; for demo we use generic col1…col5
    for i in range(1, 6):
        parser.add_argument(f"--col{i}", required=False, help=f"Value for column {i}")
    args = parser.parse_args()
    # Build dict of non‑None values
    row = {f"col{i}": getattr(args, f"col{i}") for i in range(1, 6) if getattr(args, f"col{i}") is not None}
    return row

def parse_env():
    """Read COL1, COL2 … from environment (overrides CLI if present)."""
    row = {}
    for i in range(1, 6):
        val = os.getenv(f"COL{i}")
        if val is not None:
            row[f"col{i}"] = val
    return row

def build_row():
    # precedence: env > CLI > auto‑generated timestamp column
    row = parse_cli()
    env_row = parse_env()
    row.update(env_row)  # env overwrites CLI if set
    # Add a timestamp column if you like
    row.setdefault("timestamp", datetime.datetime.utcnow().isoformat())
    return row

# ----------------------------------------------------------------------
# 4️⃣ CSV handling
# ----------------------------------------------------------------------
def load_or_create_csv(path: Path) -> pd.DataFrame:
    if path.is_file():
        df = pd.read_csv(path, dtype=str)  # keep everything as string to avoid dtype drift
    else:
        # No file yet → start with an empty DataFrame
        df = pd.DataFrame()
    return df

def append_row_to_csv(csv_path: Path, row: dict):
    df = load_or_create_csv(csv_path)
    # Ensure all columns exist
    for col in row.keys():
        if col not in df.columns:
            df[col] = pd.NA
    # Append
    df = df.append(row, ignore_index=True)  # pandas < 2.0
    # For pandas >= 2.0 you can use:
    # df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    # Write back (no index column)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return csv_path

# ----------------------------------------------------------------------
# 5️⃣ Git operations
# ----------------------------------------------------------------------
def git_commit_and_push(repo_path: Path, file_path: Path, branch: str):
    repo = Repo(repo_path)
    git = repo.git

    # Make sure we are on the correct branch
    try:
        repo.git.checkout(branch)
    except GitCommandError as e:
        # If the branch does not exist locally, try to create tracking branch
        repo.git.checkout("-b", branch, f"{REMOTE_NAME}/{branch}")

    # Stage the CSV
    repo.index.add([str(file_path.relative_to(repo_path))])

    # Check if there is anything to commit (skip empty commits)
    if repo.is_dirty(untracked_files=False):
        commit_message = f"CI: Append row to {file_path.name} – {datetime.datetime.utcnow().isoformat()}Z"
        repo.index.commit(
            commit_message,
            author=repo.config_reader().get_value("user", "name", fallback=COMMIT_AUTHOR_NAME),
            author_email=repo.config_reader().get_value("user", "email", fallback=COMMIT_AUTHOR_EMAIL),
        )
        # Push – use credentials that Jenkins injects (see §3)
        try:
            git.push(REMOTE_NAME, branch)
        except GitCommandError as e:
            print(f"❌ Push failed: {e}", file=sys.stderr)
            sys.exit(1)
        print("✅ Commit & push successful")
    else:
        print("ℹ️ No changes detected – nothing to commit")

# ----------------------------------------------------------------------
# 6️⃣ Main orchestration
# ----------------------------------------------------------------------
def main():
    row = build_row()
    if not row:
        print("❌ No data supplied (neither CLI nor env). Exiting.")
        sys.exit(1)

    print(f"🗂️  Appending row: {row}")
    append_row_to_csv(CSV_PATH, row)

    # Repo root is two levels up from this script (project root)
    git_commit_and_push(REPO_ROOT, CSV_PATH, BRANCH)

if __name__ == "__main__":
    main()
