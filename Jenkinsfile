pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Update CSV & Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'github-credentials-id', usernameVariable: 'GITHUB_USER', passwordVariable: 'GITHUB_PAT')]) {
                    script {
                        // Use bat for Windows execution
                        bat '''
                            @echo off
                            FOR /F "tokens=*" %%i IN ('git config --get remote.origin.url') DO SET RAW_URL=%%i
                            
                            rem Clean up URL to extract repo path
                            SET REPO_URL=%RAW_URL:https://=%
                            SET REPO_URL=%REPO_URL:git@github.com:=github.com/%
                            
                            rem Reconfigure remote origin with credentials
                            git remote set-url origin "https://%GITHUB_USER%:%GITHUB_PAT%@%REPO_URL%"
                            
                            rem Run Python script
                            python append_csv.py
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                if (getContext(hudson.FilePath)) {
                    cleanWs()
                }
            }
        }
    }
}
