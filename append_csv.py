import csv
import os
import subprocess
from datetime import datetime

CSV_FILE = "data/metrics.csv"


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
        # 1. Set Git author identity for the Jenkins environment
        subprocess.run(
            ["git", "config", "user.name", "Jenkins CI"], check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "sanjeeva6268@gmail.com"], check=True
        )

        # 2. Get credentials injected by Jenkins
        github_user = os.environ.get("GITHUB_USER")
        github_pat = os.environ.get("GITHUB_PAT")

        # ⚠️ REPLACE THESE WITH YOUR ACTUAL GITHUB DETAILS
        repo_owner = "sanjeeva6268-oss"
        repo_name = "csvautomation"

        if github_user and github_pat:
            authenticated_url = f"https://{github_user}:{github_pat}@github.com/{repo_owner}/{repo_name}.git"
            subprocess.run(
                ["git", "remote", "set-url", "origin", authenticated_url],
                check=True,
            )

        # 3. Stage changes
        subprocess.run(["git", "add", CSV_FILE], check=True)

        # 4. Check status and commit
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )
        if status.stdout.strip():
            subprocess.run(
                ["git", "commit", "-m", "ci: update csv log file [skip ci]"],
                check=True,
            )
            subprocess.run(["git", "push", "origin", "HEAD:master"], check=True)
            print("Successfully pushed updated CSV to GitHub.")
        else:
            print("No changes detected.")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        raise
if __name__ == "__main__":
    append_data_row()
    git_commit_and_push()
