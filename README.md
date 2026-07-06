# CSV Appender — CI/CD Pipeline

A minimal but production-shaped pipeline that appends a single row to a CSV
file in this repo every time it runs. Built with **Python**, **Jenkins**,
and **GitHub**.

```
+----------------+      +-----------+      +-----------------+
| Build w/ params| ---> |  Jenkins  | ---> | GitHub repo     |
| (Jenkins UI)   |      | pipeline  |      | (CSV updated)   |
+----------------+      +-----------+      +-----------------+
                              |
                              v
                       append_to_csv.py
                       (Python stdlib)
```

## Repo layout

```
.
├── append_to_csv.py      # Python script: appends one row
├── Jenkinsfile           # Declarative pipeline
├── requirements.txt      # Empty (stdlib only). See comment for pandas.
├── data/
│   └── metrics.csv       # Sample CSV with header (delete to test creation)
└── README.md
```

## 1. Create a GitHub Personal Access Token (PAT)

1. GitHub -> **Settings -> Developer settings -> Personal access tokens
   -> Tokens (classic)**.
2. Click **Generate new token**.
3. Select scope: **`repo`** (full control of private repositories).
   *For organization repos* also enable `read:org` if required by SSO.
4. Copy the token. **You will not see it again.**

> If you prefer SSH, see the *Alternative: SSH key* section at the bottom.

## 2. Add the PAT to Jenkins

1. Jenkins -> **Manage Jenkins -> Credentials -> (global) -> Add Credentials**.
2. Fill in:
   * **Kind:** Username with password
   * **Username:** `csv-bot` (or your GitHub username)
   * **Password:** the PAT from step 1
   * **ID:** `github-pat`  ← must match `GITHUB_CREDENTIALS_ID` in the
     Jenkinsfile
   * **Description:** `GitHub PAT for CSV appender`
3. Click **Create**.

The token is stored encrypted in Jenkins' credentials store and is never
printed in build logs (the Jenkinsfile uses `withCredentials` to bind it to
short-lived env vars).

## 3. Create the Jenkins job

1. Jenkins -> **New Item -> Pipeline**.
2. Name: `csv-appender` (or anything you like).
3. Under **Pipeline**:
   * **Definition:** `Pipeline script from SCM`
   * **SCM:** `Git`
   * **Repository URL:** `https://github.com/<your-org>/<your-repo>.git`
   * **Credentials:** select `github-pat` (username + token)
   * **Branch Specifier:** `*/main` (or `*/master`)
4. Save.

## 4. (Optional) Add the GitHub webhook

1. GitHub repo -> **Settings -> Webhooks -> Add webhook**.
2. **Payload URL:** `http://<jenkins-host>/github-webhook/`
3. **Content type:** `application/json`
4. **Which events:** "Just the *push* event."
5. Save.

The Jenkinsfile declares `triggers { githubPush() }`, so a push to `main`
will queue a new run with default parameters.

## 5. Run it

### Manual run with parameters

1. Open the job -> **Build with Parameters**.
2. Fill in the `FIELD_*` values (any subset is allowed; the script maps the
   parameters into the column names).
3. Click **Build**.

The pipeline will:
1. Clone the repo at the chosen branch.
2. Run `python append_to_csv.py --file <CSV_FILE> --field …`.
3. Stage the updated CSV.
4. Commit & push the change back to the same branch as `csv-bot`.

### Local smoke test

```bash
python append_to_csv.py \
    --file data/metrics.csv \
    --field timestamp=2026-07-06T10:00:00Z \
    --field service=api-gateway \
    --field status=200 \
    --field latency_ms=42
```

You should see `[OK] Appended row to data/metrics.csv: {...}` and a new
line in the CSV.

## How credentials are handled (security notes)

* The PAT is stored in **Jenkins Credentials Provider**, encrypted with
  Jenkins' master key. It is **never** in the repo, the Jenkinsfile, or
  the build log.
* The Jenkinsfile uses the **`withCredentials`** step to bind the username
  and token to `GIT_USER` / `GIT_TOKEN` for the duration of one shell
  block. The `sed`-rewritten remote URL is **not** persisted to
  `git config`, so the secret does not leak into `.git/config`.
* The pipeline stages only the `--file` parameter (e.g. `data/metrics.csv`)
  with `git add`. It never runs `git add -A` or `git add .`, so unrelated
  workspace junk cannot end up in your repo.
* `cleanWs` runs in `post.always` to wipe the workspace, including the
  `.git` checkout, after every build.
* Branching is also constrained: the pipeline pushes back to
  `${BRANCH_NAME:-main}`, which is whatever was checked out. To lock it
  down further, add a `when { branch 'main' }` guard or use a
  branch-protection rule on GitHub requiring PR review for the `main`
  branch and have the bot push to a feature branch instead.

## Error handling

* **No field parameters provided** -> the build fails fast with a clear
  error message (no empty row is appended).
* **Missing values for required columns** -> the Python script lists the
  missing column names and exits with code 2; Jenkins marks the build red.
* **No changes in the CSV after the run** -> the commit step detects
  `git diff --cached --quiet` and skips the commit and push, logging
  "No changes detected… Skipping commit."
* **Push failure (auth, network, branch protection)** -> the shell exits
  non-zero; Jenkins marks the build red and the `post.failure` block fires.

## Alternative: SSH key instead of a PAT

1. Generate a dedicated keypair: `ssh-keygen -t ed25519 -C "csv-bot@example.com"`.
2. Add the public key to the bot GitHub account
   (**Settings -> SSH and GPG keys**).
3. In Jenkins, create a credential of kind **SSH Username with private key**,
   ID `github-ssh`, paste the private key.
4. In the `Checkout` stage of the Jenkinsfile change:
   * `userRemoteConfigs: [[ url: 'git@github.com:org/repo.git', credentialsId: 'github-ssh' ]]`
5. In the push step, switch the `REMOTE_URL` rewrite to plain `git push origin HEAD:${BRANCH_NAME:-main}` (no token needed).

## Customising the CSV

* **Different column names** — change the `FIELD_*` parameters in the
  Jenkinsfile, or pass arbitrary `--field name=value` pairs.
* **Different file path** — change the `CSV_FILE` parameter default.
* **Switch to pandas** — uncomment `pandas>=2.0` in `requirements.txt`
  and update `append_to_csv.py` to use `pd.concat([df, pd.DataFrame([row])])`.
  A pure-stdlib implementation is the default because it has zero install
  cost on the Jenkins agent.
