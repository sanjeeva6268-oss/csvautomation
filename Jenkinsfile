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
        string(name: 'PR_NUMBER',
               defaultValue: '',
               description: 'GitHub PR number (auto-set by the GitHub PR trigger). Leave blank for manual runs.')
        string(name: 'COMMIT_AUTHOR_NAME',
               defaultValue: 'csv-bot',
               description: 'Git author name for the auto-commit.')
        string(name: 'COMMIT_AUTHOR_EMAIL',
               defaultValue: 'csv-bot@example.com',
               description: 'Git author email for the auto-commit.')
    }

    // -----------------------------------------------------------------
    // Triggers -- this pipeline can be:
    //   * started manually with parameters (set PR_NUMBER + body), or
    //   * triggered automatically on a push to a branch.
    //
    // NOTE: `githubPush()` only fires on `push` events, NOT on pull-request
    // open/synchronize events. The runtime code below still accepts a
    // PR_NUMBER parameter and reads the PR title/body from the GitHub API
    // for *manual* runs, but it will NOT be invoked automatically when a
    // PR is opened -- to get that behaviour, run this as a multibranch
    // pipeline backed by the GitHub Branch Source plugin (which sets
    // CHANGE_ID / CHANGE_BRANCH / ghprbPullId on PR builds).
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
                // Use env.GIT_URL (always set when the build is tied to a
                // Git SCM) and fall back to scm.userRemoteConfigs[0].url for
                // older Jenkins versions that don't expose GIT_URL.
                script {
                    def branch = env.BRANCH_NAME ?: 'main'
                    def remoteUrl = env.GIT_URL ?: scm.userRemoteConfigs[0].url
                    checkout([
                        $class           : 'GitSCM',
                        branches         : [[name: "*/${branch}"]],
                        userRemoteConfigs: [[
                            url          : remoteUrl,
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
                // Two ways to get the row data:
                //   1. From a GitHub PR -- the PR title + body contain
                //      "key=value" lines that we forward to the Python script.
                //   2. From a manual "Build with Parameters" run, where the
                //      operator can also pass raw key=value lines via the
                //      PR_FIELDS_RAW parameter.
                withCredentials([usernamePassword(
                    credentialsId: env.GITHUB_CREDENTIALS_ID,
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_TOKEN'
                )]) {
                    script {
                        // Resolve which PR we should read from. PR_NUMBER is
                        // the canonical parameter; we also fall back to the
                        // ghprb* env vars that the GitHub Branch Source
                        // plugin sets automatically.
                        def prNumber = params.PR_NUMBER?.trim()
                        if (!prNumber) {
                            prNumber = env.ghprbPullId ?: env.CHANGE_ID ?: ''
                        }
                        if (!prNumber) {
                            error("No PR_NUMBER provided and no GitHub PR context detected. " +
                                  "Either set the PR_NUMBER parameter (Build with Parameters) " +
                                  "or open a PR to trigger this build via webhook.")
                        }

                        echo "Fetching PR #${prNumber} from ${env.GIT_URL_NAME ?: 'origin'}..."

                        // Fetch the PR's title + body via the GitHub REST API.
                        // The URL is the remote origin minus ".git".
                        // Note: don't include `@echo off` here -- in a `bat`
                        // step with `returnStdout: true`, the `@echo off` line
                        // itself gets emitted to stdout before it can take
                        // effect, which would corrupt the captured output.
                        def remoteUrl = bat(returnStdout: true, script: 'git config --get remote.origin.url').trim()
                        // Extract "<owner>/<repo>" from the remote URL. Examples:
                        //   https://github.com/sanjeeva6268-oss/csvautomation.git
                        //   git@github.com:sanjeeva6268-oss/csvautomation.git
                        // We use java.util.regex.Pattern explicitly (NOT Groovy
                        // slashy strings /.../ or ~/.../) to avoid a Groovy parser
                        // bug with character classes inside slashy regexes.
                        def ownerRepoRe1 = java.util.regex.Pattern.compile('^https?://github\\.com/([^/]+/[^/]+?)(?:\\.git)?$')
                        def m1 = ownerRepoRe1.matcher(remoteUrl)
                        def repoPath = m1.matches() ? m1.group(1) : null
                        if (repoPath == null) {
                            def ownerRepoRe2 = java.util.regex.Pattern.compile('^git@github\\.com:([^/]+/[^/]+?)(?:\\.git)?$')
                            def m2 = ownerRepoRe2.matcher(remoteUrl)
                            if (m2.matches()) { repoPath = m2.group(1) }
                        }
                        if (!repoPath) {
                            error("Could not parse GitHub repo path from remote URL: ${remoteUrl}")
                        }
                        def apiUrl = "https://api.github.com/repos/${repoPath}/pulls/${prNumber}"

                        // Use curl via bat so we can capture both stdout and the
                        // HTTP status code in one call.
                        // Note: no leading `@echo off` -- see comment on the
                        // `git config` call above for why.
                        def prJson = bat(returnStdout: true, script: """
                            curl -sS -w "\\n__HTTP__%{http_code}" ^
                                 -H "Authorization: Bearer %GIT_TOKEN%" ^
                                 -H "Accept: application/vnd.github+json" ^
                                 "${apiUrl}"
                        """).trim()

                        // curl prints "<json>\n__HTTP__<code>". Split it.
                        // Use Pattern.compile (not slashy strings) for safety.
                        def httpCodeRe  = java.util.regex.Pattern.compile('__HTTP__(\\d+)$')
                        def httpMatcher = httpCodeRe.matcher(prJson)
                        if (!httpMatcher.find()) {
                            error("Could not find __HTTP__ marker in curl output. Output was: ${prJson}")
                        }
                        def httpCode = httpMatcher.group(1) as Integer
                        def jsonBody = prJson.substring(0, httpMatcher.start()).trim()
                        if (httpCode != 200) {
                            error("GitHub API returned HTTP ${httpCode} for ${apiUrl}. Body: ${jsonBody}")
                        }

                        // Extract "title" and "body" from the JSON. We use
                        // Pattern.compile (not slashy strings) to avoid the
                        // character-class-in-slashy parser bug.
                        def titleRe = java.util.regex.Pattern.compile('"title"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"')
                        def titleMatcher = titleRe.matcher(jsonBody)
                        def title = titleMatcher.find() ? titleMatcher.group(1).replaceAll('\\\\"', '"') : ''
                        def bodyRe = java.util.regex.Pattern.compile('"body"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"')
                        def bodyMatcher = bodyRe.matcher(jsonBody)
                        def body  = bodyMatcher.find()
                            ? bodyMatcher.group(1)
                                .replaceAll('\\\\"', '"')
                                .replaceAll('\\\\n', '\\n')
                                .replaceAll('\\\\r', '')
                            : ''

                        echo "PR #${prNumber} title: ${title}"

                        // Combine title and body, then harvest every "key=value"
                        // pair. Lines that don't match the format are ignored.
                        def rawText = (title + "\n" + body)
                        def fieldArgs = []
                        // Use Pattern.compile (not slashy strings) for safety.
                        def pairRe = java.util.regex.Pattern.compile('^([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(.+)$')
                        rawText.split('\n').each { line ->
                            def m = pairRe.matcher(line.trim())
                            if (m.matches()) {
                                def key   = m.group(1)
                                def value = m.group(2).trim()
                                // Strip surrounding quotes if the author used them.
                                if (value.startsWith('"') && value.endsWith('"') && value.length() >= 2) {
                                    value = value.substring(1, value.length() - 1)
                                }
                                // Wrap the value in double quotes and escape any
                                // embedded `"` so cmd.exe's argument splitter hands
                                // the entire `key=value` token to Python intact --
                                // even if `value` contains spaces.
                                value = value.replace('"', '\\"')
                                fieldArgs << "--field ${key}=\"${value}\""
                            }
                        }

                        if (fieldArgs.isEmpty()) {
                            error("No 'key=value' pairs were found in PR #${prNumber}'s title or body. " +
                                  "Add lines like 'service=auth' / 'status=500' / 'latency_ms=312' to the PR description.")
                        }

                        echo "Fields to append: ${fieldArgs.join(' ')}"
                        env.CSV_FIELDS = fieldArgs.join(' ')

                        // Hand off to the Python script via cmd.exe.
                        bat """
                            python append_to_csv.py --file "${params.CSV_FILE}" %CSV_FIELDS%
                        """
                    }
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

                        rem --- Resolve the target branch.
                        rem     When triggered by a PR, push back to the PR's
                        rem     head branch so the PR sees the change. Otherwise
                        rem     push to whatever branch was checked out (or main).
                        rem     PR-specific env vars (CHANGE_BRANCH, ghprbSourceBranch)
                        rem     take precedence over BRANCH_NAME, which on multibranch
                        rem     PR builds usually points at the *target* branch.
                        set "BRANCH="
                        if defined CHANGE_BRANCH set "BRANCH=%CHANGE_BRANCH%"
                        if defined ghprbSourceBranch set "BRANCH=%ghprbSourceBranch%"
                        if "!BRANCH!"=="" if defined BRANCH_NAME set "BRANCH=%BRANCH_NAME%"
                        if "!BRANCH!"=="" set "BRANCH=main"
                        if "!BRANCH!"=="" (
                            echo ERROR: Could not determine target branch. Aborting push.
                            exit /b 1
                        )

                        rem --- Build the commit message. Use a temp file so embedded
                        rem     newlines and special characters survive intact.
                        set "MSG_FILE=%TEMP%\\csv-commit-msg.txt"
                        (
                            echo chore(data^): append row to %CSV_FILE% via PR #%PR_NUMBER%
                            echo(
                            echo Build:   %BUILD_URL%
                            echo Run id:  %BUILD_ID%
                            echo Branch:  !BRANCH!
                            echo Author:  %COMMIT_AUTHOR_NAME%
                            echo(
                            echo Fields:
                        ) > "%MSG_FILE%"
                        echo %CSV_FIELDS% >> "%MSG_FILE%"

                        git commit -F "%MSG_FILE%"
                        del "%MSG_FILE%"

                        rem --- Rewrite the remote URL to embed the token so the push
                        rem     authenticates non-interactively. The URL is scoped to
                        rem     this command block -- never persisted to .git/config.
                        rem     Split into two `set` statements so a `!` inside the
                        rem     PAT doesn't break cmd's `set` parser.
                        for /f "delims=" %%U in ('git config --get remote.origin.url') do set "REMOTE_URL=%%U"
                        call set "REMOTE_URL_NO_SCHEME=%%REMOTE_URL:https://=%%"
                        set "AUTH_URL=https://%GIT_USER%:%GIT_TOKEN%@%REMOTE_URL_NO_SCHEME%"

                        rem --- Push back to the resolved branch.
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
                    cleanWs(deleteDirs: true)
                } catch (NoSuchMethodError | MissingMethodException ignored) {
                    echo "Workspace Cleanup plugin not installed; skipping cleanWs."
                }
            }
        }
    }
}
