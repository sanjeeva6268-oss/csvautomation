import csv
import os
import subprocess
from datetime import datetime

CSV_FILE = "data.csv"


def append_data_row():
    # Example data row: [Timestamp, Status, Source]
    new_row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "SUCCESS", "Jenkins-CI"]

    # Check if file exists to write headers if needed
    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Status", "Source"])  # Headers
        writer.writerow(new_row)

    print(f"Appended new row: {new_row}")


def git_commit_and_push():
    try:
        # Configure local git user for CI execution
        subprocess.run(
            ["git", "config", "user.name", "Jenkins CI"], check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "jenkins@example.com"], check=True
        )

        # Stage, commit, and push
        subprocess.run(["git", "add", CSV_FILE], check=True)

        # Check if there are changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )
        if status.stdout.strip():
            subprocess.run(
                ["git", "commit", "-m", "ci: update csv log file [skip ci]"],
                check=True,
            )
            # Push using origin HEAD to target current branch
            subprocess.run(["git", "push", "origin", "HEAD"], check=True)
            print("Successfully pushed updated CSV to GitHub.")
        else:
            print("No changes detected.")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        raise


if __name__ == "__main__":
    append_data_row()
    git_commit_and_push()
