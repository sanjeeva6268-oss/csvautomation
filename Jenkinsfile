pipeline {
    agent any
     environment {
        // Jenkins will replace these with the secret values at runtime
        GIT_USERNAME = credentials('github-ci-username') // ID of the "username" credential
        GIT_PASSWORD = credentials('github-ci-pat')     // ID of the "password" credential
    }

    // ---------- PARAMETERS ----------
    // Users can trigger the job manually and fill these in.
    parameters {
        string(name: 'COL1', defaultValue: '', description: 'Value for column 1')
        string(name: 'COL2', defaultValue: '', description: 'Value for column 2')
        string(name: 'COL3', defaultValue: '', description: 'Value for column 3')
        string(name: 'COL4', defaultValue: '', description: 'Value for column 4')
        string(name: 'COL5', defaultValue: '', description: 'Value for column 5')
    }

    // ---------- CREDENTIALS ----------
    environment {
        // Replace these IDs with the ones you created in Jenkins.
        GIT_USERNAME = credentials('github-ci-username')
        GIT_PASSWORD = credentials('github-ci-pat')
        // Optional: Slack webhook or email config
        SLACK_WEBHOOK = credentials('slack-webhook')
    }

    // ---------- OPTIONS ----------
    options {
        timeout(time: 10, unit: 'MINUTES')
        timestamps()
        // Keep only the last 30 builds
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    stages {
        stage('Checkout') {
            steps {
                // Use the PAT in the URL so push works later.
                checkout([$class: 'GitSCM',
                          branches: [[name: '*/main']],
                          doGenerateSubmoduleConfigurations: false,
                          extensions: [
                              [$class: 'CleanBeforeCheckout'],
                              [$class: 'LocalBranch', localBranch: 'main']
                          ],
                          userRemoteConfigs: [[
                              url: "https://${env.GIT_USERNAME}:${env.GIT_PASSWORD}@github.com/your-org/your-repo.git",
                              credentialsId: '' // we already embedded creds in the URL
                          ]]
                ])
           
