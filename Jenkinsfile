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
        // (ansiColor is intentionally NOT in `options` -- it's a `wrap` step
        //  that requires the AnsiColor plugin. The default console output is
        //  fine; install the plugin and wrap the `sh` blocks if you want
        //  color in the logs.)
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
                bat '''
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
                    // NOTE: cmd.exe needs the args joined into a single line.
                    def fieldsJoined = fieldArgs.join(' ')
                    bat """
                        python append_to_csv.py --file "${params.CSV_FILE}" ${fieldsJoined}
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
                    bat '''
                        @echo off
                        setlocal EnableDelayedExpansion

                        rem --- Identify the author/committer for the bot.
                        git config user.name  "%COMMIT_AUTHOR_NAME%"
                        git config user.email "%COMMIT_AUTHOR_EMAIL%"

                        rem --- Stage the CSV file specifically -- never `git add -A`,
                        rem     which would risk committing unrelated workspace changes.
                        git add "%CSV_FILE%"

                        rem --- Detect whether the file actually changed. If not, skip
                        rem     the commit/push to avoid an empty commit and a wasted
                        rem     API call.
                        git diff --cached --quiet
                        if %ERRORLEVEL% EQU 0 (
                            echo No changes detected in %CSV_FILE%. Skipping commit.
                            exit /b 0
                        )

                        rem --- Build the commit message. Use a temp file so embedded
                        rem     newlines and special characters survive intact.
                        set "MSG_FILE=%TEMP%\\csv-commit-msg.txt"
                        (
                            echo chore(data^): append row to %CSV_FILE%
                            echo.
                            echo Build:    %BUILD_URL%
                            echo Run id:   %BUILD_ID%
                            echo Author:   %COMMIT_AUTHOR_NAME%
                        ) > "%MSG_FILE%"

                        git commit -F "%MSG_FILE%"
                        del "%MSG_FILE%"

                        rem --- Rewrite the remote URL to embed the token so the push
                        rem     authenticates non-interactively. The URL is scoped to
                        rem     this command block -- never persisted to .git/config.
                        for /f "delims=" %%U in ('git config --get remote.origin.url') do set "REMOTE_URL=%%U"
                        set "AUTH_URL=https://%GIT_USER%:%GIT_TOKEN%@!REMOTE_URL:https://=!"

                        rem --- Push back to the same branch we built from.
                        set "BRANCH=%BRANCH_NAME%"
                        if "!BRANCH!"=="" set "BRANCH=main"
                        git push "%AUTH_URL%" "HEAD:!BRANCH!"
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
            // Wrapped in try/catch in case the Workspace Cleanup plugin is
            // not installed on this Jenkins instance.
            script {
                try {
                    cleanWs(deleteDirs: true,
                            patterns: [[pattern: '.git/**', type: 'INCLUDE']])
                } catch (NoSuchMethodError | MissingMethodException ignored) {
                    echo "Workspace Cleanup plugin not installed; skipping cleanWs."
                }
            }
        }
    }
}
