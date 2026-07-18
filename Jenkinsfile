pipeline {
    agent any                     // any Linux agent with Python3 & git

    /*----------------------------------------------------
      1️⃣  PARAMETERS – supplied at build time (or via webhook)
      ----------------------------------------------------*/
    parameters {
        string(name: 'CSV_PATH', defaultValue: 'data/users.csv',
               description: 'Path to the CSV file inside the repo (relative to workspace).')
        string(name: 'ROW_VALUES', defaultValue: '',
               description: 'New row to append – CSV escaped (e.g. "john@example.com,John,Doe,2024-07-18").')
        booleanParam(name: 'STRICT_HEADER', defaultValue: true,
                      description: 'Fail if row column count does not match CSV header.')
    }

    /*----------------------------------------------------
      2️⃣  ENV – keep the GitHub PAT out of the script
      ----------------------------------------------------*/
    environment {
        // The credential ID you will create in Jenkins (see setup instructions)
        GITHUB_TOKEN = credentials('github-pat-jenkins')   // type: Secret Text
        // Optional: use a separate user‑email / name for the commit
        GIT_AUTHOR_NAME  = 'jenkins-bot'
        GIT_AUTHOR_EMAIL = 'jenkins-bot@example.com'
    }

    /*----------------------------------------------------
      3️⃣  OPTIONS
      ----------------------------------------------------*/
    options {
        timestamps()                     // nice timestamps in console output
        timeout(time: 15, unit: 'MINUTES')
        ansiColor('xterm')               // colourised logs (optional)
        // Prevent concurrent builds on the same branch to avoid race conditions
        disableConcurrentBuilds()
    }

    stages {

        /*----------------------------------------------------
          4️⃣  CHECKOUT – clone the repo (shallow is fine)
          ----------------------------------------------------*/
        stage('Checkout') {
            steps {
                // The repo URL can be a parameter if you have multiple repos
                git url: 'https://github.com/your‑org/your‑repo.git',
                    credentialsId: env.GITHUB_TOKEN,
                    branch: 'main'    // or a specific branch / tag
            }
        }

        /*----------------------------------------------------
          5️⃣  SETUP – ensure a clean Python venv
          ----------------------------------------------------*/
        stage('Setup Python') {
            steps {
                // Install virtualenv if not present (once per agent)
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet --upgrade pip
                '''
            }
        }

        /*----------------------------------------------------
          6️⃣  RUN APPEND SCRIPT
          ----------------------------------------------------*/
        stage('Append row to CSV') {
            steps {
                // Activate venv and run the script
                sh '''
                    . .venv/bin/activate
                    python3 scripts/append_csv.py \
                        --file "${CSV_PATH}" \
                        --row "${ROW_VALUES}" \
                        ${STRICT_HEADER ? "--strict-header" : ""} \
                        || exit 1
                '''
            }
        }

        /*----------------------------------------------------
          7️⃣  GIT COMMIT & PUSH
          ----------------------------------------------------*/
        stage('Commit & Push') {
            steps {
                // All git commands run inside the workspace
                sh '''
                    set -euo pipefail

                    # Configure user for this repo only (won’t affect global config)
                    git config user.name "${GIT_AUTHOR_NAME}"
                    git config user.email "${GIT_AUTHOR_EMAIL}"

                    # Create a temporary branch to avoid contaminating main in case of failure
                    TEMP_BRANCH="ci/append-${BUILD_NUMBER}-${BUILD_ID}"
                    git checkout -b "${TEMP_BRANCH}"

                    # Add & commit only the CSV (or the whole repo if you prefer)
                    git add "${CSV_PATH}"
                    git commit -m "ci: append row via Jenkins #${BUILD_NUMBER}"
                    
                    # Push the temporary branch back to GitHub using the PAT
                    git push -u origin "${TEMP_BRANCH}"
                '''
            }
        }

        /*----------------------------------------------------
          8️⃣  OPTIONAL: Create a Pull Request (GitHub CLI)
          ----------------------------------------------------*/
        stage('Create PR (optional)') {
            when {
                expression { return true }   // set to false if you don’t want a PR
            }
            steps {
                // The GitHub CLI (gh) must be installed on the agent.
                // You can also use the GitHub API via curl if you prefer.
                sh '''
                    # Install gh if missing (Debian/Ubuntu example)
                    if ! command -v gh >/dev/null 2>&1; then
                        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
                            | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
                        sudo apt-add-repository https://cli.github.com/packages
                        sudo apt-get update
                        sudo apt-get install -y gh
                    fi

                    # Authenticate gh with the PAT (no interactive prompt)
                    echo "${GITHUB_TOKEN}" | gh auth login --with-token

                    # Create PR from the temp branch into the target branch (main)
                    gh pr create \
                        --title "ci: Append row to ${CSV_PATH}" \
                        --body "Automated change from Jenkins build #${BUILD_NUMBER}" \
                        --base main \
                        --head "${TEMP_BRANCH}" \
                        --label "ci" \
                        --assignee "${GIT_AUTHOR_NAME}"
                '''
            }
        }
    }

    post {
        /*----------------------------------------------------
          9️⃣  CLEAN‑UP – delete temp branch locally (optional)
          ----------------------------------------------------*/
        always {
            sh '''
                git checkout main || true
                git branch -D "ci/append-${BUILD_NUMBER}-${BUILD_ID}" || true
            '''
        }

        success {
            echo "✅ CSV updated and changes pushed successfully."
        }

        failure {
            echo "❌ Something went wrong – see the console output above."
        }
    }
}
