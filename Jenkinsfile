// Jenkinsfile
// ----------------------------------------------------------------------------
// CI/CD pipeline that appends a new row to a CSV file in this repository.
//
// Trigger:    manual (with parameters) or webhook on push to `main`.
// Secrets:    `github-pat`  -- a Jenkins Credentials Provider entry of kind
//              "Username and password" (or "Secret text") holding a GitHub
//              Personal Access Token (PAT) with `repo` scope.
// Tooling:    Python 3.9+ available on the agent (PATH must include `python`
//              and `git`).
// ----------------------------------------------------------------------------

pipeline {
    agent any

    options {
        // Don't queue duplicate builds; cap the run history to keep the
        // Jenkins controller tidy.
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 10, unit: 'MINUTES')
        ansiColor('xterm')
    }

    // -----------------------------------------------------------------
    // Build parameters -- exposed in the "Build with Parameters" UI and
    // passed through to the Python script as --field arguments.
    // -----------------------------------------------------------------
    parameters {
        string(name: 'CSV_FILE',
               defaultValue: 'data/metrics.csv',
               description: 'Path to the CSV file inside the repo (relative path).')
        string(name: 'FIELD_TIMESTAMP',
               defaultValue: '',
               description: 'Value for the "timestamp" column (e.g. 2026-07-06T10:00:00Z).')
        string(name: 'FIELD_SERVICE',
               defaultValue: '',
               description: 'Value for the "service" column.')
        string(name: 'FIELD_STATUS',
               defaultValue: '',
               description: 'Value for the "status" column (e.g. 200, 500).')
        string(name: 'FIELD_LATENCY_MS',
               defaultValue: '',
               description: 'Value for the "latency_ms" column.')
        string(name: 'COMMIT_AUTHOR_NAME',
               defaultValue: 'csv-bot',
               description: 'Git author name for the auto-commit.')
        string(name: 'COMMIT_AUTHOR_EMAIL',
               defaultValue: 'csv-bot@example.com',
               description: 'Git author email for the auto-commit.')
    }

    // -----------------------------------------------------------------
    // Triggers -- this pipeline can be:
    //   * started manually with parameters, or
    //   * triggered by a GitHub webhook on push to `main`.
    //
    // The webhook URL is /github-webhook/ on the Jenkins controller and
    // the repository settings -> Webhooks should point at it.
    // -----------------------------------------------------------------
    triggers {
        githubPush()
    }

    environment {
        // Name of the credential in Jenkins Credentials Provider that holds
        // the GitHub Personal Access Token.
        GITHUB_CREDENTIALS_ID = 'github-pat'
    }

    stages {
        stage('Checkout') {
            steps {
                // Clone the repo. If `main` doesn't exist, fall back to `master`
                // so this works on older repos too.
                script {
                    def branch = env.BRANCH_NAME ?: 'main'
                    checkout([
                        $class           : 'GitSCM',
                        branches         : [[name: "*/${branch}"]],
                        userRemoteConfigs: [[
                            url          : scm.userRemoteConfigs[0].url,
                            credentialsId: env.GITHUB_CREDENTIALS_ID
                        ]]
                    ])
                }
            }
        }

        stage('Setup') {
            steps {
                // Sanity-check tooling before we touch anything.
                sh '''
                    set -eu
                    python --version
                    git --version
                '''
            }
        }

        stage('Append row to CSV') {
            steps {
                // Build the --field arguments from parameters only when the
                // operator actually provided values, so empty parameters
                // don't pollute the row.
                script {
                    def fieldArgs = []
                    ['FIELD_TIMESTAMP', 'FIELD_SERVICE', 'FIELD_STATUS', 'FIELD_LATENCY_MS'].each { p ->
                        def val = params[p]?.trim()
                        if (val) {
                            // Convert PARAM_FIELD_TIMESTAMP -> "timestamp"
                            def col = p.replace('FIELD_', '').toLowerCase()
                            fieldArgs << "--field ${col}=${val}"
                        }
                    }

                    if (fieldArgs.isEmpty()) {
                        error("No --field values were provided. At least one FIELD_* parameter must be set.")
                    }

                    // Run the Python script with the assembled flags.
                    sh """
                        set -eu
                        python append_to_csv.py \
                            --file "${params.CSV_FILE}" \
                            ${fieldArgs.join(' ')}
                    """
                }
            }
        }

        stage('Commit & push') {
            steps {
                // Configure git on the agent and push the updated CSV back to
                // the same branch. We use the PAT through the credential ID
                // so the secret never appears in the build log.
                withCredentials([usernamePassword(
                    credentialsId: env.GITHUB_CREDENTIALS_ID,
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_TOKEN'
                )]) {
                    sh '''
                        set -eu

                        # Identify the author/committer for the bot.
                        git config user.name  "${COMMIT_AUTHOR_NAME}"
                        git config user.email "${COMMIT_AUTHOR_EMAIL}"

                        # Stage the CSV file specifically -- never `git add -A`,
                        # which would risk committing unrelated workspace changes.
                        git add "${CSV_FILE}"

                        # Detect whether the file actually changed. If not, skip
                        # the commit/push to avoid an empty commit and a wasted
                        # API call.
                        if git diff --cached --quiet; then
                            echo "No changes detected in ${CSV_FILE}. Skipping commit."
                            exit 0
                        fi

                        COMMIT_MSG="chore(data): append row to ${CSV_FILE}

                        Build:    ${BUILD_URL}
                        Trigger:  ${BUILD_CAUSE}
                        Run id:   ${BUILD_ID}
                        Author:   ${COMMIT_AUTHOR_NAME}"

                        git commit -m "${COMMIT_MSG}"

                        # Rewrite the remote URL to embed the token so the push
                        # authenticates non-interactively. The URL is scoped to
                        # this command via an env-var-style substitution.
                        REMOTE_URL=$(git config --get remote.origin.url)
                        AUTH_URL=$(echo "${REMOTE_URL}" | sed "s#https://#https://${GIT_USER}:${GIT_TOKEN}@#")

                        # Push back to the same branch we built from.
                        git push "${AUTH_URL}" "HEAD:${BRANCH_NAME:-main}"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "CSV row appended and pushed successfully."
        }
        failure {
            // Surface a short message in the Jenkins UI; details are in the
            // console log. Hook a Slack/Email step here in production.
            echo "Pipeline failed. Check the console output for details."
        }
        always {
            // Clean up the workspace so secrets (and large CSVs) don't linger.
            cleanWs(deleteDirs: true,
                    patterns: [[pattern: '.git/**', type: 'INCLUDE']])
        }
    }
}
